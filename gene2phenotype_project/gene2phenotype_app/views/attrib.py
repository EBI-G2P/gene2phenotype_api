from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema

from gene2phenotype_app.serializers import AttribTypeSerializer, AttribSerializer
from gene2phenotype_app.models import AttribType, Attrib


@extend_schema(exclude=True)
class AttribTypeList(APIView):
    serializer_class = AttribTypeSerializer

    def get(self, request, *args, **kwargs):
        """
        Fetch all available attributes grouped by type.

        Returns: A dictionary where the keys represent attribute types,
                and the values are lists of their respective attributes.
        """
        queryset = AttribType.objects.filter(is_deleted=0)

        result = {}
        for attrib_type in queryset:
            serializer = AttribTypeSerializer(attrib_type)
            all_attribs = serializer.get_all_attribs(attrib_type.id)
            result[attrib_type.code] = all_attribs

        return Response(result)


@extend_schema(exclude=True)
class AttribTypeDescriptionList(APIView):
    serializer_class = AttribTypeSerializer

    def get(self, request, *args, **kwargs):
        """
        Fetch all attributes with their corresponding descriptions
        grouped by attribute type.

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
        # Fetch attrib types that are not deleted
        queryset = AttribType.objects.filter(is_deleted=0)
        result = {}
        for attrib_type in queryset:
            serializer = AttribTypeSerializer(attrib_type)
            all_attribs_description = serializer.get_all_attrib_description(
                attrib_type.id
            )
            result[attrib_type.code] = all_attribs_description

        return Response(result)


@extend_schema(exclude=True)
class AttribList(APIView):
    lookup_field = "type"
    serializer_class = AttribSerializer

    def get_queryset(self):
        attrib_type = self.kwargs["attrib_type"]

        try:
            attrib_type_obj = AttribType.objects.get(code=attrib_type)
        except AttribType.DoesNotExist:
            return None
        else:
            return Attrib.objects.filter(type=attrib_type_obj)

    def get(self, request, *args, **kwargs):
        """
        Fetch all attribute values for a specific attribute type.

        Args:
            attrib_type (string): attribute type

        Returns: list of attributes with the following format
                    results (list): list of attributes
                    count (int): number of attributes

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
        attrib_type = self.kwargs["attrib_type"]
        queryset = self.get_queryset()

        if not queryset:
            return Response(
                {"error": f"Attrib type '{attrib_type}' not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        attrib_type_list = [attrib.value for attrib in queryset]

        return Response({"results": attrib_type_list, "count": len(attrib_type_list)})
