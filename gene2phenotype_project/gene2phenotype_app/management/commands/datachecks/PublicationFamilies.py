from django.core.checks import Error
from gene2phenotype_app.models import LGDPublication
from django.db.models import F


def check_model_constraints():
    errors = []

    pub_families_check = LGDPublication.objects.filter(
        number_of_families__gt=F("affected_individuals"), is_deleted=0
    )
    for obj in pub_families_check:
        errors.append(
            Error(
                f"Publication ID {obj.publication_id} has number of families greater than the number of affected individuals",
                hint="Number of families can not be greater than affected individuals",
                id="gene2phenotype_app.E001",
            )
        )

    return errors
