from rest_framework import generics, permissions
from django.shortcuts import get_object_or_404
from rest_framework.response import Response

from gene2phenotype_app.serializers import (PanelSerializer,
                                            UserSerializer,
                                            PanelDetailSerializer,
                                            AttribTypeSerializer,
                                            AttribSerializer,
                                            LocusGenotypeDiseaseSerializer)

from gene2phenotype_app.models import Panel, User, AttribType, Attrib, LocusGenotypeDisease


class PanelList(generics.ListAPIView):
    queryset = Panel.objects.filter()
    serializer_class = PanelSerializer

class PanelDetail(generics.ListAPIView):
    lookup_field = 'name'
    serializer_class = PanelDetailSerializer

    def get_queryset(self):
        name = self.kwargs['name']
        return Panel.objects.filter(name=name)

class PanelStats(generics.ListAPIView):
    def get(self, request, name, *args, **kwargs):
        panel = get_object_or_404(Panel, name=name)
        serializer = PanelDetailSerializer()
        stats = serializer.calculate_stats(panel)
        response_data = {
            'panel_name': panel.name,
            'stats': stats,
        }

        return Response(response_data)

class PanelRecordsSummary(generics.ListAPIView):
    def get(self, request, name, *args, **kwargs):
        panel = get_object_or_404(Panel, name=name)
        serializer = PanelDetailSerializer()
        summmary = serializer.records_summary(panel)
        response_data = {
            'panel_name': panel.name,
            'records_summary': summmary,
        }

        return Response(response_data)

class UserList(generics.ListAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer

class AttribTypeList(generics.ListAPIView):
    queryset = AttribType.objects.all()
    serializer_class = AttribTypeSerializer

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        code_list = [attrib.code for attrib in queryset]
        return Response(code_list)

class AttribList(generics.ListAPIView):
    lookup_field = 'type'
    serializer_class = AttribSerializer

    def get_queryset(self):
        code = self.kwargs['code']
        return Attrib.objects.filter(type=AttribType.objects.get(code=code))
    
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        code_list = [attrib.value for attrib in queryset]
        return Response(code_list)

class LocusGenotypeDiseaseDetail(generics.RetrieveUpdateDestroyAPIView):
    lookup_field = 'stable_id'
    serializer_class = LocusGenotypeDiseaseSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        stable_id = self.kwargs['stable_id']
        return LocusGenotypeDisease.objects.filter(stable_id=stable_id)