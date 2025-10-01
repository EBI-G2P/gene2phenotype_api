import csv
import logging
import os.path

from django.core.management.base import BaseCommand, CommandError
from django.db.models import F

from ...utils import get_ontology, get_ontology_source

from gene2phenotype_app.models import (
    Disease,
    DiseaseOntologyTerm,
    OntologyTerm,
    Source,
    LocusGenotypeDisease,
    User,
    Attrib,
)


"""
Command to load Mondo disease ontologies into G2P database.

Supported input file: csv

How to run the command:
python manage.py load_disease_ontologies --data_file <csv data file> --email <user account email>
"""

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            "--data_file",
            required=True,
            type=str,
            help="Input file containing the disease ontologies (supported format: csv)",
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
        unique_diseases = {}

        if not os.path.isfile(data_file):
            raise CommandError(f"Invalid file {data_file}")

        if not data_file.endswith(".csv"):
            raise CommandError(f"Unsupported file format {data_file}")

        # Define the mandatory input headers
        mandatory_headers = [
            "g2p id",
            "G2P disease name",
            "OMIM",
            "exact match MONDO",
            "status",
        ]

        # Get user info
        try:
            user_obj = User.objects.get(email=input_email)
        except User.DoesNotExist:
            raise CommandError(f"Invalid user {input_email}")

        # Get disease attrib to insert into ontology
        try:
            attrib_obj = Attrib.objects.get(
                value="disease", type__code="ontology_term_group"
            )
        except Attrib.DoesNotExist:
            raise CommandError(
                "Attrib 'disease' type 'ontology_term_group' is missing from attrib table"
            )

        # Get attrib 'Data source' to insert into disease_ontology
        try:
            attrib_mapping_obj = Attrib.objects.get(
                value="Data source", type__code="ontology_mapping"
            )
        except Attrib.DoesNotExist:
            raise CommandError(
                "Attrib 'Data source' type 'ontology_mapping' is missing from attrib table"
            )

        # Get sources
        g2p_sources = {}
        source_list = Source.objects.all()
        for source_obj in source_list:
            g2p_sources[source_obj.name] = source_obj

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
                g2p_id = row["g2p id"].strip()
                disease_name = row["G2P disease name"].strip()
                omim_id = row["OMIM"].strip()
                ontology_to_add = row["exact match MONDO"].strip()
                status = row["status"].strip()

                if status == "DIFFERENT" or not ontology_to_add.startswith("MONDO"):
                    continue

                print(f"\n{g2p_id} -> to add {ontology_to_add}")

                source = get_ontology_source(ontology_to_add)
                # Get the source ID in G2P
                source_ontology_obj = g2p_sources[source]

                # Make sure Mondo always uses the same ID format
                if source == "Mondo":
                    ontology_to_add = ontology_to_add.replace("_", ":")

                if disease_name in unique_diseases:
                    if (
                        ontology_to_add
                        != unique_diseases[disease_name]["ontology_to_add"]
                    ):
                        logger.warning(
                            f"Trying to add different ontology to same disease: {disease_name}"
                        )
                    # Skip this import - it was already imported
                    continue
                else:
                    unique_diseases[disease_name] = {}
                    unique_diseases[disease_name]["ontology_to_add"] = ontology_to_add

                # Save the disease name associated with the g2p id
                record_disease = None
                record_disease_obj = None
                try:
                    record_obj = LocusGenotypeDisease.objects.get(
                        stable_id__stable_id=g2p_id
                    )
                except LocusGenotypeDisease.DoesNotExist:
                    logger.warning(f"Cannot find record '{g2p_id}'")
                else:
                    record_disease = record_obj.disease.name
                    record_disease_obj = record_obj.disease

                try:
                    Disease.objects.get(name=disease_name)
                except Disease.DoesNotExist:
                    if record_disease:
                        # The disease from the file could be missing commas or small characters
                        record_disease_tmp = (
                            record_disease.replace(",", "").replace(".", "").lower()
                        )
                        if disease_name.lower() != record_disease_tmp:
                            logger.warning(
                                f"Cannot find disease '{disease_name}'. Do you mean '{record_disease}'? Skipping '{ontology_to_add}'"
                            )
                            continue

                current_disease_ontologies = (
                    DiseaseOntologyTerm.objects.filter(disease__name=record_disease)
                    .annotate(ontology_accession_tmp=F("ontology_term__accession"))
                    .values_list("ontology_accession_tmp", flat=True)
                )

                if omim_id not in current_disease_ontologies:
                    logger.warning(
                        f"{omim_id} not found associated with disease '{disease_name}'. Skipping '{ontology_to_add}'\n"
                    )
                    continue

                # Get the ontology data from the source
                ontology = get_ontology(ontology_to_add, source)

                if not ontology:
                    logger.warning(f"Invalid ontology {ontology_to_add}")
                    continue

                ontology_term = ontology["label"]
                ontology_id = ontology["obo_id"]
                ontology_description = None

                if "description" in ontology and len(ontology["description"]):
                    ontology_description = ontology["description"][0]

                if not ontology_description:
                    ontology_description = ontology_term

                if ontology_id != ontology_to_add:
                    logger.warning(
                        f"Cannot find ontology '{ontology_to_add}' in {source}"
                    )

                try:
                    ontology_obj = OntologyTerm.objects.get(accession=ontology_to_add)
                except OntologyTerm.DoesNotExist:
                    ontology_obj = OntologyTerm(
                        accession=ontology_to_add,
                        term=ontology_term,
                        description=ontology_description,
                        source=source_ontology_obj,
                        group_type=attrib_obj,
                    )
                    ontology_obj._history_user = user_obj
                    ontology_obj.save()

                try:
                    DiseaseOntologyTerm.objects.get(
                        ontology_term=ontology_obj,
                        disease=record_disease_obj,
                    )
                except DiseaseOntologyTerm.DoesNotExist:
                    # Add the disease ontology
                    disease_ontology_obj = DiseaseOntologyTerm(
                        ontology_term=ontology_obj,
                        disease=record_disease_obj,
                        mapped_by_attrib=attrib_mapping_obj,
                    )
                    disease_ontology_obj._history_user = user_obj
                    disease_ontology_obj.save()
                    print(
                        f"Added ontology '{ontology_to_add}' to disease '{record_disease}'"
                    )
                else:
                    print(
                        f"Ontology '{ontology_to_add}' already associated with disease '{record_disease}'"
                    )
