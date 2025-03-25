from django.apps import AppConfig
from django.db.models.signals import post_migrate
from django.dispatch import receiver

class Gene2PhenotypeAppConfig(AppConfig):
    default_auto_field = 'django.db.models.AutoField'
    name = 'gene2phenotype_app'
    
    def ready(self, **kwargs):
        from . import checks
        post_migrate.connect(checks.check_ar_constraint, sender=self)
        post_migrate.connect(checks.mutation_consequence, sender=self)
        post_migrate.connect(checks.check_model_constraints, sender=self)
