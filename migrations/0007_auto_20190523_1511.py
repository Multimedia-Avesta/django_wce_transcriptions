# Generated by Django 2.1.4 on 2019-05-23 15:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('transcriptions', '0006_auto_20190523_1510'),
    ]

    operations = [
        migrations.AlterField(
            model_name='transcription',
            name='document_id',
            field=models.TextField(verbose_name='document_id'),
        ),
        migrations.AlterField(
            model_name='transcription',
            name='siglum',
            field=models.TextField(verbose_name='siglum'),
        ),
    ]
