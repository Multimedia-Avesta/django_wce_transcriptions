# Generated by Django 2.1.4 on 2019-05-27 17:57

import django.contrib.postgres.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('transcriptions', '0007_auto_20190523_1511'),
    ]

    operations = [
        migrations.AddField(
            model_name='collationunit',
            name='equivalent_contexts',
            field=django.contrib.postgres.fields.ArrayField(base_field=models.TextField(), null=True, size=None),
        ),
    ]