from gene2phenotype_app.models import LocusGenotypeDisease, LGDMolecularMechanismSynopsis, LGDPanel
from django.core.checks import Error
from .AllelicRequirement import should_process
from django.db.models import Q, Count


def mutation_consequence_constraint():
    errors = []
    undetermined_inferred_check = LocusGenotypeDisease.objects.filter(mechanism__value="undetermined").exclude(mechanism_support__value="inferred")
    for obj in undetermined_inferred_check:
        if not should_process(obj.id):
            continue
        errors.append(
            Error(
                f"Mechanism value is undetermined, Mechanism support is not inferred {obj.stable_id.stable_id}",
                hint="Change mechanism support to inferred",
                id="gene2phenotype_app.E007",
            )
        )

    undertimed_lof_check = LGDMolecularMechanismSynopsis.objects.filter(
        lgd__mechanism__value = "undetermined non-loss of function"
    ).exclude(synopsis__value=None).exclude(synopsis_support__value=None)
    
    for obj in undertimed_lof_check:
        if not should_process(obj.lgd_id):
            continue
        errors.append(
            Error(
                f"Mechanism value is undetermined non loss of function, Mechanism synopis can not be defined {obj.lgd.stable_id.stable_id}",
                hint="Change mechanism categorization to Null",
                id="gene2phenotype_app.E008",
            )
        )
    
    loss_of_function_check = LGDMolecularMechanismSynopsis.objects.filter(
        lgd__mechanism__value="loss of function"
    ).exclude(synopsis__value__icontains="LOF")
    for obj in loss_of_function_check:
        if not should_process(obj.lgd_id):
            continue
        errors.append(
            Error(
                f"Mechanism value is loss of function and categorization is not loss of functionr related{obj.lgd.stable_id.stable_id}",
                hint="Change categorization to a loss of function categorization",
                id="gene2phenotype_app.E009",
            )
        )
    
    dominant_negative_check = LGDMolecularMechanismSynopsis.objects.filter(
                                lgd__mechanism__value="dominant negative"
                            ).exclude(synopsis__value__icontains="dominant")
    for obj in dominant_negative_check:
        if not should_process(obj.lgd_id):
            continue
        errors.append(
            Error(
                f"Mechanism value is dominant negative and categorization is not considered dominant negative{obj.lgd.stable_id.stable_id}",
                hint="Change categorization to a dominant negative related synopsis",
                id="gene2phenotype_app.E0010"
            )
        )
    
    gain_of_function_check = LGDMolecularMechanismSynopsis.objects.filter(
                                lgd__mechanism__value="gain of function"
                            ).exclude(
                                synopsis__value__icontains="GOF"
                            ).exclude(
                                synopsis__value="aggregation"
                            )
    for obj in gain_of_function_check:
        if not should_process(obj.lgd_id):
            continue
        errors.append(
            Error(
                f"Mechanism value is gain of function and mechanism categorization is not GOF or aggregation{obj.lgd.stable_id.stable_id}",
                hint="Change categorization to gain of function related or aggregation",
                id="gene2phenotype_app.E0011"
            )
        )

    #first Count the occurence grouped by gene_name, disease_name and genotype_obj and mutation mechanism obj
    monoallelic_biallelic_counts = LocusGenotypeDisease.objects.filter(mechanism__value="loss of function").values("disease__name", "locus__name").annotate(
        mono_count=Count('id', filter=Q(genotype__value__icontains="monoallelic")),
        bi_count=Count('id', filter=Q(genotype__value__icontains="biallelic")),
    ).filter(mono_count__gt=0, bi_count__gt=0)
    for entry in monoallelic_biallelic_counts:
        errors.append(
            Error(
                f"Mechanism value of monoallelic and biallelic loss of function exists with the same disease name ({entry['disease__name']}) and locus name ({entry['locus__name']})",
                hint="Flag this to the curators",
                id="gene2phenotype_app.E0012"
            )
        )

    
    
    return errors