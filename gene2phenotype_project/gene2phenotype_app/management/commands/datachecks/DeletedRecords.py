from django.core.checks import Error
from django.db.models import F

from gene2phenotype_app.models import (
    LocusGenotypeDisease,
    LGDComment,
    LGDCrossCuttingModifier,
    LGDMolecularMechanismEvidence,
    LGDMolecularMechanismSynopsis,
    LGDPanel,
    LGDPhenotype,
    LGDPhenotypeSummary,
    LGDPublication,
    LGDVariantGenccConsequence,
    LGDVariantType,
    LGDVariantTypeDescription,
)


def append_active_records_with_deleted_g2p_ids_error(
    errors, queryset, lgd_id_field, g2p_id_field, error_id
):
    """Append an error for active records linked to deleted G2P IDs."""
    table_name = queryset.model._meta.db_table
    invalid_records = list(
        queryset.annotate(
            record_lgd_id=F(lgd_id_field),
            deleted_g2p_stable_id=F(g2p_id_field),
        ).values("record_lgd_id", "deleted_g2p_stable_id")
    )

    if invalid_records:
        errors.append(
            Error(
                f"Active records in {table_name} linked to deleted G2P IDs: "
                + ", ".join(
                    f"lgd_id={record['record_lgd_id']} ({record['deleted_g2p_stable_id']})"
                    for record in invalid_records
                ),
                id=error_id,
            )
        )


def check_deleted_records():
    """Check LGD-related tables for active records linked to deleted G2P IDs."""
    errors = []

    # Check active records linked to deleted G2P IDs in LocusGenotypeDisease objects
    append_active_records_with_deleted_g2p_ids_error(
        errors,
        LocusGenotypeDisease.objects.filter(stable_id__is_deleted=1, is_deleted=0),
        "id",
        "stable_id__stable_id",
        "gene2phenotype_app.E701",
    )

    # Check active records linked to deleted G2P IDs in LGDMolecularMechanismSynopsis objects
    append_active_records_with_deleted_g2p_ids_error(
        errors,
        LGDMolecularMechanismSynopsis.objects.filter(
            lgd__stable_id__is_deleted=1, is_deleted=0
        ),
        "lgd__id",
        "lgd__stable_id__stable_id",
        "gene2phenotype_app.E702",
    )

    # Check active records linked to deleted G2P IDs in LGDMolecularMechanismEvidence objects
    append_active_records_with_deleted_g2p_ids_error(
        errors,
        LGDMolecularMechanismEvidence.objects.filter(
            lgd__stable_id__is_deleted=1, is_deleted=0
        ),
        "lgd__id",
        "lgd__stable_id__stable_id",
        "gene2phenotype_app.E703",
    )

    # Check active records linked to deleted G2P IDs in LGDCrossCuttingModifier objects
    append_active_records_with_deleted_g2p_ids_error(
        errors,
        LGDCrossCuttingModifier.objects.filter(
            lgd__stable_id__is_deleted=1, is_deleted=0
        ),
        "lgd__id",
        "lgd__stable_id__stable_id",
        "gene2phenotype_app.E704",
    )

    # Check active records linked to deleted G2P IDs in LGDPhenotype objects
    append_active_records_with_deleted_g2p_ids_error(
        errors,
        LGDPhenotype.objects.filter(lgd__stable_id__is_deleted=1, is_deleted=0),
        "lgd__id",
        "lgd__stable_id__stable_id",
        "gene2phenotype_app.E705",
    )

    # Check active records linked to deleted G2P IDs in LGDPhenotypeSummary objects
    append_active_records_with_deleted_g2p_ids_error(
        errors,
        LGDPhenotypeSummary.objects.filter(lgd__stable_id__is_deleted=1, is_deleted=0),
        "lgd__id",
        "lgd__stable_id__stable_id",
        "gene2phenotype_app.E706",
    )

    # Check active records linked to deleted G2P IDs in LGDVariantType objects
    append_active_records_with_deleted_g2p_ids_error(
        errors,
        LGDVariantType.objects.filter(lgd__stable_id__is_deleted=1, is_deleted=0),
        "lgd__id",
        "lgd__stable_id__stable_id",
        "gene2phenotype_app.E707",
    )

    # Check active records linked to deleted G2P IDs in LGDVariantTypeDescription objects
    append_active_records_with_deleted_g2p_ids_error(
        errors,
        LGDVariantTypeDescription.objects.filter(
            lgd__stable_id__is_deleted=1, is_deleted=0
        ),
        "lgd__id",
        "lgd__stable_id__stable_id",
        "gene2phenotype_app.E708",
    )

    # Check active records linked to deleted G2P IDs in LGDVariantGenccConsequence objects
    append_active_records_with_deleted_g2p_ids_error(
        errors,
        LGDVariantGenccConsequence.objects.filter(
            lgd__stable_id__is_deleted=1, is_deleted=0
        ),
        "lgd__id",
        "lgd__stable_id__stable_id",
        "gene2phenotype_app.E709",
    )

    # Check active records linked to deleted G2P IDs in LGDComment objects
    append_active_records_with_deleted_g2p_ids_error(
        errors,
        LGDComment.objects.filter(lgd__stable_id__is_deleted=1, is_deleted=0),
        "lgd__id",
        "lgd__stable_id__stable_id",
        "gene2phenotype_app.E710",
    )

    # Check active records linked to deleted G2P IDs in LGDPublication objects
    append_active_records_with_deleted_g2p_ids_error(
        errors,
        LGDPublication.objects.filter(lgd__stable_id__is_deleted=1, is_deleted=0),
        "lgd__id",
        "lgd__stable_id__stable_id",
        "gene2phenotype_app.E711",
    )

    # Check active records linked to deleted G2P IDs in LGDPanel objects
    append_active_records_with_deleted_g2p_ids_error(
        errors,
        LGDPanel.objects.filter(lgd__stable_id__is_deleted=1, is_deleted=0),
        "lgd__id",
        "lgd__stable_id__stable_id",
        "gene2phenotype_app.E712",
    )

    return errors
