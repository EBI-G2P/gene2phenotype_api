from django.core.checks import Error
from gene2phenotype_app.models import LGDPublication, LocusGenotypeDisease
from django.db.models import F, Q

from .Base import should_process


def check_publication_families():
    """Check that family counts do not exceed affected individual counts."""
    errors = []

    pub_families_check = LGDPublication.objects.filter(
        number_of_families__gt=F("affected_individuals"), is_deleted=0
    )
    for obj in pub_families_check:
        errors.append(
            Error(
                f"Publication ID {obj.publication_id} has number of families greater than the number of affected individuals",
                hint="Number of families can not be greater than affected individuals",
                id="gene2phenotype_app.E101",
            )
        )

    return errors

def check_number_publications():
    """Check that strong and definitive records have at least two publications."""
    errors = []
    locus_genotype_check = (
        LocusGenotypeDisease.objects.filter(
            Q(confidence__value="definitive") | Q(confidence__value="strong"),
            is_deleted=0,
        )
        .select_related("confidence")
        .annotate(
            obj_id=F("id"),
            confidence_value=F("confidence__value"),
            g2p_id=F("stable_id__stable_id"),
        )
        .prefetch_related()
    )

    for obj in locus_genotype_check:
        if not should_process(obj.obj_id):
            continue

        lgd_publications = LGDPublication.objects.filter(lgd=obj, is_deleted=0)

        number_publications = len(lgd_publications)
        if number_publications < 2:
            errors.append(
                Error(
                    f"'{obj.g2p_id}' has confidence '{obj.confidence_value}' but only {number_publications} publication(s)",
                    hint="Confidence 'definitive' and 'strong' require more than 1 publication",
                    id="gene2phenotype_app.E206",
                )
            )

    return errors
