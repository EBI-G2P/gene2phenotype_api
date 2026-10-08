from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken
from django.conf import settings


class CustomAuthentication(JWTAuthentication):

    def authenticate(self, request):
        header = self.get_header(request)

        if header is None:
            # Getting authentication details from cookies
            # It only requires the access token but if the refresh token is present, it checks if it's blacklisted
            refresh_token = request.COOKIES.get(settings.SIMPLE_JWT["REFRESH_COOKIE"])
            raw_token = request.COOKIES.get(settings.SIMPLE_JWT["AUTH_COOKIE"])

            if refresh_token and self.is_refresh_token_valid(refresh_token) is False:
                raise AuthenticationFailed("Invalid authentication credentials")
        else:
            # Fallback to the default behavior if the header is present
            # JWTAuthentication will handle the token validation and user retrieval
            # By default, it only checks the access token
            raw_token = self.get_raw_token(header)

        if not raw_token:
            return None

        try:
            validated_token = self.get_validated_token(raw_token)
        except Exception:
            raise AuthenticationFailed("Invalid authentication credentials")
        return self.get_user(validated_token), validated_token

    @staticmethod
    def is_refresh_token_valid(token_string):
        if not token_string:
            return False

        try:
            RefreshToken(token_string)
            return True
        except TokenError:
            return False
