from rest_framework import serializers
from django.core.exceptions import ValidationError
from ..models import User, UserPanel
from django.contrib.auth import authenticate
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.tokens import RefreshToken, TokenError
from rest_framework.validators import UniqueValidator


class UserSerializer(serializers.ModelSerializer):
    """
        Serializer for the User model.
    """

    user_name = serializers.SerializerMethodField()
    email = serializers.CharField(read_only=True)
    panels = serializers.SerializerMethodField()
    is_active = serializers.BooleanField()
    is_superuser = serializers.BooleanField()
    is_staff = serializers.BooleanField()

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
                user=id, is_deleted=0
                ).select_related('panel'
                                 ).values_list('panel__description', flat=True)
        else:
            user_panels = UserPanel.objects.filter(
                user=id, is_deleted=0, panel__is_visible=1
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
                user=id, is_deleted=0
                ).select_related('panel'
                                 ).values_list('panel__name', flat=True)
        else:
            user_panels = UserPanel.objects.filter(
                user=id, is_deleted=0, panel__is_visible=1
                ).select_related('panel'
                                 ).values_list('panel__name', flat=True)

        return user_panels

    def check_panel_permission(self, panels):
        """
            Check if user has permission to edit the inputted panels.

            Args:
                panels: a list of panels

            Returns:
                True if user has permission to edit all panels from the list
                False if user does not have permission to edit at least one panel
        """
        user_login = self.context.get('user')

        if user_login and user_login.is_authenticated:
            for panel in panels:
                panel_name = panel.get("name")
                try:
                    user_panel_obj = UserPanel.objects.get(
                        user = user_login.id,
                        panel__name = panel_name,
                        is_deleted = 0
                    )
                except UserPanel.DoesNotExist:
                    return False

        return True

    class Meta:
        model = User
        fields = ['user_name', 'email', 'is_active', 'panels', 'is_superuser', 'is_staff']
        extra_kwargs = {'password': {'write_only': True }}


class CreateUserSerializer(serializers.ModelSerializer):
    """
        This serializer is used to validate and create a new user object.
    """

    def validate(self, attrs):
        email = attrs.get('email')
        if email is None: 
            raise serializers.ValidationError({"message": "Email is needed to create a user"}, email)
        username = attrs.get('username')
        if username is None: 
            raise serializers.ValidationError({"message": "Username is needed to create a user"}, username)
        
        return attrs

    def create(self, validated_data):
        """
            This method creates a user using the `create_user` method, which ensures that
            the password is hashed before storing it in the database.

            validated_data has the following fields:
                - username: The username is unique in the system (mandatory)
                - email: The email of the user which has to be unique in the system (mandatory)
                - password: The password for the user. This field is write-only and 
                has a minimum length of 5 characters to ensure password strength (mandatory)
                - first_name: The user's first name
                - last_name: The user's last name
                - is_superuser: set to True if the user is a super user (default: False)
                - is_staff: set to True if the user is a staff member (default: False)
        """
        return User.objects.create_user(**validated_data)

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'first_name', 'last_name', 'is_superuser', 'is_staff']
        extra_kwargs = {'password': {'write_only': True, 'min_length': 6}, 'email': {
            'validators': [
                UniqueValidator(
                    queryset=User.objects.all()
                )
            ]
        }}


class LoginSerializer(serializers.ModelSerializer):
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
        trim_whitespace=False,
        write_only=True
    )
    tokens = serializers.SerializerMethodField()
    
    def get_tokens(self, obj):
        user = User.objects.get(email=obj['email'])

        return {
            'refresh': user.tokens()['refresh'],
            'access': user.tokens()['access']
        }
    
    def validate(self, attrs):
        username = attrs.get('username')
        password = attrs.get('password')
        
        user = authenticate(
            request=self.context.get('request'),
            username=username,
            password=password
        )
        
        if not user:
            raise AuthenticationFailed("Username or password is incorrect", code='authentication')

        if user.is_deleted:
            raise AuthenticationFailed('Account disbaled. Please contact Admin at g2p-help@ebi.ac.uk')

        attrs['user'] = user
        return {
            'email': user.email,
            'username': user.username,
            'tokens': user.tokens
        }
    
    class Meta:
        model = User
        fields = ['username','password','tokens']
    

class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()

    def validate(self, attrs):
        self.token = attrs['refresh']

        return attrs
    
    def save(self, **kwargs):
        try:
            RefreshToken(self.token.blacklist())
        except TokenError as e:
            raise serializers.ValidationError({"message": str(e)})
        
    class Meta: 
        model = User
        fields = ['refresh']
        

    


