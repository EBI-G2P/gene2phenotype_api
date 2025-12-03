import json
import logging
import os.path

from django.core.management.base import BaseCommand, CommandError

from gene2phenotype_app.models import (
    LGDMinedPublication,
    User,
)


"""
Command to load the Gemini scores of the mined publications.
The scores are going to be saved into table 'lgd_mined_publications'.
The command does not perform a bulk import because we want to populate the history tables - bulk updates
do not insert rows into history tables.

Supported input file: json
This file is the output file of the Gemini analysis.

How to run the command:
python manage.py load_mined_publications_scores --data_file <json data file> --email <user account email>
"""

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            "--data_file",
            required=True,
            type=str,
            help="Input file containing the mined publications' scores (supported format: json)",
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

        if not os.path.isfile(data_file):
            raise CommandError(f"Invalid file {data_file}")

        if not data_file.endswith(".json"):
            raise CommandError(f"Unsupported file format {data_file}")

        # Get user info
        try:
            user_obj = User.objects.get(email=input_email)
        except User.DoesNotExist:
            raise CommandError(f"Invalid user {input_email}")

        n_scores = 0
        n_scores_updated = 0

        with open(data_file, newline="") as fh:
            data_reader = json.load(fh)
            for record_data in data_reader:
                g2p_id = record_data["id"]
                for publication in record_data["publications"]:
                    if publication["status"] and publication["status"] != "incomplete":
                        pmid = publication["id"]
                        score = publication["status"]
                        score_comment = publication["comment"]
                        full_text = publication["fulltext"]
                        n_scores += 1

                        if full_text:
                            score_comment += " (Score based on full text)"
                        else:
                            score_comment += " (Score based on abstract only)"

                        try:
                            lgd_mined_pub_obj = LGDMinedPublication.objects.get(
                                lgd_id__stable_id__stable_id=g2p_id,
                                mined_publication__pmid=pmid,
                                status="mined",
                            )
                        except LGDMinedPublication.DoesNotExist:
                            continue
                        else:
                            # Check if lgd_mined_publication already has a score
                            # If existing score is different from the new score, then update it
                            if (lgd_mined_pub_obj.score and lgd_mined_pub_obj.score != score) or not lgd_mined_pub_obj.score:
                                lgd_mined_pub_obj.score = score
                                lgd_mined_pub_obj.score_comment = score_comment
                                lgd_mined_pub_obj._history_user = user_obj
                                lgd_mined_pub_obj.save()
                                n_scores_updated += 1
        
        print(f"\nTotal scores in the input file: {n_scores}")
        print(f"Total scores updated in the database: {n_scores_updated}\n")
