from rest_framework import generics, status
from django.shortcuts import get_object_or_404
from django.http import Http404
from rest_framework.response import Response
from django.db.models import Q

from gene2phenotype_app.serializers import (UserSerializer,
                                            PanelDetailSerializer,
                                            AttribTypeSerializer,
                                            AttribSerializer,
                                            LocusGenotypeDiseaseSerializer,
                                            LocusGeneSerializer, DiseaseSerializer)

from gene2phenotype_app.models import (Panel, User, AttribType, Attrib,
                                       LocusGenotypeDisease, Locus, OntologyTerm,
                                       DiseaseOntology, Disease, LGDPanel,
                                       LocusAttrib)


class BaseView(generics.ListAPIView):
    def handle_no_permission(self, name_type, name):
        if name is None:
            raise Http404(f"{name_type}")
        else:
            raise Http404(f"No matching {name_type} found for: {name}")

    def handle_exception(self, exc):
        if isinstance(exc, Http404):
            return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)

        return super().handle_exception(exc)

class PanelList(generics.ListAPIView):
    queryset = Panel.objects.filter()
    serializer_class = PanelDetailSerializer

    def list(self, request, *args, **kwargs):
        user = self.request.user
        queryset = self.get_queryset()
        panel_list = []
        for panel in queryset:
            if panel.is_visible == 1 or (user.is_authenticated and panel.is_visible == 0):
                panel_list.append(panel.name)
        return Response(panel_list)

class PanelDetail(BaseView):
    lookup_field = 'name'
    serializer_class = PanelDetailSerializer

    def get_queryset(self):
        name = self.kwargs['name']
        queryset = Panel.objects.filter(name=name)

        if not queryset.exists():
            self.handle_no_permission('Panel', name)

        return queryset

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

class LocusGene(BaseView):
    lookup_field = 'name'
    serializer_class = LocusGeneSerializer

    def get_queryset(self):
        name = self.kwargs['name']
        attrib_type = AttribType.objects.filter(code='locus_type')
        attrib = Attrib.objects.filter(type=attrib_type.first().id, value='gene')
        queryset = Locus.objects.filter(name=name, type=attrib.first().id)

        if not queryset.exists():
            # Try to find gene in locus_attrib (gene synonyms)
            attrib_type = AttribType.objects.filter(code='gene_synonym')
            queryset = LocusAttrib.objects.filter(value=name, attrib_type=attrib_type.first().id, is_deleted=0)

            if not queryset.exists():
                self.handle_no_permission('Gene', name)

            queryset = Locus.objects.filter(id=queryset.first().locus.id)

        return queryset

class LocusGeneSummary(BaseView):
    serializer_class = LocusGeneSerializer

    def get(self, request, name, *args, **kwargs):
        attrib_type = AttribType.objects.filter(code='locus_type')
        attrib = Attrib.objects.filter(type=attrib_type.first().id, value='gene')
        queryset = Locus.objects.filter(name=name, type=attrib.first().id)

        if not queryset.exists():
            # Try to find gene in locus_attrib (gene synonyms)
            attrib_type = AttribType.objects.filter(code='gene_synonym')
            queryset = LocusAttrib.objects.filter(value=name, attrib_type=attrib_type.first().id, is_deleted=0)

            if not queryset.exists():
                self.handle_no_permission('Gene', name)

            queryset = Locus.objects.filter(id=queryset.first().locus.id)

        serializer = LocusGeneSerializer
        summmary = serializer.records_summary(queryset.first())
        response_data = {
            'gene_symbol': queryset.first().name,
            'records_summary': summmary,
        }

        return Response(response_data)

class DiseaseDetail(BaseView):
    serializer_class = DiseaseSerializer

    def get_queryset(self):
        id = self.kwargs['id']
        ontology_term = OntologyTerm.objects.filter(accession=id)

        if not ontology_term.exists():
            self.handle_no_permission('Disease', id)

        disease_ontology = DiseaseOntology.objects.filter(ontology_term_id=ontology_term.first().id)

        if not disease_ontology.exists():
            self.handle_no_permission('Disease', id)

        queryset = Disease.objects.filter(id=disease_ontology.first().disease_id)

        if not queryset.exists():
            self.handle_no_permission('Disease', id)

        return queryset

class UserList(generics.ListAPIView):
    queryset = User.objects.filter(is_active=1, is_staff=0)
    serializer_class = UserSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update({'user':self.request.user})
        return context

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

class LocusGenotypeDiseaseDetail(BaseView):
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
                self.handle_no_permission('Entry', stable_id)
        else:
            self.handle_no_permission('Entry', stable_id)

class SearchView(BaseView):
    serializer_class = LocusGenotypeDiseaseSerializer

    def get_queryset(self):
        user = self.request.user
        search_type = self.request.query_params.get('type', None)
        search_query = self.request.query_params.get('query', None)
        search_panel = self.request.query_params.get('panel', None)

        if not search_query:
            return LocusGenotypeDisease.objects.none()

        # Generic search
        if not search_type:
            if search_panel:
                queryset = LocusGenotypeDisease.objects.filter(
                    Q(locus__name=search_query, is_deleted=0, lgdpanel__panel__name=search_panel) |
                    Q(locus__locusidentifier__isnull=False, locus__locusidentifier__identifier=search_query, lgdpanel__panel__name=search_panel) |
                    Q(locus__locusattrib__isnull=False, locus__locusattrib__value=search_query, locus__locusattrib__is_deleted=0, lgdpanel__panel__name=search_panel) |
                    Q(disease__name__icontains=search_query, is_deleted=0, lgdpanel__panel__name=search_panel) |
                    Q(disease__diseaseontology__ontology_term__accession=search_query, is_deleted=0, lgdpanel__panel__name=search_panel) |
                    Q(lgdphenotype__phenotype__term__icontains=search_query, lgdphenotype__isnull=False, is_deleted=0, lgdpanel__panel__name=search_panel) |
                    Q(lgdphenotype__phenotype__accession=search_query, lgdphenotype__isnull=False, is_deleted=0, lgdpanel__panel__name=search_panel)
                ).order_by('locus__name', 'stable_id').distinct()
            else:
                queryset = LocusGenotypeDisease.objects.filter(
                    Q(locus__name=search_query, is_deleted=0) |
                    Q(locus__locusidentifier__isnull=False, locus__locusidentifier__identifier=search_query) |
                    Q(locus__locusattrib__isnull=False, locus__locusattrib__value=search_query, locus__locusattrib__is_deleted=0) |
                    Q(disease__name__icontains=search_query, is_deleted=0) |
                    Q(disease__diseaseontology__ontology_term__accession=search_query, is_deleted=0) |
                    Q(lgdphenotype__phenotype__term__icontains=search_query, lgdphenotype__isnull=False, is_deleted=0) |
                    Q(lgdphenotype__phenotype__accession=search_query, lgdphenotype__isnull=False, is_deleted=0)
                ).order_by('locus__name', 'stable_id').distinct()

            if not queryset.exists():
                self.handle_no_permission('results', search_query)

            if user.is_authenticated == False:
                for lgd in queryset:
                    lgdpanel_select = LGDPanel.objects.filter(lgd=lgd, panel__is_visible=1)
                    if lgdpanel_select.exists() == False:
                        queryset = queryset.exclude(id=lgd.id)

            return queryset

        queryset = LocusGenotypeDisease.objects.none()

        if search_type == 'gene':
            if search_panel:
                queryset = LocusGenotypeDisease.objects.filter(
                    Q(locus__name=search_query, is_deleted=0, lgdpanel__panel__name=search_panel) |
                    Q(locus__locusidentifier__isnull=False, locus__locusidentifier__identifier=search_query, lgdpanel__panel__name=search_panel) |
                    Q(locus__locusattrib__isnull=False, locus__locusattrib__value=search_query, locus__locusattrib__is_deleted=0, lgdpanel__panel__name=search_panel)
                ).order_by('locus__name', 'stable_id').distinct()
            else:
                queryset = LocusGenotypeDisease.objects.filter(
                    Q(locus__name=search_query, is_deleted=0) |
                    Q(locus__locusidentifier__isnull=False, locus__locusidentifier__identifier=search_query) |
                    Q(locus__locusattrib__isnull=False, locus__locusattrib__value=search_query, locus__locusattrib__is_deleted=0)
                ).order_by('locus__name', 'stable_id').distinct()

            if not queryset.exists():
                self.handle_no_permission('Gene', search_query)

        elif search_type == 'disease':
            if search_panel:
                queryset = LocusGenotypeDisease.objects.filter(
                    Q(disease__name__icontains=search_query, is_deleted=0, lgdpanel__panel__name=search_panel) |
                    Q(disease__diseaseontology__ontology_term__accession=search_query, is_deleted=0, lgdpanel__panel__name=search_panel)
                ).order_by('locus__name', 'stable_id').distinct()
            else:
                queryset = LocusGenotypeDisease.objects.filter(
                    Q(disease__name__icontains=search_query, is_deleted=0) |
                    Q(disease__diseaseontology__ontology_term__accession=search_query, is_deleted=0)
                ).order_by('locus__name', 'stable_id').distinct()

            if not queryset.exists():
                self.handle_no_permission('Disease', search_query)

        elif search_type == 'phenotype':
            if search_panel:
                queryset = LocusGenotypeDisease.objects.filter(
                    Q(lgdphenotype__phenotype__term__icontains=search_query, lgdphenotype__isnull=False, is_deleted=0, lgdpanel__panel__name=search_panel) |
                    Q(lgdphenotype__phenotype__accession=search_query, lgdphenotype__isnull=False, is_deleted=0, lgdpanel__panel__name=search_panel)
                ).order_by('locus__name', 'stable_id').distinct()
            else:
                queryset = LocusGenotypeDisease.objects.filter(
                    Q(lgdphenotype__phenotype__term__icontains=search_query, lgdphenotype__isnull=False, is_deleted=0) |
                    Q(lgdphenotype__phenotype__accession=search_query, lgdphenotype__isnull=False, is_deleted=0)
                ).order_by('locus__name', 'stable_id').distinct()

            if not queryset.exists():
                self.handle_no_permission('Phenotype', search_query)

        else:
            self.handle_no_permission('Search type is not valid', None)

        # If the user is not logged in, only show visible panels
        if queryset.exists():
            if user.is_authenticated == False:
                for lgd in queryset:
                    lgdpanel_select = LGDPanel.objects.filter(lgd=lgd, panel__is_visible=1)
                    if lgdpanel_select.exists() == False:
                        queryset = queryset.exclude(id=lgd.id)

        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        list_output = []

        for lgd in queryset:
            panels = LGDPanel.objects.filter(lgd=lgd.id)
            data = { 'id':lgd.stable_id,
                     'gene':lgd.locus.name,
                     'genotype':lgd.genotype.value,
                     'disease':lgd.disease.name,
                     'panel':[panel_obj.panel.name for panel_obj in panels] }
            list_output.append(data)

        return Response(list_output)