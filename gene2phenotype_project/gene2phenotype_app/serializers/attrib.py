from rest_framework import serializers
from ..models import Attrib, AttribType


class AttribTypeSerializer(serializers.ModelSerializer):
    """
        Return the list of attribs for a specific type.
    """
    # to do - the way we presently fetch mutation mechanism is wrong 
    def get_all_attribs(self, id):
        # Get list of attribs for the specific type
        queryset = Attrib.objects.filter(type=id, is_deleted=0)
        code_list = [attrib.value for attrib in queryset]
        return code_list

    def get_all_attrib_description(self, id):
        """
            Retrieve all attribute descriptions for a given type.

            This method queries the `Attrib` model to fetch all non-deleted
            attributes associated with the specified type (identified by `id`).
            It returns a list of dictionaries, where each dictionary maps an
            attribute's value to its corresponding description.

            Args:
                id (int): The identifier for the type of attributes to retrieve.

            Returns:
                list[dict]: A list of dictionaries, each containing a key-value pair
                            where the key is the attribute's value and the value is
                            the attribute's description.

            Example:
                Suppose `Attrib` objects have `value = "definitive"` and 
                `description = "This category is well-supported by evidence."`, 
                and `id = 1` corresponds to a specific type. The method might return:
                
                [
                    {"definitive": "This category is well-supported by evidence."},
                    {"disputed": "This category has conflicting evidence."},
                    ...
                ]
        """
        queryset = Attrib.objects.filter(type=id, is_deleted=0)
        code_description = [{attrib.value: attrib.description} for attrib in queryset]
        return code_description
    

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



