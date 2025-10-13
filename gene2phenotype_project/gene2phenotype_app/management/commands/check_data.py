from django.core.management.base import BaseCommand
import logging

from .datachecks import (
    check_publication_families,
    check_ar_constraint,
    check_ar_publications,
    mutation_consequence_constraint,
    check_mined_publication_status,
    check_cross_references,
    check_disease_name,
    get_similar_records,
)

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Check for issues in the data"

    def add_arguments(self, parser):
        parser.add_argument(
            "--include_warnings",
            required=False,
            action='store_true',
            help="Include non-critical data checks",
        )

    def handle(self, *args, **options):
        include_warnings = options["include_warnings"]

        print("Running data checks...")

        publication_families_errors = check_publication_families()
        for error in publication_families_errors:
            logger.error(error)

        allelic_requirement_errors = check_ar_constraint()
        for error in allelic_requirement_errors:
            logger.error(error)

        allelic_requirement_errors_2 = check_ar_publications()
        for error in allelic_requirement_errors_2:
            logger.error(error)

        mc_errors = mutation_consequence_constraint()
        for error in mc_errors:
            logger.error(error)

        mined_publication_status = check_mined_publication_status()
        for error in mined_publication_status:
            logger.error(error)

        # Check if the locus is in the disease name
        disease_name_errors = check_disease_name()
        for error in disease_name_errors:
            logger.error(error)

        print("Running data checks... done")

        ### The following checks are non critical: level = WARNING ###
        if include_warnings:
            print("\nRunning non-critical data checks...")
            # Check for similar records
            similar_records = get_similar_records()
            for error in similar_records:
                logger.warning(error)

            # Run the disease cross references check
            disease_cr_errors = check_cross_references()
            for error in disease_cr_errors:
                logger.warning(error)
            print("Running non-critical data checks... done")
