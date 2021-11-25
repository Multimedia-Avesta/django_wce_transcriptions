# -*- coding: utf-8 -*-
import sys
import re
from copy import deepcopy
from lxml import etree
from transcriptions.exceptions import XMLStructureError


class YasnaWordParser(object):
    """Parse verses into tokenised witnesses."""

    def __init__(self):
        self.namespace = 'http://www.tei-c.org/ns/1.0'
        self.nsmap = {'tei': self.namespace}

    def prefix(self, tag):
        """Tag with namespace prefix."""
        return '{{{}}}{}'.format(self.namespace, tag)

    def parse_unit(self, unit, corrector_order):
        self.current_language = unit['language']
        # now if there is a foreign tag remove it and add the xml:lang to all of the words
        unit = self.extract_language_from_foreign_tags(unit)
        readings = self.get_readings_from_unit(unit, corrector_order)
        processed_readings = self.walk_readings(readings, unit)

        add = False
        for reading in processed_readings:
            if len(reading['tokens']) > 0 or 'gap_reading' in reading:
                add = True
        if add is True:
            unit['witnesses'] = processed_readings
        return unit

    def extract_language_from_foreign_tags(self, unit):
        tei = unit['tei']

        # remove linebreaks and tabs
        text = tei.replace(u'\n', u'')
        text = tei.replace(u'\t', u'')
        # no load into XML tree
        try:
            tei_element = etree.XML(text)
        except ValueError:
            tei_element = etree.XML(text.encode('utf8'))

        if len(tei_element.xpath('//tei:foreign', namespaces=self.nsmap)) > 0:
            # then we need to deal with this
            for foreign in tei_element.xpath('//tei:foreign', namespaces=self.nsmap):
                lang = foreign.get('{http://www.w3.org/XML/1998/namespace}lang', None)
                for w in foreign.xpath('.//tei:w', namespaces=self.nsmap):
                    if lang is not None:
                        w.set('{http://www.w3.org/XML/1998/namespace}lang', lang)
            for element in tei_element.xpath('//tei:foreign', namespaces=self.nsmap):
                parent = element.getparent()
                index = parent.index(element)
                for child in reversed(element.getchildren()):
                    parent.insert(index, child)
                parent.remove(element)
            unit['tei'] = etree.tounicode(tei_element)
            return unit
        else:
            # no changes required
            return unit

    def walk_readings(self, readings, unit):
        """Walk all readings."""
        processed_readings = []
        for reading in readings:
            temp = self.walk_reading(
                reading['tokens'],
                unit,
                reading['id'])
            tokens = temp[0]
            details = {'id': reading['id'],
                       'hand': reading['hand'] if 'hand' in reading else 'firsthand',
                       'hand_abbreviation': reading['hand_abbreviation'] if 'hand_abbreviation' in reading else '*',
                       'tokens': tokens}
            if len(temp) > 1:
                details['gap_reading'] = temp[1]

            processed_readings.append(details)
        return processed_readings

    def flatten_texts(self, elem, expand=True, word_spaces=False):
        """Flatten texts.

        If `expand` is True then <ex> contents are expanded
        and in <choice> expan is used rather than abbr
        """

        ignore = [self.prefix('note'), self.prefix('fw'), self.prefix('seg')]

        if not expand:
            ignore.append(self.prefix('ex'))

        result = [(elem.text or "")]
        for sel in elem:
            if word_spaces is True and sel.tag == self.prefix('w'):
                result.append(' ')
            if sel.tag not in ignore:
                if sel.tag == self.prefix('supplied'):
                    result.append('[{}]'.format(self.flatten_texts(sel)))
                elif sel.tag == self.prefix('unclear'):
                    result.append('{{{}}}'.format(self.flatten_texts(sel)))
                elif sel.tag == self.prefix('abbr'):
                    result.append('({})'.format(self.flatten_texts(sel)))
                elif sel.tag == self.prefix('gap'):
                    if sel.get('reason') == 'editorial':
                        gap_text = ''
                    elif sel.get('quantity'):
                        gap_text = '[{}]'.format(sel.get('quantity'))
                    else:
                        gap_text = '[...]'
                    result.append(gap_text)
                # NB: this will only work for the restricted use of choice as created by the MUYA OTE
                elif sel.tag == self.prefix('choice'):
                    for child in sel:
                        if expand:
                            if child.tag == self.prefix('expan'):
                                result.append(self.flatten_texts(child))
                        else:
                            if child.tag == self.prefix('abbr'):
                                result.append('({})'.format(self.flatten_texts(child)))
                else:
                    result.append(self.flatten_texts(sel))
            result.append(sel.tail or '')
        if word_spaces is True:
            result = re.sub(r'\s+', ' ', ''.join(result))
        else:
            result = re.sub(r'\s+', '', ''.join(result))
        if (result.find('][') != -1):
            result = re.sub(r'(\D)\]\[(\D)', r'\g<1>\g<2>', result)
        if (result.find('}{') != -1):
            result = re.sub(r'(\D)\}\{(\D)', r'\g<1>\g<2>', result)
        return result

    def _restructure_word_wrapping_tags(self, reading):
        """
        The OTE often wraps gaps in word tags even if they are bigger than words so I remove the w tags if they are
        there
        Remove any word tags which contains only gap with reason="abbreviatedText"
        Remove any word tags which contains only supplied tag and gap tag with reason="abbreviatedtext"
        """

        for element in reading.getchildren():
            if element.tag == self.prefix('w'):
                if len(element.getchildren()) == 1:
                    child = element.getchildren()[0]
                    if child.tag == self.prefix('gap'):
                        if child.get('reason') == 'abbreviatedText':
                            parent = element.getparent()
                            index = parent.index(element)
                            parent.insert(index, child)
                            parent.remove(element)

        for element in reading.getchildren():
            if element.tag == self.prefix('w'):
                if len(element.getchildren()) == 1:
                    child = element.getchildren()[0]
                    if child.tag == self.prefix('supplied'):
                        if len(child.getchildren()) == 1:
                            grandchild = child.getchildren()[0]
                            if grandchild.tag == self.prefix('gap'):
                                if grandchild.get('reason') == 'abbreviatedText':
                                    parent = element.getparent()
                                    index = parent.index(element)
                                    parent.insert(index, child)
                                    parent.remove(element)
        return reading

    def walk_reading(self, reading, verse, name):
        """Walk each reading and process the tokens."""
        textual_gap_units = ['chapter', 'verse', 'verseline', 'stanza', 'line']
        tokens = []
        word = None
        gap = False
        gap_only = False
        current_gap_unit = ''
        gap_details = ''
        pc_before = []
        pc_after = []
        rd_before = []
        rdt_before = []
        rd_after = []
        rdt_after = []
        counter = 2
        elems = []
        reading = self._restructure_word_wrapping_tags(reading)

        if len(reading.xpath('//tei:ab', namespaces=self.nsmap)) > 0:
            reading = reading.xpath('//tei:ab', namespaces=self.nsmap)[0]
            for element in reading.getchildren():
                if element.tag not in elems:
                    elems.append(element.tag)
                if element.tag == self.prefix('w'):
                    if gap and word:
                        word['gap_after'] = True
                        word['gap_details'] = gap_details
                    if len(pc_after) > 0:
                        word['pc_after'] = ''.join(pc_after)
                        pc_after = []
                    if len(rd_after) > 0:
                        word['rd_after'] = ' '.join(rd_after)
                        rd_after = []
                    if len(rdt_after) > 0:
                        word['rdt_after'] = ' '.join(rdt_after)
                        rdt_after = []
                    if word:
                        if word['t'] != '':
                            tokens.append(word)
                        else:
                            word = None
                            counter -= 2
                    word = {
                        'verse': reading.get('n'),
                        'index': str(counter),
                        'reading': name,
                        'siglum': verse['siglum'],
                        }
                    if element.get('subtype'):
                        word['type'] = element.get('subtype')
                    counter += 2
                    if gap and word['index'] == '2':  # only add gap before if it is the first unit
                        word['gap_before'] = True
                        word['gap_before_details'] = gap_details
                    gap_details = ''
                    current_gap_unit = ''
                    gap = False
                    if len(pc_before) > 0:
                        word['pc_before'] = ''.join(pc_before)
                        pc_before = []
                    if len(rd_before) > 0:
                        word['rd_before'] = ' '.join(rd_before)
                        rd_before = []
                    if len(rdt_before) > 0:
                        word['rdt_before'] = ' '.join(rdt_before)
                        rdt_before = []
                    if len(element.xpath('.//tei:supplied', namespaces=self.nsmap)) > 0:
                        word['supplied'] = True
                    if len(element.xpath('.//tei:unclear', namespaces=self.nsmap)) > 0:
                        word['unclear'] = True
                    if len(element.xpath('.//tei:abbr[@type="nomSac"]', namespaces=self.nsmap)) > 0:
                        word['nomSac'] = True
                    if element.get('lemma', None):
                        word['lemma'] = element.get('lemma')
                    if element.get('{http://www.w3.org/XML/1998/namespace}lang', None) is not None:
                        word['foreign'] = True
                        word['language'] = element.get('{http://www.w3.org/XML/1998/namespace}lang')

                    word_text = self.flatten_texts(element, expand=False).strip()
                    word['original'] = word_text
                    if 'lemma' in word.keys():
                        word['rule_match'] = [self.prepare_rule_match(word['lemma'])]
                    else:
                        word['rule_match'] = [self.prepare_rule_match(word_text)]
                    expanded_word = self.flatten_texts(
                        element, expand=True).strip()
                    if expanded_word != word_text:
                        word['expanded'] = expanded_word
                        word['rule_match'].append(
                            self.prepare_rule_match(expanded_word))
                    if 'lemma' in word.keys():
                        word['t'] = self.prepare_t(word['lemma'])
                    else:
                        word['t'] = self.prepare_t(expanded_word)
                elif element.tag == self.prefix('gap'):
                    if element.get('reason') and element.get('reason') != 'editorial':  # ignore editorial gaps

                        gap = True
                        # if this is the first in a series of gaps
                        # or the currently stored gap is not textual
                        # or the currently stored gap and this gap are both textual
                        if (current_gap_unit == ''
                                or current_gap_unit not in textual_gap_units
                                or (current_gap_unit in textual_gap_units
                                    and element.get('unit') in textual_gap_units)):
                            if element.get('reason') and element.get('reason').lower() == 'witnessend':
                                gap_details = 'lac witness end'
                            elif element.get('reason') and element.get('reason').lower() == 'abbreviatedtext':
                                gap_details = 'abbreviated text'
                            elif element.get('reason') and element.get('reason').lower() == 'notexpected':
                                gap_details = 'not expected'
                            elif (element.get('reason') and element.get('reason').lower() == 'lacuna'
                                    and element.get('extent')):
                                gap_details = 'lac {} {}'.format(element.get('extent'),
                                                                 element.get('unit'))
                            elif (element.get('reason') and element.get('reason').lower() == 'lacuna'
                                    and element.get('quantity')):
                                gap_details = 'lac {} {}'.format(element.get('quantity'),
                                                                 element.get('unit'))
                            elif (element.get('reason') and element.get('reason').lower() == 'illegible'
                                    and element.get('extent')):
                                gap_details = 'illegible {} {}'.format(element.get('extent'),
                                                                       element.get('unit'))
                            elif (element.get('reason') and element.get('reason').lower() == 'illegible'
                                    and element.get('quantity')):
                                gap_details = 'illegible {} {}'.format(element.get('quantity'),
                                                                       element.get('unit'))
                            elif element.get('extent'):
                                gap_details = 'gap {} {}'.format(element.get('extent'),
                                                                 element.get('unit'))
                            elif element.get('quantity'):
                                gap_details = 'gap {} {}'.format(element.get('quantity'),
                                                                 element.get('unit'))
                            else:
                                gap_details = 'gap unknown {}'.format(element.get('unit'))
                            current_gap_unit = element.get('unit')
                elif element.tag == self.prefix('supplied'):
                    if len(element.getchildren()) == 1 and element.getchildren()[0].tag == self.prefix('gap'):
                        child = element.getchildren()[0]
                        if child.get('reason') and child.get('reason').lower() == 'abbreviatedtext':
                            if (current_gap_unit == ''
                                    or current_gap_unit not in textual_gap_units
                                    or (current_gap_unit in textual_gap_units
                                        and element.get('unit') in textual_gap_units)):
                                gap = True
                                gap_details = 'supplied abbreviated text'
                                current_gap_unit = element.get('unit')

                elif element.tag == self.prefix('pc'):
                    if not word:
                        pc_before.append(self.flatten_texts(element).strip())
                    else:
                        pc_after.append(self.flatten_texts(element).strip())
                elif element.tag == self.prefix('note') and element.get('type') == 'moved_ritual_direction':
                    if not word:
                        rd_before.append(self.flatten_texts(element, word_spaces=True).strip())
                        rd_transcriptions = element.xpath('.//tei:note[@type="transcriptionRD"]',
                                                          namespaces=self.nsmap)
                        if len(rd_transcriptions) > 0:
                            # there should only be one but lets get all of them just in case
                            for rdt in rd_transcriptions:
                                rdt_before.append(rdt.text)
                    else:
                        rd_after.append(self.flatten_texts(element, word_spaces=True).strip())
                        rd_transcriptions = element.xpath('.//tei:note[@type="transcriptionRD"]',
                                                          namespaces=self.nsmap)
                        if len(rd_transcriptions) > 0:
                            # there should only be one but lets get all of them just in case
                            for rdt in rd_transcriptions:
                                rdt_after.append(rdt.text)
                elif element.tag == self.prefix('space'):
                    if not word:
                        pc_before.append('<space of {} {}>'.format(element.get('unit'),
                                                                   element.get('quantity')))
                    else:
                        pc_after.append('<space of {} {}>'.format(element.get('unit'),
                                                                  element.get('quantity')))

            if gap and word:
                word['gap_after'] = True
                word['gap_details'] = gap_details
            elif gap:
                gap_only = True
            if word:
                if len(pc_before) > 0:
                    word['pc_before'] = ''.join(pc_before)
                if len(pc_after) > 0:
                    word['pc_after'] = ''.join(pc_after)
                if len(rd_before) > 0:
                    word['rd_before'] = ' '.join(rd_before)
                if len(rdt_before) > 0:
                    word['rdt_before'] = ' '.join(rdt_before)
                if len(rd_after) > 0:
                    word['rd_after'] = ' '.join(rd_after)
                if len(rdt_after) > 0:
                    word['rdt_after'] = ' '.join(rdt_after)
                if word and word['t'] != '':
                    tokens.append(word)
            if not word and (len(rd_before) > 0 or len(rd_after) > 0):
                pass

        if gap_only:
            return [tokens, gap_details]
        else:
            return [tokens]

    def prepare_rule_match(self, data):
        """Prepare the rule match by making lowercase."""
        return data.lower()

    def prepare_t(self, data):
        """prepare the t token by removing various unwanted things
        and lowercasing"""
        data = data.replace('[', '').replace(']', '')
        data = data.replace('{', '').replace('}', '')
        data = data.replace('(', '').replace(')', '')
        return data.lower()

    def get_hand_for_reading(self, reading, siglum):
        temp = reading.split('_')
        reading_hand = temp[1]
        reading_type = temp[0]
        if reading_type == 'orig':
            return [siglum, '*']
        if reading_type == 'alt':
            return [siglum, 'A{}'.format(self.get_corrector_hand(reading_hand, reading_type))]
        if reading_type == 'altZ':
            return [siglum, 'Z']
        if reading_type == 'corr':
            return [siglum, self.get_corrector_hand(reading_hand, reading_type)]
        if reading_type == 'gloss':
            return [siglum, 'G']
        # this should never happen but will
        # highlight things that are not being dealt with
        return [siglum, '-{}-{}'.format(reading_type, reading_hand)]

    def get_corrector_hand(self, hand_name, reading_type):
        if hand_name == 'firsthand':
            if reading_type == 'alt':
                return '*'
            return 'C*'
        elif hand_name == 'corrector' or hand_name == 'unspecified':
            return 'C'
        else:
            return hand_name.replace('corrector', 'C')

    # app tags have been used in the OTE with little regard to the XML structure and therefore we have to deal with a
    # lot of embedding but we need to careful how to handle these. App tags embedded in App tags will not get this far
    # as they make no sense and so are flagged as part of validation.
    def fix_embedded_app_tags(self, tei_element):
        apps = tei_element.xpath('.//tei:app', namespaces=self.nsmap)
        for app in apps:
            parent = app.getparent()
            if (parent.tag == self.prefix('fw') or
                    len(parent.xpath('./ancestor::tei:fw', namespaces=self.nsmap)) > 0):
                # then we don't need to worry about this as the fw data is not to be collated
                pass

            elif parent.tag != self.prefix('ab'):
                # then we have an app tag which is embedded in something else and it needs to be dealt with

                if parent.getparent().tag != self.prefix('ab'):
                    if (parent.tag in [self.prefix('hi'), self.prefix('supplied')] and
                            parent.getparent().tag == self.prefix('w')):
                        # then this is probably a <w><supplied><app> type thing so we will
                        # delete the <w> (because it makes no sense) and sort out the rest with the regular function
                        word = parent.getparent()
                        word_parent = word.getparent()
                        index = word_parent.index(word)
                        word_parent.insert(index, parent)
                        word_parent.remove(word)
                        tei_element = self.do_fix_embedded_app_tags(app, tei_element)
                    else:
                        message = ('There is a problem with the level of embedding of the app tag in the following '
                                   'unit: {}. The grandparent of the app tag is {}. This must be fixed in the XML '
                                   'before the transcription can be uploaded.'.format(etree.tostring(tei_element),
                                                                                      parent.getparent().tag))
                        raise XMLStructureError(message)
                else:
                    tei_element = self.do_fix_embedded_app_tags(app, tei_element)

        return tei_element

    def do_fix_embedded_app_tags(self, app, tei_element):
        parent = app.getparent()

        index = tei_element.index(parent)
        for word in app.xpath('.//tei:w', namespaces=self.nsmap):
            new_elem = etree.Element(parent.tag)
            for att in parent.attrib:
                new_elem.set(att, parent.attrib[att])
            if word.text is not None:
                new_elem.text = word.text
                word.text = None
            for child in word.iterchildren():
                new_elem.append(child)
            word.append(new_elem)
        tei_element.insert(index, app)
        if app.tail is not None:
            # If the app tag had a tail then raise an error because the XML needs to be fixed.
            raise XMLStructureError('There is an app tag in this transcription which has a tail and this '
                                    'needs to be fixed. The tail reads "{}"'.format(app.tail))

        tei_element.remove(parent)
        return tei_element

    def get_readings_from_unit(self, unit, corrector_order):
        # Remove linebreaks and tabs
        tei = unit['tei']
        text = tei.replace(u'\n', u'').replace(u'\t', u'')
        try:
            tei_element = etree.XML(text)
        except ValueError:
            tei_element = etree.XML(text.encode('utf8'))
        # Here fix any app tags that are not direct children of ab
        if (len(tei_element.findall(self.prefix('app'))) !=
                len(tei_element.xpath('.//tei:app', namespaces=self.nsmap))):
            tei_element = self.fix_embedded_app_tags(tei_element)

        # If there are app tags (without fw ancestors), split them into readings if not just return the tei_element
        app_tags = tei_element.xpath('.//tei:app[not(ancestor::tei:fw)]', namespaces=self.nsmap)
        if len(app_tags) == 0:
            try:
                return [{"id": unit['siglum'],
                         'tokens': tei_element}]
            except KeyError as e:
                message = ('There was a problem parsing the following unit {}'.format(unit))
                raise DataParsingError(message) from e

        else:
            # start by collecting all the hands (by type) in the element and then get the unique set
            hands = []
            for rdg in tei_element.xpath('.//tei:rdg', namespaces=self.nsmap):
                hand = '{}_{}'.format(rdg.get('type'), rdg.get('hand'))
                rdg.set('siglum', hand)
                hands.append(hand)
            hands = list(set(hands))
            compiled_readings = {}
            for z, app in enumerate(app_tags):
                # Pull out the readings
                # For each reading:
                # replace the whole app tag with the contents of the reading (removing positional correction segs)
                # name each reading according to the hand
                readings = app.findall(self.prefix('rdg'))
                for hand in hands:
                    found = False
                    if hand in compiled_readings:
                        compiled_reading = compiled_readings[hand]
                    else:
                        compiled_reading = deepcopy(tei_element)
                    try:
                        app_tag = compiled_reading.xpath('//tei:app[not(ancestor::tei:fw)]',
                                                         namespaces=self.nsmap)[z]
                    except IndexError:
                        pass
                    else:
                        app_index = compiled_reading.index(app_tag)
                        readings = app.findall(self.prefix('rdg'))
                        try:
                            i = corrector_order.index(hand)
                        except ValueError:
                            i = -1
                        while i >= 0 and found is False:
                            for reading in readings:
                                if (reading.get('siglum') == corrector_order[i]
                                        and (corrector_order[i].split('_')[0] != 'alt'
                                             or hand == corrector_order[i])):
                                    match = reading
                                    found = True
                                    break
                            i -= 1
                        if found is True:  # then we have the reading of the hand we are in
                            # if there is only 1 child and it is a seg use its children
                            if (len(match.getchildren()) == 1
                                    and len(match.xpath('./tei:seg', namespaces=self.nsmap)) > 0):
                                newmatch = match.xpath('./tei:seg', namespaces=self.nsmap)[0]
                                for i, child in enumerate(newmatch.getchildren()):
                                    app_tag.getparent().insert(app_index + 1 + i, deepcopy(child))
                            else:
                                for i, child in enumerate(match.getchildren()):
                                    app_tag.getparent().insert(app_index + 1 + i, deepcopy(child))

                        else:
                            reading = app_tag.xpath('.//tei:rdg[@type="orig"]', namespaces=self.nsmap)
                            if len(reading) > 0:
                                for i, child in enumerate(reading[0].getchildren()):
                                    app_tag.getparent().insert(app_index + 1 + i, deepcopy(child))

                        compiled_readings[hand] = compiled_reading
            for hand in compiled_readings.keys():
                apps = compiled_readings[hand].xpath('//tei:app[not(ancestor::tei:fw)]', namespaces=self.nsmap)
                for app in apps:
                    app.getparent().remove(app)

            return [{"id": ''.join(self.get_hand_for_reading(identifier, unit['siglum'])),
                     'hand': identifier.split('_')[1],
                     'hand_abbreviation': self.get_hand_for_reading(identifier, unit['siglum'])[1],
                     'tokens': tokens} for
                    identifier, tokens in compiled_readings.items()]
