from rest_framework.response import Response
from rest_framework import generics, permissions
from rest_framework.exceptions import ParseError
from rest_framework import status
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from drf_spectacular.utils import extend_schema
from datetime import timedelta, datetime
from django.conf import settings
from datetime import timedelta
from .base import BaseView
from django.db.models import F

from gene2phenotype_app.authentication import CustomAuthentication

from gene2phenotype_app.serializers import (
    UserSerializer,
    LoginSerializer,
    CreateUserSerializer,
    AddUserToPanelSerializer,
    LogoutSerializer,
    ChangePasswordSerializer,
    VerifyEmailSerializer,
    PasswordResetSerializer
)
from gene2phenotype_app.models import (
    User,
    UserPanel
)


@extend_schema(exclude=True)
class UserPanels(BaseView):
    lookup_field = 'name'
    serializer_class = User
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user_email = self.request.user

        queryset = User.objects.filter(email=user_email, is_deleted=0, is_active=1)

        if not queryset.exists():
            self.handle_no_permission('User', user_email)

        return queryset

    def list(self, request, *args, **kwargs):
        """
        Returns the list of panels the current user can edit.

        Returns:
            list of panels (dict)
        """
        user_obj = self.get_queryset().first()

        queryset_user_panels = UserPanel.objects.filter(
            user = user_obj,
            is_deleted = 0).select_related(
                'panel').order_by('panel__description').annotate(
                name=F('panel__name'),
                description=F('panel__description')).values(
                    'name', 'description')

        return Response(queryset_user_panels)


@extend_schema(exclude=True)
class CreateUserView(generics.CreateAPIView):
    """
    View for creating a new user.

    This view handles POST requests to create a new user using the `CreateUserSerializer`. 
    It is based on Django's `CreateAPIView` which provides the default implementation 
    for handling object creation.

    Usage:
        Send a POST request with the required user details (username, email, 
        password, first_name, last_name, panels) to this API to create a new user account.
    """
    serializer_class = CreateUserSerializer
    permission_classes = [permissions.IsAdminUser]


@extend_schema(exclude=True)
class AddUserToPanelView(generics.CreateAPIView):
    """
    API view to add a user to a panel.
    Only available to admin users, as enforced by the IsAdminUser permission class.
    """    
    serializer_class = AddUserToPanelSerializer
    permission_classes = [permissions.IsAdminUser]


@extend_schema(exclude=True)
class LoginView(generics.GenericAPIView):
    serializer_class = LoginSerializer
    permission_classes = (permissions.AllowAny,)

    def post(self, request, *args, **kwargs):
        """
        Handles the POST request for user login.

        This method authenticates a user based on the provided credentials, generates an access 
        token, and sets it in a secure cookie for client-side use. It also returns the user 
        details and token information in the response body.
        Parameters:
            - request: The HTTP request containing user credentials in the request body (e.g., 
            `username` and `password`).
        Returns:
            - Response: An HTTP response object with the user data and tokens in the body. 
            The access token is also stored as a secure cookie.
            The refresh token is also stored as a secure cookie

        Raises:
            - ValidationError: Raised if the provided credentials are invalid.
            - ValueError: Raised if the cookie cannot be set due to a response error.
        """
        serializer = LoginSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        login_data = serializer.login(serializer.validated_data)
        access_token = login_data.get('tokens', {}).get('access', None) # to access the token which is in the serializer.data
        refresh_token = login_data.get('tokens', {}).get('refresh', None)
        response = Response(login_data, status=status.HTTP_200_OK)
        if response.status_code == 200:
            refresh_token_lifetime = getattr(settings, "SIMPLE_JWT", {}).get("REFRESH_TOKEN_LIFETIME", timedelta(days=1))
            access_token_lifetime = getattr(settings, "SIMPLE_JWT", {}).get("ACCESS_TOKEN_LIFETIME", timedelta(hours=1))
            refresh_expires = datetime.utcnow() + refresh_token_lifetime  # Calculate refresh expiration time
            access_expires = datetime.utcnow() + access_token_lifetime # calculate access expiration time
            refresh_expires_iso = refresh_expires.isoformat()
            login_data['refresh_token_time'] = refresh_expires.isoformat() # to add the refresh token time to the response
            response.set_cookie(
                key=settings.SIMPLE_JWT["AUTH_COOKIE"],
                value=access_token,
                domain=settings.SIMPLE_JWT["AUTH_COOKIE_DOMAIN"],
                path=settings.SIMPLE_JWT["AUTH_COOKIE_PATH"],
                expires=access_expires,
                secure=settings.SIMPLE_JWT["AUTH_COOKIE_SECURE"],
                httponly=settings.SIMPLE_JWT["AUTH_COOKIE_HTTP_ONLY"],
                samesite=settings.SIMPLE_JWT["AUTH_COOKIE_SAMESITE"],
            )

            response.set_cookie(
                key=settings.SIMPLE_JWT["REFRESH_COOKIE"],  # Refresh token cookie name
                value=refresh_token,
                domain=settings.SIMPLE_JWT["AUTH_COOKIE_DOMAIN"],
                path=settings.SIMPLE_JWT["AUTH_COOKIE_PATH"],
                expires=refresh_expires,
                secure=settings.SIMPLE_JWT["AUTH_COOKIE_SECURE"],
                httponly=settings.SIMPLE_JWT["AUTH_COOKIE_HTTP_ONLY"],
                samesite=settings.SIMPLE_JWT["AUTH_COOKIE_SAMESITE"],
            )
            response.set_cookie(
                key="refresh_token_lifetime",
                value=refresh_expires_iso,
                domain=settings.SIMPLE_JWT["AUTH_COOKIE_DOMAIN"],
                path=settings.SIMPLE_JWT["AUTH_COOKIE_PATH"],
                expires=refresh_expires,
                secure=settings.SIMPLE_JWT["AUTH_COOKIE_SECURE"],
                httponly=settings.SIMPLE_JWT["AUTH_COOKIE_HTTP_ONLY"],
                samesite=settings.SIMPLE_JWT["AUTH_COOKIE_SAMESITE"],
            )
        else:
            raise ValueError("Failed to set cookies")
        del(login_data['tokens']) # to delete tokens from the response after setting cookies
        return response


@extend_schema(exclude=True)
class LogOutView(generics.GenericAPIView):
    serializer_class = LogoutSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        """
        Handles the POST request for logging out a user.

        This method validates the provided refresh token and blacklists it to prevent further 
        use. It ensures that only authenticated users can access this endpoint.
        Parameters:
            - request: The HTTP request containing the refresh token in the request body.
        Returns:
            - A Response object with HTTP 204 NO CONTENT status to indicate a successful logout.

        Raises:
            - ValidationError: Raised if the refresh token is invalid or missing.
            - AuthenticationFailed: Raised if the user is not authenticated.
        """
        refresh_token = request.COOKIES.get(getattr(settings, "SIMPLE_JWT", {}).get("REFRESH_COOKIE", "refresh_token"))

        if not refresh_token:
            return Response({"error": "Refresh token missing"}, status=status.HTTP_400_BAD_REQUEST)

        data = {
            'refresh': refresh_token
        }
        serializer = self.serializer_class(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        # return Response(status=status.HTTP_204_NO_CONTENT)
        response = Response(status=status.HTTP_204_NO_CONTENT)
        if response:
            response.delete_cookie(       
                key=settings.SIMPLE_JWT["AUTH_COOKIE"],
                path=settings.SIMPLE_JWT["AUTH_COOKIE_PATH"],
            )
            response.delete_cookie(        
                key=settings.SIMPLE_JWT["REFRESH_COOKIE"],
                path=settings.SIMPLE_JWT["AUTH_COOKIE_PATH"],
                )
            response.delete_cookie(
                key="refresh_token_lifetime",
                path=settings.SIMPLE_JWT["AUTH_COOKIE_PATH"],
            )
        return response


@extend_schema(exclude=True)
class ManageUserView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        """
        Retrieve and return the authenticated user information.
        This method overrides the default to ensure the user data being
        accessed belongs to the currently logged-in user.
        """
        serializer = UserSerializer(request.user)
        result = serializer.data
        refresh_token_value = request.COOKIES.get('refresh_token_lifetime')
        result['refresh_token_time'] = refresh_token_value
        return Response(result, status=status.HTTP_200_OK)


@extend_schema(exclude=True)
class ChangePasswordView(generics.GenericAPIView):
    serializer_class = ChangePasswordSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        """
        Post method for authenticated users to change their password.

        Args:
            request (Request): the HTTP request object

        Returns:
            Response: a response containing the user information and a success status
        """        
        serializer = self.serializer_class(data=request.data, context={'user':request.user})
        serializer.is_valid(raise_exception=True)
        result = serializer.change_password(user=request.user)
        return Response(result,  status=status.HTTP_201_CREATED)


@extend_schema(exclude=True)  
class VerifyEmailView(generics.GenericAPIView):
    serializer_class = VerifyEmailSerializer
    permission_classes = (permissions.AllowAny,)

    def post(self, request, *args, **kwargs):
        """
        Post method for V]verification of email for password reset.

        Args:
            request (Request): the HTTP request object

        Returns:
            Response: Response (user information)
        """        
        serializer = self.serializer_class(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        result = serializer.get_user_and_send_email(user=request.data)

        return Response(result)


@extend_schema(exclude=True)
class ResetPasswordView(generics.GenericAPIView): 
    serializer_class = PasswordResetSerializer
    permission_classes = (permissions.AllowAny,)

    def post(self, request, uid, token):
        """
        Post method for Password reset

        Args:
            request (Request): Django HttpRequest Object
            uid (str): encrypted user id 
            token (str): tine restricted configured password reset token 

        Returns:
            Response: a response containing the email of the user
        """        
        serializer = self.serializer_class(data=request.data, context={'uid':uid, 'token':token})
        serializer.is_valid(raise_exception=True)
        result = serializer.reset(password=request.data,user=uid)
        return Response(result)


@extend_schema(exclude=True)
class CustomTokenRefreshView(TokenRefreshView):
    serializer_class = TokenRefreshSerializer
    permission_classes = (permissions.AllowAny,)

    def post(self, request, *args, **kwargs):
        """
        Handles the Post method to refresh token and generate a new access and refresh token

        Args:
            request (Request): instance of Django's HttpRequest object

        Raises:
            AuthenticationFailed : If the refresh token has been blacklisted (logged out)
            ParseError : If the request is bad for other reasons 

        Returns:
            Response: the response
        """

        #fetch refresh_token from the cookies 
        refresh_token = request.COOKIES.get(getattr(settings, "SIMPLE_JWT", {}).get("REFRESH_COOKIE", "refresh_token"))

        if CustomAuthentication.is_token_blacklisted(refresh_token):
            raise AuthenticationFailed("Token has been blacklisted")
      
        data = {'refresh' : refresh_token} # to make sure the data thats being sent is from the cookies
        serializer = TokenRefreshSerializer(data=data) # instead of request data, give it the data created
        serializer.is_valid(raise_exception=True)
        refresh_token = serializer.validated_data.get("refresh") # the validated results sent from the TokenRefreshSerializer
        access_token = serializer.validated_data.get('access') # the validated results sent from the TokenRefreshSerializer
  
        try:
            if getattr(settings, "SIMPLE_JWT", {}).get("ROTATE_REFRESH_TOKENS", True):
               new_refresh_token = str(RefreshToken(refresh_token))
            else:
                new_refresh_token = refresh_token
        except ParseError as e: 
            return Response({"message": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
        response_data = serializer.data
        response = Response(response_data, status=status.HTTP_200_OK)
    
        if response.status_code == 200:
            refresh_token_lifetime = request.COOKIES.get('refresh_token_lifetime') # we are getting the refresh timeline from the cookie 
            access_token_lifetime = getattr(settings, "SIMPLE_JWT", {}).get("ACCESS_TOKEN_LIFETIME", timedelta(hours=1))
            refresh_expires = datetime.fromisoformat(refresh_token_lifetime)  # Calculate refresh expiration time
            access_expires = datetime.utcnow() + access_token_lifetime # calculate access expiration time
            response_data['refresh_token_time'] = refresh_expires
            refresh_expires_iso = refresh_expires.isoformat()
            response.set_cookie(
                key=getattr(settings, "SIMPLE_JWT", {}).get("AUTH_COOKIE", "access_token"),
                value=access_token,
                domain=getattr(settings, "SIMPLE_JWT", {}).get("AUTH_COOKIE_DOMAIN", None),
                path=getattr(settings, "SIMPLE_JWT", {}).get("AUTH_COOKIE_PATH", "/"),
                expires=access_expires,
                secure=getattr(settings, "SIMPLE_JWT", {}).get("AUTH_COOKIE_SECURE", False),
                httponly=getattr(settings, "SIMPLE_JWT", {}).get("AUTH_COOKIE_HTTP_ONLY", True),
                samesite=getattr(settings, "SIMPLE_JWT", {}).get("AUTH_COOKIE_SAMESITE", "Lax"),
            )
            response.set_cookie(
                key=getattr(settings, "SIMPLE_JWT", {}).get("REFRESH_COOKIE", "refresh_token"),
                value=new_refresh_token,
                domain=getattr(settings, "SIMPLE_JWT", {}).get("AUTH_COOKIE_DOMAIN", None),
                path=getattr(settings, "SIMPLE_JWT", {}).get("AUTH_COOKIE_PATH", "/"),
                expires=refresh_expires,
                secure=getattr(settings, "SIMPLE_JWT", {}).get("AUTH_COOKIE_SECURE", False),
                httponly=getattr(settings, "SIMPLE_JWT", {}).get("AUTH_COOKIE_HTTP_ONLY", True),
                samesite=getattr(settings, "SIMPLE_JWT", {}).get("AUTH_COOKIE_SAMESITE", "Lax"),
            )
            response.set_cookie(
                key="refresh_token_lifetime",
                value=refresh_expires_iso,
                domain=settings.SIMPLE_JWT["AUTH_COOKIE_DOMAIN"],
                path=settings.SIMPLE_JWT["AUTH_COOKIE_PATH"],
                expires=refresh_expires,
                secure=settings.SIMPLE_JWT["AUTH_COOKIE_SECURE"],
                httponly=settings.SIMPLE_JWT["AUTH_COOKIE_HTTP_ONLY"],
                samesite=settings.SIMPLE_JWT["AUTH_COOKIE_SAMESITE"],
            )
        
        return response