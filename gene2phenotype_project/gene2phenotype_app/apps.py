from django.apps import AppConfig


class Gene2PhenotypeAppConfig(AppConfig):
    default_auto_field = 'django.db.models.AutoField'
    name = 'gene2phenotype_app'

    def ready(self):
        from . import checks
