from django.test import TestCase
from django.urls import reverse
from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken
from gene2phenotype_app.models import User


class LGDGetCurationDraftEndpoint(TestCase):
    """
    Test endpoint to get curation draft
    """

    fixtures = [
        "gene2phenotype_app/fixtures/g2p_stable_id.json",
        "gene2phenotype_app/fixtures/user_panels.json",
        "gene2phenotype_app/fixtures/curation_data.json",
    ]

    def setUp(self):
        self.url_get_curation = reverse(
            "curation_details", kwargs={"stable_id": "G2P00004"}
        )
        self.url_get_invalid_curation = reverse(
            "curation_details", kwargs={"stable_id": "G2P04444"}
        )
        self.url_get_no_curation = reverse(
            "curation_details", kwargs={"stable_id": "G2P00001"}
        )

    def test_get_curation_success(self):
        """
        Test successful call to get curation draft endpoint
        """
        # Login
        user = User.objects.get(email="user5@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        # Authenticate by setting cookie on the test client
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        response = self.client.get(self.url_get_curation)
        self.assertEqual(response.status_code, 200)

        self.assertEqual(response.data.get("session_name"), "test session")
        self.assertEqual(response.data.get("type"), "manual")
        self.assertEqual(response.data.get("curator_email"), "user5@test.ac.uk")

    def test_get_curation_unauthorised_access(self):
        """
        Test call to get curation draft without authentication
        """

        response = self.client.get(self.url_get_curation)
        self.assertEqual(response.status_code, 401)

    def test_get_curation_invalid(self):
        """
        Test call to get curation draft for an invalid stable id
        """
        # Login
        user = User.objects.get(email="user5@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        # Authenticate by setting cookie on the test client
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        response = self.client.get(self.url_get_invalid_curation)
        self.assertEqual(response.status_code, 404)

        response = response.json()
        self.assertEqual(response["error"], "No G2PStableID matches the given query.")

    def test_get_no_curation(self):
        """
        Test call to get curation draft that doesn't exist
        """
        # Login
        user = User.objects.get(email="user5@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        # Authenticate by setting cookie on the test client
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        response = self.client.get(self.url_get_no_curation)
        self.assertEqual(response.status_code, 404)

        response = response.json()
        self.assertEqual(response["error"], "No matching Entry found for: G2P00001")
