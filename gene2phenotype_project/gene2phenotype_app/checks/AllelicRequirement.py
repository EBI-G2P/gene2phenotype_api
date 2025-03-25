from ..models import Locus, LocusGenotypeDisease, Attrib, Sequence
from django.core.checks import Error, register


@register() # to register this so the systemcheck can recognize it
def check_ar_constraint(app_configs, **kwargs):
    errors = []
    for obj in LocusGenotypeDisease.objects.all():
        if "autosomal" in obj.genotype.value.lower() and not (1 <= int(obj.locus.sequence.name) <= 22):
            errors.append(
                Error(
                    f"Autosomal not in Chr 1-22, {obj.stable_id.stable_id}",
                    # level="CRITICAL",
                    hint="Genotype autosomal not in chromosome 1-22",
                    id="gene2phenotype_app.E002",
                )
            )
        
        if obj.genotype.value.lower() == "mitochondrial" and obj.locus.sequence.name != "MT":
            errors.append(
                Error(
                    f"Mitochondrial genotype in non mitchondrial chromosome {obj.stable_id.stable_id}",
                    hint="Genotype mitchondrial not in chromosome MT",
                    id="gene2phenotype_app.E003",
                )
            )
        
        if "par" in obj.genotype.value.lower() and (obj.locus.sequence.name != "X" or obj.locus.sequence.name != "Y"):
            errors.append(
                Error(
                    f"PAR genotype not X or Y chromosome {obj.stable_id.stable_id}",
                    hint="Genotype PAR not in chromsome X or Y",
                    id="gene2phenotype_app.E004",
                )
            )
        
        if "X" in obj.genotype.value and obj.locus.sequence.name != "X":
            errors.append(
                Error(
                    f"X genotype in a non X chromosome {obj.stable_id.stable_id}",
                    hint="Genotype X linked not in chromosome X",
                    id="gene2phenotype_app.E005",
                )
            )
        
        if "Y" in obj.genotype.value and obj.locus.sequence.name != "Y":
            errors.append(
                Error(
                    f"Y genotype in a non Y chromsome {obj.stable_id.stable_id}",
                    hint="Genotype Y linked not in chromsome Y",
                    id="gene2phenotype_app.E006",
                )
            )
    
    return errors