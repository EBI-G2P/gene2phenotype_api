from rest_framework import serializers
from .models import Panel, User, UserPanel, AttribType, Attrib

class PanelSerializer(serializers.ModelSerializer):
    name = serializers.CharField(read_only=True)
    description = serializers.CharField(read_only=True)

    class Meta:
        model = Panel
        fields = ['name', 'description']

class PanelDetailSerializer(PanelSerializer):
    curators = serializers.SerializerMethodField()

    def get_curators(self, id):
        x = UserPanel.objects.filter(panel=id)
        users = []
        for u in x:
            if u.user.is_active == 1:
                users.append(u.user.username)
        return users
    
    class Meta:
        model = Panel
        fields = PanelSerializer.Meta.fields + ['curators']

class UserSerializer(serializers.ModelSerializer):
    user = serializers.CharField(read_only=True, source="username")
    email = serializers.CharField(read_only=True)
    panels = serializers.SerializerMethodField()
    is_active = serializers.CharField(read_only=True)

    def get_panels(self, id):
        x = UserPanel.objects.filter(user=id)
        panels_list = []
        for p in x:
            panels_list.append(p.panel.name)
        return panels_list

    class Meta:
        model = User
        fields = ['user', 'email', 'is_active', 'panels']

class AttribTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttribType
        fields = ['code']

class AttribSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attrib
        fields = ['value']
