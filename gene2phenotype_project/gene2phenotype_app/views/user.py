from rest_framework.response import Response
from rest_framework import generics, permissions
from django.db.models import F
from rest_framework.authtoken.serializers import AuthTokenSerializer
from django.contrib.auth import login
from knox.views import LoginView as KnoxLoginView

from gene2phenotype_app.serializers import (UserSerializer, AuthSerializer,
                                            CreateUserSerializer)
from gene2phenotype_app.models import User, UserPanel
from .base import BaseView


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
            password, first_name, last_name) to this API to create a new user account.
    """

    serializer_class = CreateUserSerializer
    permission_classes = [permissions.IsAuthenticated]


class LoginView(KnoxLoginView):
    """
        API view for user login, extending KnoxLoginView.

        This view handles user login requests and is integrated with the Django REST Knox 
        token-based authentication system. It authenticates the user and generates a token 
        upon successful login.

        Attributes:
            - serializer_class: Specifies the serializer used for authentication, which is 
            `AuthSerializer`.
            - permission_classes: Allows any user (authenticated or not) to access this 
            endpoint, using `AllowAny` permission.

        Methods:
            - post(request): 
                Handles the POST request to log in a user. It validates the provided 
                credentials using the `AuthTokenSerializer`. If valid, the user is logged 
                in using Django's `login` function. After login, it delegates to the Knox 
                `post` method to generate and return an authentication token.

                Parameters:
                    - request: The HTTP request containing user credentials (username 
                    and password).

                Returns:
                    A response from the parent `KnoxLoginView`, which includes an 
                    authentication token if the login is successful.

        Raises:
            - ValidationError: Raised if the provided credentials are invalid.
    """

    serializer_class = AuthSerializer
    permission_classes = (permissions.AllowAny,)

    def post(self, request):
        serializer = AuthTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        login(request, user)
        return super(LoginView, self).post(request, format=None)


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

    def get_object(self):
        """Retrieve and return authenticated user"""
        return self.request.user
