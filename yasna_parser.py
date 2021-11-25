"""Parse TEI transcription file.

Parses documents created using MUYA XML transcription schema"""

import re
import os
import io
import json
from copy import deepcopy
from lxml import etree
from transcriptions.yasna_word_parser import YasnaWordParser as WordParser
from transcriptions.exceptions import XMLStructureError


class YasnaParser(object):
    """Parse a TEI file."""
    def __init__(self, file_string, filename=None, collection='', debug=False,
                 manuscript_id=None, siglum=None, languages=['ae'],
                 lang=None, private=True, user_id=None):

        # parse the file_string into a tree and get the root
        if file_string is None:
            raise ValueError('file_string provided was None')
        else:
            try:
                self.tree = etree.parse(io.BytesIO(file_string))
            except etree.XMLSyntaxError as e:
                raise e
            except TypeError:
                try:
                    self.tree = etree.parse(io.StringIO(file_string))
                except etree.XMLSyntaxError as e:
                    raise e
                except Exception:
                    raise
        self.root = self.tree.getroot()
        self.file_string = file_string

        # set namespace details (required for functions called below)
        self.nsmap = self._check_for_namespace()
        if 'tei' in self.nsmap:
            self.default_ns = 'tei'
        else:
            self.default_ns = None

        # set other simple features
        self.private = private
        self._debug = debug
        self.user_id = user_id
        self.collection = collection

        if filename is not None:
            self.source = filename
        else:
            self.source = 'Web Upload'

        self.siglum = self._get_siglum(siglum)
        self.work = self._get_work()
        self.document_id = self._get_id(manuscript_id)
        try:
            self.main_lang = self._get_main_lang(lang)
        except IndexError:
            self.main_lang = 'ae'
        self.languages = languages
        # establish if we need to get ritualdirections from this transcription
        self.collect_ritual_directions = False
        ritual_direction_siglum = 'basetext'
        if self.siglum == ritual_direction_siglum:
            self.collect_ritual_directions = True

    def _get_siglum(self, siglum):
        """Get Siglum for apparatus, if the user did not supply one
        the siglum is the n attribute on the title element
        with @type = document.
        """
        if siglum:
            return siglum
        return self.root.xpath('.//tei:title[@type="document"]/@n', namespaces=self.nsmap)[0]

    def _get_work(self):
        """Get the ceremony based on the numerical range of the Siglum
        """
        if self.siglum == 'basetext':
            return 'Y'
        try:
            numerical_siglum = int(self.siglum)
        except ValueError:
            # it might be a supplement and end with S
            try:
                numerical_siglum = int(self.siglum[:-1])
            except ValueError:
                try:
                    numerical_siglum = int(self.siglum[:-2])
                except ValueError:
                    return None

        if numerical_siglum < 300:
            return 'Y'
        if numerical_siglum < 400:
            return 'YiR'
        if numerical_siglum >= 400 and numerical_siglum < 2000:
            return 'Y'
        if numerical_siglum >= 2000 and numerical_siglum < 2500:
            return 'VrS'
        if numerical_siglum >= 4000 and numerical_siglum < 4600:
            return 'VS'
        if numerical_siglum >= 5000 and numerical_siglum < 5300:
            return 'VytS'
        return None

    def _get_id(self, manuscript_id):
        """Get document id.

        The doc id is the key attribute on the title element with
        the type attribute document. If there isn't one it defaults to n attribute

        """
        if manuscript_id:
            return manuscript_id
        try:
            return self.root.xpath('.//tei:title[@type="document"]/@key', namespaces=self.nsmap)[0]
        except IndexError:
            return self.root.xpath('.//tei:title[@type="document"]/@n', namespaces=self.nsmap)[0]

    def _get_main_lang(self, lang):
        """Get an element from a page number string."""
        if lang:
            return lang
        return self.root.xpath('.//tei:text/@xml:lang', namespaces=self.nsmap)[0].lower()

    def _check_for_namespace(self):
        """If there is an unnamed default namespace,
        call it tei."""
        nsmap = self.root.nsmap
        if None in nsmap:
            nsmap['tei'] = nsmap.pop(None)
        return nsmap

    def get_transcription(self):
        """Make dictionary of data for transcription object."""
        chapters = list(set(self.root.xpath('.//tei:div[@type="chapter"]/@n', namespaces=self.nsmap)))
        chapters = [int(x.split('.')[1])for x in chapters]
        chapters.sort()

        if len(chapters) == 1:
            self.chapter_range = 'Y{}'.format(chapters[0])
        elif len(chapters) == 0:
            self.chapter_range = ''
        else:
            self.chapter_range = 'Y{}-Y{}'.format(chapters[0], chapters[-1])

        correctors = None
        if len(self.root.xpath('.//tei:listWit/tei:witness', namespaces=self.nsmap)) > 0:
            id_string = '{http://www.w3.org/XML/1998/namespace}id'
            correctors = [wit.get(id_string) for wit in self.root.xpath('.//tei:listWit/tei:witness',
                                                                        namespaces=self.nsmap)]

        # we make this for transcription and then overwrite if needed for private_transcription
        transcription = {
            'identifier': '{}_{}_{}'.format(self.collection, self.siglum, self.chapter_range),
            'collection': self.collection,
            'document_id': self.document_id,
            'tei': self.file_string,
            'source': self.source,
            'siglum': self.siglum,
            'work': self.work,
            'main_language': self.main_lang
            }
        # if this is a basetext and main language is not Avestan
        # add a capitalised first letter of main language before the Y
        if self.siglum == 'basetext' and self.main_lang != 'ae':
            transcription['identifier'] = '{}_{}_{}{}'.format(self.collection,  self.siglum,
                                                              self.main_lang[0].upper(), self.chapter_range)
        if correctors is not None:
            transcription['corrector_order'] = correctors

        # In some projects we would remove the user_id from public transcriptions
        # but in this case we need to make sure people cannot override others basetexts
        # so the public flag is set accordingly but the user_id reference and its position
        # in the identifier are kept.
        transcription['identifier'] = '{}_{}'.format(transcription['identifier'], self.user_id)
        transcription['user_id'] = self.user_id

        if self.private:
            transcription['public'] = False
        else:
            transcription['public'] = True

        self.transcription_id = transcription['identifier']  # used for adding to other models later
        return transcription

    def get_unit_details(self, ab_element, context_info, language):
        units = []
        unit_info = {'tei': etree.tounicode(ab_element),
                     'document_id': self.document_id,
                     }
        matcher = r'(?P<work>\w+).(?P<chapter_number>\d+).(?P<stanza_number>\d+).(?P<line_number>\d+)'
        match_object = re.match(matcher, context_info)
        try:
            info_dict = match_object.groupdict()
        except AttributeError as e:
            message = ('The ab element does not have correctly formatted content in the n attribute.'
                       'Value = {}'.format(context_info))
            raise XMLStructureError(message) from e

        unit_info['chapter_number'] = int(info_dict['chapter_number'])
        unit_info['stanza_number'] = int(info_dict['stanza_number'])
        unit_info['line_number'] = int(info_dict['line_number'])
        unit_info['context'] = context_info
        unit_info['reference'] = ab_element.get('n')

        unit_info['transcription_identifier'] = self.transcription_id
        unit_info['transcription_siglum'] = self.siglum
        unit_info['siglum'] = self.siglum

        # In some projects we would remove the user_id from public transcriptions
        # but in this case we need to make sure people cannot override others basetexts
        # so the public flag is set accordingly but the user_id reference and its position
        # in the identifier are kept.
        unit_info['user_id'] = self.user_id

        if self.private:
            unit_info['public'] = False
        else:
            unit_info['public'] = True

        # for language in languages:
        real_unit = deepcopy(unit_info)
        real_unit['language'] = language
        real_unit['identifier'] = '{}_{}_{}_{}'.format(self.collection,
                                                       language.upper(),
                                                       self.siglum,
                                                       real_unit['context'])
        real_unit['identifier'] = '{}_{}'.format(real_unit['identifier'], self.user_id)
        units.append(real_unit)
        return units

    def join_elements(self, ab_list):
        if len(ab_list) == 1:
            return ab_list[0]
        base_ab = ab_list[0]
        for index, ab in enumerate(ab_list[1:]):
            for child in ab.getchildren():
                base_ab.append(child)
        try:
            del base_ab.attrib['part']
        except KeyError:
            pass
        return base_ab

    # A special version which adds the subtype of the ab to word w for later use
    def join_tr_com_elements(self, ab_list):
        for ab in ab_list:
            if ab.get('subtype') is not None:
                subtype = ab.get('subtype')
                for target in ab.xpath('.//*[self::tei:w or self::tei:pc]',
                                       namespaces={'tei': 'http://www.tei-c.org/ns/1.0'}):
                    target.set('subtype', subtype)
                del ab.attrib['subtype']

        return self.join_elements(ab_list)

    def add_ritual_direction_note(self, ab, rds, location):
        note = etree.Element('note')
        note.set('type', 'moved_ritual_direction')
        for rd in rds:
            for child in rd:
                note.append(child)
        if location == 'start':
            ab.insert(0, note)
        else:
            ab.append(note)
        return

    def reorganise_ritual_directions(self):
        # In here turn ritual direction abs into something that can be processed with the <w> tags so maybe
        # put note after the last word in the ab_element (even parts) if the next sibling/s are ritual direction
        # until we hit our next ab[@type="line" or @type="verseline"]
        # use stanza/verse as the limit so that we always add within the same stanza/verse
        for stanza in self.tree.xpath('//tei:div[@type="stanza" or @type="verse"]',
                                      namespaces={'tei': 'http://www.tei-c.org/ns/1.0'}):
            waiting_ritual_directions = []
            previous_line = None
            next_line = None
            for child in stanza.getchildren():
                if child.tag == ('{http://www.tei-c.org/ns/1.0}ab'):
                    if child.get('type') == 'line' or child.get('type') == 'verseline':
                        if len(waiting_ritual_directions) == 0:
                            previous_line = child
                        else:
                            next_line = child
                            # now we are at a point where we have ritual directions and we have at least one
                            # ab we can put them in (maybe two)
                            if previous_line is None:
                                # then they have to go at the beginning of the next line
                                self.add_ritual_direction_note(next_line, waiting_ritual_directions, 'start')
                            else:
                                self.add_ritual_direction_note(previous_line, waiting_ritual_directions, 'end')
                            # clear the stored data
                            waiting_ritual_directions = []
                            previous_line = next_line
                            next_line = None
                    elif child.get('type') == 'ritualdirection':
                        waiting_ritual_directions.append(child)
                    else:
                        pass
                else:
                    try:
                        message = 'There is an unexpected XML element in the stanza/verse {}'.format(stanza.get('n'))
                    except Exception:
                        message = 'There is an unexpected XML element in one of the stanzas/verses'
                    raise XMLStructureError(message)
            # check if anything is left in waiting_ritual_directions and add them to the end of the last line if so
            if len(waiting_ritual_directions) > 0:
                self.add_ritual_direction_note(previous_line, waiting_ritual_directions, 'end')
        return

    def get_all_collation_units(self, language):
        """Get info about collation units from TEI."""
        if self.collect_ritual_directions is True:
            self.reorganise_ritual_directions()

        if language == self.main_lang:
            ab_elements = self.tree.xpath('//tei:ab[@type="line" or @type="verseline"]'
                                          '[not(@xml:lang) or @xml:lang="{}"]'.format(language),
                                          namespaces={'tei': 'http://www.tei-c.org/ns/1.0'})
        else:
            # get all the collation units
            ab_elements = self.tree.xpath('//tei:ab[@type="line" or @type="verseline"]'
                                          '[@xml:lang="{}"]'.format(language),
                                          namespaces={'tei': 'http://www.tei-c.org/ns/1.0'})

        units = []
        index = 0
        for position, ab_element in enumerate(ab_elements):
            # basic context data - should never need to be overwritten
            unit_info = {'index': index}
            parent = ab_element.getparent()
            context = ab_element.get('n')

            # Avestan is treated in a different way to other languages and the part attributes can be used to ensure
            # that the units are complete and correctly joined.
            # This is not possible for other languages as the translation and commentary subtypes are transcribed
            # separately each using their own part attributes but need to be extracted for collation in transcription
            # order ignoring what kind of subtype them belong to. Sometimes there will only be one of the subtypes
            # present so we need lots more flexibility while keeping some of the safety of the part attributes. Also
            # one of the subtypes may be in parts and the other not so we cannot rely on the presence of the part
            # attribute for the special treatment.

            if language == 'ae':
                if ab_element.get('part'):
                    if ab_element.get('part') == 'I':
                        to_join = [ab_element]
                        n = ab_element.get('n')
                        i = position
                        looking = True
                        while looking and i+1 < len(ab_elements):
                            if ab_elements[i+1].get('n') != n:
                                looking = False
                            elif ab_elements[i+1].get('part') == 'F':
                                to_join.append(ab_elements[i+1])
                                looking = False
                            elif not ab_elements[i+1].get('part'):
                                looking = False
                            else:
                                to_join.append(ab_elements[i+1])
                            i += 1
                        unit_details = self.get_unit_details(self.join_elements(to_join), context, language)
                    else:
                        continue
                else:
                    unit_details = self.get_unit_details(ab_element, context, language)
                index += 1
            else:
                # specifying the subtypes to be extracted in case they change
                subtypes = ['translation', 'commentary']
                if ab_element.get('subtype') in subtypes and ab_element.get('done') is None:
                    to_join = [ab_element]
                    n = ab_element.get('n')
                    subtype = ab_element.get('subtype')
                    # keep track of which subtypes have parts
                    need_final = []
                    if ab_element.get('part') == 'I':
                        need_final.append(subtype)
                    i = position
                    looking = True
                    while looking and i+1 < len(ab_elements):
                        subtype = ab_elements[i+1].get('subtype')
                        if ab_elements[i+1].get('n') != n:
                            looking = False
                        elif ab_elements[i+1].get('part') == 'I':
                            ab_elements[i+1].set('done', 'true')
                            to_join.append(ab_elements[i+1])
                            need_final.append(subtype)
                        elif ab_elements[i+1].get('part') == 'F':
                            ab_elements[i+1].set('done', 'true')
                            to_join.append(ab_elements[i+1])
                            try:
                                need_final.remove(subtype)
                            except ValueError:
                                print('The XML is not correct but so many of the examples provided weren\'t we are '
                                      'just carrying on and pretending it is all okay')
                        else:
                            ab_elements[i+1].set('done', 'true')
                            to_join.append(ab_elements[i+1])
                        i += 1
                    unit_details = self.get_unit_details(self.join_tr_com_elements(to_join), context, language)
                    index += 1
                else:
                    continue
            # loop here
            for unit in unit_details:
                if unit is None:
                    continue
                else:
                    real_unit_info = deepcopy(unit_info)
                    real_unit_info.update(unit)
                units.append(real_unit_info)
        # check for duplicates
        units = self.check_duplicate_units(units)
        return units

    def check_duplicate_units(self, units):
        multiple_counts = {}
        processed_unit_ids = []
        for unit in units:
            if unit['identifier'] in processed_unit_ids:
                if unit['identifier'] in multiple_counts.keys():
                    multiple_counts[unit['identifier']] += 1
                else:
                    multiple_counts[unit['identifier']] = 2

                unit['siglum'] = '{}-{}'.format(self.siglum, multiple_counts[unit['identifier']])
                unit['duplicate_position'] = multiple_counts[unit['identifier']]
                unit['identifier'] = '{}_{}_{}-{}_{}_{}'.format(self.collection,
                                                                unit['language'].upper(),
                                                                self.siglum,
                                                                multiple_counts[unit['identifier']],
                                                                unit['context'],
                                                                self.user_id)
            processed_unit_ids.append(unit['identifier'])

        # now check whether we need to add -1 to any of the sigla
        if len(multiple_counts.keys()) > 0:
            for i, unit in enumerate(units):
                if unit['identifier'] in multiple_counts.keys():
                    unit['identifier'] = '{}_{}_{}-1_{}_{}'.format(self.collection,
                                                                   unit['language'].upper(),
                                                                   self.siglum,
                                                                   unit['context'],
                                                                   self.user_id)
                    unit['siglum'] = '{}-1'.format(unit['siglum'])
                    unit['duplicate_position'] = 1
        return units

    def _get_unique_units(self, units):
        references = []
        for unit in units:
            references.append(unit['reference'])
        return len(set(references))

    def get_data_online(self):
        """Get all manuscript data."""
        data = {}
        data['transcription'] = self.get_transcription()

        all_units = {}
        for language in self.languages:

            units = self.get_all_collation_units(language)

            corrector_order = None
            if 'corrector_order' in data['transcription']:
                corrector_order = self.doctor_corrector_order(data['transcription']['corrector_order'])

            word_parser = WordParser()
            for unit in units:
                unit = word_parser.parse_unit(unit, corrector_order)

            all_units[language] = units

        data['collation_units'] = all_units
        return data

    # adds in alt hands which is a specific way of doing things for the ECM but at least using
    # it here will be a starting point
    def doctor_corrector_order(self, corrector_order):
        new_corrector_order = []
        for hand in corrector_order:
            if hand == 'firsthand':
                new_corrector_order.extend(['orig_firsthand', 'corr_firsthand', 'alt_firsthand'])
            elif hand == 'glossator':
                new_corrector_order.extend(['gloss_{}'.format(hand)])
            else:
                new_corrector_order.extend(['corr_{}'.format(hand), 'alt_{}'.format(hand)])
        return new_corrector_order
