from collections import defaultdict

from django.db import migrations


def populate_and_deduplicate(apps, schema_editor):
    """
    LGDVariantType used to have a direct (nullable) publication FK, so the same
    variant type got a separate row per supporting publication.
    For each (lgd, variant_type_ot) group of rows:
      - keep the earliest row as canonical
      - copy every row's publication link into the new LGDVariantTypePublication join table
      - re-point any comments from the surplus duplicate rows onto the canonical row
      - merge the inherited/de_novo/unknown_inheritance flags (logical OR), matching the
        merge semantics the API already applied when displaying these duplicates
      - delete the surplus duplicate rows
    """
    LGDVariantType = apps.get_model("gene2phenotype_app", "LGDVariantType")
    LGDVariantTypePublication = apps.get_model(
        "gene2phenotype_app", "LGDVariantTypePublication"
    )
    LGDVariantTypeComment = apps.get_model(
        "gene2phenotype_app", "LGDVariantTypeComment"
    )

    groups = defaultdict(list)
    for row in LGDVariantType.objects.all().order_by("id"):
        groups[(row.lgd_id, row.variant_type_ot_id)].append(row)

    for rows in groups.values():
        canonical = rows[0]

        for row in rows:
            if row.publication_id:
                LGDVariantTypePublication.objects.get_or_create(
                    lgd_variant_type_id=canonical.id,
                    publication_id=row.publication_id,
                    defaults={"is_deleted": row.is_deleted},
                )

        for row in rows[1:]:
            LGDVariantTypeComment.objects.filter(lgd_variant_type_id=row.id).update(
                lgd_variant_type_id=canonical.id
            )
            canonical.inherited = canonical.inherited or row.inherited
            canonical.de_novo = canonical.de_novo or row.de_novo
            canonical.unknown_inheritance = (
                canonical.unknown_inheritance or row.unknown_inheritance
            )
            if row.is_deleted == 0:
                canonical.is_deleted = 0
            row.delete()

        canonical.save()


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("gene2phenotype_app", "0021_add_lgd_variant_type_publication"),
    ]

    operations = [
        migrations.RunPython(populate_and_deduplicate, noop_reverse),
    ]
