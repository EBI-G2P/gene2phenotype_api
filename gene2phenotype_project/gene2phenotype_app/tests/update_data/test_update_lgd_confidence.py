from django.test import TestCase
from django.urls import reverse
from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken
from gene2phenotype_app.models import User


class LGDUpdateLGDConfidence(TestCase):
    """
    Test endpoint to update the record confidence
    """

    fixtures = [
        "gene2phenotype_app/fixtures/attribs.json",
        "gene2phenotype_app/fixtures/cv_molecular_mechanism.json",
        "gene2phenotype_app/fixtures/disease.json",
        "gene2phenotype_app/fixtures/g2p_stable_id.json",
        "gene2phenotype_app/fixtures/lgd_mechanism_evidence.json",
        "gene2phenotype_app/fixtures/lgd_mechanism_synopsis.json",
        "gene2phenotype_app/fixtures/lgd_panel.json",
        "gene2phenotype_app/fixtures/lgd_publication.json",
        "gene2phenotype_app/fixtures/locus_genotype_disease.json",
        "gene2phenotype_app/fixtures/locus.json",
        "gene2phenotype_app/fixtures/publication.json",
        "gene2phenotype_app/fixtures/sequence.json",
        "gene2phenotype_app/fixtures/user_panels.json",
        "gene2phenotype_app/fixtures/ontology_term.json",
        "gene2phenotype_app/fixtures/source.json",
    ]

    def setUp(self):
        self.url_lgd_confidence = reverse(
            "lgd_update_confidence", kwargs={"stable_id": "G2P00001"}
        )

        # Setup login
        user = User.objects.get(email="user5@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        self.access_token = str(refresh.access_token)

    def test_invalid_update(self):
        """
        Test updating confidence with invalid input data
        """
        input_data = {}

        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = self.access_token

        response = self.client.put(
            self.url_lgd_confidence, input_data, content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)

        response_data = response.json()
        expected_error = {"confidence": ["This field is required."]}
        self.assertEqual(response_data["error"], expected_error)

    def test_no_permission(self):
        """
        Test updating record confidence without being authenticated
        """
        input_data = {"confidence": "definitive"}

        response = self.client.put(
            self.url_lgd_confidence, input_data, content_type="application/json"
        )
        self.assertEqual(response.status_code, 401)

    def test_update_same_value(self):
        """
        Test updating the confidence to the same value
        """
        input_data = {"confidence": "definitive"}

        # Authenticate by setting cookie on the test client
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = self.access_token

        response = self.client.put(
            self.url_lgd_confidence, input_data, content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)

        response_data = response.json()
        self.assertEqual(
            response_data["error"],
            "G2P record 'G2P00001' already has confidence value definitive",
        )

    def test_valid_update(self):
        """
        Test successfully updating the record confidence
        """
        input_data = {"confidence": "limited"}

        # Authenticate by setting cookie on the test client
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = self.access_token

        response = self.client.put(
            self.url_lgd_confidence, input_data, content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)

        response_data = response.json()
        self.assertEqual(
            response_data["message"], "Data updated successfully for 'G2P00001'"
        )

    def test_insufficient_publications(self):
        """
        Test updating the confidence with insufficient number of publications
        """
        input_data = {"confidence": "strong"}

        # Authenticate by setting cookie on the test client
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = self.access_token

        response = self.client.put(
            self.url_lgd_confidence, input_data, content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)

        response_data = response.json()
        self.assertEqual(
            response_data["error"],
            "Cannot assign confidence 'strong' with only 1 publication(s) as evidence",
        )
