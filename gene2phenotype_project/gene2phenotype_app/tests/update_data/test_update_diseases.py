from django.test import TestCase
from django.urls import reverse
from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken

from gene2phenotype_app.models import (
    User,
    Disease,
    DiseaseSynonym,
)


class UpdateDiseasesEndpoint(TestCase):
    """
    Test endpoint to update disease names
    """

    fixtures = [
        "gene2phenotype_app/fixtures/attribs.json",
        "gene2phenotype_app/fixtures/cv_molecular_mechanism.json",
        "gene2phenotype_app/fixtures/disease.json",
        "gene2phenotype_app/fixtures/disease_synonym.json",
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
        self.url_update = reverse("update_diseases")
        self.diseases_to_update = [
            {"id": 3, "name": "MICROPHTHALMIA SYNDROMIC"},
            {"id": 6, "name": "INTELLECTUAL DEVELOPMENTAL DISORDER X-LINKED"},
            {"id": 11, "name": "RAB27A-related Griscelli syndrome"},
        ]
        self.diseases_to_update_with_synonym = [
            {"id": 3, "name": "MICROPHTHALMIA SYNDROMIC", "add_synonym": True},
            {"id": 10, "name": "RAB27A-related Griscelli", "add_synonym": True},
        ]
        self.incorrect_disease_to_update = [
            {"id": 3000, "name": "MICROPHTHALMIA SYNDROMIC"},
            {"id": 6, "name": "INTELLECTUAL DEVELOPMENTAL DISORDER X-LINKED"},
        ]

    def test_update_invalid_disease(self):
        """
        Test updating an invalid disease
        """
        # Login
        user = User.objects.get(email="john@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        response = self.client.post(
            self.url_update,
            self.incorrect_disease_to_update,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 404)

        response_data = response.json()
        self.assertEqual(response_data["detail"], "No Disease matches the given query.")

    def test_no_permission(self):
        """
        Test updating diseases for non super user
        """
        # Login
        user = User.objects.get(email="user1@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        response = self.client.post(
            self.url_update,
            self.diseases_to_update,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)

    def test_invalid_input(self):
        """
        Test updating diseases with an invalid input
        """
        # Login
        user = User.objects.get(email="john@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        response = self.client.post(
            self.url_update, [{}], content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)

        response_data = response.json()
        self.assertEqual(
            response_data["error"],
            [{"error": "Both 'id' and 'name' are required."}],
        )

    def test_invalid_input_format(self):
        """
        Test updating diseases with an invalid input format
        """
        # Login
        user = User.objects.get(email="john@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        response = self.client.post(
            self.url_update, {"id": "", "name": ""}, content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)

        response_data = response.json()
        self.assertEqual(
            response_data["error"], "Request should be a list of diseases",
        )

    def test_update_diseases(self):
        """
        Test updating the disease names
        """
        # Login
        user = User.objects.get(email="john@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        response = self.client.post(
            self.url_update, self.diseases_to_update, content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)

        response_data = response.json()
        self.assertEqual(
            response_data["updated"],
            [
                {"id": 3, "name": "MICROPHTHALMIA SYNDROMIC"},
                {"id": 6, "name": "INTELLECTUAL DEVELOPMENTAL DISORDER X-LINKED"},
            ],
        )
        self.assertEqual(
            response_data["error"],
            [
                {
                    "id": 11,
                    "name": "RAB27A-related Griscelli syndrome",
                    "existing_id": 10,
                    "error": "A disease with the name 'RAB27A-related Griscelli syndrome' already exists.",
                }
            ],
        )

        # Test updated records
        disease_obj = Disease.objects.get(id=3)
        self.assertEqual(disease_obj.name, "MICROPHTHALMIA SYNDROMIC")
        history_records = Disease.history.all()
        self.assertEqual(len(history_records), 2)

    def test_update_disease_with_synonym(self):
        """
        Test updating the disease name and save current name as synonym
        """
        # Login
        user = User.objects.get(email="john@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        response = self.client.post(
            self.url_update, self.diseases_to_update_with_synonym, content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)

        response_data = response.json()
        self.assertEqual(
            response_data["updated"],
            [
                {"id": 3, "name": "MICROPHTHALMIA SYNDROMIC"},
            ],
        )
        self.assertEqual(
            response_data["error"],
            [
                {"id": 10,
                 "name": "RAB27A-related Griscelli",
                 "error": "Disease is associated with multiple records."},
            ],
        )

        # Test updated records
        disease_obj = Disease.objects.get(id=3)
        self.assertEqual(disease_obj.name, "MICROPHTHALMIA SYNDROMIC")
        disease_synonym_obj = DiseaseSynonym.objects.get(disease=disease_obj)
        self.assertEqual(disease_synonym_obj.synonym, "MICROPHTHALMIA SYNDROMIC TYPE 9")
