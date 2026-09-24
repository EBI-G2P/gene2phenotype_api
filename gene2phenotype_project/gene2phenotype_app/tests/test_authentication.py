from django.conf import settings
from django.test import RequestFactory, TestCase
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.tokens import TokenError
from unittest.mock import patch

from gene2phenotype_app.authentication import CustomAuthentication
from gene2phenotype_app.serializers.user import LogoutSerializer


class CustomAuthenticationTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.authentication = CustomAuthentication()

    def test_token_validation_error_returns_generic_message(self):
        request = self.factory.get("/")
        request.COOKIES[settings.SIMPLE_JWT["AUTH_COOKIE"]] = "invalid-token"

        with patch.object(
            self.authentication,
            "get_validated_token",
            side_effect=Exception("sensitive token parser detail"),
        ):
            with self.assertRaises(AuthenticationFailed) as context:
                self.authentication.authenticate(request)

        self.assertEqual(
            str(context.exception.detail), "Invalid authentication credentials"
        )
        self.assertNotIn("sensitive token parser detail", str(context.exception.detail))

    def test_blacklist_check_error_returns_generic_message(self):
        with patch(
            "gene2phenotype_app.authentication.RefreshToken",
            side_effect=Exception("sensitive blacklist detail"),
        ):
            with self.assertRaises(AuthenticationFailed) as context:
                CustomAuthentication.is_token_blacklisted("invalid-refresh-token")

        self.assertEqual(
            str(context.exception.detail), "Invalid authentication credentials"
        )
        self.assertNotIn("sensitive blacklist detail", str(context.exception.detail))

    def test_logout_token_error_returns_generic_message(self):
        serializer = LogoutSerializer()
        serializer.token = "invalid-refresh-token"

        with patch(
            "gene2phenotype_app.serializers.user.RefreshToken",
            side_effect=TokenError("sensitive logout token detail"),
        ):
            with self.assertRaises(Exception) as context:
                serializer.save()

        self.assertEqual(
            str(context.exception.detail["message"]),
            "Could not invalidate refresh token.",
        )
        self.assertNotIn("sensitive logout token detail", str(context.exception.detail))
