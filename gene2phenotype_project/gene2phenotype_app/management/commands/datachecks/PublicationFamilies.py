from django.core.checks import Error
from gene2phenotype_app.models import PublicationFamilies


def check_model_constraints():
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
