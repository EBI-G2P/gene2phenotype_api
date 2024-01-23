from rest_framework import serializers
from .models import Panel

class PanelSerializer(serializers.ModelSerializer):
    name = serializers.CharField()
    description = serializers.CharField(read_only=True)

    class Meta:
        model = Panel
        fields = ['name', 'description']
