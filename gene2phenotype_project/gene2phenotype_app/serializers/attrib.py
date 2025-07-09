from rest_framework import serializers
from ..models import Attrib, AttribType


class AttribTypeSerializer(serializers.ModelSerializer):
    """
    Return the list of attribs for a specific type.
    """

    def get_all_attribs(self, id):
        # Get list of attribs for the specific type
        queryset = Attrib.objects.filter(type=id, is_deleted=0)
        code_list = [attrib.value for attrib in queryset]
        return code_list

    def get_all_attrib_description(self, id):
        """
        Retrieve all attribute descriptions for a given attribute type.

        Args:
            id (int): The attribute type

        Returns:
            list[dict]: A list of dictionaries, each containing a key-value pair
                        where the key is the attribute's value and the value is
                        the attribute's description.
        """
        queryset = Attrib.objects.filter(type=id, is_deleted=0)
        code_description = [{attrib.value: attrib.description} for attrib in queryset]
        return code_description

    class Meta:
        model = AttribType
        fields = ["code"]


class AttribSerializer(serializers.ModelSerializer):
    """
    Attribs represent controlled vocabulary.
    """
    class Meta:
        model = Attrib
        fields = ["value"]
