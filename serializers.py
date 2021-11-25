from rest_framework import serializers
from api import serializers as api_serializers
from . import models


class CollectionSerializer(api_serializers.BaseModelSerializer):

    class Meta:
        model = models.Collection


class WorkSerializer(api_serializers.BaseModelSerializer):

    class Meta:
        model = models.Work


class TranscriptionSerializer(api_serializers.BaseModelSerializer):

    class Meta:
        model = models.Transcription


class CollationUnitSerializer(api_serializers.BaseModelSerializer):

    class Meta:
        model = models.CollationUnit
