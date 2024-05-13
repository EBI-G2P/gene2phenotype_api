import json
import jsonschema
from jsonschema import validate, exceptions
from rest_framework import generics, status, permissions
from django.http import Http404
from rest_framework.response import Response
from rest_framework.decorators import api_view
from django.db.models import Q
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404
from django.conf import settings 




from gene2phenotype_app.serializers import (UserSerializer,
                                            PanelDetailSerializer,
                                            AttribTypeSerializer,
                                            AttribSerializer,
                                            LocusGenotypeDiseaseSerializer,
                                            LocusGeneSerializer,
                                            CreateDiseaseSerializer, GeneDiseaseSerializer,
                                            DiseaseDetailSerializer, PublicationSerializer,
                                            PhenotypeSerializer, LGDPanelSerializer,
                                            CurationDataSerializer)

from gene2phenotype_app.models import (Panel, User, AttribType, Attrib,
                                       LocusGenotypeDisease, Locus, OntologyTerm,
                                       DiseaseOntology, Disease, LGDPanel,
                                       LocusAttrib, GeneDisease, G2PStableID,
                                       CurationData, Publication)

from .utils import get_publication, get_authors, clean_omim_disease


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
        serializer = PanelDetailSerializer()
        panel_list = []

        for panel in queryset:
            panel_info = {}
            if panel.is_visible == 1 or (user.is_authenticated and panel.is_visible == 0):
                stats = serializer.calculate_stats(panel)
                panel_info['name'] = panel.name
                panel_info['description'] = panel.description
                panel_info['stats'] = stats
                panel_list.append(panel_info)

        return Response({'results':panel_list, 'count':len(panel_list)})

class PanelDetail(BaseView):
    def get(self, request, name, *args, **kwargs):
        user = self.request.user
        queryset = Panel.objects.filter(name=name)

        flag = 0
        for panel in queryset:
            if panel.is_visible == 1 or (user.is_authenticated and panel.is_visible == 0):
                flag = 1

        if flag == 1:
            serializer = PanelDetailSerializer()
            curators = serializer.get_curators(queryset.first())
            last_update = serializer.get_last_updated(queryset.first())
            stats = serializer.calculate_stats(queryset.first())
            response_data = {
                'name': queryset.first().name,
                'description': queryset.first().description,
                'curators': curators,
                'last_updated': last_update,
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

"""
    Retrieves all diseases associated with a specific gene.

    Args:
            gene_name (str): gene symbol or the synonym symbol

    Return:
            Response object includes:
                - results (list): contains disease data
                                    - original_disease_name
                                    - disease_name
                                    - identifier
                                    - source name
                - count (int): number of diseases associated with the gene
"""
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

    def get(self, request, name, *args, **kwargs):
        queryset = self.get_queryset()
        results = []
        for gene_disease_obj in queryset:
            # Return the original disease name and the clean version (without subtype)
            # In the future, we will import diseases from other sources (Mondo, GenCC)
            new_disease_name = clean_omim_disease(gene_disease_obj.disease)
            results.append({
                            'original_disease_name': gene_disease_obj.disease,
                            'disease_name': new_disease_name,
                            'identifier': gene_disease_obj.identifier,
                            'source': gene_disease_obj.source.name
                           })

        return Response({'results': results, 'count': len(results)})


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
            # Fetch disease by name or by synonym
            queryset = Disease.objects.filter(name=id) | Disease.objects.filter(Q(diseasesynonym__synonym=id))

        if not queryset.exists():
            self.handle_no_permission('Disease', id)

        return queryset

    def list(self, request, *args, **kwargs):
        disease_obj = self.get_queryset().first()
        serializer = DiseaseDetailSerializer(disease_obj)
        return Response(serializer.data)

class DiseaseSummary(DiseaseDetail):
    def list(self, request, *args, **kwargs):
        disease = kwargs.get('id')
        disease_obj = self.get_queryset().first()
        serializer = DiseaseDetailSerializer(disease_obj)
        summmary = serializer.records_summary(disease_obj.id, self.request.user)
        response_data = {
            'disease': disease,
            'records_summary': summmary,
        }

        return Response(response_data)

"""
    Retrieve publication data for a list of PMIDs.
    If PMID is found in G2P then return details from G2P.
    If PMID not found in G2P then returns info from EuropePMC.

    Args:
            request (HttpRequest): HTTP request
            pmids (str): A comma-separated string of PMIDs

    Return:
            Response object includes:
                - results (list): contains publication data for each publication
                                    - pmid
                                    - title
                                    - authors
                                    - year
                                    - source (possible values: 'G2P', 'EuropePMC', 'Not found')
                - count (int): number of PMIDs in the response
            If a PMID is invalid it returns Http404
"""
@api_view(['GET'])
def PublicationDetail(request, pmids):
    id_list = pmids.split(',')
    data = []

    for pmid_str in id_list:
        try:
            pmid = int(pmid_str)

            try:
                publication = Publication.objects.get(pmid=pmid)
                data.append({
                    'pmid': int(publication.pmid),
                    'title': publication.title,
                    'authors': publication.authors,
                    'year': int(publication.year),
                    'source': 'G2P'
                })
            except Publication.DoesNotExist:
                # Query EuropePMC
                response = get_publication(pmid)
                if response['hitCount'] == 0:
                    data.append({
                        'pmid': int(pmid),
                        'title': None,
                        'authors': None,
                        'year': None,
                        'source': 'Not found'
                    })
                else:
                    authors = get_authors(response)
                    year = None
                    publication_info = response['result']
                    title = publication_info['title']
                    if 'pubYear' in publication_info:
                        year = publication_info['pubYear']

                    data.append({
                        'pmid': int(pmid),
                        'title': title,
                        'authors': authors,
                        'year': int(year),
                        'source': 'EuropePMC'
                    })

        except:
            raise Http404(f"Invalid PMID:{pmid_str}")

    return Response({'results': data, 'count': len(data)})

class UserList(generics.ListAPIView):
    serializer_class = UserSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update({'user_login':self.request.user})
        return context

    def get_queryset(self):
        user = self.request.user
        if user and user.is_authenticated:
            queryset = User.objects.filter(is_active=1)
        else:
            queryset = User.objects.filter(is_active=1, is_staff=0)

        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = UserSerializer(queryset, many=True, context={'user': self.request.user})

        return Response({'results': serializer.data, 'count':len(serializer.data)})

class AttribTypeList(generics.ListAPIView):
    queryset = AttribType.objects.all()

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        result = {}
        for attrib_type in queryset:
            serializer = AttribTypeSerializer(attrib_type)
            all_attribs = serializer.get_all_attribs(attrib_type.id)
            result[attrib_type.code] = all_attribs

        return Response(result)

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

"""
    Retrives a list of all variant types.
"""
class VariantTypesList(generics.ListAPIView):
    def get_queryset(self):
        group = Attrib.objects.filter(value="variant_type", type__code="ontology_term_group")
        return OntologyTerm.objects.filter(group_type=group.first().id)

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        list_nmd = []
        list_splice = []
        list_regulatory = []
        list_protein = []
        list = []
        for obj in queryset:
            if "NMD" in obj.term:
                list_nmd.append({"term": obj.term, "accession":obj.accession})
            elif "splice_" in obj.term:
                list_splice.append({"term": obj.term, "accession":obj.accession})
            elif "regulatory" in obj.term or "UTR" in obj.term:
                list_regulatory.append({"term": obj.term, "accession":obj.accession})
            elif "missense" in obj.term or "frame" in obj.term or "start" in obj.term or "stop" in obj.term:
                list_protein.append({"term": obj.term, "accession":obj.accession})
            else:
                list.append({"term": obj.term, "accession":obj.accession})
        return Response({'NMD_variants': list_nmd,
                         'splice_variants': list_splice,
                         'regulatory_variants': list_regulatory,
                         'protein_changing_variants': list_protein,
                         'other_variants': list})

class LocusGenotypeDiseaseDetail(BaseView):
    serializer_class = LocusGenotypeDiseaseSerializer

    def get_queryset(self):
        stable_id = self.kwargs['stable_id']
        user = self.request.user

        g2p_stable_id = get_object_or_404(G2PStableID, stable_id=stable_id)

        # Authenticated users (curators) can see all entries:
        #   - in visible and non-visible panels
        #   - entries flagged as not reviewed (is_reviewed=0)
        #   - entries with 'refuted' and 'disputed' confidence category
        if user.is_authenticated:
            queryset = LocusGenotypeDisease.objects.filter(stable_id=g2p_stable_id, is_deleted=0)
        else:
            queryset = LocusGenotypeDisease.objects.filter(stable_id=g2p_stable_id, is_reviewed=1, is_deleted=0, lgdpanel__panel__is_visible=1).distinct()
            # Remove entries with 'refuted' and 'disputed' confidence category
            queryset = queryset.filter(~Q(confidence__value='refuted') & ~Q(confidence__value='disputed'))

        if not queryset.exists():
            self.handle_no_permission('Entry', stable_id)
        else:
            return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset().first()
        serializer = LocusGenotypeDiseaseSerializer(queryset)
        return Response(serializer.data)


"""
    Search G2P entries by different types:
                                        - gene
                                        - disease
                                        - phenotype
                                        - G2P ID
    If no search type is specified then it performs a generic search.
    The search can be specific to one panel if using parameter 'panel'.
"""
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
        base_disease_2 = Q(disease__diseasesynonym__synonym__icontains=search_query, is_deleted=0)
        base_disease_3 = Q(disease__diseaseontology__ontology_term__accession=search_query, is_deleted=0)
        base_phenotype = Q(lgdphenotype__phenotype__term__icontains=search_query, lgdphenotype__isnull=False, is_deleted=0)
        base_phenotype_2 = Q(lgdphenotype__phenotype__accession=search_query, lgdphenotype__isnull=False, is_deleted=0)
        base_g2p_id = Q(stable_id__stable_id=search_query, is_deleted=0)

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
                    base_disease_3 & Q(lgdpanel__panel__name=search_panel) |
                    base_phenotype & Q(lgdpanel__panel__name=search_panel) |
                    base_phenotype_2 & Q(lgdpanel__panel__name=search_panel) |
                    base_g2p_id & Q(lgdpanel__panel__name=search_panel)
                ).order_by('locus__name', 'stable_id__stable_id').distinct()
            else:
                queryset = LocusGenotypeDisease.objects.filter(
                    base_locus |
                    base_locus_2 |
                    base_locus_3 |
                    base_disease |
                    base_disease_2 |
                    base_disease_3 |
                    base_phenotype |
                    base_phenotype_2 |
                    base_g2p_id
                ).order_by('locus__name', 'stable_id__stable_id').distinct()

            if not queryset.exists():
                self.handle_no_permission('results', search_query)

        elif search_type == 'gene':
            if search_panel:
                queryset = LocusGenotypeDisease.objects.filter(
                    base_locus & Q(lgdpanel__panel__name=search_panel) |
                    base_locus_2 & Q(lgdpanel__panel__name=search_panel) |
                    base_locus_3 & Q(lgdpanel__panel__name=search_panel)
                ).order_by('locus__name', 'stable_id__stable_id').distinct()
            else:
                queryset = LocusGenotypeDisease.objects.filter(
                    base_locus |
                    base_locus_2 |
                    base_locus_3
                ).order_by('locus__name', 'stable_id__stable_id').distinct()

            if not queryset.exists():
                self.handle_no_permission('Gene', search_query)

        elif search_type == 'disease':
            if search_panel:
                queryset = LocusGenotypeDisease.objects.filter(
                    base_disease & Q(lgdpanel__panel__name=search_panel) |
                    base_disease_2 & Q(lgdpanel__panel__name=search_panel) |
                    base_disease_3 & Q(lgdpanel__panel__name=search_panel)
                ).order_by('locus__name', 'stable_id__stable_id').distinct()
            else:
                queryset = LocusGenotypeDisease.objects.filter(
                    base_disease |
                    base_disease_2 |
                    base_disease_3
                ).order_by('locus__name', 'stable_id__stable_id').distinct()

            if not queryset.exists():
                self.handle_no_permission('Disease', search_query)

        elif search_type == 'phenotype':
            if search_panel:
                queryset = LocusGenotypeDisease.objects.filter(
                    base_phenotype & Q(lgdpanel__panel__name=search_panel) |
                    base_phenotype_2 & Q(lgdpanel__panel__name=search_panel)
                ).order_by('locus__name', 'stable_id__stable_id').distinct()
            else:
                queryset = LocusGenotypeDisease.objects.filter(
                    base_phenotype |
                    base_phenotype_2
                ).order_by('locus__name', 'stable_id__stable_id').distinct()

            if not queryset.exists():
                self.handle_no_permission('Phenotype', search_query)

        elif search_type == 'g2p_id':
            if search_panel:
                queryset = LocusGenotypeDisease.objects.filter(
                    base_g2p_id & Q(lgdpanel__panel__name=search_panel)
                ).order_by('locus__name', 'stable_id__stable_id').distinct()
            else:
                queryset = LocusGenotypeDisease.objects.filter(
                    base_g2p_id
                ).order_by('locus__name', 'stable_id__stable_id').distinct()

            if not queryset.exists():
                self.handle_no_permission('g2p_id', search_query)

        else:
            self.handle_no_permission('Search type is not valid', None)

        new_queryset = []
        if queryset.exists():
            for lgd in queryset:
                # If the user is not logged in, only show visible panels
                if user.is_authenticated == False:
                    lgdpanel_select = LGDPanel.objects.filter(lgd=lgd, panel__is_visible=1, is_deleted=0)
                else:
                    lgdpanel_select = LGDPanel.objects.filter(lgd=lgd, is_deleted=0)

                lgd_panels = []
                for lp in lgdpanel_select:
                    lgd_panels.append(lp.panel.name)

                # Add new property to LGD object
                lgd.panels = lgd_panels
                if lgd_panels:
                    new_queryset.append(lgd)

        return new_queryset

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        list_output = []

        for lgd in queryset:
            data = { 'id':lgd.stable_id.stable_id,
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
    http_method_names = ['post', 'head']

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

"""
    Add new disease.
    The create method is in the CreateDiseaseSerializer.
"""
class AddDisease(BaseAdd):
    serializer_class = CreateDiseaseSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

"""
    Add new publication.
    The create method is in the PublicationSerializer.
"""
class AddPublication(BaseAdd):
    serializer_class = PublicationSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

"""
    Add new phenotype.
    The create method is in the PhenotypeSerializer.
"""
class AddPhenotype(BaseAdd):
    serializer_class = PhenotypeSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

"""
    Add panel to an existing G2P record (LGD).
    A single record can be linked to more than one panel.
"""
class LocusGenotypeDiseaseAddPanel(BaseAdd):
    serializer_class = LGDPanelSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def post(self, request, stable_id):
        user = self.request.user

        if not user.is_authenticated:
            return Response({"message": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)

        # Check if user can update panel
        user_obj = get_object_or_404(User, email=user)
        serializer = UserSerializer(user_obj, context={'user' : user})
        user_panel_list_lower = [panel.lower() for panel in serializer.get_panels(user_obj)]
        panel_name_input = request.data.get('name', None)

        if panel_name_input is None:
            return Response({"message": f"Please enter a panel name"}, status=status.HTTP_400_BAD_REQUEST)

        if panel_name_input.lower() not in user_panel_list_lower:
            return Response({"message": f"No permission to update panel {panel_name_input}"}, status=status.HTTP_403_FORBIDDEN)

        g2p_stable_id = get_object_or_404(G2PStableID, stable_id=stable_id) #using the g2p stable id information to get the lgd 
        lgd = get_object_or_404(LocusGenotypeDisease, stable_id=g2p_stable_id, is_deleted=0)
        serializer_class = LGDPanelSerializer(data=request.data, context={'lgd': lgd, 'include_details' : True})

        if serializer_class.is_valid():
            serializer_class.save()
            response = Response({'message': 'Panel added to the G2P entry successfully.'}, status=status.HTTP_200_OK)
        else:
            response = Response({"message": "Error adding a panel"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return response

class AddCurationData(BaseAdd):
    """
        Add a new curation entry.
        It is only available for authenticated users.
        We do not need to check for authenticated users because of the user management issues.
    """
    serializer_class = CurationDataSerializer
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        """
            Handle POST requests.

            Args:
                request: The HTTP request object.

            Returns:
                A Response object with appropriate status and message.
        """
        json_file_path = settings.BASE_DIR.joinpath("gene2phenotype_app", "utils", "curation_schema.json")
        try:
            with open(json_file_path, 'r') as file:
                schema = json.load(file)
        except FileNotFoundError:
            return Response({"message": "Schema file not found"}, status=status.HTTP_404_NOT_FOUND)

        # Validate the JSON data against the schema
        try:
            validate(instance=request.data, schema=schema)
        except exceptions.ValidationError as e:
            return Response({"message": "JSON data does not follow the required format, Required format is" + str(e)}, status=status.HTTP_400_BAD_REQUEST)

        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            
            serializer.save()
            return Response({"message": "Data saved successfully"}, status=status.HTTP_200_OK)
        else:
            return Response({"errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


class ListCurationEntries(BaseView):
    """
        List all the curation entries being curated by the user.
        It is only available for authenticated users.
        Returns:
            - list of entries
            - number of entries
    """
    serializer_class = CurationDataSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
            Retrieve the queryset of CurationData objects.

            Returns:
                Queryset of CurationData objects.
            Future:

                user = self.request.user commenting this out for now we should user to filter the Curation objects we are getting for the future
        """
        queryset = CurationData.objects.all()

        return queryset

    def list(self, request, *args, **kwargs):
        """
            List the CurationData objects.

            Args:
                request: The HTTP request object.
                *args: Additional positional arguments.
                **kwargs: Additional keyword arguments.

            Returns:
                Response containing the list of CurationData objects with specified fields.
        """
        queryset = self.get_queryset()
        list_data = []
        for data in queryset:
            entry = {
                "locus":data.json_data["locus"],
                "session_name": data.session_name,
                "stable_id": data.stable_id.stable_id,
                "created_on": data.date_created.strftime("%Y-%m-%d %H:%M"),
                "last_update": data.date_last_update.strftime("%Y-%m-%d %H:%M")
            }

            list_data.append(entry)

        return Response({'results':list_data, 'count':len(list_data)})


class CurationDataDetail(BaseView):
    """
        Returns all the data for a specific curation entry.
        It is only available for authenticated users.
    """
    serializer_class = CurationDataSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        stable_id = self.kwargs['stable_id']
        user = self.request.user

        g2p_stable_id = get_object_or_404(G2PStableID, stable_id=stable_id)
        # Get the entry if the user matches
        queryset = CurationData.objects.filter(stable_id=g2p_stable_id, user=user)

        if not queryset.exists():
            self.handle_no_permission('Entry', stable_id)
        else:
            return queryset

    def list(self, request, *args, **kwargs):
        curation_data_obj = self.get_queryset().first()

        response_data = {
                'session_name': curation_data_obj.session_name,
                'stable_id': curation_data_obj.stable_id.stable_id,
                'created_on': curation_data_obj.date_created,
                'last_updated_on': curation_data_obj.date_last_update,
                'data': curation_data_obj.json_data,
            }
        return Response(response_data)

"""
    Updates the JSON data for the stable_id
"""
class UpdateCurationData(generics.UpdateAPIView):
    http_method_names = ['put', 'options']
    serializer_class = CurationDataSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        stable_id = self.kwargs['stable_id']
        user = self.request.user

        g2p_stable_id = get_object_or_404(G2PStableID, stable_id=stable_id)
        # Get the entry if the user matches
        queryset = CurationData.objects.filter(stable_id=g2p_stable_id, user__email=user)

        if not queryset.exists():
            self.handle_no_permission('Entry', stable_id)
        else:
            return queryset

    def update(self, request, *args, **kwargs):
        curation_obj = self.get_queryset().first()

        serializer = CurationDataSerializer(curation_obj, data=request.data, context={'user': self.request.user})

        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Data updated successfully"})

        else:
            return Response({"message": "failed", "details": serializer.errors})
