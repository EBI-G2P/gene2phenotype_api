from rest_framework.views import APIView
from rest_framework.response import Response
from django.db.models import Max

from gene2phenotype_app.models import Meta

from gene2phenotype_app.serializers import MetaSerializer


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
        Get method to get the reference data

        Args:
            request (_type_): A get request

        Returns:
            _type_: Response object [key, source, version]
        """
        queryset = self.get_queryset()
        serializer = MetaSerializer(queryset, many=True)

        # Format the OMIM and Mondo versions
        for query_data in queryset:
            if query_data.key == "import_gene_disease_omim":
                query_data.source.name = "Added by curators"
                query_data.version = "" # we don't have a specific version
            elif query_data.key == "import_gene_disease_mondo":
                query_data.source.name = "Added by curators"
                query_data.version = f"Checked against version {query_data.version}"

        return Response(serializer.data)
