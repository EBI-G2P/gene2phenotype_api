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
                                            LocusGeneSerializer, DiseaseSerializer)

from gene2phenotype_app.models import (Panel, User, AttribType, Attrib,
                                       LocusGenotypeDisease, Locus, OntologyTerm,
                                       DiseaseOntology, Disease)


class PanelList(generics.ListAPIView):
    queryset = Panel.objects.filter()
    serializer_class = PanelSerializer

    def list(self, request, *args, **kwargs):
        user = self.request.user
        queryset = self.get_queryset()
        panel_list = []
        for panel in queryset:
            if panel.is_visible == 1 or (user.is_authenticated and panel.is_visible == 0):
                panel_list.append(panel.name)
        return Response(panel_list)

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
        attrib = Attrib.objects.filter(type=attrib_type.first().id, value='gene')
        queryset = Locus.objects.filter(name=name, type=attrib.first().id)

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
        attrib = Attrib.objects.filter(type=attrib_type.first().id, value='gene')
        queryset = Locus.objects.filter(name=name, type=attrib.first().id)

        if not queryset.exists():
            self.handle_no_permission(name)

        serializer = LocusGeneSerializer
        summmary = serializer.records_summary(queryset.first())
        response_data = {
            'panel_name': queryset.first().name,
            'records_summary': summmary,
        }

        return Response(response_data)

    def handle_no_permission(self, name):
        raise Http404(f"No matching Gene found for symbol: {name}")

    def handle_exception(self, exc):
        if isinstance(exc, Http404):
            return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)

        return super().handle_exception(exc)

class DiseaseDetail(generics.ListAPIView):
    # lookup_field = 'name'
    serializer_class = DiseaseSerializer

    def get_queryset(self):
        id = self.kwargs['id']
        ontology_term = OntologyTerm.objects.filter(accession=id)

        if not ontology_term.exists():
            self.handle_no_permission(id)

        disease_ontology = DiseaseOntology.objects.filter(ontology_term_id=ontology_term.first().id)

        if not disease_ontology.exists():
            self.handle_no_permission(id)

        queryset = Disease.objects.filter(id=disease_ontology.first().disease_id)

        if not queryset.exists():
            self.handle_no_permission(id)

        return queryset

    def handle_no_permission(self, id):
        raise Http404(f"No matching Disease found for: {id}")

    def handle_exception(self, exc):
        if isinstance(exc, Http404):
            return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)

        return super().handle_exception(exc)

class UserList(generics.ListAPIView):
    queryset = User.objects.filter(is_active=1, is_staff=0)
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

class LocusGenotypeDiseaseDetail(generics.ListAPIView):
    lookup_field = 'stable_id'
    serializer_class = LocusGenotypeDiseaseSerializer

    def get_queryset(self):
        stable_id = self.kwargs['stable_id']
        user = self.request.user
        queryset = LocusGenotypeDisease.objects.filter(stable_id=stable_id)

        if queryset.exists():
            obj = queryset.first()
            if user.is_authenticated and obj.is_deleted == 0:
                return LocusGenotypeDisease.objects.filter(stable_id=stable_id)
            elif obj.is_deleted == 0 and obj.is_reviewed == 1:
                return LocusGenotypeDisease.objects.filter(stable_id=stable_id)
            else:
                raise Http404('Entry not found in G2P')
        else:
            raise Http404('Entry not found in G2P')