# The Transcriptions app

This Django app forms part of the MUYA Workspace for Collaborative Editing (MUYA-WCE). It is used for TEI-XML
transcription validation and uploading the data into the database and deleting a transcription for the database.

The transcriptions to be uploaded must follow the MUYA TEI schema included in the code and meet the following criteria:

1.  the sigla must be supplied at the xpath ```//tei:title[@type="document"]/@n``` and must meet one of the following criteria:
    - be 'basetext'
    - contain only digits
    - contain only digits with the addition of S, S1 or S2 for supplements
2.  all corrector hands referenced in the transcription must be listed in chronological order of activity in the ```<listWit>``` element of the header, for example:
```xml
<listWit>
<witness xml:id="firsthand"/>
<witness xml:id="corrector"/>
</listWit>
```
3.  the ```<app>``` elements in the transcription are not embedded in other ```<app>``` elements

Before any transcriptions can be uploaded the MUYA works need to be added to the database using the Django management
command ```load_MUYA_works```.

## Configuration/Dependencies

This app is tested with Django 3.2.

It requires the MUYA-WCE api (https://github.com/Multimedia-Avesta/django_wce_api) and accounts (https://github.com/Multimedia-Avesta/django_wce_accounts) apps to be installed.

The app requires Celery (https://docs.celeryproject.org/en/stable/) and a message broker such as RabbitMQ
(https://www.rabbitmq.com/) for handling the long running task of uploading and indexing the transcriptions. It has
been tested with Celery 5.1.2.

A celery result backend is also required such as django-celery-results
(https://github.com/celery/django-celery-results). It has been tested with django-celery-results 2.2.0.

lxml (https://lxml.de/) is required for the transcription parsing. The app has been tested with lxml
4.6.3.

Celery and RabbitMQ require some configuration in the Django settings file as shown in the following example:

```python
CELERY_BROKER_URL = 'amqp://me:example@localhost'
CELERY_RESULT_BACKEND = 'django-db'
```

## License

This app is licensed under the GNU General Public License v3.0.

## Acknowledgments

This application was released as part of the Multimedia Yasna Project funded by the European Union Horizon 2020
Research and Innovation Programme (grant agreement 694612).

The software was created by Catherine Smith at the Institute for Textual Scholarship and Electronic Editing (ITSEE) in
the University of Birmingham. It is based on a suite of tools developed for and supported by the following research
projects:

- The Workspace for Collaborative Editing (AHRC/DFG collaborative project 2010-2013)
- COMPAUL (funded by the European Union 7th Framework Programme under grant agreement 283302, 2011-2016)
- CATENA (funded by the European Union Horizon 2020 Research and Innovation Programme under grant agreement 770816, 2018-2023)

[![DOI](https://zenodo.org/badge/431907595.svg)](https://zenodo.org/badge/latestdoi/431907595)
