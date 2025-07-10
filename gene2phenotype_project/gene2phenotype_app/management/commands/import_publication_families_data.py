import csv

from django.core.management.base import BaseCommand, CommandError
from gene2phenotype_app.models import (
    Attrib,
    Publication,
    LGDPublication,
    LocusGenotypeDisease,
)


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            "--data_file",
            required=True,
            type=str,
            help="Input file with publication families data",
        )

    def handle(self, *args, **options):
        data_file = options["data_file"]

        with open(data_file, newline="") as fh_file:
            data_reader = csv.DictReader(fh_file)
            for row in data_reader:
                # Get consanguinity object
                consanguinity_value = row["consanguinity"].strip()
                try:
                    consanguinity_obj = Attrib.objects.get(
                        value=consanguinity_value, type__code="consanguinity"
                    )
                except Attrib.DoesNotExist:
                    raise CommandError(f"Invalid consanguinity '{consanguinity_value}'")

                # Get publication object
                pmid_value = row["pmid"].strip()
                try:
                    publication_obj = Publication.objects.get(pmid=pmid_value)
                except Publication.DoesNotExist:
                    raise CommandError(f"Invalid PMID '{pmid_value}'")

                # Get record object
                lgd_id = row["lgd_id"].strip()
                try:
                    lgd_obj = LocusGenotypeDisease.objects.get(id=lgd_id)
                except LocusGenotypeDisease.DoesNotExist:
                    raise CommandError(f"Invalid record ID '{lgd_id}'")

                # Get the LGDPublication obj to be updated
                try:
                    lgd_publication_obj = LGDPublication.objects.get(
                        lgd=lgd_obj, publication=publication_obj
                    )
                except LGDPublication.DoesNotExist:
                    raise CommandError(
                        f"Cannot fetch lgd-publication {lgd_id}-{publication_obj.id}"
                    )

                # Checking if lgd-publication already has families counts
                if lgd_publication_obj.number_of_families:
                    raise CommandError(
                        f"Cannot update lgd-publication {lgd_id}-{publication_obj.id} as it already has families data"
                    )

                try:
                    lgd_publication_obj.number_of_families = row[
                        "number of families"
                    ].strip()
                    lgd_publication_obj.consanguinity = consanguinity_obj
                    lgd_publication_obj.affected_individuals = row[
                        "affected individuals"
                    ].strip()
                    lgd_publication_obj.ancestry = row["ancestries"].strip()
                    lgd_publication_obj.save()
                except Exception as e:
                    raise CommandError(
                        f"Cannot save data for PMID '{pmid_value}' for record '{lgd_id}'",
                        str(e),
                    )
                else:
                    self.stdout.write("Data updated successfully")
