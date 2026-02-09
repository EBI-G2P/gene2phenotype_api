import json
from django.conf import settings
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
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
        Test the endpoint that retrieves the list of panels the current user can edit.
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

    def test_create_user_success(self):
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

    def test_create_user_missing_info(self):
        post_data = {
            "username": "test_user6",
            "password": "testpassword2",
            "password2": "testpassword2",
            "is_superuser": False,
            "is_staff": False,
            "panels": ["DD"],
        }

        json_data = json.dumps(post_data)
        response = self.client.post(
            self.url_create_user, json_data, content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)

    def test_create_user_existing_email(self):
        post_data = {
            "username": "test_user30",
            "email": "user3@test.ac.uk",
            "first_name": "First name test",
            "last_name": "Last name test",
            "password": "testpassword3",
            "password2": "testpassword3",
            "is_superuser": False,
            "is_staff": False,
            "panels": ["DD"],
        }

        json_data = json.dumps(post_data)
        response = self.client.post(
            self.url_create_user, json_data, content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)


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
        self.url_profile = reverse("profile")
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

        # Check the profile
        response_profile = self.client.get(
            self.url_profile, content_type="application/json"
        )
        self.assertEqual(response_profile.status_code, 200)
        self.assertEqual(response_profile.data["full_name"], "Test User5")
        self.assertEqual(response_profile.data["email"], "user5@test.ac.uk")
        self.assertEqual(response_profile.data["is_superuser"], True)
        self.assertEqual(
            list(response_profile.data["panels"]), ["Developmental disorders", "Eye disorders"]
        )

        # Logout
        response_logout = self.client.post(
            self.url_logout, content_type="application/json"
        )
        self.assertEqual(response_logout.status_code, 204)

    def test_login_failure(self):
        data = {"username": "user56@test.ac.uk", "password": "test_user56"}

        # Login
        response = self.client.post(
            self.url_login, data, content_type="application/json"
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.data["error"], "Username or password is incorrect")

    def test_login_deleted_user(self):
        data = {"username": "user2@test.ac.uk", "password": "test_user2"}

        # Login
        response = self.client.post(
            self.url_login, data, content_type="application/json"
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.data["error"], "Account disabled. Please contact Admin at g2p-help@ebi.ac.uk")

class ChangePasswordTest(TestCase):
    fixtures = ["gene2phenotype_app/fixtures/user_panels.json"]

    def setUp(self):
        self.url_change_password = reverse("change_password")
        self.url_verify_email = reverse("verify_email")

        user = User.objects.get(email="user5@test.ac.uk")
        access_token = login(user)
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

    def test_change_password_success(self):
        """
        Test changing password with correct old password
        """
        change_password_data = {
            "old_password": "test_user5",
            "password": "new_test_user5",
            "password2": "new_test_user5",
        }

        response_change_password = self.client.post(
            self.url_change_password,
            change_password_data,
            content_type="application/json",
        )

        self.assertEqual(response_change_password.status_code, 201)

    def test_change_password_failure(self):
        """
        Test changing password with incorrect old password
        """
        change_password_data = {
            "old_password": "test_user",
            "password": "new_test_user5",
            "password2": "new_test_user5",
        }

        response_change_password = self.client.post(
            self.url_change_password,
            change_password_data,
            content_type="application/json",
        )

        self.assertEqual(response_change_password.status_code, 400)

    def test_verify_email_success(self):
        """
        Test verifying email for password reset with correct email
        """
        response = self.client.post(
            self.url_verify_email,
            {"email": "user5@test.ac.uk"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("id", response.data)
        self.assertIn("email", response.data)
        self.assertIn("token", response.data)

    def test_verify_email_failure(self):
        """
        Test verifying email for password reset with non-existent email
        """
        response = self.client.post(
            self.url_verify_email,
            {"email": "nonexistent@test.mail.com"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["message"], "If an account exists for this email, a reset link has been sent.")


class TokenRefreshTest(TestCase):
    fixtures = ["gene2phenotype_app/fixtures/user_panels.json"]

    def setUp(self):
        self.url_login = reverse("_login")
        self.url_logout = reverse("logout")
        self.url_refresh = reverse("token_refresh")
        self.user = User.objects.get(email="user5@test.ac.uk")

    def _set_refresh_cookies(self, refresh_token):
        refresh_expires = timezone.now() + settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"]
        self.client.cookies[settings.SIMPLE_JWT["REFRESH_COOKIE"]] = str(refresh_token)
        self.client.cookies["refresh_token_lifetime"] = refresh_expires.isoformat()

    def test_token_refresh_success(self):
        refresh = RefreshToken.for_user(self.user)
        self._set_refresh_cookies(refresh)

        response = self.client.post(self.url_refresh, content_type="application/json")

        self.assertEqual(response.status_code, 200)
        self.assertIn(settings.SIMPLE_JWT["AUTH_COOKIE"], response.cookies)

    def test_token_refresh_missing_cookie(self):
        response = self.client.post(self.url_refresh, content_type="application/json")

        self.assertEqual(response.status_code, 400)

    def test_token_refresh_invalid_token(self):
        self.client.cookies[settings.SIMPLE_JWT["REFRESH_COOKIE"]] = "not-a-jwt"
        refresh_expires = timezone.now() + settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"]
        self.client.cookies["refresh_token_lifetime"] = refresh_expires.isoformat()

        response = self.client.post(self.url_refresh, content_type="application/json")

        self.assertEqual(response.status_code, 401)

    def test_token_refresh_blacklisted_token(self):
        refresh = RefreshToken.for_user(self.user)
        refresh.blacklist()
        self._set_refresh_cookies(refresh)

        response = self.client.post(self.url_refresh, content_type="application/json")

        self.assertEqual(response.status_code, 401)

    def test_logout_requires_access_token(self):
        refresh = RefreshToken.for_user(self.user)
        self._set_refresh_cookies(refresh)

        response_logout = self.client.post(
            self.url_logout, content_type="application/json"
        )

        self.assertEqual(response_logout.status_code, 401)

    def test_logout_blacklists_refresh_token(self):
        refresh = RefreshToken.for_user(self.user)
        access_token = str(refresh.access_token)
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token
        self._set_refresh_cookies(refresh)

        response_logout = self.client.post(
            self.url_logout, content_type="application/json"
        )
        self.assertEqual(response_logout.status_code, 204)

        self._set_refresh_cookies(refresh)
        response_refresh = self.client.post(
            self.url_refresh, content_type="application/json"
        )

        self.assertEqual(response_refresh.status_code, 401)


class ResetPasswordTest(TestCase):
    fixtures = ["gene2phenotype_app/fixtures/user_panels.json"]

    def setUp(self):
        self.user = User.objects.get(email="user5@test.ac.uk")

    def test_reset_password_invalid_token(self):
        uid = urlsafe_base64_encode(force_bytes(self.user.id))
        response = self.client.post(
            reverse("reset_password", kwargs={"uid": uid, "token": "invalid-token"}),
            {"password": "new_password1", "password2": "new_password1"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)

    def test_reset_password_mismatch(self):
        uid = urlsafe_base64_encode(force_bytes(self.user.id))
        token = PasswordResetTokenGenerator().make_token(self.user)
        response = self.client.post(
            reverse("reset_password", kwargs={"uid": uid, "token": token}),
            {"password": "new_password1", "password2": "new_password2"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)


class UserAdminPermissionTest(TestCase):
    fixtures = ["gene2phenotype_app/fixtures/user_panels.json"]

    def setUp(self):
        self.url_create_user = reverse("create_user")
        self.url_add_to_panel = reverse("add_user_panel")
        user = User.objects.get(email="user1@test.ac.uk")
        access_token = login(user)
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

    def test_non_admin_cannot_create_user(self):
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

        self.assertEqual(response.status_code, 403)

    def test_non_admin_cannot_add_user_to_panel(self):
        post_data = {"user": "user2@test.ac.uk", "panel": ["Eye"]}
        json_data = json.dumps(post_data)
        response = self.client.post(
            self.url_add_to_panel, json_data, content_type="application/json"
        )

        self.assertEqual(response.status_code, 403)
