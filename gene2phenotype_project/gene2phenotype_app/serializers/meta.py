from rest_framework import serializers

from ..models import Meta

class MetaSerializer(serializers.ModelSerializer):
    key = serializers.CharField()
    version = serializers.CharField() 
    source = serializers.SerializerMethodField()

    def get_source(self, obj):
        source = obj.source.name
        return source

    class Meta:
        model = Meta
        fields = ["key", "source", "version"]