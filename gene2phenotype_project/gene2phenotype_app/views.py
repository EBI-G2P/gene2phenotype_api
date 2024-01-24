from rest_framework import generics, permissions
from gene2phenotype_app.serializers import PanelSerializer
from gene2phenotype_app.models import Panel

class PanelList(generics.ListAPIView):
    queryset = Panel.objects.filter()
    serializer_class = PanelSerializer
