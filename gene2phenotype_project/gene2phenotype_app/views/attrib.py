from rest_framework import generics, status
from rest_framework.response import Response

from gene2phenotype_app.serializers import AttribTypeSerializer, AttribSerializer
from gene2phenotype_app.models import AttribType, Attrib


class AttribTypeList(generics.ListAPIView):
    """
        Display all available attribs by type.
        Some attribs can be deprecated.

        Returns:
                (dict) response: list of attribs for each attrib type.
    """
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
        API view to list all attribute types with their associated attribute descriptions.

        This view inherits from Django REST Framework's `ListAPIView` and is responsible
        for retrieving and returning a dictionary where each key corresponds to an 
        attribute type code, and each value is a list of dictionaries. Each dictionary 
        in the list contains a mapping of an attribute's value to its description.

        Attributes:
            queryset (QuerySet): The base queryset of `AttribType` objects.

        Methods:
            list(request, *args, **kwargs):
                Customizes the default list method to return a dictionary where each key 
                is an attribute type code and each value is a list of attribute descriptions.

        Example:
            Suppose the `AttribType` model has entries with `code = "type1"` and an `id` of `1`.
            If `Attrib` objects related to this type have values and descriptions, the 
            response might look like this:

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
    

    queryset = AttribType.objects.filter(is_deleted=0)
    
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        result = {}
        for attrib_type in queryset:
            serializer = AttribTypeSerializer(attrib_type)
            all_attribs_description = serializer.get_all_attrib_description(attrib_type.id)
            result[attrib_type.code] = all_attribs_description

        return Response(result)

class AttribList(generics.ListAPIView):
    """
        Display the attribs for a specific attrib type.

        Args:
            (string) code: type of attrib

        Returns:
                Response object includes:
                    (list) results: list of attribs
                    (int) count: number of attribs

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
            return Response(
                {"error": f"Attrib type {code} not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        return Attrib.objects.filter(type=attrib_type_obj)

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        code_list = [attrib.value for attrib in queryset]
        return Response({'results':code_list, 'count':len(code_list)})
