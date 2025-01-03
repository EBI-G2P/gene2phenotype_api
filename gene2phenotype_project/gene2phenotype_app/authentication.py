from rest_framework.authentication import CSRFCheck
from rest_framework.exceptions import AuthenticationFailed
from django.conf import settings
from rest_framework import HTTP_HEADER_ENCODING, authentication
from django.middleware.csrf import CsrfViewMiddleware
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
    

class CustomAuthentication(JWTAuthentication):

    def authenticate(self, request):
        header = self.get_header(request)
        
        if header is None:
            # getting authentication details from cookies
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
    