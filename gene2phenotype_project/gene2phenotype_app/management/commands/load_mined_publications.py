import csv
import logging
import re
import os.path
from datetime import datetime

from django.core.management.base import BaseCommand, CommandError

from ...utils import get_publication, clean_title, get_date_now

from gene2phenotype_app.models import (
    Publication,
    MinedPublication,
    LGDMinedPublication,
    LGDPublication,
    LocusGenotypeDisease,
    User,
)


"""
Command to load mined publications from a csv file.
The mined publications are going to be saved in tables 'mined_publications' and 'lgd_mined_publications'.

File format is the following:
PMID\tG2P_IDs
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

        print("Start:", datetime.now())

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

        with open(data_file, newline="") as fh_file:
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

                if not pmid or not g2p_ids or not isinstance(pmid, int):
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
                        raise CommandError(f"Invalid PMID {pmid}")
                    title = clean_title(response["result"]["title"])

                    # Insert mined publication
                    mined_publication_obj = MinedPublication(
                        pmid=int(pmid), title=title, date_upload=get_date_now()
                    )
                    mined_publication_obj._history_user = user_obj
                    mined_publication_obj.save()

                # Clean the IDs, just in case the ID includes the disease name
                for g2p_id in list_g2p_ids:
                    new_g2p_id = re.sub(":.*", "", g2p_id)

                    if new_g2p_id not in final_list_g2p_ids:
                        # Get the LocusGenotypeDisease for the G2P ID
                        try:
                            lgd_obj = LocusGenotypeDisease.objects.get(
                                stable_id__stable_id=new_g2p_id, is_deleted=0
                            )
                        except LocusGenotypeDisease.DoesNotExist:
                            # The record could have been merged or deleted
                            logger.warning(
                                f"Invalid G2P ID {new_g2p_id}. Skipping import."
                            )
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
                                lgd_publication_obj = LGDPublication.objects.get(
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

        print("End:", datetime.now())
