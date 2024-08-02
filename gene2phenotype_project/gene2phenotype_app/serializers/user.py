from rest_framework import serializers
from ..models import User, UserPanel


class UserSerializer(serializers.ModelSerializer):
    """
        Serializer for the User model.
    """

    user_name = serializers.SerializerMethodField()
    email = serializers.CharField(read_only=True)
    panels = serializers.SerializerMethodField()
    is_active = serializers.CharField(read_only=True)

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
        fields = ['user_name', 'email', 'is_active', 'panels']