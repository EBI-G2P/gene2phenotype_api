from rest_framework.authentication import CSRFCheck
from rest_framework.exceptions import AuthenticationFailed
from django.conf import settings
from rest_framework import HTTP_HEADER_ENCODING, authentication
from django.middleware.csrf import CsrfViewMiddleware
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
    

class CustomAuthentication(JWTAuthentication):

    def authenticate(self, request):
        header = self.get_header(request)
        
        if header is None:
            # getting authentication details from cookies
            refresh_token = request.COOKIES.get(settings.SIMPLE_JWT['REFRESH_COOKIE'])
            if refresh_token:
                if self.is_token_blacklisted(refresh_token):
                    raise AuthenticationFailed("Token has been blacklisted")
            raw_token = request.COOKIES.get(settings.SIMPLE_JWT['AUTH_COOKIE'])
        else:
            #just giving the option from headers but no longer being implemented
            raw_token = self.get_raw_token(header)
        
        if not raw_token:
            return None

        try:
            validated_token = self.get_validated_token(raw_token)
        except Exception as e:
            raise AuthenticationFailed(str(e))
        return self.get_user(validated_token), validated_token
    
    
    def is_token_blacklisted(self, token_string):
        try:
            token = RefreshToken(token_string)
            if BlacklistedToken.objects.filter(token__jti=token['jti']).exists():
                return True
        except Exception as e:
            raise AuthenticationFailed(f"Token blacklist check failed: {e}")

        return False