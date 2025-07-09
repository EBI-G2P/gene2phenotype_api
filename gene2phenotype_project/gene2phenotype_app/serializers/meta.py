from rest_framework import serializers

from ..models import Meta


class MetaSerializer(serializers.ModelSerializer):
    """
    Meta Serializer for the model Meta
    """

    key = serializers.CharField()
    version = serializers.CharField()
    source = serializers.SerializerMethodField()

    def get_source(self, obj):
        """
        Used to get the source because the source is a ForeignKey in this table

        Args:
            obj (Queryset): Queryset object

        Returns:
            str: source
        """
        source = obj.source.name
        return source

    class Meta:
        """
        Meta class for this serializer
        """

        model = Meta
        fields = ["key", "source", "version"]
