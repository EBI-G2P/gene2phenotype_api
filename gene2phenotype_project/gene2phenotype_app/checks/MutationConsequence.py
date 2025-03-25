from ..models import LocusGenotypeDisease, CVMolecularMechanism, LGDMolecularMechanismSynopsis
from django.core.checks import Error, register




@register()
def mutation_consequence(app_configs, **kwargs):
    errors = []
    for obj in LocusGenotypeDisease.objects.all():
        if obj.mechanism.value == "undetermined" and obj.mechanism_support.value != "inferred":
            errors.append(
                Error(
                    f"Mechanism value is undetermined, Mechanism support is not inferred {obj.stable_id.stable_id}",
                    hint="Change mechanism support to inferred",
                    id="gene2phenotype_app.E007",
                )
            )
    
    for obj in LGDMolecularMechanismSynopsis.objects.all():
        if obj.lgd.mechanism.value == "undetermined non-loss-of-function" and obj.synopsis_id is not NULL and obj.synopsis_support_id is not NULL:
            errors.append(
                Error(
                    f"Mechanism value is undetermined non loss of function, Mechanism synopis can not be defined {obj.stable_id.stable_id}",
                    hint="Change mechanism synopsis to Null",
                    id="gene2phenotype_app.E008",
                )
            )
    
    for obj in LGDMolecularMechanismSynopsis.objects.all():
        if "LOF" in obj.synopsis.value and "loss of function" not in obj.lgd.mechanism.value:
            errors.append(
                Error(
                    f"Mechanism synopsis is loss of function related and Mechanism synopsis is not loss of function {obj.stable_id.stable_id}",
                    hint="Change synopsis to a loss of function related synopsis",
                    id="gene2phenotype_app.E009",
                )
            )
    
    return errors