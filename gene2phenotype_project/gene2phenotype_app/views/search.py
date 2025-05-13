from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q, F
import textwrap
from drf_spectacular.utils import (
    extend_schema,
    OpenApiResponse,
    OpenApiParameter,
    OpenApiExample
)

from gene2phenotype_app.serializers import (
    LocusGenotypeDiseaseSerializer,
    CurationDataSerializer
)

from gene2phenotype_app.models import (
    LGDPanel,
    LocusGenotypeDisease,
    CurationData
)

from .base import BaseView


class CustomPagination(PageNumberPagination):
    """
    Custom method to define the number of results per page
    """
    page_size = 20


@extend_schema(
    tags=["Search records"],
    description=textwrap.dedent("""
    Search G2P records and return summaries of LGMDE records.
    Stable G2P IDs are returned to enable extraction of full details.

    Supported search types are:

        gene      : by gene symbol
        disease   : by text string (e.g. Cowden syndrome), Mondo or OMIM identifier
        phenotype : by description (e.g. Goiter) or accession (e.g.  HP:0000853)
        g2p_id    : by the stable G2P ID

    When more than 20 records are available, results are paginated.

    If no search type is specified then it performs a generic search.
    The search can be specific to one panel if using parameter 'panel'.

    Example: `search/?type=gene&query=RHO&panel=Cancer`
    """),
    parameters=[
        OpenApiParameter(
            name='query',
            type=str,
            location=OpenApiParameter.QUERY,
            description='Search term',
            required=True
        ),
        OpenApiParameter(
            name='type',
            type=str,
            location=OpenApiParameter.QUERY,
            description='Type of search can be: gene, disease, phenotype or g2p_id'
        ),
        OpenApiParameter(
            name='panel',
            type=str,
            location=OpenApiParameter.QUERY,
            description='Fetch only records associated with a specific panel'
        ),
    ],
    examples=[
        OpenApiExample(
            'Search by phenotype',
            description='Search G2P records associated with phenotype HP:0003416',
            value={
                "stable_id": "G2P01947",
                "gene": "ADAMTS10",
                "genotype": "biallelic_autosomal",
                "disease": "ADAMTS10-related Weill-Marchesani syndrome",
                "mechanism": "loss of function",
                "panel": [
                    "Eye",
                    "Skin"
                ],
                "confidence": "definitive"
            }
        ),
        OpenApiExample(
            'Search by gene',
            description='Search G2P records associated with gene TP53',
            value={
                "stable_id": "G2P01830",
                "gene": "TP53",
                "genotype": "monoallelic_autosomal",
                "disease": "TP53-related Li-Fraumeni syndrome",
                "mechanism": "loss of function",
                "panel": [
                    "Cancer"
                ],
                "confidence": "definitive"
            }
        )
    ],
    responses={
        200: OpenApiResponse(
            description="Search response",
            response={
                "type": "object",
                "properties": {
                    "stable_id": {"type": "string"},
                    "gene": {"type": "string"},
                    "genotype": {"type": "string"},
                    "disease": {"type": "string"},
                    "mechanism": {"type": "string"},
                    "panel": {"type": "array", "items": {"type": "string"}},
                    "confidence": {"type": "string"}
                }
            }
        )
    }
)
class SearchView(BaseView):
    pagination_class = CustomPagination

    def get_serializer_class(self):
        if self.request.query_params.get('type', None) == 'draft':
            return CurationDataSerializer

        return LocusGenotypeDiseaseSerializer

    def get_queryset(self):
        user = self.request.user
        search_type = self.request.query_params.get('type', None)
        search_query = self.request.query_params.get('query', None)
        search_panel = self.request.query_params.get('panel', None)

        if not search_query:
            return LocusGenotypeDisease.objects.none()

        # Some disease names contain parenthesis
        # In mysql, parenthesis is a special character that has to be search with "\\("
        if search_query.find("(") or search_query.find(")"):
            search_query = search_query.replace("(", "\\(").replace(")", "\\)")

        # Remove leading whitespaces, newline and tab characters from the beginning and end of the query text
        search_query = search_query.lstrip().rstrip()

        base_locus = Q(locus__name=search_query, is_deleted=0)
        base_locus_2 = Q(locus__locusidentifier__isnull=False, locus__locusidentifier__identifier=search_query, is_deleted=0)
        base_locus_3 = Q(locus__locusattrib__isnull=False, locus__locusattrib__value=search_query, locus__locusattrib__is_deleted=0)
        base_disease = Q(disease__name__regex=fr"(?i)(?<![\w]){search_query}(?![\w])", is_deleted=0)
        base_disease_2 = Q(disease__diseasesynonym__synonym__regex=fr"(?i)(?<![\w]){search_query}(?![\w])", is_deleted=0)
        base_disease_3 = Q(disease__diseaseontologyterm__ontology_term__accession=search_query, is_deleted=0)
        base_phenotype = Q(lgdphenotype__phenotype__term__regex=fr"(?i)(?<![\w]){search_query}(?![\w])", lgdphenotype__isnull=False, is_deleted=0)
        base_phenotype_2 = Q(lgdphenotype__phenotype__accession=search_query, lgdphenotype__isnull=False, is_deleted=0)
        base_g2p_id = Q(stable_id__stable_id=search_query, is_deleted=0)

        queryset = LocusGenotypeDisease.objects.none()

        # Generic search
        if not search_type:
            if search_panel:
                # First search by gene
                queryset = LocusGenotypeDisease.objects.filter(
                    base_locus & Q(lgdpanel__panel__name=search_panel) |
                    base_locus_2 & Q(lgdpanel__panel__name=search_panel) |
                    base_locus_3 & Q(lgdpanel__panel__name=search_panel)
                ).order_by('locus__name', 'disease__name').distinct()

                # If the search by gene didn't return results, try the other types
                if not queryset.exists():
                    queryset = LocusGenotypeDisease.objects.filter(
                        base_disease & Q(lgdpanel__panel__name=search_panel) |
                        base_disease_2 & Q(lgdpanel__panel__name=search_panel) |
                        base_disease_3 & Q(lgdpanel__panel__name=search_panel) |
                        base_phenotype & Q(lgdpanel__panel__name=search_panel) |
                        base_phenotype_2 & Q(lgdpanel__panel__name=search_panel) |
                        base_g2p_id & Q(lgdpanel__panel__name=search_panel)
                    ).order_by('locus__name', 'disease__name').distinct()
            else:
                # Searching all panels
                # First search by gene
                queryset = LocusGenotypeDisease.objects.filter(
                    base_locus |
                    base_locus_2 |
                    base_locus_3
                ).order_by('locus__name', 'disease__name').distinct()

                # If the search by gene didn't return results, try the other types
                if not queryset.exists():
                    queryset = LocusGenotypeDisease.objects.filter(
                        base_disease |
                        base_disease_2 |
                        base_disease_3 |
                        base_phenotype |
                        base_phenotype_2 |
                        base_g2p_id
                    ).order_by('locus__name', 'disease__name').distinct()

            if not queryset.exists():
                self.handle_no_permission('results', search_query)

        elif search_type == 'gene':
            if search_panel:
                queryset = LocusGenotypeDisease.objects.filter(
                    base_locus & Q(lgdpanel__panel__name=search_panel) |
                    base_locus_2 & Q(lgdpanel__panel__name=search_panel) |
                    base_locus_3 & Q(lgdpanel__panel__name=search_panel)
                ).order_by('locus__name', 'disease__name').distinct()
            else:
                queryset = LocusGenotypeDisease.objects.filter(
                    base_locus |
                    base_locus_2 |
                    base_locus_3
                ).order_by('locus__name', 'disease__name').distinct()

            if not queryset.exists():
                self.handle_no_permission('Gene', search_query)

        elif search_type == 'disease':
            if search_panel:
                queryset = LocusGenotypeDisease.objects.filter(
                    base_disease & Q(lgdpanel__panel__name=search_panel) |
                    base_disease_2 & Q(lgdpanel__panel__name=search_panel) |
                    base_disease_3 & Q(lgdpanel__panel__name=search_panel)
                ).order_by('locus__name', 'disease__name').distinct()
            else:
                queryset = LocusGenotypeDisease.objects.filter(
                    base_disease |
                    base_disease_2 |
                    base_disease_3
                ).order_by('locus__name', 'disease__name').distinct()

            if not queryset.exists():
                self.handle_no_permission('Disease', search_query)

        elif search_type == 'phenotype':
            if search_panel:
                queryset = LocusGenotypeDisease.objects.filter(
                    base_phenotype & Q(lgdpanel__panel__name=search_panel) |
                    base_phenotype_2 & Q(lgdpanel__panel__name=search_panel)
                ).order_by('locus__name', 'disease__name').distinct()
            else:
                queryset = LocusGenotypeDisease.objects.filter(
                    base_phenotype |
                    base_phenotype_2
                ).order_by('locus__name', 'disease__name').distinct()

            if not queryset.exists():
                self.handle_no_permission('Phenotype', search_query)

        elif search_type == 'g2p_id':
            if search_panel:
                queryset = LocusGenotypeDisease.objects.filter(
                    base_g2p_id & Q(lgdpanel__panel__name=search_panel)
                ).order_by('locus__name', 'disease__name').distinct()
            else:
                queryset = LocusGenotypeDisease.objects.filter(
                    base_g2p_id
                ).order_by('locus__name', 'disease__name').distinct()

            if not queryset.exists():
                self.handle_no_permission('g2p_id', search_query)

        elif search_type == 'draft' and user.is_authenticated:
            queryset = CurationData.objects.filter(
                gene_symbol=search_query
                ).order_by('stable_id__stable_id').distinct()

            # to extend the queryset being annotated when it is draft,
            # want to return username so curator can see who is curating
            # adding the curator email, incase of the notification.
            queryset = queryset.annotate(
                first_name=F('user_id__first_name'),
                last_name=F('user_id__last_name'),
                user_email=F('user__email')
            )

            for obj in queryset:
                obj.json_data_info = CurationDataSerializer.get_entry_info_from_json_data(self, obj.json_data)

            if not queryset.exists():
                self.handle_no_permission("draft", search_query)

        else:
            self.handle_no_permission('Search type is not valid', None)

        new_queryset = []
        if queryset.exists():
            if search_type != 'draft':
                for lgd in queryset:
                # If the user is not logged in, only show visible panels
                    if user.is_authenticated is False:
                        lgdpanel_select = LGDPanel.objects.filter(
                            Q(lgd=lgd, panel__is_visible=1, is_deleted=0))
                    else:
                        lgdpanel_select = LGDPanel.objects.filter(lgd=lgd, is_deleted=0)

                    lgd_panels = []
                    for lp in lgdpanel_select:
                        lgd_panels.append(lp.panel.name)

                    # Add new property to LGD object
                    lgd.panels = lgd_panels
                    if lgd_panels:
                        new_queryset.append(lgd)
            else:
                return queryset

        return new_queryset

    def list(self, request, *args, **kwargs):
        """
        Search G2P records. Supported search types are:
            - gene
            - disease
            - phenotype
            - G2P ID
            - draft (only available for authenticated users)

        If no search type is specified then it performs a generic search.
        The search can be specific to one panel if using parameter 'panel'.
        """
        queryset = self.get_queryset()
        serializer = self.get_serializer_class()
        search_query = request.query_params.get('query', None)
        search_type = request.query_params.get('type', None)

        if not search_type:
            search_type = "results"
        elif search_type != "g2p_id" and search_type != "draft":
            search_type = search_type.capitalize()

        # Check if queryset is empty, if so return appropriate message
        if isinstance(queryset, list) and not queryset:
            self.handle_no_permission(search_type, search_query)

        list_output = []
        if issubclass(serializer, LocusGenotypeDiseaseSerializer):
            for lgd in queryset:
                data = {
                    'stable_id':lgd.stable_id.stable_id,
                    'gene':lgd.locus.name,
                    'genotype':lgd.genotype.value,
                    'disease':lgd.disease.name,
                    'mechanism':lgd.mechanism.value,
                    'panel':lgd.panels,
                    'confidence': lgd.confidence.value
                }
                list_output.append(data)
        else:
            for c_data in queryset:
                data = {
                    "stable_id" : c_data.stable_id.stable_id,
                    "gene": c_data.gene_symbol,
                    "date_created": c_data.date_created,
                    "date_last_updated": c_data.date_last_update,
                    "curator_first": c_data.first_name,
                    "curator_last_name": c_data.last_name,
                    "genotype": c_data.json_data_info["genotype"],
                    "disease_name" : c_data.json_data_info["disease"],
                    "panels" : c_data.json_data_info["panel"],
                    "confidence" : c_data.json_data_info["confidence"],
                    "curator_email": c_data.user_email
                }
                list_output.append(data)

        paginated_output = self.paginate_queryset(list_output)

        if paginated_output is not None:
            return self.get_paginated_response(paginated_output)

        return Response({"results": list_output, "count": len(list_output)})
