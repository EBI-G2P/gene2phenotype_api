from gene2phenotype_app.models import (
    LocusGenotypeDisease,
    LGDMolecularMechanismSynopsis,
    LGDPanel,
)
from django.core.checks import Error
from .Base import should_process
from django.db.models import Q, Count, Min


def mutation_consequence_constraint():
    """Check consistency between mechanism values and mechanism synopsis data."""
    errors = []

    undertimed_lof_check = (
        LGDMolecularMechanismSynopsis.objects.filter(
            lgd__mechanism__value="undetermined non-loss of function", is_deleted=0
        )
        .exclude(synopsis__value=None)
        .exclude(synopsis_support__value=None)
    )

    for obj in undertimed_lof_check:
        if not should_process(obj.lgd_id):
            continue
        errors.append(
            Error(
                f"{obj.lgd.stable_id.stable_id} has mechanism 'undetermined non-loss of function' and a defined mechanism categorisation '{obj.synopsis.value}'",
                hint="Undetermined non-loss of function cannot have mechanism categorisation",
                id="gene2phenotype_app.E301",
            )
        )

    loss_of_function_check = LGDMolecularMechanismSynopsis.objects.filter(
        lgd__mechanism__value="loss of function", is_deleted=0
    ).exclude(synopsis__value__icontains="LOF")
    for obj in loss_of_function_check:
        if not should_process(obj.lgd_id):
            continue
        errors.append(
            Error(
                f"{obj.lgd.stable_id.stable_id} mechanism value is 'loss of function' and mechanism categorisation is '{obj.synopsis.value}'",
                hint="Loss of function mechanism should have a loss of function related categorisation",
                id="gene2phenotype_app.E302",
            )
        )

    dominant_negative_check = LGDMolecularMechanismSynopsis.objects.filter(
        lgd__mechanism__value="dominant negative", is_deleted=0
    ).exclude(synopsis__value__icontains="dominant")
    for obj in dominant_negative_check:
        if not should_process(obj.lgd_id):
            continue
        errors.append(
            Error(
                f"{obj.lgd.stable_id.stable_id} mechanism value is 'dominant negative' and mechanism categorisation is '{obj.synopsis.value}'",
                hint="Dominant negative mechanism should have dominant negative related categorisation",
                id="gene2phenotype_app.E303",
            )
        )

    gain_of_function_check = (
        LGDMolecularMechanismSynopsis.objects.filter(
            lgd__mechanism__value="gain of function", is_deleted=0
        )
        .exclude(synopsis__value__icontains="GOF")
        .exclude(synopsis__value="aggregation")
    )
    for obj in gain_of_function_check:
        if not should_process(obj.lgd_id):
            continue
        errors.append(
            Error(
                f"{obj.lgd.stable_id.stable_id} mechanism value is 'gain of function' and mechanism categorisation is '{obj.synopsis.value}'",
                hint="Gain of function mechanism should have GOF related or aggregation categorisation",
                id="gene2phenotype_app.E304",
            )
        )

    # Keep only records that belong to at least one non-Demo active panel before aggregation.
    non_demo_lgd_ids = LGDPanel.objects.filter(
        is_deleted=0
    ).exclude(panel__name="Demo").values("lgd_id")

    # Count the occurrence grouped by gene and disease to detect when both
    # monoallelic and biallelic loss-of-function records exist in the same group.
    monoallelic_biallelic_counts = (
        LocusGenotypeDisease.objects.filter(
            mechanism__value="loss of function",
            is_deleted=0,
            id__in=non_demo_lgd_ids,
        )
        .values("disease__name", "locus__name")
        .annotate(
            mono_count=Count("id", filter=Q(genotype__value__icontains="monoallelic")),
            bi_count=Count("id", filter=Q(genotype__value__icontains="biallelic")),
            sample_lgd_id=Min("id"),
        )
        .filter(mono_count__gt=0, bi_count__gt=0)
    )
    for entry in monoallelic_biallelic_counts:
        if not should_process(entry["sample_lgd_id"]):
            continue
        errors.append(
            Error(
                f"There are monoallelic and biallelic records for the same mechanism (loss of function), disease name : {entry['disease__name']} and gene: {entry['locus__name']}",
                hint="Flag this to the curators",
                id="gene2phenotype_app.E305",
            )
        )

    return errors
