from gene2phenotype_app.models import LocusGenotypeDisease, LGDPanel, LGDPublication
from django.core.checks import Error
from django.db.models import Q, F


# helper function to skip checks for anything in panel Demo
def should_process(obj):
    lgd_panels = LGDPanel.objects.filter(lgd_id=obj, is_deleted=0).annotate(
        panel_name=F("panel__name")
    )

    for lgd_panel in lgd_panels:
        return lgd_panel.panel_name != "Demo"


def check_ar_constraint():
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
            obj.locus_sequence != "X" or obj.locus_sequence != "Y"
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


def check_ar_publications():
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
