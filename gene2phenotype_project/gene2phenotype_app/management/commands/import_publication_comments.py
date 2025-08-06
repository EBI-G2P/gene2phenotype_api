import csv
from datetime import datetime

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from gene2phenotype_app.models import (
    Publication,
    LGDPublication,
    LGDPublicationComment,
    LocusGenotypeDisease,
    User,
)


"""
Command to import the record publication comments from a csv file.
File format is the following:
    g2p id,lgd_id,pmid,publication_id,comment,user_id,username,date,id_deleted
"""


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            "--data_file",
            required=True,
            type=str,
            help="Input file with publication comments linked to records",
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

        # Get user info
        try:
            user_obj = User.objects.get(email=input_email)
        except Exception as e:
            raise CommandError(str(e))

        with open(data_file, newline="") as fh_file:
            data_reader = csv.DictReader(fh_file)
            for row in data_reader:
                # Format date
                date_formatted = datetime.strptime(
                    row["date"].strip(), "%d/%m/%Y %H:%M"
                )
                date_aware = timezone.make_aware(date_formatted)

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

                # Get the LGDPublication obj
                try:
                    lgd_publication_obj = LGDPublication.objects.get(
                        lgd=lgd_obj, publication=publication_obj
                    )
                except LGDPublication.DoesNotExist:
                    raise CommandError(
                        f"Cannot fetch lgd-publication {lgd_id}-{publication_obj.id}"
                    )

                # Get user who wrote the comment
                try:
                    user_comment_obj = User.objects.get(id=row["user_id"].strip())
                except Exception as e:
                    raise CommandError(str(e))

                # Create comment for the LGDPublication
                try:
                    comment_obj = LGDPublicationComment.objects.get(
                        lgd_publication=lgd_publication_obj,
                        comment=row["comment"].strip(),
                        is_public=0,
                        is_deleted=0,
                        date=date_aware,
                        user=user_comment_obj,
                    )
                except LGDPublicationComment.DoesNotExist:
                    comment_obj = LGDPublicationComment(
                        lgd_publication=lgd_publication_obj,
                        comment=row["comment"].strip(),
                        is_public=0,
                        is_deleted=0,
                        date=date_aware,
                        user=user_comment_obj,
                    )
                    comment_obj._history_user = user_obj
                    comment_obj.save()
                    self.stdout.write("LGDPublicationComment created successfully")
                else:
                    raise CommandError(
                        f"Duplicate LGDPublicationComment: PMID {pmid_value} for {row['g2p id']}"
                    )
