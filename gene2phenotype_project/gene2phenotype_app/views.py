from rest_framework import generics, status, permissions
from django.http import Http404
from rest_framework.response import Response
from django.db.models import Q
from rest_framework.pagination import PageNumberPagination


from gene2phenotype_app.serializers import (UserSerializer,
                                            PanelDetailSerializer,
                                            AttribTypeSerializer,
                                            AttribSerializer,
                                            LocusGenotypeDiseaseSerializer,
                                            LocusGeneSerializer, DiseaseSerializer,
                                            CreateDiseaseSerializer, GeneDiseaseSerializer,
                                            DiseaseDetailSerializer, PublicationSerializer)

from gene2phenotype_app.models import (Panel, User, AttribType, Attrib,
                                       LocusGenotypeDisease, Locus, OntologyTerm,
                                       DiseaseOntology, Disease, LGDPanel,
                                       LocusAttrib, GeneDisease)


class BaseView(generics.ListAPIView):
    def handle_no_permission(self, name_type, name):
        if name is None:
            raise Http404(f"{name_type}")
        else:
            raise Http404(f"No matching {name_type} found for: {name}")

    def handle_exception(self, exc):
        if isinstance(exc, Http404):
            return Response({"message": str(exc)}, status=status.HTTP_404_NOT_FOUND)

        return super().handle_exception(exc)

class PanelList(generics.ListAPIView):
    queryset = Panel.objects.all()
    serializer_class = PanelDetailSerializer

    def list(self, request, *args, **kwargs):
        user = self.request.user
        queryset = self.get_queryset()
        panel_list = []
        for panel in queryset:
            if panel.is_visible == 1 or (user.is_authenticated and panel.is_visible == 0):
                panel_list.append(panel.name)
        return Response({'results':panel_list, 'count':len(panel_list)})

class PanelDetail(BaseView):
    serializer_class = PanelDetailSerializer

    def get_queryset(self):
        name = self.kwargs['name']
        user = self.request.user
        queryset = Panel.objects.filter(name=name)

        flag = 0
        for panel in queryset:
            if panel.is_visible == 1 or (user.is_authenticated and panel.is_visible == 0):
                flag = 1

        # Panel doesn't exist or user has no permission to view it
        if flag == 0:
            self.handle_no_permission('Panel', name)
        else:
            return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset().first()
        serializer = PanelDetailSerializer(queryset)
        return Response(serializer.data)

class PanelStats(BaseView):
    def get(self, request, name, *args, **kwargs):
        user = self.request.user
        queryset = Panel.objects.filter(name=name)

        flag = 0
        for panel in queryset:
            if panel.is_visible == 1 or (user.is_authenticated and panel.is_visible == 0):
                flag = 1

        if flag == 1:
            serializer = PanelDetailSerializer()
            stats = serializer.calculate_stats(queryset.first())
            response_data = {
                'panel_name': queryset.first().name,
                'stats': stats,
            }
            return Response(response_data)

        else:
            self.handle_no_permission('Panel', name)

class PanelRecordsSummary(BaseView):
    def get(self, request, name, *args, **kwargs):
        user = self.request.user
        queryset = Panel.objects.filter(name=name)

        flag = 0
        for panel in queryset:
            if panel.is_visible == 1 or (user.is_authenticated and panel.is_visible == 0):
                flag = 1

        if flag == 1:
            serializer = PanelDetailSerializer()
            summary = serializer.records_summary(queryset.first())
            response_data = {
                'panel_name': queryset.first().name,
                'records_summary': summary,
            }
            return Response(response_data)

        else:
            self.handle_no_permission('Panel', name)

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

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset().first()
        serializer = LocusGeneSerializer(queryset)
        return Response(serializer.data)

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
        summmary = serializer.records_summary(queryset.first(), self.request.user)
        response_data = {
            'gene_symbol': queryset.first().name,
            'records_summary': summmary,
        }

        return Response(response_data)

class GeneFunction(BaseView):
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
        summmary = serializer.function(queryset.first())
        response_data = {
            'gene_symbol': queryset.first().name,
            'function': summmary,
        }

        return Response(response_data)

class GeneDiseaseView(BaseView):
    serializer_class = GeneDiseaseSerializer

    def get_queryset(self):
        name = self.kwargs['name']
        gene_obj = Locus.objects.filter(name=name)
        queryset = GeneDisease.objects.filter(gene=gene_obj.first())

        if not queryset.exists():
            # Try to find gene in locus_attrib (gene synonyms)
            attrib_type = AttribType.objects.filter(code='gene_synonym')
            queryset = LocusAttrib.objects.filter(value=name, attrib_type=attrib_type.first().id, is_deleted=0)

            if not queryset.exists():
                self.handle_no_permission('Gene', name)

            gene_obj = Locus.objects.filter(id=queryset.first().locus.id)
            queryset = GeneDisease.objects.filter(gene=gene_obj.first())

            if not queryset.exists():
                self.handle_no_permission('Gene-Disease association', name)

        return queryset

class DiseaseDetail(BaseView):
    serializer_class = DiseaseDetailSerializer

    def get_queryset(self):
        id = self.kwargs['id']

        # Fetch disease by MONDO ID
        if id.startswith('MONDO'):
            ontology_term = OntologyTerm.objects.filter(accession=id)

            if not ontology_term.exists():
                self.handle_no_permission('Disease', id)

            disease_ontology = DiseaseOntology.objects.filter(ontology_term_id=ontology_term.first().id)

            if not disease_ontology.exists():
                self.handle_no_permission('Disease', id)

            queryset = Disease.objects.filter(id=disease_ontology.first().disease_id)

        else:
            # Fetch disease by name
            queryset = Disease.objects.filter(name=id)

        if not queryset.exists():
            self.handle_no_permission('Disease', id)

        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset().first()
        serializer = DiseaseDetailSerializer(queryset)
        return Response(serializer.data)

class UserList(generics.ListAPIView):
    queryset = User.objects.filter(is_active=1, is_staff=0)
    serializer_class = UserSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update({'user_login':self.request.user})
        return context

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = UserSerializer(queryset, many=True)

        return Response({'results': serializer.data, 'count':len(serializer.data)})

class AttribTypeList(generics.ListAPIView):
    queryset = AttribType.objects.all()
    serializer_class = AttribTypeSerializer

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        code_list = [attrib.code for attrib in queryset]
        return Response({'results':code_list, 'count':len(code_list)})

class AttribList(generics.ListAPIView):
    lookup_field = 'type'
    serializer_class = AttribSerializer

    def get_queryset(self):
        code = self.kwargs['code']
        return Attrib.objects.filter(type=AttribType.objects.get(code=code))
    
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        code_list = [attrib.value for attrib in queryset]
        return Response({'results':code_list, 'count':len(code_list)})

class LocusGenotypeDiseaseDetail(BaseView):
    serializer_class = LocusGenotypeDiseaseSerializer

    def get_queryset(self):
        stable_id = self.kwargs['stable_id']
        user = self.request.user

        if user.is_authenticated:
            queryset = LocusGenotypeDisease.objects.filter(stable_id=stable_id, is_deleted=0)
        else:
            queryset = LocusGenotypeDisease.objects.filter(stable_id=stable_id, is_reviewed=1, is_deleted=0, lgdpanel__panel__is_visible=1).distinct()

        if not queryset.exists():
            self.handle_no_permission('Entry', stable_id)
        else:
            return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset().first()
        serializer = LocusGenotypeDiseaseSerializer(queryset)
        return Response(serializer.data)

class SearchView(BaseView):
    serializer_class = LocusGenotypeDiseaseSerializer
    pagination_class = PageNumberPagination

    def get_queryset(self):
        user = self.request.user
        search_type = self.request.query_params.get('type', None)
        search_query = self.request.query_params.get('query', None)
        search_panel = self.request.query_params.get('panel', None)

        if not search_query:
            return LocusGenotypeDisease.objects.none()

        base_locus = Q(locus__name=search_query, is_deleted=0)
        base_locus_2 = Q(locus__locusidentifier__isnull=False, locus__locusidentifier__identifier=search_query)
        base_locus_3 = Q(locus__locusattrib__isnull=False, locus__locusattrib__value=search_query, locus__locusattrib__is_deleted=0)
        base_disease = Q(disease__name__icontains=search_query, is_deleted=0)
        base_disease_2 = Q(disease__diseaseontology__ontology_term__accession=search_query, is_deleted=0)
        base_phenotype = Q(lgdphenotype__phenotype__term__icontains=search_query, lgdphenotype__isnull=False, is_deleted=0)
        base_phenotype_2 = Q(lgdphenotype__phenotype__accession=search_query, lgdphenotype__isnull=False, is_deleted=0)

        queryset = LocusGenotypeDisease.objects.none()

        # Generic search
        if not search_type:
            if search_panel:
                queryset = LocusGenotypeDisease.objects.filter(
                    base_locus & Q(lgdpanel__panel__name=search_panel) |
                    base_locus_2 & Q(lgdpanel__panel__name=search_panel) |
                    base_locus_3 & Q(lgdpanel__panel__name=search_panel) |
                    base_disease & Q(lgdpanel__panel__name=search_panel) |
                    base_disease_2 & Q(lgdpanel__panel__name=search_panel) |
                    base_phenotype & Q(lgdpanel__panel__name=search_panel) |
                    base_phenotype_2 & Q(lgdpanel__panel__name=search_panel)
                ).order_by('locus__name', 'stable_id').distinct()
            else:
                queryset = LocusGenotypeDisease.objects.filter(
                    base_locus |
                    base_locus_2 |
                    base_locus_3 |
                    base_disease |
                    base_disease_2 |
                    base_phenotype |
                    base_phenotype_2
                ).order_by('locus__name', 'stable_id').distinct()

            if not queryset.exists():
                self.handle_no_permission('results', search_query)

        elif search_type == 'gene':
            if search_panel:
                queryset = LocusGenotypeDisease.objects.filter(
                    base_locus & Q(lgdpanel__panel__name=search_panel) |
                    base_locus_2 & Q(lgdpanel__panel__name=search_panel) |
                    base_locus_3 & Q(lgdpanel__panel__name=search_panel)
                ).order_by('locus__name', 'stable_id').distinct()
            else:
                queryset = LocusGenotypeDisease.objects.filter(
                    base_locus |
                    base_locus_2 |
                    base_locus_3
                ).order_by('locus__name', 'stable_id').distinct()

            if not queryset.exists():
                self.handle_no_permission('Gene', search_query)

        elif search_type == 'disease':
            if search_panel:
                queryset = LocusGenotypeDisease.objects.filter(
                    base_disease & Q(lgdpanel__panel__name=search_panel) |
                    base_disease_2 & Q(lgdpanel__panel__name=search_panel)
                ).order_by('locus__name', 'stable_id').distinct()
            else:
                queryset = LocusGenotypeDisease.objects.filter(
                    base_disease |
                    base_disease_2
                ).order_by('locus__name', 'stable_id').distinct()

            if not queryset.exists():
                self.handle_no_permission('Disease', search_query)

        elif search_type == 'phenotype':
            if search_panel:
                queryset = LocusGenotypeDisease.objects.filter(
                    base_phenotype & Q(lgdpanel__panel__name=search_panel) |
                    base_phenotype_2 & Q(lgdpanel__panel__name=search_panel)
                ).order_by('locus__name', 'stable_id').distinct()
            else:
                queryset = LocusGenotypeDisease.objects.filter(
                    base_phenotype |
                    base_phenotype_2
                ).order_by('locus__name', 'stable_id').distinct()

            if not queryset.exists():
                self.handle_no_permission('Phenotype', search_query)

        else:
            self.handle_no_permission('Search type is not valid', None)

        if queryset.exists():
            for lgd in queryset:
                # If the user is not logged in, only show visible panels
                if user.is_authenticated == False:
                    lgdpanel_select = LGDPanel.objects.filter(lgd=lgd, panel__is_visible=1, is_deleted=0)
                    if lgdpanel_select.exists() == False:
                        queryset = queryset.exclude(id=lgd.id)
                else:
                    lgdpanel_select = LGDPanel.objects.filter(lgd=lgd, is_deleted=0)
                lgd_panels = []
                for lp in lgdpanel_select:
                    lgd_panels.append(lp.panel.name)
                lgd.panels = lgd_panels

        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        list_output = []

        for lgd in queryset:
            data = { 'id':lgd.stable_id,
                     'gene':lgd.locus.name,
                     'genotype':lgd.genotype.value,
                     'disease':lgd.disease.name,
                     'panel':lgd.panels
                   }
            list_output.append(data)

        paginated_output = self.paginate_queryset(list_output)

        if paginated_output is not None:
            return self.get_paginated_response(paginated_output)

        return Response({"results": list_output, "count": len(list_output)})


### Add data
class BaseAdd(generics.CreateAPIView):
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

class AddDisease(BaseAdd):
    serializer_class = CreateDiseaseSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get(self, request, *args, **kwargs):
        user = self.request.user
        if user.is_authenticated:
            response = Response({"message": "This endpoint is for creating diseases. Use POST to submit data."}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
        else:
            response = Response({"message": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)

        return response

class AddPublication(BaseAdd):
    serializer_class = PublicationSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get(self, request, *args, **kwargs):
        user = self.request.user
        if user.is_authenticated:
            response = Response({"message": "This endpoint is for creating publications. Use POST to submit data."}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
        else:
            response = Response({"message": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)

        return response
