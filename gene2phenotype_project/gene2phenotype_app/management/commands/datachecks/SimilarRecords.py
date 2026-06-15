from django.core.checks import Error
from django.db.models import F

from gene2phenotype_app.models import LGDPanel, LGDPublication, LocusGenotypeDisease

from .Base import should_process


def get_similar_records():
    """Check for visible records that share locus, disease, and genotype with an undetermined mechanism."""
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
        else:
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


def get_records_with_publication_overlap():
    """Check for non-deleted records sharing at least 60% of publications within a locus."""
    errors = []
    overlap_threshold = 0.6
    records_by_locus = {}
    panels_by_record = {}
    publications_by_record = {}

    lgd_records = (
        LocusGenotypeDisease.objects.annotate(g2p_id=F("stable_id__stable_id"))
        .filter(is_deleted=0)
        .values("id", "g2p_id", "locus_id", "disease_id", "genotype_id", "mechanism_id")
    )

    for obj in lgd_records:
        if not should_process(obj["id"]):
            continue

        records_by_locus.setdefault(obj["locus_id"], []).append(
            {
                "id": obj["id"],
                "g2p_id": obj["g2p_id"],
                "disease_id": obj["disease_id"],
                "genotype_id": obj["genotype_id"],
                "mechanism_id": obj["mechanism_id"],
            }
        )

    lgd_panels = LGDPanel.objects.filter(is_deleted=0).values("lgd_id", "panel_id")
    for obj in lgd_panels:
        panels_by_record.setdefault(obj["lgd_id"], set()).add(obj["panel_id"])

    lgd_publications = (
        LGDPublication.objects.annotate(pmid=F("publication__pmid"))
        .filter(is_deleted=0, lgd__is_deleted=0)
        .values("lgd_id", "pmid")
    )

    for obj in lgd_publications:
        publications_by_record.setdefault(obj["lgd_id"], set()).add(obj["pmid"])

    for records in records_by_locus.values():
        if len(records) < 2:
            continue

        for index, record in enumerate(records):
            record_publications = publications_by_record.get(record["id"], set())
            if not record_publications:
                continue

            for candidate in records[index + 1 :]:
                if record["disease_id"] == candidate["disease_id"]:
                    continue
                if record["genotype_id"] != candidate["genotype_id"]:
                    continue

                candidate_publications = publications_by_record.get(candidate["id"], set())
                if not candidate_publications:
                    continue

                shared_publications = record_publications & candidate_publications
                minimum_publications = min(
                    len(record_publications), len(candidate_publications)
                )

                if minimum_publications == 0:
                    continue

                overlap = len(shared_publications) / minimum_publications
                if overlap >= overlap_threshold:
                    shared_pmids = ", ".join(sorted(str(pmid) for pmid in shared_publications))
                    errors.append(
                        Error(
                            f"Records share at least 60% of publications: {record['g2p_id']}, {candidate['g2p_id']}. Shared PMIDs: {shared_pmids}",
                            id="gene2phenotype_app.E602",
                        )
                    )

    return errors
