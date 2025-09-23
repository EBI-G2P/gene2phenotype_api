from django.test import TestCase
from django.urls import reverse
from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken

from gene2phenotype_app.models import (
    User,
    Disease,
)


class LGDAddDiseaseEndpoint(TestCase):
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
