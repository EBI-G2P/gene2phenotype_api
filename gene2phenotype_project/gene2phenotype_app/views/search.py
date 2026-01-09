from functools import reduce
from operator import or_
from rest_framework.response import Response
from django.db.models import Q, F
import textwrap, re
from drf_spectacular.utils import (
    extend_schema,
    OpenApiResponse,
    OpenApiParameter,
    OpenApiExample,
)

from gene2phenotype_app.serializers import (
    LocusGenotypeDiseaseSerializer,
    CurationDataSerializer,
)

from gene2phenotype_app.models import (
    LGDPanel,
    LocusGenotypeDisease,
    CurationData,
    G2PStableID,
)

from .base import BaseView, CustomPagination


@extend_schema(
    tags=["Search records"],
    description=textwrap.dedent("""
    Search G2P records and return summaries of LGMDE records.
    G2P stable IDs (stable_id) are returned to enable extraction of full details.

    You can tailor your search using the following query parameters:

    **Required Parameter**
    - `query`
      The term you wish to search for.
      This could be a gene symbol, disease name, phenotype (e.g. HP:0000853) or a G2P stable ID.

    **Optional Parameters**
    - `type`
      Specifies the type of your search. If omitted, the endpoint performs a generic search across all types.

      Accepted values include:


        gene      : by gene symbol
        disease   : by text string (e.g. Cowden syndrome), Mondo or OMIM identifier
        phenotype : by description (e.g. Goiter) or accession (e.g.  HP:0000853)
        stable_id : by the G2P stable ID


    - `panel`
      Filters results to a specific panel by name.

      Accepted names include:


        Cancer
        Cardiac
        DD
        Ear
        Eye
        Skeletal
        Skin


    - `mechanism`
      Filters results to a specific molecular mechanism.

      Accepted values include:


        dominant negative
        gain of function
        loss of function
        undetermined
        undetermined non-loss-of-function


    - `variant_consequence`
      Filters results to a specific variant consequence.
      The consequence can be provided either as a Sequence Ontology term or accession.

      Accepted values can be found at:
      https://www.ebi.ac.uk/gene2phenotype/about/terminology#variant-consequence-section


    When more than 20 records are available, results are paginated.

    **Example Requests**
    - Search by gene:
        `/search/?query=TP53&type=gene`

    - Search by phenotype:
        `/search/?query=HP:0003416&type=phenotype`

    - Generic search across all categories:
        `/search/?query=Weill-Marchesani syndrome`

    - Search gene within a specific panel:
        `/search/?type=gene&query=FBN1&panel=DD`

    - Search gene filtering by molecular mechanism and variant consequence:
        `/search/?type=gene&query=FBN1&mechanism=loss of function&variant_consequence=SO:0002317`
    """),
    parameters=[
        OpenApiParameter(
            name="query",
            type=str,
            location=OpenApiParameter.QUERY,
            description="The term you wish to search for",
            required=True,
        ),
        OpenApiParameter(
            name="type",
            type=str,
            location=OpenApiParameter.QUERY,
            description="Type of search can be: gene symbol, disease name, phenotype (e.g. HP:0000853) or a G2P stable ID",
        ),
        OpenApiParameter(
            name="panel",
            type=str,
            location=OpenApiParameter.QUERY,
            description="Fetch only records associated with a specific panel",
        ),
    ],
    examples=[
        OpenApiExample(
            "Search by phenotype",
            description="Search G2P records associated with phenotype HP:0003416",
            value={
                "stable_id": "G2P01947",
                "gene": "ADAMTS10",
                "genotype": "biallelic_autosomal",
                "disease": "ADAMTS10-related Weill-Marchesani syndrome",
                "mechanism": "loss of function",
                "panel": ["Eye", "Skin"],
                "confidence": "definitive",
            },
        ),
        OpenApiExample(
            "Search by gene",
            description="Search G2P records associated with gene TP53",
            value={
                "stable_id": "G2P01830",
                "gene": "TP53",
                "genotype": "monoallelic_autosomal",
                "disease": "TP53-related Li-Fraumeni syndrome",
                "mechanism": "loss of function",
                "panel": ["Cancer"],
                "confidence": "definitive",
            },
        ),
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
                    "confidence": {"type": "string"},
                },
            },
        )
    },
)
class SearchView(BaseView):
    pagination_class = CustomPagination

    def get_serializer_class(self):
        if self.request.query_params.get("type", None) == "draft":
            return CurationDataSerializer

        return LocusGenotypeDiseaseSerializer

    def get_queryset(self):
        user = self.request.user
        params = self.request.query_params

        search_type = params.get("type", None)
        search_query = params.get("query", None)
        search_panel = params.get("panel", None)
        search_mechanism = params.get("mechanism", None)
        search_variant_consequence = params.get("variant_consequence", None)

        if not search_query:
            return LocusGenotypeDisease.objects.none()

        # Some disease names contain parenthesis
        # In mysql, parenthesis is a special character that has to be search with "\\("
        if search_query.find("(") or search_query.find(")"):
            search_query = search_query.replace("(", "\\(").replace(")", "\\)")

        # Remove leading whitespaces, newline and tab characters from the beginning and end of the query text
        search_query = search_query.lstrip().rstrip()

        # Base constraint - exclude deleted records
        base_deleted = Q(is_deleted=0)

        # Additional options constraints
        options_query = Q()

        if search_panel:
            options_query &= Q(lgdpanel__panel__name=search_panel)

        if search_mechanism:
            options_query &= Q(mechanism__value=search_mechanism)

        if search_variant_consequence:
            if search_variant_consequence.startswith("SO:"):
                options_query &= Q(
                    lgdvariantgenccconsequence__variant_consequence__accession=search_variant_consequence,
                    lgdvariantgenccconsequence__isnull=False,
                    lgdvariantgenccconsequence__is_deleted=0,
                )
            else:
                options_query &= Q(
                    lgdvariantgenccconsequence__variant_consequence__term=search_variant_consequence,
                    lgdvariantgenccconsequence__isnull=False,
                    lgdvariantgenccconsequence__is_deleted=0,
                )

        base_locus = or_q(
            Q(locus__name=search_query),
            Q(
                locus__locusidentifier__isnull=False,
                locus__locusidentifier__identifier=search_query,
            ),
            Q(
                locus__locusattrib__isnull=False,
                locus__locusattrib__value=search_query,
                locus__locusattrib__is_deleted=0,
            ),
        )

        base_disease = or_q(
            Q(disease__name__regex=rf"(?i)(?<![\w]){search_query}(?![\w])"),
            Q(
                disease__diseasesynonym__synonym__regex=rf"(?i)(?<![\w]){search_query}(?![\w])"
            ),
            Q(disease__diseaseontologyterm__ontology_term__accession=search_query),
        )

        base_phenotype = or_q(
            Q(
                lgdphenotype__phenotype__term__regex=rf"(?i)(?<![\w]){search_query}(?![\w])",
                lgdphenotype__isnull=False,
                lgdphenotype__is_deleted=0,
            ),
            Q(
                lgdphenotype__phenotype__accession=search_query,
                lgdphenotype__isnull=False,
                lgdphenotype__is_deleted=0,
            ),
        )

        base_g2p_id = Q(stable_id__stable_id=search_query)

        queryset = LocusGenotypeDisease.objects.none()

        # Generic search
        if not search_type:
            # First search by gene
            queryset = (
                LocusGenotypeDisease.objects.filter(
                    base_deleted & options_query & base_locus
                )
                .order_by("locus__name", "disease__name")
                .distinct()
            )

            # If the search by gene didn't return results, try the other types
            if not queryset.exists():
                queryset = (
                    LocusGenotypeDisease.objects.filter(
                        base_deleted
                        & options_query
                        & (base_disease | base_phenotype | base_g2p_id)
                    )
                    .order_by("locus__name", "disease__name")
                    .distinct()
                )

            if not queryset.exists():
                self.handle_no_permission("results", search_query)

        elif search_type == "gene":
            queryset = (
                LocusGenotypeDisease.objects.filter(
                    base_deleted & options_query & base_locus
                )
                .order_by("locus__name", "disease__name")
                .distinct()
            )

            if not queryset.exists():
                self.handle_no_permission("Gene", search_query)

        elif search_type == "disease":
            queryset = (
                LocusGenotypeDisease.objects.filter(
                    base_deleted & options_query & base_disease
                )
                .order_by("locus__name", "disease__name")
                .distinct()
            )

            if not queryset.exists():
                self.handle_no_permission("Disease", search_query)

        elif search_type == "phenotype":
            queryset = (
                LocusGenotypeDisease.objects.filter(
                    base_deleted & options_query & base_phenotype
                )
                .order_by("locus__name", "disease__name")
                .distinct()
            )

            if not queryset.exists():
                self.handle_no_permission("Phenotype", search_query)

        elif search_type == "stable_id":
            queryset = (
                LocusGenotypeDisease.objects.filter(
                    base_deleted & options_query & base_g2p_id
                )
                .order_by("locus__name", "disease__name")
                .distinct()
            )

            if not queryset.exists():
                self.handle_no_permission("stable_id", search_query)

        elif search_type == "draft" and user.is_authenticated:
            # to extend the queryset being annotated when it is draft,
            # we want to return username so curator can see who is curating
            # also add the curator email, incase of the notification
            queryset = (
                CurationData.objects.filter(gene_symbol=search_query)
                .order_by("stable_id__stable_id")
                .distinct()
                .annotate(
                    first_name=F("user_id__first_name"),
                    last_name=F("user_id__last_name"),
                    user_email=F("user__email"),
                )
            )

            for obj in queryset:
                obj.json_data_info = (
                    CurationDataSerializer.get_entry_info_from_json_data(
                        self, obj.json_data
                    )
                )

            if not queryset.exists():
                self.handle_no_permission("draft", search_query)

        else:
            self.handle_no_permission("Search type is not valid", None)

        new_queryset = []
        if queryset.exists():
            if search_type != "draft":
                for lgd in queryset:
                    # If the user is not logged in, only show visible panels
                    if user.is_authenticated is False:
                        lgdpanel_select = LGDPanel.objects.filter(
                            Q(lgd=lgd, panel__is_visible=1, is_deleted=0)
                        )
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
        search_query = request.query_params.get("query", None)
        search_type = request.query_params.get("type", None)

        # Check if query is a merged or deleted record
        if search_type == "stable_id" or (
            search_query and search_query.startswith("G2P")
        ):
            try:
                g2p_obj = G2PStableID.objects.get(stable_id=search_query, is_deleted=1)
            except G2PStableID.DoesNotExist:
                pass
            else:
                if g2p_obj.comment and g2p_obj.comment.startswith("Merged into"):
                    match = re.search(r"G2P\d{5,}", g2p_obj.comment)
                    return self.handle_merged_record(search_query, match.group())
                else:
                    # No comment or comment with other description is considered to be simply deleted
                    return self.handle_deleted_record(search_query)

        queryset = self.get_queryset()
        serializer = self.get_serializer_class()

        if not search_type:
            search_type = "results"
        elif search_type != "stable_id" and search_type != "draft":
            search_type = search_type.capitalize()

        # Check if queryset is empty, if so return appropriate message
        if isinstance(queryset, list) and not queryset:
            self.handle_no_permission(search_type, search_query)

        list_output = []
        if issubclass(serializer, LocusGenotypeDiseaseSerializer):
            for lgd in queryset:
                data = {
                    "stable_id": lgd.stable_id.stable_id,
                    "gene": lgd.locus.name,
                    "genotype": lgd.genotype.value,
                    "disease": lgd.disease.name,
                    "mechanism": lgd.mechanism.value,
                    "panel": lgd.panels,
                    "confidence": lgd.confidence.value,
                }
                list_output.append(data)
        else:
            for c_data in queryset:
                data = {
                    "stable_id": c_data.stable_id.stable_id,
                    "gene": c_data.gene_symbol,
                    "date_created": c_data.date_created,
                    "date_last_updated": c_data.date_last_update,
                    "curator_first": c_data.first_name,
                    "curator_last_name": c_data.last_name,
                    "genotype": c_data.json_data_info["genotype"],
                    "disease_name": c_data.json_data_info["disease"],
                    "panels": c_data.json_data_info["panel"],
                    "confidence": c_data.json_data_info["confidence"],
                    "curator_email": c_data.user_email,
                }
                list_output.append(data)

        paginated_output = self.paginate_queryset(list_output)

        if paginated_output is not None:
            return self.get_paginated_response(paginated_output)

        return Response({"results": list_output, "count": len(list_output)})


def or_q(*qs: Q) -> Q:
    """Combine a list of Q objects using OR operator"""
    return reduce(or_, qs)
