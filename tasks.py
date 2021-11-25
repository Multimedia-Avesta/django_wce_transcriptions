from celery import shared_task
from lxml import etree
from django.db import IntegrityError
from accounts.models import User
from transcriptions import models
from transcriptions.yasna_parser import YasnaParser
from transcriptions.yasna_word_parser import YasnaWordParser


@shared_task(track_started=True)
def index_transcription(xml_string, collection, username=None, siglum=None, project_id=None, public_flag=False,
                        languages=['ae']):

    if public_flag is True:
        private_boolean = False
    else:
        private_boolean = True
    source = 'Web upload'

    parser = YasnaParser(xml_string, collection=collection, filename=source, private=private_boolean, user_id=username,
                         languages=languages)

    data = parser.get_data_online()

    user = User.objects.get(id=username)
    data['transcription']['user'] = user
    try:
        del data['transcription']['user_id']
    except KeyError:
        pass

    # replace string of collection abbreviation with collection object
    collections = models.Collection.objects.all().filter(abbreviation=data['transcription']['collection'])
    if len(collections) == 1:
        data['transcription']['collection'] = collections[0]

    # replace work abbreviation with work objects
    if data['transcription']['work'] is None:
        raise Exception('The work specified in the transcription could not be identified.')

    works = models.Work.objects.all().filter(abbreviation=data['transcription']['work'])
    if len(works) == 1:
        current_work = works[0]
        data['transcription']['work'] = current_work
    else:
        raise Exception('The work specified in the transcription could not be found int he system. '
                        'The abbreviation required is {}.'.format(data['transcription']['work']))

    # if we have got this far with parsing it will probably all save fine
    # so delete the existing collation units for this transcription if there
    # are any

    existing_transcription_identifier = None

    transcriptions = models.Transcription.objects.filter(identifier=data['transcription']['identifier'])
    if transcriptions.count() > 1:
        raise Exception('There are too many transcriptions with the identifier {} in the system. '
                        'This must be fixed before uploading this '
                        'transcription.'.format(data['transcription']['identifier']))

    if transcriptions.count() == 1:
        current_id = transcriptions[0].id
        units = models.CollationUnit.objects.filter(transcription_identifier=data['transcription']['identifier'])
        units.delete()
        data['transcription']['id'] = current_id

    # check that the deletion worked
    units = models.CollationUnit.objects.filter(transcription_identifier=data['transcription']['identifier'])
    if units.count() > 0:
        raise Exception('The existing collation units did not delete correctly. Please try the upload again.')

    # Now make the new objects
    transcription_object = models.Transcription(**data['transcription'])
    transcription_object.save()

    for language in data['collation_units'].keys():
        for unit in data['collation_units'][language]:
            unit['transcription'] = transcription_object
            unit['user'] = user
            unit['work'] = current_work
            try:
                del unit['user_id']
            except KeyError:
                pass
            collationunit_object = models.CollationUnit(**unit)
            try:
                collationunit_object.save()
            except IntegrityError as e:
                raise e
