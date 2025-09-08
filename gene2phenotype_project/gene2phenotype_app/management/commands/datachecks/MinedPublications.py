from django.core.checks import Error
from django.db.models import F, OuterRef, Exists

from gene2phenotype_app.models import (
    MinedPublication,
    LGDMinedPublication,
    LGDPublication,
)


def check_mined_publication_status():
    errors = []

    # Curated rows have to be stored in LGDPublication
    list_curated_lgd_publications = (
        LGDMinedPublication.objects.select_related("mined_publication", "lgd")
        .annotate(
            mined_pmid=F("mined_publication__pmid"),
            g2p_id=F("lgd__stable_id__stable_id"),
        )
        .filter(status="curated")
        .exclude(
            Exists(
                LGDPublication.objects.filter(
                    lgd=OuterRef("lgd"),
                    publication__pmid=OuterRef("mined_publication__pmid"),
                    is_deleted=0,
                )
            )
        )
    )

    # Rejected rows cannot be stored in LGDPublication
    list_rejected_lgd_publications = (
        LGDMinedPublication.objects.select_related("mined_publication", "lgd")
        .annotate(
            mined_pmid=F("mined_publication__pmid"),
            g2p_id=F("lgd__stable_id__stable_id"),
        )
        .filter(
            Exists(
                LGDPublication.objects.filter(
                    lgd=OuterRef("lgd"),
                    publication__pmid=OuterRef("mined_publication__pmid"),
                    is_deleted=0,
                )
            ),
            status="rejected",
        )
    )

    for obj in list_curated_lgd_publications:
        errors.append(
            Error(
                f"Record {obj.g2p_id} has mined publication PMID '{obj.mined_pmid}' with wrong status 'curated'",
                id="gene2phenotype_app.E501",
            )
        )

    for obj in list_rejected_lgd_publications:
        errors.append(
            Error(
                f"Record {obj.g2p_id} has mined publication PMID '{obj.mined_pmid}' with wrong status 'rejected'",
                id="gene2phenotype_app.E502",
            )
        )

    return errors
