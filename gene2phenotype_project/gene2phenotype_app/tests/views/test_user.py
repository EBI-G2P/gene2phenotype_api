import json
from django.conf import settings
from django.test import TestCase
from django.urls import reverse
from gene2phenotype_app.models import User
from rest_framework_simplejwt.tokens import RefreshToken


def login(user):
    # trying to keep code dry
    # Create token for the user
    refresh = RefreshToken.for_user(user)
    access_token = str(refresh.access_token)

    # Authenticate by setting cookie on the test client

    return access_token


class UserPanelEndpointTests(TestCase):
    """
    Test the User Endpoint UserPanel
    """

    fixtures = ["gene2phenotype_app/fixtures/user_panels.json"]

    def setUp(self):
        self.url_user_panels = reverse("user_panels")

        user = User.objects.get(email="user5@test.ac.uk")

        access_token = login(user)
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

    def test_get_user_panels(self):
        """
        Test the response of the User endpoint
        """

        response = self.client.get(self.url_user_panels)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 3)


class CreateUserEndpointTest(TestCase):
    fixtures = ["gene2phenotype_app/fixtures/user_panels.json"]

    def setUp(self):
        self.url_create_user = reverse("create_user")

        user = User.objects.get(email="user5@test.ac.uk")

        access_token = login(user)
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

    def test_create_user(self):
        post_data = {
            "username": "test_user6",
            "email": "user6@test.ac.uk",
            "first_name": "First name test",
            "last_name": "Last name test",
            "password": "testpassword2",
            "password2": "testpassword2",
            "is_superuser": False,
            "is_staff": False,
            "panels": ["DD", "Ear"],
        }

        json_data = json.dumps(post_data)
        response = self.client.post(
            self.url_create_user, json_data, content_type="application/json"
        )
        self.assertEqual(response.status_code, 201)
        # test if the user was really created
        new_user = User.objects.get(username="test_user6")
        self.assertEqual(new_user.email, "user6@test.ac.uk")


class AddUserToPanelEndpointTest(TestCase):
    fixtures = ["gene2phenotype_app/fixtures/user_panels.json"]

    def setUp(self):
        self.url_add_to_panel = reverse("add_user_panel")

        user = User.objects.get(email="user5@test.ac.uk")

        access_token = login(user)

        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

    def test_add_user_to_panel(self):
        post_data = {"user": "user2@test.ac.uk", "panel": ["Eye"]}

        json_data = json.dumps(post_data)

        response = self.client.post(
            self.url_add_to_panel, json_data, content_type="application/json"
        )

        self.assertEqual(response.status_code, 201)


class LoginLogoutTest(TestCase):
    fixtures = ["gene2phenotype_app/fixtures/user_panels.json"]

    def setUp(self):
        self.url_login = reverse("_login")
        self.url_logout = reverse("logout")

    def test_login_success(self):
        data = {"username": "user5@test.ac.uk", "password": "test_user5"}

        # Login
        response = self.client.post(
            self.url_login, data, content_type="application/json"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["email"], "user5@test.ac.uk")
        self.assertEqual(response.data["full_name"], "Test User5")
        self.assertEqual(response.data["is_superuser"], True)
        self.assertEqual(
            list(response.data["panels"]), ["Developmental disorders", "Eye disorders"]
        )

        # Logout
        response_logout = self.client.post(
            self.url_logout, content_type="application/json"
        )
        self.assertEqual(response_logout.status_code, 204)
