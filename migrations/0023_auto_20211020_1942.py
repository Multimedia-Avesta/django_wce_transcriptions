# Generated by Django 2.2 on 2021-10-20 19:42

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('transcriptions', '0022_auto_20210126_1828'),
    ]

    operations = [
        migrations.AlterField(
            model_name='work',
            name='abbreviation',
            field=models.TextField(verbose_name='Abbreviation'),
        ),
        migrations.AlterField(
            model_name='work',
            name='identifier',
            field=models.TextField(unique=True, verbose_name='Identifier'),
        ),
        migrations.AlterField(
            model_name='work',
            name='name',
            field=models.TextField(verbose_name='Name'),
        ),
    ]
