from django.test import TestCase
from django.urls import reverse
from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken

from gene2phenotype_app.models import (
    User,
    Disease,
    DiseaseOntologyTerm,
)


class AddDiseaseEndpoint(TestCase):
    """
    Test endpoint to add a disease
    """

    fixtures = [
        "gene2phenotype_app/fixtures/attribs.json",
        "gene2phenotype_app/fixtures/cv_molecular_mechanism.json",
        "gene2phenotype_app/fixtures/disease.json",
        "gene2phenotype_app/fixtures/g2p_stable_id.json",
        "gene2phenotype_app/fixtures/lgd_mechanism_evidence.json",
        "gene2phenotype_app/fixtures/lgd_mechanism_synopsis.json",
        "gene2phenotype_app/fixtures/lgd_panel.json",
        "gene2phenotype_app/fixtures/locus_genotype_disease.json",
        "gene2phenotype_app/fixtures/locus.json",
        "gene2phenotype_app/fixtures/publication.json",
        "gene2phenotype_app/fixtures/sequence.json",
        "gene2phenotype_app/fixtures/user_panels.json",
        "gene2phenotype_app/fixtures/ontology_term.json",
        "gene2phenotype_app/fixtures/source.json",
    ]

    def setUp(self):
        self.url_add_disease = reverse("add_disease")
        self.add_existing_disease = {
            "name": "RAB27A-related Griscelli syndrome biallelic"
        }
        self.add_new_disease = {"name": "LDLR-related hypercholesterolaemia"}
        self.add_disease_with_ontology = {
            "name": "STRA6-related syndromic microphthalmia",
            "ontology_terms": [
                {
                    "accession": "MONDO:0011010",
                    "term": "Matthew-Wood syndrome",
                    "description": None,
                    "source": "Mondo",
                }
            ],
        }
        self.add_disease_with_invalid_ontology = {
            "name": "STRA6-related syndromic microphthalmia 2",
            "ontology_terms": [
                {
                    "accession": "MONDO:00000000000",
                    "term": "syndrome",
                    "description": None,
                    "source": "Mondo",
                }
            ],
        }
        self.add_disease_with_invalid_ontology_source = {
            "name": "STRA6-related moebius syndrome",
            "ontology_terms": [
                {
                    "accession": "Orphanet:570",
                    "term": "Moebius syndrome",
                    "description": None,
                    "source": "Orphanet",
                }
            ],
        }

    def test_add_no_permission(self):
        """
        Test the endpoint to add disease for non super user
        """
        # Login
        user = User.objects.get(email="user1@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        response = self.client.post(
            self.url_add_disease,
            self.add_new_disease,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)

    def test_add_disease(self):
        """
        Test the endpoint to add a disease
        """
        # Login
        user = User.objects.get(email="john@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        response = self.client.post(
            self.url_add_disease,
            self.add_new_disease,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)

        response_data = response.json()
        self.assertIn("id", response_data)
        self.assertIn("name", response_data)

        # Check inserted data
        diseases = Disease.objects.filter(name="LDLR-related hypercholesterolaemia")
        self.assertEqual(len(diseases), 1)
        # Test the Disease history table
        history_records = Disease.history.all()
        self.assertEqual(len(history_records), 1)

    def test_add_disease_with_ontology(self):
        """
        Test the endpoint to add a disease with ontologies
        """
        # Login
        user = User.objects.get(email="john@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        response = self.client.post(
            self.url_add_disease,
            self.add_disease_with_ontology,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)

        response_data = response.json()
        self.assertIn("id", response_data)
        self.assertIn("name", response_data)

        # Check inserted data
        diseases = Disease.objects.filter(name="STRA6-related syndromic microphthalmia")
        self.assertEqual(len(diseases), 1)
        disease_ontologies = DiseaseOntologyTerm.objects.filter(disease=diseases[0])
        self.assertEqual(len(disease_ontologies), 1)
        # # Test the history tables
        history_records = Disease.history.all()
        self.assertEqual(len(history_records), 1)
        history_ontologies_records = DiseaseOntologyTerm.history.all()
        self.assertEqual(len(history_ontologies_records), 1)

    def test_add_duplicate_disease(self):
        """
        Test the endpoint to add a disease that already exists
        """
        # Login
        user = User.objects.get(email="john@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        response = self.client.post(
            self.url_add_disease,
            self.add_existing_disease,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

        response_data = response.json()
        self.assertEqual(
            response_data["name"], ["disease with this name already exists."]
        )

    def test_add_disease_with_invalid_ontology(self):
        """
        Test the endpoint to add a disease with an invalid ontology
        """
        # Login
        user = User.objects.get(email="john@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        response = self.client.post(
            self.url_add_disease,
            self.add_disease_with_invalid_ontology,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

        response_data = response.json()
        self.assertEqual(
            response_data["error"], "Invalid Mondo ID. Please check ID 'MONDO:00000000000'"
        )

    def test_add_disease_with_invalid_ontology_source(self):
        """
        Test the endpoint to add a disease with an invalid ontology source
        """
        # Login
        user = User.objects.get(email="john@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        response = self.client.post(
            self.url_add_disease,
            self.add_disease_with_invalid_ontology_source,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

        response_data = response.json()
        self.assertEqual(
            response_data["error"], "Invalid ID 'Orphanet:570'. Please input a valid ID from OMIM or Mondo"
        )