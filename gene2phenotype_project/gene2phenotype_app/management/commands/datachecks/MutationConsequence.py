from gene2phenotype_app.models import LocusGenotypeDisease, LGDMolecularMechanismSynopsis, LGDPanel
from django.core.checks import Error
from .AllelicRequirement import should_process


def mutation_consequence_constraint():
    errors = []
    for obj in LocusGenotypeDisease.objects.all():
        if not should_process(obj.id):
            continue
        if obj.mechanism.value == "undetermined" and obj.mechanism_support.value != "inferred":
            errors.append(
                Error(
                    f"Mechanism value is undetermined, Mechanism support is not inferred {obj.stable_id.stable_id}",
                    hint="Change mechanism support to inferred",
                    id="gene2phenotype_app.E007",
                )
            )
    
    for obj in LGDMolecularMechanismSynopsis.objects.all():
        if not should_process(obj.lgd_id):
            continue
        if obj.lgd.mechanism.value == "undetermined non-loss-of-function" and obj.synopsis_id is not NULL and obj.synopsis_support_id is not NULL:
            errors.append(
                Error(
                    f"Mechanism value is undetermined non loss of function, Mechanism synopis can not be defined {obj.lgd.stable_id.stable_id}",
                    hint="Change mechanism categorization to Null",
                    id="gene2phenotype_app.E008",
                )
            )
    
    for obj in LGDMolecularMechanismSynopsis.objects.all():
        if not should_process(obj.lgd_id):
            continue
        if obj.lgd.mechanism.value == "loss of function" and "LOF" not in obj.synopsis.value:
            errors.append(
                Error(
                    f"Mechanism value is loss of function and categorization is not loss of functionr related{obj.lgd.stable_id.stable_id}",
                    hint="Change categorization to a loss of function categorization",
                    id="gene2phenotype_app.E009",
                )
            )
    
    for obj in LGDMolecularMechanismSynopsis.objects.all():
        if not should_process(obj.lgd_id):
            continue
        if obj.lgd.mechanism.value == "dominant negative" and "dominant" not in obj.synopsis.value:
            errors.append(
                Error(
                    f"Mechanism value is dominant negative and categorization is not considered dominant negative{obj.lgd.stable_id.stable_id}",
                    hint="Change categorization to a dominant negative related synopsis",
                    id="gene2phenotype_app.E0010"
                )
            )
    
    for obj in LGDMolecularMechanismSynopsis.objects.all():
        if not should_process(obj.lgd_id):
            continue
        if obj.lgd.mechanism.value == "gain of function" and not ("GOF" in obj.synopsis.value or obj.synopsis.value == "aggregation"):
            errors.append(
                Error(
                    f"Mechanism value is gain of function and mechanism categorization is not GOF or aggregation{obj.lgd.stable_id.stable_id}",
                    hint="Change categorization to gain of function related or aggregation",
                    id="gene2phenotype_app.E0011"
                )
            )
    
    return errors