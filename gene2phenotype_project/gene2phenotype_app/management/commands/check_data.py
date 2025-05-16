from django.core.management.base import BaseCommand
import logging

from .datachecks import (
    check_model_constraints,
    check_ar_constraint,
    mutation_consequence_constraint,
    check_cross_references
)

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Check for issues in the data"

    def handle(self, *args, **kwargs):
        print("Running data checks ...")

        publication_families_errors = check_model_constraints()
        if publication_families_errors:
            for error in publication_families_errors:
                logger.error(error)

        allelic_errors = check_ar_constraint()
        if allelic_errors:
            for error in allelic_errors:
                logger.error(error)

        mc_errors = mutation_consequence_constraint()
        if mc_errors:
            for error in mc_errors:
                logger.error(error)

        # Run the disease cross references check
        # This check is non critical: level = WARNING
        disease_cr_errors = check_cross_references()
        if disease_cr_errors:
            for error in disease_cr_errors:
                logger.warning(error)