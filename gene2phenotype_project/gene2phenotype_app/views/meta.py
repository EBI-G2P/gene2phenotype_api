from rest_framework.views import APIView
from rest_framework.response import Response
from django.db.models import Max
from drf_spectacular.utils import extend_schema, OpenApiResponse
import textwrap

from gene2phenotype_app.models import Meta

from gene2phenotype_app.serializers import MetaSerializer


@extend_schema(
    tags=["Reference data"],
    description=textwrap.dedent("""
    Fetch list of all reference data used in G2P with their respective versions.
    """),
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
    API view for retrieving the reference data.
    """

    def get_queryset(self):
        """
        Method to get a queryset containing the latest records for each unique key

        Returns:
            QuerySet: a queryset containing the latest records
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
        Return a list of the reference data used in G2P with their respective versions.

        Returns:
            Response: A serialized list of the latest meta records.
        """
        queryset = self.get_queryset()
        serializer = MetaSerializer(queryset, many=True)
        return Response(serializer.data)
