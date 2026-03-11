import csv
import json
import logging
from pathlib import Path
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

Supported input formats: csv, json

The csv file format is the following:
    PMID\tG2P_IDs\trelevance_label
note: relevance_label is optional

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
        parser.add_argument(
            "--check_json",
            required=False,
            type=Path,
            help="Path to the JSON files containing the Gemini scores (output of gemini_publication_analyser.py)",
        )

    def handle(self, *args, **options):
        data_file = options["data_file"]
        input_email = options["email"]
        check_json_files = options["check_json"]
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

        # Get the Gemini scores to determine which PMIDs to skip
        pmids_to_skip = {}
        gemini_scores = {}
        if check_json_files and os.path.isdir(check_json_files):
            for json_file in Path(check_json_files).glob("*.json"):
                with open(json_file) as f:
                    check_json_data = json.load(f)
                    for g2p_record in check_json_data:
                        for publication in g2p_record["publications"]:
                            if publication["status"] is None:
                                continue

                            if publication["status"] == "low":
                                if g2p_record["id"] in pmids_to_skip:
                                    pmids_to_skip[g2p_record["id"]].add(publication["id"])
                                else:
                                    pmids_to_skip[g2p_record["id"]] = {publication["id"]}
                            else:
                                if publication["status"] == "incomplete":
                                    score_comment = "No access to this publication"
                                    score = "N/A"
                                else:
                                    score = publication["status"]
                                    score_comment = publication["comment"]
                                    if publication["fulltext"] is not None:
                                        score_comment += " (Score based on full text)"
                                    else:
                                        score_comment += " (Score based on abstract only)"

                                if g2p_record["id"] in gemini_scores:
                                    if publication["id"] not in gemini_scores[g2p_record["id"]]:
                                        gemini_scores[g2p_record["id"]][publication["id"]] = {
                                                "score": score,
                                                "comment": score_comment
                                            }
                                else:
                                    gemini_scores[g2p_record["id"]] = {
                                        publication["id"]: {
                                            "score": score,
                                            "comment": score_comment
                                        }
                                    }

        # for g2p_id in gemini_scores:
        #     print("->", g2p_id, gemini_scores[g2p_id])

        invalid_g2p_ids = set()

        all_records, publication_counts = self.get_all_record_publications()

        # Open the file again to import the data
        with open(data_file, newline="", encoding="utf-8-sig") as fh_file, open(output_file, "w") as wr:
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

                if "relevance_label" in row:
                    relevant_publication = row["relevance_label"].strip()
                    if relevant_publication == "low":
                        logger.warning(f"Low score {pmid}-{g2p_ids}. Skipping import.")
                        continue

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

                    # Insert mined publication
                    mined_publication_obj = MinedPublication(
                        pmid=int(pmid),
                        title=title,
                        year=year,
                        date_upload=get_date_now(),
                    )
                    mined_publication_obj._history_user = user_obj
                    mined_publication_obj.save()

                for g2p_id in list_g2p_ids:
                    # Clean the IDs
                    new_g2p_id = re.sub(r'[\*."`)]+', "", g2p_id).strip()

                    # Check if the G2P ID-PMID has a low score in the Gemini output (json files)
                    if new_g2p_id in pmids_to_skip and int(pmid) in pmids_to_skip[new_g2p_id]:
                        logger.warning(f"Low score {pmid}-{new_g2p_id}. Skipping import.")
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

                            # Get scores (if available)
                            score = None
                            score_comment = None
                            if new_g2p_id in gemini_scores:
                                if int(pmid) in gemini_scores[g2p_id]:
                                    score = gemini_scores[g2p_id][int(pmid)]["score"]
                                    score_comment = gemini_scores[g2p_id][int(pmid)]["comment"]

                            lgd_mined_pub_obj = LGDMinedPublication(
                                lgd=lgd_obj,
                                mined_publication=mined_publication_obj,
                                status=status,
                                score=score,
                                score_comment=score_comment,
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