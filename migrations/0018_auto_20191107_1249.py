# Generated by Django 2.1.4 on 2019-11-07 12:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('transcriptions', '0017_auto_20190903_1242'),
    ]

    operations = [
        migrations.AlterField(
            model_name='collationunit',
            name='language',
            field=models.CharField(max_length=15, verbose_name='language'),
        ),
    ]