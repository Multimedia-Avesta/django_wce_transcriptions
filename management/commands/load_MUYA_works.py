import os
from django.core.management.base import BaseCommand, CommandError
from transcriptions.models import Collection, Work


class Command(BaseCommand):

    '''
    loads collections and works. If they already exist in the database then the
    existing id will be used so multiple entries will not be created and
    relations will maintained.
    '''

    def handle(self, *args, **options):

        collection_data = {
            'AV': {'identifier': 'AV', 'name': 'Avesta', 'abbreviation': 'AV'}
        }

        for key in collection_data:

            coll = Collection(**collection_data[key])
            # check if we have an existing entry - if so we must ensure we keep the pk as other things link to this
            try:
                existing = Collection.objects.get(identifier=collection_data[key]['identifier'])
                coll.id = existing.id
            except Collation.DoesNotExist:
                pass
            coll.save()

        MUYA_works_data = {
            'A': {'name': 'Afrinagan'},
            'ABu': {'name': 'Afrin i Buzorgan'},
            'AD': {'name': 'Afrin i Dahman'},
            'AG': {'name': 'Afrin i Gahambar'},
            'As': {'name': 'Asirvad'},
            'AvAlph': {'name': 'Avestan alphabet'},
            'Col': {'name': 'Colophon'},
            'DrYt': {'name': 'Drōn Yašt'},
            'DuP': {'name': 'Duʾa Paymani'},
            'FiO': {'name': 'Frahang i Oim'},
            'FrW': {'name': 'Fragment Westergard'},
            'G': {'name': 'Gah'},
            'H': {'name': 'Herbedestan'},
            'HB': {'name': 'Hosbam'},
            'HN': {'name': 'Hadoxt Nask'},
            'N': {'name': 'Nerangestan'},
            'NiAs': {'name': 'Nirang Asoan'},
            'Nirang': {'name': 'Nirang'},
            'NiSY': {'name': 'Nirang Sangriza Yastan'},
            'NkB': {'name': 'Nerang i kustig bastan'},
            'NS': {'name': 'Nam Stayisn'},
            'Ny': {'name': 'Nyayisn'},
            'Par': {'name': 'Paragna'},
            'PaIr': {'name': 'Patet Irani'},
            'PaPas': {'name': 'Patet Pasemanih'},
            'PaXw': {'name': 'Patet Xwad'},
            'PazT': {'name': 'Pazand texts'},
            'PPhl': {'name': 'Payman i Pahlawi'},
            'PS': {'name': 'Payman i Sanskrit'},
            'S': {'name': 'Siroza'},
            'SrB': {'name': 'Sros Baj'},
            'V': {'name': 'Videvdad'},
            'VN': {'name': 'Vaeϑa Nask'},
            'Vr': {'name': 'Visparad'},
            'VrS': {'name': 'Visperad Sade'},
            'VS': {'name': 'Videvdad Sade'},
            'Vyt': {'name': 'Vistasp Yast'},
            'VytS': {'name': 'Vishtasp Yasht Sade'},
            'Y': {'name': 'Yasna'},
            'Yt': {'name': 'Yast'},
            'YiR': {'name': 'Yasna ī Rapihwin'},
            'YVr': {'name': 'Yasna Visperad'},
            'Y-gah': {'name': 'Yazisn-gah'}
        }

        for entry in MUYA_works_data:

            work = {
                'identifier': 'AV_%s' % entry,
                'name': MUYA_works_data[entry]['name'],
                'abbreviation': entry
            }
            w = Work(**work)
            try:
                existing = Work.objects.get(identifier='AV_%s' % work['abbreviation'])
                w.id = existing.id
            except Work.DoesNotExist:
                pass
            collection = Collection.objects.get(identifier='AV')
            w.collection = collection
            w.save()
