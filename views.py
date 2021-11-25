import re
import os
import base64
import json
from lxml import etree
from celery.result import AsyncResult
from django.shortcuts import render, get_object_or_404
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required, permission_required
from django.conf import settings
from django.http import HttpResponse, JsonResponse, HttpResponseRedirect
from django.urls import reverse
from django.forms import modelformset_factory as formset_factory
from django.db.models import Q
from rest_framework.request import Request

import api.views
from transcriptions import models, tasks


def get_login_status(request):
    if request.user.is_authenticated:
        return request.user.username
    else:
        return None


def process_validation_errors(log):
    errors = []
    for i in range(0, len(log)):
        error = str(log[i])
        error = error.replace('<string>:', 'Error in line ')
        error = error.replace('{http://www.tei-c.org/ns/1.0}', '')
        error = error.replace('0:ERROR:SCHEMASV:SCHEMAV_ELEMENT_CONTENT:', '')
        errors.append(error)
    return errors


def sort_by_sigla(item):
    if item.siglum == 'basetext':
        return -1
    try:
        return float(item.siglum)
    except ValueError:
        match = re.match(r'^(\d+)S(\d?)$', item.siglum)
        if match is not None:
            siglum = float(match.group(1)) + 0.1
            if match.group(2) != '':
                siglum += float(match.group(2))/100
            return siglum
    return item.siglum


def home(request):

    post_login_url = request.path + '?' + request.GET.urlencode()
    login_details = get_login_status(request)

    if login_details is not None:
        return HttpResponseRedirect('/transcriptions/manage')

    data = {
            'login_status': login_details,
            'post_login_url': post_login_url,
            'post_logout_url': '/transcriptions'
        }
    data['page_title'] = 'Transcription Home Page'
    return render(request, 'transcriptions/home.html', data)


@login_required
@permission_required(['transcriptions.delete_transcription',
                      'transcriptions.delete_collationunit',
                      'transcriptions.change_transcription',
                      'transcriptions.change_collationunit',
                      'transcriptions.add_transcription',
                      'transcriptions.add_collationunit',
                      ], raise_exception=True)
def manage(request):

    if 'task' in request.GET:
        post_login_url = request.path + '?' + request.GET.urlencode()
        login_details = get_login_status(request)
        task = AsyncResult(request.GET.get('task'))
        siglum = request.GET.get('siglum')
        data = {'siglum': siglum,
                'result': task.result,
                'state': task.state,
                'task_id': task.task_id
                }
        return JsonResponse(data)

    post_login_url = request.path + '?' + request.GET.urlencode()
    login_details = get_login_status(request)

    transcriptions = models.Transcription.objects.filter(user__id=request.user.id)
    # sort them for the list display
    transcription_list = []
    for transcription in transcriptions:
        transcription_list.append(transcription)
    transcription_list.sort(key=sort_by_sigla)

    data = {'login_status': login_details,
            'post_login_url': post_login_url,
            'post_logout_url': '/transcriptions',
            'page_title': 'Transcription Uploader',
            'transcriptions': transcription_list
            }
    return render(request, 'transcriptions/manage.html', data)


# validation function
def validate_xml(tree, filename, skip_schema=False):

    results = {}
    if not skip_schema:
        # first check with the schema unless instructed to skip
        schema_directory = os.path.join(settings.BASE_DIR, 'transcriptions', 'schema')
        schema = etree.XMLSchema(etree.parse(os.path.join(schema_directory, 'TEI-MUYA.xsd')))

        result = schema.validate(tree)
        log = schema.error_log

        if result is False:
            results['valid'] = False
            results['errors'] = process_validation_errors(log)
            results['filename'] = filename
        else:
            results['valid'] = True
            results['errors'] = []
            results['filename'] = filename
    else:
        results['valid'] = True
        results['errors'] = ['The file has not been validated against the schema.']
        results['filename'] = filename

    # check that all hands are included in the header
    declared_hands = tree.xpath('//tei:listWit/tei:witness/@xml:id',
                                namespaces={'tei': 'http://www.tei-c.org/ns/1.0',
                                            'xml': 'http://www.w3.org/XML/1998/namespace'})
    declared_hands = set(declared_hands)
    hands = tree.xpath('//tei:rdg/@hand', namespaces={'tei': 'http://www.tei-c.org/ns/1.0'})

    unique_hands = set(hands)
    missing_hands = unique_hands - declared_hands
    if len(missing_hands) > 0:
        results['valid'] = False
        results['errors'].insert(0, 'There are hands in this transcription which have not been declared in the '
                                 'header. The missing hands are: %s.' % ', '.join(missing_hands))

    # is there a sigla and is it acceptable
    titles = tree.xpath('//tei:title[@type="document"]/@n', namespaces={'tei': 'http://www.tei-c.org/ns/1.0'})
    try:
        siglum = titles[0]
    except IndexError:
        results['valid'] = False
        results['errors'].insert(0, 'No siglum provided in the transcription. '
                                 'The siglum should be at //tei:title[@type="document"]/@n')
    else:
        # TODO: this is perhaps better as a regex but it needs to work in partnership with the filtering of Supplements
        # in the output so I am restricting here until I know how that will work.
        if len(siglum) > 1 and siglum.rfind('S') == len(siglum) - 1:
            vsiglum = siglum[:-1]
        elif len(siglum) > 1 and siglum.rfind('S1') == len(siglum) - 2:
            vsiglum = siglum[:-2]
        elif len(siglum) > 1 and siglum.rfind('S2') == len(siglum) - 2:
            vsiglum = siglum[:-2]
        else:
            vsiglum = siglum
        if vsiglum != 'basetext' and not vsiglum.isdigit():
            results['valid'] = False
            results['errors'].insert(0, 'The siglum provided in the transcription (%s) does not comply with the '
                                     'project conventions. It should be "basetext" or a numerical identifier '
                                     '(possibly followed by S, S1 or S2).' % siglum)

    # embedded app tags (it happens and is valid TEI but makes no sense in the context of these transcriptions)
    if len(tree.xpath('//tei:app//tei:app', namespaces={'tei': 'http://www.tei-c.org/ns/1.0'})) > 0:
        results['valid'] = False
        results['errors'].insert(0, 'The transcription contains an app tag embedded in another app tag.'
                                 'This cannot be indexed for collation and should be fixed.')
    return results


@require_http_methods(["POST"])
def validate(request):
    filename = request.POST.get('file_name', None)
    skip_schema = request.POST.get('skip_schema', False)
    base64file = request.POST.get('src', None)
    if base64file is not None:
        meta, content = base64file.split(',', 1)
        ext_m = re.match("data:.*?/(.*?);base64", meta)
        if not ext_m:
            raise ValueError("Can't parse base64 file data ({})".format(meta))
        real_content = base64.b64decode(content)
    else:
        real_content = request.POST.get('xml', None)
        real_content = unquote(real_content)
    try:
        tree = etree.fromstring(real_content)
    except lxml.etree.XMLSyntaxError:
        return HttpResponse('the file was not well formed xml', status=415)

    # now validate against our schema
    results = validate_xml(tree, filename, skip_schema)

    return JsonResponse(results)


@ensure_csrf_cookie
@require_http_methods(["POST"])
@permission_required(['transcriptions.delete_transcription',
                      'transcriptions.delete_collationunit',
                      'transcriptions.change_transcription',
                      'transcriptions.change_collationunit',
                      'transcriptions.add_transcription',
                      'transcriptions.add_collationunit',
                      ], raise_exception=True)
def index(request):
    filename = request.POST.get('file_name', None)
    project_id = request.POST.get('project_id', None)
    transcription_id = request.POST.get('transcription_id', None)
    base64file = request.POST.get('src', None)
    skip_schema = request.POST.get('skip_schema', False)
    languages = []
    for key in request.POST:
        if key.find('language') == 0 and request.POST.get(key) != '':
            languages.append(request.POST.get(key))

    if base64file is not None:
        meta, content = base64file.split(',', 1)
        ext_m = re.match("data:.*?/(.*?);base64", meta)
        if not ext_m:
            raise ValueError("Can't parse base64 file data ({})".format(meta))
        xml_string = base64.b64decode(content)
    else:
        xml_string = self.get_argument('xml', None)
        xml_string = unquote(xml_string)
    try:
        tree = etree.fromstring(xml_string)
    except lxml.etree.XMLSyntaxError:
        return HttpResponse('the file was not well formed xml', status=415)

    # now validate against our schema
    results = validate_xml(tree, filename, skip_schema)
    if results['valid'] is False:
        return HttpResponse('the file did not validate (use the validate option for more detail)', status=415)

    # else we have a valid XML file so we can continue to indexing
    collection = request.POST.get('collection', 'unknown')
    username = request.user.id
    siglum = tree.xpath('//tei:title[@type="document"]/@n', namespaces={'tei': 'http://www.tei-c.org/ns/1.0'})[0]
    if siglum == 'basetext':
        public_flag = True
    else:
        public_flag = False

    # remove the encoding declaration because etree parser does not support it
    # (to do that it needs to be turned from bytes to string)
    xml_string = re.sub(r'<\?xml.+?\?>', '', xml_string.decode('utf-8'))
    # now we are allowed to start the indexing
    task = tasks.index_transcription.delay(xml_string,
                                           collection,
                                           siglum=siglum,
                                           username=username,
                                           public_flag=public_flag,
                                           languages=languages)

    return HttpResponseRedirect('/transcriptions/manage?task=' + task.task_id + '&siglum=' + siglum)


@login_required
@require_http_methods(["GET"])
def schema_download(request):
    schema_path = os.path.join(settings.BASE_DIR, 'transcriptions', 'schema', 'TEI-MUYA.rng')
    file = open(schema_path, mode='r')
    response = HttpResponse(file, content_type='text/rng+xml')
    response['Content-Disposition'] = 'attachment; filename=TEI-MUYA.rng'
    return response


@login_required
@ensure_csrf_cookie
@require_http_methods(["POST"])
@permission_required(['transcriptions.delete_transcription',
                      'transcriptions.delete_collationunit'
                      ], raise_exception=True)
def delete(request):
    transcription_id = request.POST.get('delete-transcription', None)
    if transcription_id is not None:
        try:
            models.Transcription.objects.filter(id=transcription_id.split('|')[1]).delete()
        except Exception:
            pass
    return HttpResponseRedirect(reverse('manage'))


@login_required
def collation_units(request):

    post_login_url = request.path + '?' + request.GET.urlencode()
    login_details = get_login_status(request)

    siglum = request.GET.get('siglum', None)
    units = models.CollationUnit.objects.all().filter(siglum=siglum,
                                                      user=request.user).distinct().order_by('language',
                                                                                             'chapter_number',
                                                                                             'stanza_number',
                                                                                             'line_number')

    context = {
        'login_status': login_details,
        'post_login_url': post_login_url,
        'post_logout_url': '/transcriptions',
        'page_title': 'Collation units for {}'.format(siglum),
        'data': units
        }

    return render(request, 'transcriptions/collation_units.html', context)
