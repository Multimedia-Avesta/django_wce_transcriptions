# Generated by Django 3.2 on 2021-10-22 10:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('transcriptions', '0023_auto_20211020_1942'),
    ]

    operations = [
        migrations.AlterField(
            model_name='ceremonymapping',
            name='id',
            field=models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID'),
        ),
        migrations.AlterField(
            model_name='ceremonymapping',
            name='mappings',
            field=models.JSONField(null=True),
        ),
        migrations.AlterField(
            model_name='collationunit',
            name='id',
            field=models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID'),
        ),
        migrations.AlterField(
            model_name='collationunit',
            name='witnesses',
            field=models.JSONField(null=True),
        ),
        migrations.AlterField(
            model_name='collection',
            name='id',
            field=models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID'),
        ),
        migrations.AlterField(
            model_name='transcription',
            name='id',
            field=models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID'),
        ),
        migrations.AlterField(
            model_name='transcription',
            name='loading_complete',
            field=models.BooleanField(null=True, verbose_name='loading_complete'),
        ),
        migrations.AlterField(
            model_name='work',
            name='id',
            field=models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID'),
        ),
    ]
