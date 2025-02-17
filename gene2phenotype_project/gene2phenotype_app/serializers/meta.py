from rest_framework import serializers

from ..models import Meta

class MetaSerializer(serializers.ModelSerializer):
    key = serializers.CharField()
    version = serializers.CharField() 
    date_update = serializers.DateTimeField()

    class Meta:
        model = Meta
        fields = ["key", "version", "date_update"]