# Generated by Django 2.2 on 2021-01-26 18:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('transcriptions', '0021_auto_20200716_1639'),
    ]

    operations = [
        migrations.AlterField(
            model_name='collationunit',
            name='identifier',
            field=models.TextField(unique=True, verbose_name='identifier'),
        ),
    ]