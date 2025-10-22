import csv
import logging
import re
import os.path

from django.db.models import Count, F
from django.core.management.base import BaseCommand, CommandError

from ...utils import get_publication, clean_title, get_date_now

from gene2phenotype_app.models import (
    MinedPublication,
    LGDMinedPublication,
    LGDPublication,
    LocusGenotypeDisease,
    User,
)


"""
Command to load mined publications into G2P database.
The mined publications are going to be saved into tables 'mined_publications' and 'lgd_mined_publications'.
The command does not perform a bulk import because we want to populate the history tables - bulk updates
do not insert rows into history tables.

Supported input file: csv
File format is the following:
PMID\tG2P_IDs

How to run the command:
python manage.py load_mined_publications --data_file <csv data file> --email <user account email>
"""

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            "--data_file",
            required=True,
            type=str,
            help="Input file containing the mined publications (supported format: csv)",
        )
        parser.add_argument(
            "--email",
            required=True,
            type=str,
            help="User email to store in the history table",
        )

    def handle(self, *args, **options):
        data_file = options["data_file"]
        input_email = options["email"]
        output_file = "invalid_g2p_ids.txt"

        if not os.path.isfile(data_file):
            raise CommandError(f"Invalid file {data_file}")

        if not data_file.endswith(".csv"):
            raise CommandError(f"Unsupported file format {data_file}")

        # Define the mandatory input headers
        mandatory_headers = ["PMID", "G2P_IDs"]

        # Get user info
        try:
            user_obj = User.objects.get(email=input_email)
        except User.DoesNotExist:
            raise CommandError(f"Invalid user {input_email}")

        invalid_g2p_ids = set()
        g2p_records_skip = {}
        # filter_year = 2000

        all_records, publication_counts = self.get_all_record_publications()

        # Pre-process the file
        with open(data_file, newline="") as fh:
            data_reader = csv.DictReader(fh)

            # Check headers
            if not all(
                column in data_reader.fieldnames for column in mandatory_headers
            ):
                raise CommandError(
                    f"Missing data. Mandatory fields are: {mandatory_headers}"
                )

            for row in data_reader:
                pmid = row["PMID"].strip()
                g2p_ids = row["G2P_IDs"].strip()
                list_g2p_ids = g2p_ids.split(";")

                for g2p_id in list_g2p_ids:
                    # Clean the IDs
                    new_g2p_id = re.sub(r'[\*."`)]+', "", g2p_id).strip()

                    if new_g2p_id not in g2p_records_skip:
                        g2p_records_skip[new_g2p_id] = 1
                    else:
                        g2p_records_skip[new_g2p_id] += 1

        # Open the file again to import the data
        with open(data_file, newline="") as fh_file, open(output_file, "w") as wr:
            data_reader = csv.DictReader(fh_file)

            # Check headers
            if not all(
                column in data_reader.fieldnames for column in mandatory_headers
            ):
                raise CommandError(
                    f"Missing data. Mandatory fields are: {mandatory_headers}"
                )

            for row in data_reader:
                pmid = row["PMID"].strip()
                g2p_ids = row["G2P_IDs"].strip()

                if not pmid or not g2p_ids or not g2p_ids.startswith("G2P"):
                    logger.warning(f"Invalid PMID or G2P IDs in row {str(row)}")
                    continue

                list_g2p_ids = g2p_ids.split(";")
                # to make sure we don't try to insert duplicates
                final_list_g2p_ids = set()

                try:
                    mined_publication_obj = MinedPublication.objects.get(pmid=int(pmid))
                except MinedPublication.DoesNotExist:
                    response = get_publication(int(pmid))
                    if response["hitCount"] == 0:
                        logger.warning(f"Invalid PMID '{pmid}'. Skipping import.")
                        continue
                    title = clean_title(response["result"]["title"])
                    year = response["result"]["pubYear"]

                    # Filter the publications
                    # TODO: review
                    # Filter by date
                    # if int(year) <= filter_year:
                    #     logger.warning(f"Skipping old PMID '{pmid}' ({year})")
                    #     continue

                    # Insert mined publication
                    mined_publication_obj = MinedPublication(
                        pmid=int(pmid),
                        title=title,
                        year=year,
                        date_upload=get_date_now(),
                    )
                    mined_publication_obj._history_user = user_obj
                    mined_publication_obj.save()
                # else:
                    # The mined publication is in g2p but the date could still be old
                    # Check the year of the publication and skip if it's older than 'filter_year'
                    # if mined_publication_obj.year < filter_year:
                    #     logger.warning(f"Skipping old PMID '{pmid}' ({year})")
                    #     continue

                for g2p_id in list_g2p_ids:
                    # Clean the IDs
                    new_g2p_id = re.sub(r'[\*."`)]+', "", g2p_id).strip()

                    if g2p_records_skip[new_g2p_id] >= 100:
                        logger.warning(
                            f"G2P ID '{new_g2p_id}' has >= 100 mined publications. Skipping import."
                        )
                        continue

                    if (
                        new_g2p_id not in final_list_g2p_ids
                        and new_g2p_id not in invalid_g2p_ids
                    ):
                        # Get the LocusGenotypeDisease for the G2P ID
                        try:
                            lgd_obj = all_records[new_g2p_id]
                        except KeyError:
                            # The record could have been merged or deleted
                            logger.warning(
                                f"Invalid G2P ID '{new_g2p_id}'. Skipping import."
                            )
                            invalid_g2p_ids.add(new_g2p_id)
                            wr.write(new_g2p_id.replace(",", " ") + "\n")
                            continue

                        final_list_g2p_ids.add(new_g2p_id)

                        # Check number of publications linked to the record
                        # n_publications = 0
                        # if new_g2p_id in publication_counts:
                        #     n_publications = publication_counts[new_g2p_id]

                        # confidence = lgd_obj.confidence.value
                        # if n_publications >= 10 and (confidence == "definitive" or confidence == "strong") and int(mined_publication_obj.year) < 2020:
                        #     logger.warning(
                        #         f"G2P ID '{new_g2p_id}' (definitive) with {n_publications} publications. Skipping import."
                        #     )
                        #     continue

                        # Check if LGDMinedPublication already exists
                        try:
                            LGDMinedPublication.objects.get(
                                lgd=lgd_obj, mined_publication=mined_publication_obj
                            )
                        except LGDMinedPublication.DoesNotExist:
                            # Insert the LGDMinedPublication obj
                            # Before insertion we need to know if the LGD-publication association already exists
                            try:
                                LGDPublication.objects.get(
                                    lgd=lgd_obj, publication__pmid=pmid, is_deleted=0
                                )
                            except LGDPublication.DoesNotExist:
                                status = "mined"
                            else:
                                status = "curated"

                            lgd_mined_pub_obj = LGDMinedPublication(
                                lgd=lgd_obj,
                                mined_publication=mined_publication_obj,
                                status=status,
                                comment=None,
                            )
                            lgd_mined_pub_obj._history_user = user_obj
                            lgd_mined_pub_obj.save()
                        else:
                            logger.warning(
                                f"{new_g2p_id}-{pmid} already exists. Skipping import."
                            )

    def get_all_record_publications(self):
        """
        Get all records and associated number of publications.
        """
        all_records = {}
        publication_counts = {}

        lgd_publication_data = (
            LGDPublication.objects.filter(is_deleted=0)
                .annotate(g2p_id=F("lgd__stable_id__stable_id"))
                .values("g2p_id")
                .annotate(publication_count=Count("publication", distinct=True))
                .order_by("g2p_id")
            )

        for c in lgd_publication_data:
            publication_counts[c['g2p_id']] = c['publication_count']

        g2p_records_data = (
            LocusGenotypeDisease.objects.filter(is_deleted=0).select_related("stable_id")
        )

        for record in g2p_records_data:
            all_records[record.stable_id.stable_id] = record
        
        return all_records, publication_counts