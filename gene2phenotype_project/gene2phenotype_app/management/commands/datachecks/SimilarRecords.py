from django.core.checks import Error
from django.db.models import F

from gene2phenotype_app.models import LocusGenotypeDisease


def get_similar_records():
    errors = []
    list_of_records = {}

    lgd_records = (
        LocusGenotypeDisease.objects.annotate(
            g2p_id=F("stable_id__stable_id"),
            disease_name=F("disease__name"),
            locus_name=F("locus__name"),
            genotype_value=F("genotype__value"),
            mechanism_value=F("mechanism__value"),
        )
        .filter(lgdpanel__panel__is_visible=1, is_deleted=0)
        .values(
            "g2p_id", "disease_name", "locus_name", "genotype_value", "mechanism_value"
        )
        .distinct()
    )

    for obj in lgd_records:
        key = f"{obj['locus_name']}---{obj['disease_name']}---{obj['genotype_value']}"

        if key not in list_of_records:
            list_of_records[key] = [
                {"g2p_id": obj["g2p_id"], "mechanism": obj["mechanism_value"]}
            ]
        elif obj["g2p_id"] not in list_of_records[key]:
            list_of_records[key].append(
                {"g2p_id": obj["g2p_id"], "mechanism": obj["mechanism_value"]}
            )

    for key, items in list_of_records.items():
        if len(items) > 1:
            has_undetermined = any(
                obj.get("mechanism") == "undetermined" for obj in items
            )
            if has_undetermined:
                all_g2p_ids = [obj["g2p_id"] for obj in items]
                errors.append(
                    Error(
                        f"Records with same locus, disease, genotype and one has undetermined mechanism: {', '.join(all_g2p_ids)}",
                        id="gene2phenotype_app.E601",
                    )
                )

    return errors
