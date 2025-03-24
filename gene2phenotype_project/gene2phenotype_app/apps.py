from django.apps import AppConfig
from django.db.models.signals import post_migrate
from django.dispatch import receiver

class Gene2PhenotypeAppConfig(AppConfig):
    default_auto_field = 'django.db.models.AutoField'
    name = 'gene2phenotype_app'
    
    @receiver(post_migrate)
    def ready(self):
        from . import checks
