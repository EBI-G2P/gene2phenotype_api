from gene2phenotype_app.models import (
    LocusGenotypeDisease,
    LGDMolecularMechanismSynopsis,
)
from django.core.checks import Error
from .AllelicRequirement import should_process
from django.db.models import Q, Count


def mutation_consequence_constraint():
    errors = []
    undetermined_inferred_check = LocusGenotypeDisease.objects.filter(
        mechanism__value="undetermined", is_deleted=0
    ).exclude(mechanism_support__value="inferred")
    for obj in undetermined_inferred_check:
        if not should_process(obj.id):
            continue
        errors.append(
            Error(
                f"{obj.stable_id.stable_id} has mechanism value 'undetermined' and support is not inferred",
                hint="Undetermined mechanism should have inferred support",
                id="gene2phenotype_app.E301",
            )
        )

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
                id="gene2phenotype_app.E302",
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
                id="gene2phenotype_app.E303",
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
                id="gene2phenotype_app.E304",
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
                id="gene2phenotype_app.E305",
            )
        )

    # first Count the occurrence grouped by gene_name, disease_name and genotype_obj and mutation mechanism obj
    monoallelic_biallelic_counts = (
        LocusGenotypeDisease.objects.filter(
            mechanism__value="loss of function", is_deleted=0
        )
        .values("disease__name", "locus__name", "id")
        .annotate(
            mono_count=Count("id", filter=Q(genotype__value__icontains="monoallelic")),
            bi_count=Count("id", filter=Q(genotype__value__icontains="biallelic")),
        )
        .filter(mono_count__gt=0, bi_count__gt=0)
    )
    for entry in monoallelic_biallelic_counts:
        if not should_process(entry.id):
            continue
        errors.append(
            Error(
                f"There are monoallelic and biallelic records for the same mechanism (loss of function), disease name : ({entry['disease__name']}) and gene: ({entry['locus__name']})",
                hint="Flag this to the curators",
                id="gene2phenotype_app.E306",
            )
        )

    return errors
