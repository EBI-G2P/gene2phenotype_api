import csv
import logging
import re
import os.path

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
        filter_year = 2010

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

                    # TODO: review
                    if int(year) <= filter_year:
                        logger.warning(f"Skipping old PMID '{pmid}' ({year})")
                        continue

                    # Insert mined publication
                    mined_publication_obj = MinedPublication(
                        pmid=int(pmid), title=title, date_upload=get_date_now()
                    )
                    mined_publication_obj._history_user = user_obj
                    mined_publication_obj.save()
                else:
                    # The mined publication is in g2p but the date could still be old
                    # Check the year of the publication and skip if it's older than 'filter_year'
                    if mined_publication_obj.year < filter_year:
                        logger.warning(f"Skipping old PMID '{pmid}' ({year})")
                        continue

                for g2p_id in list_g2p_ids:
                    # Clean the IDs
                    new_g2p_id = re.sub(r'[\*."`)]+', '', g2p_id).strip()

                    if new_g2p_id not in final_list_g2p_ids and new_g2p_id not in invalid_g2p_ids:
                        # Get the LocusGenotypeDisease for the G2P ID
                        try:
                            lgd_obj = LocusGenotypeDisease.objects.get(
                                stable_id__stable_id=new_g2p_id, is_deleted=0
                            )
                        except LocusGenotypeDisease.DoesNotExist:
                            # The record could have been merged or deleted
                            logger.warning(
                                f"Invalid G2P ID '{new_g2p_id}'. Skipping import."
                            )
                            invalid_g2p_ids.add(new_g2p_id)
                            wr.write(new_g2p_id+"\n")
                            continue

                        final_list_g2p_ids.add(new_g2p_id)

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

        print("\n---\nNumber of invalid G2P IDs:", len(invalid_g2p_ids))
