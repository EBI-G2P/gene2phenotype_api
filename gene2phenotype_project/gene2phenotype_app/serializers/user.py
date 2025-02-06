from rest_framework import serializers
from django.core.exceptions import ValidationError
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.contrib.auth import authenticate
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.encoding import smart_str, force_bytes, DjangoUnicodeDecodeError
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.tokens import RefreshToken, TokenError
from rest_framework.validators import UniqueValidator
from django.contrib.auth.models import update_last_login

from ..utils import CustomMail
from ..models import User, UserPanel, Panel


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

    def get_user_name(self, obj):
        """
            Gets the user name.
            If the first and last name are not available then
            splits the username.
        """
        user = User.objects.filter(email=obj).first()
        if user.first_name is not None and user.last_name is not None:
            name = f"{user.first_name} {user.last_name}"
        else:
            user_name = user.username.split('_')
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
    password = serializers.CharField(write_only=True, style={'input_type':'password'}, min_length=6, max_length=20)
    password2 = serializers.CharField(write_only=True, style={'input_type':'password'}, min_length=6, max_length=20)
    panels = serializers.ListField(child=serializers.CharField(), write_only=True) # write only because it is not a readable field
    user_panels = serializers.SerializerMethodField()


    def get_user_panels(self, obj):
        """
        Fetches associated panels for the user.
        """
        return list(UserPanel.objects.filter(user=obj, is_deleted=False).values_list('panel__name', flat=True))

        
    def validate(self, attrs):
        """
            Validate the dictionary being passed to the CreateUserSerializer

            Args:
                attrs (_type_): Dictionary 

            Raises:
                serializers.ValidationError: If Email is not being passed
                serializers.ValidationError: If username is not being passed
                serializers.ValidationError: checks if password and confirm password are the same 
                serializers.ValidationError: If username already exists
                serializers.ValidationError: If Account with that same email already exists

            Returns:
                _type_: A validated dictionary that will be used in the create
        """        
        email = attrs.get('email')
        if email is None:
            raise serializers.ValidationError({"message": "Email is needed to create a user"})
        username = attrs.get('username')
        if username is None:
            raise serializers.ValidationError({"message": "Username is needed to create a user"})
        password = attrs.get('password')
        # pop password2 from the validated data that will be sent to models 
        password2 = attrs.pop('password2', 'None')
        if password != password2:
            raise serializers.ValidationError({"message": "Passwords do not match"})
        first_name = attrs.get('first_name')
        if first_name is None:
            raise serializers.ValidationError({'message': "First name is needed to create a user"})
        last_name = attrs.get('last_name')
        if last_name is None:
            raise serializers.ValidationError({'message': "Last name is needed to create a user"})
        
        if User.objects.filter(username=username).exists():
            raise serializers.ValidationError({'message': "Username already exists"})
        if User.objects.filter(email=email).exists():
            raise serializers.ValidationError({'message': "An account with this email already exists"})
        
        panels = attrs.get('panels', [])
        for panel in panels:
            if not Panel.objects.filter(name=panel).exists():
                raise serializers.ValidationError({'message': f"{panel} does not exist"}, panel)
        
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

      
        panels = validated_data.pop('panels', []) # popping panels because i do not need it for creation
        user = User.objects.create_user(**validated_data)
        if user:
            for panel in panels:
                panel = Panel.objects.get(name=panel)
                UserPanel.objects.create(user=user, panel=panel, is_deleted=False)

            request = self.context.get('request')
            #base_url = url_link.build_absolute_uri()
            http_response = request.scheme
            host = request.get_host()
            verify_email_link = f"{http_response}://{host}/verify/email"
            CustomMail.send_create_email(data=user, verify_link=verify_email_link, panel=panels, subject="Account Created!", to_email=user.email)
        
        
        return user

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'password', 'password2', 'is_superuser', 'is_staff', 'panels', 'user_panels']
        extra_kwargs = {'password': {'write_only': True, 'min_length': 6, 'max_length': 20}, 
                        'email': {
                            'validators': [
                                UniqueValidator(
                                    queryset=User.objects.all(),
                                    message="This email is already registered"
                                )
                            ]
                        }
                        }
        
class ChangePasswordSerializer(serializers.ModelSerializer): 
    """
        Serializer class for Change Password

        Args:
            serializers (_type_): 
                Fields:
                    old_password : current password 
                    password : new password
                    password2 : confirm new password

        Raises:
            serializers.ValidationError: Raises if old password is not correct
            serializers.ValidationError: Raises if new password and confirm new password do not match 
            serializers.ValidationError: Raises if new and old password are the same 

        Returns:
            _type_: user email
    """ 

    old_password = serializers.CharField(max_length=20, min_length=6, style={'input_type' : 'password'}, write_only=True)
    password = serializers.CharField(max_length=20, min_length=6, style={'input_type': 'password'}, write_only=True)
    password2 = serializers.CharField(max_length=20, min_length=6, style={'input_type': 'password'}, write_only=True)

    def validate(self, attrs):
        """
            Validation method for Change password method

            Args:
                attrs (_type_): Dictionary

            Raises:
                serializers.ValidationError: Raises if old password is not correct
                serializers.ValidationError: Raises if new password and confirm new password do not match 

            Returns:
                _type_: Validated dictionary attrs 
        """        
        user = self.context.get('user')
        old_password = attrs.get('old_password')
        if user.check_password(old_password) is False:
            raise serializers.ValidationError({'message' : "The password you entered is incorrect. Please provide the correct current password to update your password"})
        password = attrs.get('password')
        password2 = attrs.pop('password2', None)
        if password != password2:
            raise serializers.ValidationError({"message": "Passwords do not match"}, password)

        return attrs
    
    def change_password(self, user):
        """
            Save method for changing password 

            Args:
                user (_type_): user object

            Raises:
                serializers.ValidationError: Raises if new and old password are the same 

            Returns:
                _type_: user email
        """        
        password = self.validated_data.get('password')

        if user.check_password(password):
            raise serializers.ValidationError({"message": "The new password cannot be the same as the present password."}, password)

        user.set_password(password)
        user.save()
        CustomMail.send_change_password_email(user=user.first_name, user_email=user.email, subject='Password change confirmation', to_email=user.email)
        return user.email

    class Meta:
        model = User
        fields = ['old_password', 'password', 'password2']


class VerifyEmailSerializer(serializers.ModelSerializer):
    """
        Serializer class for Verify Email

        Args:
            serializers (_type_): 
                Fields: 
                    Email 

        Returns:
            _type_: user information
    """    
    email = serializers.EmailField(write_only=True)

    def get_user_and_send_email(self, **validated_data):
        """
            Get user and sends email to the user containing password reset link

            Returns:
                _type_: User information 
        """        
        email = self.validated_data.get('email')
        user = User.objects.get(email=email, is_deleted=0)

        # Verify Email and Return Token and id that will be used to PasswordReset
        if user:
            reset_token = PasswordResetTokenGenerator().make_token(user)
            uid =  urlsafe_base64_encode(force_bytes(user.id))
            request = self.context.get('request')
            http_response = request.scheme
            host = request.get_host()
            reset_link = f"{http_response}://{host}/gene2phenotype/reset-password/{uid}/{reset_token}"
            CustomMail.send_reset_email(user=user.first_name, subject='Reset password request', reset_link=reset_link, to_email=user.email)

            return {
                    'id' : user.id,
                    'email' : user.email,
                    'token' : reset_token
                }
    
    class Meta:
        model = User
        fields = ['email']

class PasswordResetSerializer(serializers.ModelSerializer):
    """
        Serializer class for password reset

        Args:
            serializers (_type_): 
                Fields:
                    Password - New password
                    Password2 - confirm password 

        Raises:
            serializers.ValidationError: If password and confirm password do not match 
            serializers.ValidationError: If user not associated with the Token 

        Returns:
            _type_: a user with a new reset password 
    """    
    password = serializers.CharField(max_length=20, min_length=6, style={'input_type': 'password'}, write_only=True)
    password2 = serializers.CharField(max_length=20, min_length=6, style={'input_type': 'password'}, write_only=True)

    def validate(self, attrs):
        """
            Validation step for the Password reset

            Args:
                attrs (_type_): Dictionary, used in validating the data passed in request

            Raises:
                serializers.ValidationError: If password and confirm password do not match 
                serializers.ValidationError: If user not associated with the Token 

            Returns:
                _type_: validated dictionary attrs
        """        
        password = attrs.get('password')
        password2 = attrs.pop('password2', None)

        uid = self.context.get('uid')
        token = self.context.get('token')

        if password != password2:
            raise serializers.ValidationError({'message': 'Passwords do not match'}, password)
        
        uid =  smart_str(urlsafe_base64_decode(uid))
        user = User.objects.get(id=uid)

        if not PasswordResetTokenGenerator().check_token(user, token):
            raise serializers.ValidationError('Token is not valid or expired')
   
        attrs['id'] = uid

        return attrs
    
    def reset(self, password, user):
        """
            Reset method for the Serializer class 

            Args:
                password (_type_): Validated password
                user (_type_): Validated user id 
            
            Method:
                Sets a new password and saves the user updated information 

            Returns:
                _type_: user email
        """        
        password = self.validated_data.get('password')
        user = User.objects.get(id=self.validated_data.get('id'))
        user.set_password(password)
        user.save()

        return user.email

        

    class Meta:
        model = User
        fields = ['password', 'password2']

class LoginSerializer(serializers.ModelSerializer):
    """
        Serializer class for user authentication.

        Fields:
            - username (serializers.CharField): 
        Represents the username field, allowing string input for user identification.

            - password (serializers.CharField): 
                Represents the password field, with additional configurations:
                - `style={'input_type': 'password'}`: Ensures the input is treated as a password 
                field (hidden text in forms).
                - `trim_whitespace=False`: Prevents automatic whitespace trimming, ensuring the 
                password is processed as entered.
                - `write_only=True`: Ensures this field is used only for input and not included 
                in serialized output.

            - tokens (serializers.SerializerMethodField): 
                A read-only field that provides token information for the user (e.g., `access` and 
                `refresh` tokens). This field is dynamically generated using a custom method, 
                which typically retrieves token data for authenticated users.

        Methods:
             -get_tokens(obj):
                This method retrieves the `refresh` and `access` tokens for the user based on their email.
                
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
        """
            Returns the authentication tokens for a given user.

            This method retrieves the `refresh` and `access` tokens for the user based on their email.

            Parameters:
                - obj (dict): A dictionary containing user information, including the user's email.

            Returns:
                - dict: A dictionary containing the `refresh` and `access` tokens associated with the 
                user, typically used for authentication purposes.

            Raises:
                - User.DoesNotExist: If no user with the provided email exists in the database.
        """

        user = User.objects.get(email=obj['username'])
        if user:
            return {
                'refresh': user.tokens()['refresh'],
                'access': user.tokens()['access']
            }
    
    def login(self, validated_data):
        """
            Validates the user credentials and checks account status.

            This method authenticates the user by verifying the provided username and password. It also
            checks whether the user's account is disabled. If successful, it returns the user's email, 
            username, and authentication tokens.

            Parameters:
                - attrs (dict): A dictionary containing user input data, specifically 'username' and 
                'password'.

            Returns:
                - dict: A dictionary containing the user's email, username, and tokens if authentication 
                is successful.

            Raises:
                - AuthenticationFailed: If the authentication fails due to incorrect username or password, 
                or if the user's account has been disabled.

            Note:
                The user must not be deleted (i.e., `user.is_deleted` must be `False`). If the account is 
                deleted, an error message is raised with instructions to contact support.
        """

        username = validated_data.get('username')
        password = validated_data.get('password')
        if username and password:
        
            user = authenticate(
                request=self.context.get('request'),
                email=username,
                password=password
            )
            if not user:
                raise AuthenticationFailed("Username or password is incorrect")

            if user.is_deleted:
                raise AuthenticationFailed('Account disabled. Please contact Admin at g2p-help@ebi.ac.uk')
            
            user_serializer = UserSerializer(User)
            panels = user_serializer.get_panels(id=user.id)
            update_last_login(None, user) # to update the last login column in the User table on login

            login_data = {
                
                'email': user.email,
                'user_name': user.first_name + " " + user.last_name,
                'panels': panels,
                'tokens': user.tokens()
            }
            return login_data
    
    class Meta:
        model = User
        fields = ['username','password','tokens']
    

class LogoutSerializer(serializers.Serializer):
    """
        LogoutSerializer: Handles the serialization and validation of the refresh token for logout.

        This serializer is used to validate and process the refresh token provided during a logout 
        request. It ensures that the token is valid and then attempts to blacklist it, effectively 
        revoking the token and preventing further use.

        Attributes:
            - refresh: A `CharField` that represents the refresh token to be validated and blacklisted.

        Methods:
            - validate(attrs): Validates the presence of the refresh token in the input data.
            - save(**kwargs): Blacklists the refresh token to revoke access.
    """

    refresh = serializers.CharField()

    def validate(self, attrs):
        """
            Validates the refresh token provided in the request.

            This method ensures that the `refresh` field is present in the input data and assigns it to 
            the `self.token` attribute for further processing.

            Parameters:
                - attrs (dict): The input data containing the refresh token.

            Returns:
                - dict: The validated input data.

            Raises:
                - serializers.ValidationError: If the `refresh` field is not provided or invalid.
        """

        self.token = attrs['refresh']

        return attrs
    
    def save(self,**kwargs):
        """
            Blacklists the refresh token to revoke user access.

            This method uses the Django REST Framework SimpleJWT `RefreshToken` class to blacklist the 
            provided refresh token. Blacklisting the token ensures it can no longer be used to obtain 
            new access tokens.

            Parameters:
                - **kwargs: Additional keyword arguments passed to the method (not used here).

            Raises:
                - serializers.ValidationError: If the token is invalid or blacklisting fails.
        """

        token = RefreshToken(self.token)
        try:
           token.blacklist()
        except TokenError as e:
            raise serializers.ValidationError({"message": str(e)})

        

    


