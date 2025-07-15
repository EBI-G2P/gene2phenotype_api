from django.core.management.base import BaseCommand
import logging

from .datachecks import (
    check_publication_families,
    check_ar_constraint,
    check_ar_publications,
    mutation_consequence_constraint,
    check_cross_references,
)

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Check for issues in the data"

    def handle(self, *args, **kwargs):
        print("Running data checks ...")

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

        # Run the disease cross references check
        # This check is non critical: level = WARNING
        disease_cr_errors = check_cross_references()
        for error in disease_cr_errors:
            logger.warning(error)
