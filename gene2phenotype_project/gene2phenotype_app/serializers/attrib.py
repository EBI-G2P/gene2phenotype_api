from rest_framework import serializers
from ..models import Attrib, AttribType


class AttribTypeSerializer(serializers.ModelSerializer):
    """
        Return the list of attribs for a specific type.
    """

    def get_all_attribs(self, id):
        # Get list of attribs for the specific type
        queryset = Attrib.objects.filter(type=id)
        code_list = [attrib.value for attrib in queryset]
        return code_list

    class Meta:
        model = AttribType
        fields = ['code']

class AttribSerializer(serializers.ModelSerializer):
    """
        Attribs represent controlled vocabulary.
    """

    class Meta:
        model = Attrib
        fields = ['value']
