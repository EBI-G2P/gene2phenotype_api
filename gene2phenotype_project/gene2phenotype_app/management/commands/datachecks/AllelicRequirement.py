from gene2phenotype_app.models import LocusGenotypeDisease
from django.core.checks import Error
from django.db.models import F

from .Base import should_process


def check_ar_constraint():
    """Check that allelic requirements are compatible with the locus chromosome."""
    errors = []
    locus_genotype_check = (
        LocusGenotypeDisease.objects.filter(is_deleted=0)
        .select_related("genotype", "locus")
        .annotate(
            genotype_value=F("genotype__value"),
            locus_sequence=F("locus__sequence__name"),
            g2p_id=F("stable_id__stable_id"),
        )
    )

    for obj in locus_genotype_check:
        if not should_process(obj.id):
            continue

        if "autosomal" in obj.genotype_value.lower() and not (
            1 <= int(obj.locus_sequence) <= 22
        ):
            errors.append(
                Error(
                    f"'{obj.g2p_id}' with autosomal genotype is not in chromosome 1-22",
                    hint="Autosomal genotype should be linked to chromosome 1-22",
                    id="gene2phenotype_app.E201",
                )
            )

        if obj.genotype_value.lower() == "mitochondrial" and obj.locus_sequence != "MT":
            errors.append(
                Error(
                    f"'{obj.g2p_id}' with mitochondrial genotype in non mitochondrial chromosome",
                    hint="Mitochondrial genotype should be linked to chromosome MT",
                    id="gene2phenotype_app.E202",
                )
            )

        if "par" in obj.genotype_value.lower() and (
            obj.locus_sequence != "X" and obj.locus_sequence != "Y"
        ):
            errors.append(
                Error(
                    f"'{obj.g2p_id}' PAR genotype is not in X or Y chromosome",
                    hint="Genotype of the PAR regions should be linked to chromosome X or Y",
                    id="gene2phenotype_app.E203",
                )
            )

        if "X" in obj.genotype_value and obj.locus_sequence != "X":
            errors.append(
                Error(
                    f"'{obj.g2p_id}' X genotype in a non X chromosome",
                    hint="X-linked genotype should be linked to chromosome X",
                    id="gene2phenotype_app.E204",
                )
            )

        if "Y" in obj.genotype_value and obj.locus_sequence != "Y":
            errors.append(
                Error(
                    f"'{obj.g2p_id}' Y genotype in a non Y chromosome",
                    hint="Y-linked genotype should be linked to chromosome Y",
                    id="gene2phenotype_app.E205",
                )
            )

    return errors
