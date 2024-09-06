from rest_framework import serializers
from django.core.exceptions import ValidationError
from ..models import User, UserPanel
from django.contrib.auth import authenticate
from rest_framework.validators import UniqueValidator


class UserSerializer(serializers.ModelSerializer):
    """
        Serializer for the User model.
    """

    user_name = serializers.SerializerMethodField()
    email = serializers.CharField(read_only=True)
    panels = serializers.SerializerMethodField()
    is_active = serializers.CharField(read_only=True)
    username = serializers.CharField(write_only=True)

    def get_user_name(self, id):
        """
            Gets the user name.
            If the first and last name are not available then
            splits the username.
        """

        user = User.objects.filter(email=id)
        if user.first().first_name is not None and user.first().last_name is not None:
            name = f"{user.first().first_name} {user.first().last_name}"
        else:
            user_name = user.first().username.split('_')
            name = ' '.join(user_name).title()

        return name

    def get_panels(self, id):
        """
            Get a list of panels the user has permission to edit.
            It returns the panel descriptions i.e. full name.

            Output example: ["Developmental disorders", "Ear disorders"]
        """

        user_login = self.context.get('user')
        if user_login and user_login.is_authenticated:
            user_panels = UserPanel.objects.filter(
                user=id
                ).select_related('panel'
                                 ).values_list('panel__description', flat=True)
        else:
            user_panels = UserPanel.objects.filter(
                user=id, panel__is_visible=1
                ).select_related('panel'
                                 ).values_list('panel__description', flat=True)

        return user_panels

    def panels_names(self, id):
        """
            Get a list of panels the user has permission to edit.
            It returns the panel names i.e. short name.

            Output example: ["DD", "Ear"]
        """

        user_login = self.context.get('user')
        if user_login and user_login.is_authenticated:
            user_panels = UserPanel.objects.filter(
                user=id
                ).select_related('panel'
                                 ).values_list('panel__name', flat=True)
        else:
            user_panels = UserPanel.objects.filter(
                user=id, panel__is_visible=1
                ).select_related('panel'
                                 ).values_list('panel__name', flat=True)

        return user_panels

    class Meta:
        model = User
        fields = ['user_name', 'email', 'is_active', 'panels', 'username']
        extra_kwargs = {'password': {'write_only': True }}


class CreateUserSerializer(serializers.ModelSerializer):
    """
        Serializer for creating a new user.

        This serializer is used to validate and create a new user object. It extends 
        `ModelSerializer` to automatically handle the fields related to the `User` model.

        Methods:
            - create(validated_data): 
                Overrides the default `create` method to create a user using 
                `create_user` method, which ensures that the password is hashed 
                before storing it in the database.

        Fields:
            - username: The username of the user.
            - email: The email of the user. It has a `UniqueValidator` to ensure that 
            the email is unique in the system.
            - password: The password for the user. This field is write-only and 
            has a minimum length of 5 characters to ensure password strength.
            - first_name: The user's first name.
            - last_name: The user's last name.

        Meta Options:
            - model: Specifies the `User` model to serialize.
            - fields: Lists the fields included in the serialization.
            - extra_kwargs: 
                - password: Write-only field with a minimum length of 5 characters.
                - email: Includes a `UniqueValidator` to enforce unique email addresses.

        Usage:
            This serializer can be used to create a new user by passing validated 
            data (username, email, password, first_name, last_name) and calling 
            the `create` method.
    """

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'first_name', 'last_name']
        extra_kwargs = {'password': {'write_only': True, 'min_length': 5},         'email': {
            'validators': [
                UniqueValidator(
                    queryset=User.objects.all()
                )
            ]
        }}


class AuthSerializer(serializers.Serializer):
    """
        Serializer class for user authentication.

        Fields:
            - username: A CharField representing the user's username.
            - password: A CharField representing the user's password. The 'input_type' 
            is set to 'password' to mask the input during entry, and 'trim_whitespace'
        is set to False to ensure the password is not altered.

        Methods:
             - validate(attrs): 
                This method is responsible for validating the provided username and 
                password. It attempts to authenticate the user using the `authenticate` 
                function with the given credentials.

            Parameters:
                attrs (dict): A dictionary containing 'username' and 'password'.

            Returns:
                user: If authentication is successful, the authenticated user 
                object is added to the `attrs` dictionary and returned.

            Raises:
                serializers.ValidationError: If authentication fails, an exception 
                is raised with an error message indicating that the username or 
                password is incorrect.
    """

    username = serializers.CharField()
    password = serializers.CharField(
        style={'input_type': 'password'},
        trim_whitespace=False
    )    
    def validate(self, attrs):
        username = attrs.get('username')
        password = attrs.get('password')
        
        user = authenticate(
            request=self.context.get('request'),
            username=username,
            password=password
        )
        
        if not user:
            msg = ('Username or password is incorrect')
            raise serializers.ValidationError(msg, code='authentication')

        attrs['user'] = user
        return user
