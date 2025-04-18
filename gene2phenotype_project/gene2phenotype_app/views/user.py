from rest_framework.response import Response
from rest_framework import generics, permissions
from rest_framework.exceptions import ParseError
from django.db.models import F
from rest_framework_simplejwt.serializers import TokenRefreshSerializer 
from datetime import timedelta, datetime
from rest_framework import status
from rest_framework_simplejwt.views import TokenRefreshView
from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken
from datetime import timedelta
from gene2phenotype_app.serializers import (UserSerializer, LoginSerializer,
                                            CreateUserSerializer, AddUserToPanelSerializer, LogoutSerializer, ChangePasswordSerializer, VerifyEmailSerializer, PasswordResetSerializer)
from gene2phenotype_app.models import User, UserPanel
from .base import BaseView
from gene2phenotype_app.authentication import CustomAuthentication
from rest_framework.exceptions import AuthenticationFailed


class UserPanels(BaseView):
    """
        Returns the list of panels the current user can edit

        Returns:
                (dict) list of panels

    """
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
        user_obj = self.get_queryset().first()

        queryset_user_panels = UserPanel.objects.filter(
            user = user_obj,
            is_deleted = 0).select_related(
                'panel').order_by('panel__description').annotate(
                name=F('panel__name'),
                description=F('panel__description')).values(
                    'name', 'description')

        return Response(queryset_user_panels)


class UserList(generics.ListAPIView):
    """
        Display a list of active users and their info.
        The info includes a list of panels the user has permission to edit.

        Returns:
            Response object includes:
                            (list) results: list of users
                            (int) count: number of users
    """

    serializer_class = UserSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update({'user_login':self.request.user})
        return context

    def get_queryset(self):
        user = self.request.user
        if user and user.is_authenticated:
            queryset = User.objects.filter(is_active=1)
        else:
            queryset = User.objects.filter(is_active=1, is_staff=0)

        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = UserSerializer(queryset, many=True, context={'user': self.request.user})

        return Response({'results': serializer.data, 'count':len(serializer.data)})


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

class AddUserToPanelView(generics.CreateAPIView):
    """
        Add User to Panel view

        Args:
            generics (_type_): Adds User to panel, permissions is AdminUser, so views only available to AdminUser
    """    
    serializer_class = AddUserToPanelSerializer
    permission_classes = [permissions.IsAdminUser]




class LoginView(generics.GenericAPIView):
    """
        LoginView: Handles user authentication and login.

        This view allows users to authenticate using their credentials (e.g., email/username and password).
        Upon successful authentication, the view generates a JSON Web Token (JWT) for the user and 
        sets it as a secure cookie in the HTTP response. 

        Attributes:
            - serializer_class: Specifies the serializer used for validating user credentials, 
            which is `LoginSerializer`.
            - permission_classes: Allows any user (authenticated or not) to access this endpoint 
            by using the `AllowAny` permission.

        Methods:
            - post(request, *args, **kwargs): Handles the user login process, generates the 
            access token, and sets it in a cookie.
    """

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
    
class LogOutView(generics.GenericAPIView):
    """
        API view for user logout.

        This view allows authenticated users to log out by blacklisting their refresh tokens. 
        It requires the user to provide a valid refresh token in the request. Once the token is 
        blacklisted, it becomes invalid for further use, effectively logging the user out.

        Attributes:
            - serializer_class: Specifies the serializer used for this view, which is `LogoutSerializer`.
            - permission_classes: Requires the user to be authenticated to access this endpoint.

        Methods:
            - post(request):
                Handles the POST request to log out a user. Validates the refresh token using 
                the `LogoutSerializer` and blacklists it to prevent further use.

                Parameters:
                    - request: The HTTP request containing the refresh token to be blacklisted.

                Returns:
                    A response with HTTP 204 NO CONTENT status if the logout is successful.

        Raises:
            - ValidationError: Raised if the refresh token is invalid or cannot be blacklisted.
            - PermissionDenied: Raised if the user is not authenticated.
    """
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
    

class ManageUserView(generics.RetrieveUpdateAPIView):
    """
        View for managing the authenticated user.

        This view allows the authenticated user to retrieve and update their own information. 
        It extends `RetrieveUpdateAPIView`, providing GET and PUT/PATCH methods for 
        retrieving and updating user data.

        Attributes:
            - serializer_class: Specifies the `UserSerializer` to serialize and validate 
            the user data.
            - permission_classes: Ensures that only authenticated users can access 
            this view, using `IsAuthenticated` permission.

        Methods:
            - get_object():
                Retrieves and returns the authenticated user object. This method overrides 
                the default to ensure the user data being accessed belongs to the currently 
                logged-in user.

        Usage:
            - GET: Retrieve the authenticated user's details.
    """

    serializer_class = UserSerializer
    permission_classes = (permissions.IsAuthenticated,)
    

    def get(self, request):
        """Retrieve and return authenticated user"""
        serializer = UserSerializer(request.user)
        result = serializer.data
        refresh_token_value = request.COOKIES.get('refresh_token_lifetime')
        result['refresh_token_time'] = refresh_token_value
        return Response(result, status=status.HTTP_200_OK)

class ChangePasswordView(generics.GenericAPIView):
    """
        Change password view  - Authenticated View 
    """    
    serializer_class = ChangePasswordSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        """
            Post method for ChangePasswordView

            Args:
                request (_type_): DjangoHttp Request object

            Returns:
                _type_: user information
        """        
        serializer = self.serializer_class(data=request.data, context={'user':request.user})
        serializer.is_valid(raise_exception=True)
        result = serializer.change_password(user=request.user)
        return Response(result,  status=status.HTTP_201_CREATED)
    
class VerifyEmailView(generics.GenericAPIView):
    """
        View for Verification of Email for Password Reset
    """    

    serializer_class = VerifyEmailSerializer
    permission_classes = (permissions.AllowAny,)

    def post(self, request, *args, **kwargs):
        """
        Post method for Verify Email View - Unauthenticated view 

        Args:
            request (_type_): Django HttpRequest Object

        Returns:
            _type_: Response (user information)
        """        
        serializer = self.serializer_class(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        result = serializer.get_user_and_send_email(user=request.data)

        return Response(result)
    
class ResetPasswordView(generics.GenericAPIView):
    """
        View for Password Reset - UnAuthenticated View 
    """    
    serializer_class = PasswordResetSerializer
    permission_classes = (permissions.AllowAny,)

    def post(self, request, uid, token):
        """
            Post method for Password reset

            Args:
                request (_type_): Django HttpRequest Object
                uid (_type_): encrypted user id 
                token (_type_): tine restricted configured password reset token 

            Returns:
                _type_: response - user.email
        """        
        serializer = self.serializer_class(data=request.data, context={'uid':uid, 'token':token})
        serializer.is_valid(raise_exception=True)
        result = serializer.reset(password=request.data,user=uid)
        return Response(result)

class CustomTokenRefreshView(TokenRefreshView):
    """
        Custom view for TokenRefresh, inheriting from BaseClass TokenRefreshView
        Unauthenticated View 
    """    
    serializer_class = TokenRefreshSerializer
    permission_classes = (permissions.AllowAny,)

    def post(self, request, *args, **kwargs):
        """
            Handles the Post nethod to refresh token and generate a new access and refresh token

            Args:
                request (_type_): instance of Django's HttpRequest object

            Raises:
                AuthenticationFailed: If the refresh token has been blacklisted (logged out)
                ParseError : If the request is bad for other reasons 

            Returns:
                _type_: response
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