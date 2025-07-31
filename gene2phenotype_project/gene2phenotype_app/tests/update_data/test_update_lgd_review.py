from django.test import TestCase
from django.urls import reverse
from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken
from gene2phenotype_app.models import (
    User,
    LocusGenotypeDisease,
)


class LGDEditLGDReview(TestCase):
    """
    Test endpoint to update the review status of the record
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
        self.url_lgd_review = reverse("lgd_review", kwargs={"stable_id": "G2P00001"})

    def test_invalid_update(self):
        """
        Test updating with invalid input
        """
        input_data = {}

        # Login
        user = User.objects.get(email="user5@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        # Authenticate by setting cookie on the test client
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        response = self.client.post(
            self.url_lgd_review, input_data, content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)

        response_data = response.json()
        expected_error = {"is_reviewed": ["This field is required."]}
        self.assertEqual(response_data["error"], expected_error)

    def test_no_permission(self):
        """
        Test updating review status without permission
        """
        input_data = {"is_reviewed": False}

        # Login
        user = User.objects.get(email="user1@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        # Authenticate by setting cookie on the test client
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        response = self.client.post(
            self.url_lgd_review, input_data, content_type="application/json"
        )
        self.assertEqual(response.status_code, 403)

    def test_update_same_value(self):
        """
        Test updating the status to the same value
        """
        input_data = {"is_reviewed": True}

        # Login
        user = User.objects.get(email="user5@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        # Authenticate by setting cookie on the test client
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        response = self.client.post(
            self.url_lgd_review, input_data, content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)

        response_data = response.json()
        self.assertEqual(response_data["error"], "G2P00001 is already set to reviewed")

    def test_valid_update(self):
        """
        Test updating a reviewed record to under review
        """
        input_data = {"is_reviewed": False}

        # Login
        user = User.objects.get(email="user5@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        # Authenticate by setting cookie on the test client
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        response = self.client.post(
            self.url_lgd_review, input_data, content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)

        response_data = response.json()
        self.assertEqual(
            response_data["message"], "G2P00001 successfully set to under review"
        )

        # Check the data
        lgd_obj = LocusGenotypeDisease.objects.get(stable_id__stable_id="G2P00001")
        self.assertEqual(lgd_obj.is_reviewed, 0)
