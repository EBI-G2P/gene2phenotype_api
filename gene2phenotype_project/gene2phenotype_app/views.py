from rest_framework import generics, permissions, status
from django.shortcuts import get_object_or_404
from django.http import Http404
from rest_framework.response import Response

from gene2phenotype_app.serializers import (PanelSerializer,
                                            UserSerializer,
                                            PanelDetailSerializer,
                                            AttribTypeSerializer,
                                            AttribSerializer,
                                            LocusGenotypeDiseaseSerializer,
                                            LocusGeneSerializer)

from gene2phenotype_app.models import Panel, User, AttribType, Attrib, LocusGenotypeDisease, Locus


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

class LocusGene(generics.ListAPIView):
    lookup_field = 'name'
    serializer_class = LocusGeneSerializer

    def get_queryset(self):
        name = self.kwargs['name']
        attrib_type = AttribType.objects.filter(code='locus_type')
        attrib = Attrib.objects.filter(type=attrib_type[0].id, value='gene')
        queryset = Locus.objects.filter(name=name, type=attrib[0].id)

        if not queryset.exists():
            self.handle_no_permission(name)

        return queryset

    def handle_no_permission(self, name):
        raise Http404(f"No matching Gene found for symbol: {name}")

    def handle_exception(self, exc):
        if isinstance(exc, Http404):
            return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)

        return super().handle_exception(exc)

class LocusGeneSummary(generics.ListAPIView):
    lookup_field = 'name'
    serializer_class = LocusGeneSerializer

    def get(self, request, name, *args, **kwargs):
        attrib_type = AttribType.objects.filter(code='locus_type')
        attrib = Attrib.objects.filter(type=attrib_type[0].id, value='gene')
        queryset = Locus.objects.filter(name=name, type=attrib[0].id)

        if not queryset.exists():
            self.handle_no_permission(name)

        serializer = LocusGeneSerializer
        summmary = serializer.records_summary(queryset[0])
        response_data = {
            'panel_name': queryset[0].name,
            'records_summary': summmary,
        }

        return Response(response_data)

    def handle_no_permission(self, name):
        raise Http404(f"No matching Gene found for symbol: {name}")

    def handle_exception(self, exc):
        if isinstance(exc, Http404):
            return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)

        return super().handle_exception(exc)

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