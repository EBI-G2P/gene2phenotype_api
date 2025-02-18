from rest_framework.views import APIView
from rest_framework.response import Response
from django.db.models import Max

from gene2phenotype_app.models import Meta

from gene2phenotype_app.serializers import MetaSerializer


class MetaView(APIView):
    def get_queryset(self):
        # to group by key
        latest_records =( Meta.objects.values("key").annotate(latest_date=Max('date_update')) )

        #then we use a list comprehension to check using the new column latest_date
        queryset = Meta.objects.filter(date_update__in=[record["latest_date"] for record in latest_records])

        return queryset
    
    def get(self, request):
        queryset = self.get_queryset()
        serializer = MetaSerializer(queryset, many=True)
        return Response(serializer.data)