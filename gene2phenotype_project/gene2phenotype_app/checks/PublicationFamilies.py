from django.core.checks import Error, register
from ..models import PublicationFamilies



@register()
def check_model_constraints(app_configs, **kwargs):
    errors = []

    for obj in PublicationFamilies.objects.all():
        if obj.families > obj.affected_individuals: 
            errors.append(
                Error(
                    "PublicationFanilies families can not be greater than affected individuals",
                    hint="Number of families can not be greater than affected individuals",
                    id="gene2phenotype_app.E001",
                )
            )

    return errors
