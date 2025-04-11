from rest_framework import generics, status
from rest_framework.response import Response

from gene2phenotype_app.serializers import AttribTypeSerializer, AttribSerializer
from gene2phenotype_app.models import AttribType, Attrib


class AttribTypeList(generics.ListAPIView):
    """
        Display all available attributes by their type.

        Returns: A dictionary where the keys represent attribute types,
                 and the values are lists of their respective attributes.
    """
    serializer_class = AttribTypeSerializer

    queryset = AttribType.objects.filter(is_deleted=0)

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        result = {}
        for attrib_type in queryset:
            serializer = AttribTypeSerializer(attrib_type)
            all_attribs = serializer.get_all_attribs(attrib_type.id)
            result[attrib_type.code] = all_attribs

        return Response(result)

class AttribTypeDescriptionList(generics.ListAPIView):
    """
        List all attribute types with their associated descriptions.

        Returns: A list of attribute types, each with details of their respective attributes.

        Example:

            {
                "type1": [
                    {"definitive": "This category is well-supported by evidence."},
                    {"disputed": "This category has conflicting evidence."},
                    ...
                ],
                "type2": [
                    {"limited": "This category is based on limited evidence."},
                    {"strong": "This category is strongly supported by evidence."},
                    ...
                ]
            }
    """
    serializer_class = AttribTypeSerializer

    queryset = AttribType.objects.filter(is_deleted=0)

    def list(self, request, *args, **kwargs):
        """
            This method customizes the default list method to return a dictionary where each key 
            is an attribute type code and each value is a list of attribute descriptions.
        """
        queryset = self.get_queryset()
        result = {}
        for attrib_type in queryset:
            serializer = AttribTypeSerializer(attrib_type)
            all_attribs_description = serializer.get_all_attrib_description(attrib_type.id)
            result[attrib_type.code] = all_attribs_description

        return Response(result)

class AttribList(generics.ListAPIView):
    """
        Fetch a list of attributes for a specific attribute type.

        Args:
            (string) `code`: attribute type

        Returns: list of attributes with the following format
                    (list) `results`: list of attributes
                    (int) `count`: number of attributes

        Example:

                {
                    "results": [
                        "definitive",
                        "disputed",
                        "limited",
                        "moderate",
                        "refuted",
                        "strong"
                    ],
                    "count": 6
                }
    """
    lookup_field = 'type'
    serializer_class = AttribSerializer

    def get_queryset(self):
        # 'code' is the type of attrib
        code = self.kwargs['code']

        try:
            attrib_type_obj = AttribType.objects.get(code=code)
        except AttribType.DoesNotExist:
            return None
        else:
            return Attrib.objects.filter(type=attrib_type_obj)

    def list(self, request, *args, **kwargs):
        code = self.kwargs['code']
        queryset = self.get_queryset()

        if not queryset:
            return Response(
                {"error": f"Attrib type '{code}' not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        code_list = [attrib.value for attrib in queryset]

        return Response(
            {
                "results": code_list,
                "count": len(code_list)
            }
        )
