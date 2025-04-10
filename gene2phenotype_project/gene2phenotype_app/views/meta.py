from rest_framework.views import APIView
from rest_framework.response import Response
from django.db.models import Max
from drf_spectacular.utils import extend_schema, OpenApiResponse

from gene2phenotype_app.models import Meta

from gene2phenotype_app.serializers import MetaSerializer


@extend_schema(
    responses={
        200: OpenApiResponse(
            description="Reference data response",
            response={
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "key": {"type": "string"},
                            "source": {"type": "string"},
                            "version": {"type": "string"}
                        }
                    }
            }
        )
    }
)
class MetaView(APIView):
    """
    The View for Meta record

    Args:
        APIView (_type_): APIView
    """

    def get_queryset(self):
        """
        Method to get latest records using the key to group it

        Returns:
            _type_: queryset containing the unique keys with the latest records an
        """
        # to group by key to create a queryset containing the key and the latest date
        latest_records = Meta.objects.values("key").annotate(
            latest_date=Max("date_update")
        )

        # then we use a list comprehension to check using the new column latest date 
        queryset = Meta.objects.filter(date_update__in=[record["latest_date"] for record in latest_records])

        return queryset

    def get(self, request):
        """
        Return a list with the reference data used in G2P and respective version
        """
        queryset = self.get_queryset()
        serializer = MetaSerializer(queryset, many=True)
        return Response(serializer.data)
