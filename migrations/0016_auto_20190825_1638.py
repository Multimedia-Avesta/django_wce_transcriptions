# Generated by Django 2.1.4 on 2019-08-25 16:38

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('transcriptions', '0015_auto_20190825_0841'),
    ]

    operations = [
        migrations.AlterField(
            model_name='ceremonymapping',
            name='context',
            field=models.TextField(unique=True, verbose_name='context'),
        ),
    ]
