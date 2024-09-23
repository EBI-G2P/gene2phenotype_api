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
    # TODO: add column 'is_deleted' and select only non deleted attrib
    queryset = AttribType.objects.all()

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        result = {}
        for attrib_type in queryset:
            serializer = AttribTypeSerializer(attrib_type)
            all_attribs = serializer.get_all_attribs(attrib_type.id)
            result[attrib_type.code] = all_attribs

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
                {"message": f"Attrib type {code} not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        return Attrib.objects.filter(type=attrib_type_obj)

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        code_list = [attrib.value for attrib in queryset]
        return Response({'results':code_list, 'count':len(code_list)})
