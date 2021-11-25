from django.conf import settings
from django.db import models
from api.models import BaseModel
from django.contrib.postgres.fields import ArrayField


class Collection (models.Model):

    AVAILABILITY = 'public'

    SERIALIZER = 'CollectionSerializer'

    identifier = models.TextField('identifier')
    name = models.TextField('name')
    abbreviation = models.TextField('abbreviation')

    def __str__(self):
        return '{} ({})'.format(self.name, self.identifier)

    def get_serialization_fields():
        fields = '__all__'
        return fields

    def get_fields():
        data = {}
        fields = list(Collection._meta.get_fields(include_hidden=True))
        for field in fields:
            data[field.name] = field.get_internal_type()
        return data


class Work (models.Model):

    AVAILABILITY = 'public'

    SERIALIZER = 'WorkSerializer'

    identifier = models.TextField('Identifier', unique=True)
    name = models.TextField('Name')
    collection = models.ForeignKey(Collection, on_delete=models.PROTECT, null=True)
    abbreviation = models.TextField('Abbreviation')

    class Meta:
        ordering = ['abbreviation']

    def __str__(self):
        return '{} ({})'.format(self.name, self.identifier)

    def get_serialization_fields():
        fields = '__all__'
        return fields

    def get_fields():
        data = {}
        fields = list(Work._meta.get_fields(include_hidden=True))
        for field in fields:
            data[field.name] = field.get_internal_type()
        return data


class Transcription (models.Model):

    AVAILABILITY = 'logged_in'

    RELATED_KEYS = ['work', 'user']

    SERIALIZER = 'TranscriptionSerializer'

    class Meta:
        ordering = ['siglum']

    identifier = models.TextField('identifier', unique=True)
    collection = models.ForeignKey(Collection, on_delete=models.PROTECT, null=True)
    document_id = models.TextField('document_id')
    tei = models.TextField('tei')
    source = models.TextField('source')
    siglum = models.TextField('siglum')
    main_language = models.TextField('main_language')
    corrector_order = ArrayField(models.CharField(max_length=50), null=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, models.PROTECT, null=True)
    work = models.ForeignKey('Work', on_delete=models.PROTECT, related_name="transcriptions")
    loading_complete = models.BooleanField('loading_complete', null=True)
    public = models.BooleanField('public')

    def get_serialization_fields():
        fields = '__all__'
        return fields

    def get_fields():
        data = {}
        fields = list(Transcription._meta.get_fields(include_hidden=True))
        for field in fields:
            data[field.name] = field.get_internal_type()
        return data

    def __str__(self):
        return self.identifier


class CollationUnit (models.Model):

    AVAILABILITY = 'public_or_user'

    RELATED_KEYS = ['transcription', 'work', 'user']

    SERIALIZER = 'CollationUnitSerializer'

    identifier = models.TextField('identifier', unique=True)
    index = models.IntegerField('index')
    document_id = models.TextField('document_id')
    tei = models.TextField('tei')
    context = models.TextField('context')
    reference = models.TextField('reference')
    chapter_number = models.IntegerField('chapter_number', null=True)
    stanza_number = models.IntegerField('verse_or_stanza_number', null=True)
    line_number = models.IntegerField('line_or_verseline_number')
    siglum = models.TextField('siglum')
    language = models.TextField('language')
    duplicate_position = models.IntegerField('duplicate_position', null=True)
    transcription = models.ForeignKey('Transcription', models.CASCADE, related_name="units")
    transcription_siglum = models.TextField('transcription_siglum')
    transcription_identifier = models.TextField('transcription_identifier')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, models.PROTECT, null=True)
    work = models.ForeignKey('Work', models.PROTECT, related_name="work_units")
    witnesses = models.JSONField(null=True)
    public = models.BooleanField('public')

    class Meta:
        ordering = ['chapter_number', 'stanza_number', 'line_number']

    def get_serialization_fields():
        fields = '__all__'
        return fields

    def get_fields():
        data = {}
        fields = list(CollationUnit._meta.get_fields(include_hidden=True))
        for field in fields:
            data[field.name] = field.get_internal_type()
        return data
