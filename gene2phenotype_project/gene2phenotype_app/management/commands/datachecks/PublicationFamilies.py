from django.core.checks import Error
from gene2phenotype_app.models import PublicationFamilies
from django.db.models import F


def check_model_constraints():
    errors = []

    pub_families_check = PublicationFamilies.objects.filter(families__gt=F("individual"))
    for obj in pub_families_check:
        errors.append(
            Error(
                "PublicationFanilies families can not be greater than affected individuals",
                hint="Number of families can not be greater than affected individuals",
                id="gene2phenotype_app.E001",
            )
            )

    return errors
