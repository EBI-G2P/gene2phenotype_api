from django.test import TestCase
from django.urls import reverse
from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken
from gene2phenotype_app.models import User


class LGDListCurationDraftsEndpoint(TestCase):
    """
    Test endpoint to list curation drafts
    """

    fixtures = [
        "gene2phenotype_app/fixtures/g2p_stable_id.json",
        "gene2phenotype_app/fixtures/user_panels.json",
        "gene2phenotype_app/fixtures/curation_data.json",
    ]

    def setUp(self):
        self.url_list_curation = reverse("list_curation_entries")

    def test_list_curation_success_default(self):
        """
        Test successful call to list curation drafts endpoint without query parameters
        Should retrieve manual drafts of specific user (default)
        """
        # Login
        user = User.objects.get(email="user5@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        # Authenticate by setting cookie on the test client
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        response = self.client.get(self.url_list_curation)
        self.assertEqual(response.status_code, 200)

        self.assertEqual(response.data.get("count"), 1)
        self.assertEqual(response.data.get("results")[0]["type"], "manual")

    def test_list_curation_success_with_scope_all(self):
        """
        Test successful call to list curation drafts endpoint with 'scope' = 'all'
        Should retrieve manual drafts of all users
        """
        # Login
        user = User.objects.get(email="user5@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        # Authenticate by setting cookie on the test client
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        url = f"{self.url_list_curation}?scope=all"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        self.assertEqual(response.data.get("count"), 2)
        self.assertTrue(
            all(item["type"] == "manual" for item in response.data.get("results"))
        )

    def test_list_curation_success_with_type_manual(self):
        """
        Test successful call to list curation drafts endpoint with 'type' = 'manual'
        Should retrieve manual drafts of specific user
        """
        # Login
        user = User.objects.get(email="user5@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        # Authenticate by setting cookie on the test client
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        url = f"{self.url_list_curation}?type=manual"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        self.assertEqual(response.data.get("count"), 1)
        self.assertEqual(response.data.get("results")[0]["type"], "manual")

    def test_list_curation_success_with_type_manual_and_scope_all(self):
        """
        Test successful call to list curation drafts endpoint with 'type' = 'manual' and 'scope' = 'all'
        Should retrieve manual drafts of all users
        """
        # Login
        user = User.objects.get(email="user5@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        # Authenticate by setting cookie on the test client
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        url = f"{self.url_list_curation}?type=manual&scope=all"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        self.assertEqual(response.data.get("count"), 2)
        self.assertTrue(
            all(item["type"] == "manual" for item in response.data.get("results"))
        )

    def test_list_curation_success_with_type_automatic(self):
        """
        Test successful call to list curation drafts endpoint with 'type' = 'automatic'
        Should retrieve automatic drafts of specific user
        """
        # Login
        user = User.objects.get(email="user5@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        # Authenticate by setting cookie on the test client
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        url = f"{self.url_list_curation}?type=automatic"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        self.assertEqual(response.data.get("count"), 1)
        self.assertEqual(response.data.get("results")[0]["type"], "automatic")

    def test_list_curation_success_with_type_automatic_and_scope_all(self):
        """
        Test successful call to list curation drafts endpoint with 'type' = 'automatic' and 'scope' = 'all'
        Should retrieve automatic drafts of all users
        """
        # Login
        user = User.objects.get(email="user5@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        # Authenticate by setting cookie on the test client
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        url = f"{self.url_list_curation}?type=automatic&scope=all"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        self.assertEqual(response.data.get("count"), 2)
        self.assertTrue(
            all(item["type"] == "automatic" for item in response.data.get("results"))
        )

    def test_list_curation_with_invalid_scope(self):
        """
        Test call to list curation drafts endpoint with invalid 'scope' value
        """
        # Login
        user = User.objects.get(email="user5@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        # Authenticate by setting cookie on the test client
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        url = f"{self.url_list_curation}?scope=dummy"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 400)

        response_data = response.json()
        self.assertEqual(
            response_data["error"],
            "Invalid value provided for query parameter 'scope'",
        )

    def test_list_curation_unauthorised_access(self):
        """
        Test call to list curation drafts endpoint without authentication
        """

        response = self.client.get(self.url_list_curation)
        self.assertEqual(response.status_code, 401)
