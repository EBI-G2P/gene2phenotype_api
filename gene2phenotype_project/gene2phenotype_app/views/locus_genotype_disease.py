from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db import transaction, IntegrityError
from django.db.models import Model, QuerySet
from django.http import Http404
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiResponse

import re
import textwrap
from typing import List, Type


from gene2phenotype_app.serializers import (
    UserSerializer,
    LocusGenotypeDiseaseSerializer,
    LGDCrossCuttingModifierSerializer,
    LGDCommentSerializer,
    LGDVariantConsequenceListSerializer,
    LGDVariantGenCCConsequenceSerializer,
    LGDCrossCuttingModifierListSerializer,
    LGDVariantTypeListSerializer,
    LGDVariantTypeSerializer,
    LGDVariantTypeDescriptionListSerializer,
    LGDVariantTypeDescriptionSerializer,
    LGDCommentListSerializer,
    LGDReviewSerializer,
)

from gene2phenotype_app.models import (
    User,
    Attrib,
    LocusGenotypeDisease,
    OntologyTerm,
    G2PStableID,
    CVMolecularMechanism,
    LGDCrossCuttingModifier,
    LGDVariantGenccConsequence,
    LGDVariantType,
    LGDVariantTypeComment,
    LGDVariantTypeDescription,
    LGDPanel,
    LGDPhenotype,
    LGDPhenotypeSummary,
    LGDMolecularMechanismEvidence,
    LGDMolecularMechanismSynopsis,
    LGDPublication,
    LGDComment,
)

from .base import BaseAPIView, BaseUpdate, CustomPermissionAPIView, IsSuperUser

from ..utils import get_date_now


@extend_schema(
    tags=["Terminology"],
    description=textwrap.dedent("""
    Fetch the molecular mechanism terminologies used in G2P following the definitions of Backwell and Marsh (see more details here https://europepmc.org/article/MED/35395171)
    
    The mechanism of disease is derived from the available evidence.
    
    The mechanism synopsis is a more detailed description of the molecular mechanism.
    """),
    responses={
        200: OpenApiResponse(
            description="Molecular mechanism terminology response",
            response={
                "type": "object",
                "properties": {
                    "evidence": {
                        "type": "object",
                        "properties": {
                            "function": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {"key": {"type": "string"}},
                                },
                            },
                            "rescue": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {"key": {"type": "string"}},
                                },
                            },
                            "models": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {"key": {"type": "string"}},
                                },
                            },
                            "functional_alteration": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {"key": {"type": "string"}},
                                },
                            },
                        },
                    },
                    "mechanism": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {"key": {"type": "string"}},
                        },
                    },
                    "mechanism_synopsis": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {"key": {"type": "string"}},
                        },
                    },
                    "support": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {"key": {"type": "string"}},
                        },
                    },
                },
            },
        )
    },
)
class ListMolecularMechanisms(APIView):
    def get(self, request, *args, **kwargs):
        """
        Return the molecular mechanisms terms by type and subtype (if applicable).
        Returns a dictionary where the key is the type the value is a list.
        """
        queryset = (
            CVMolecularMechanism.objects.all()
            .values("type", "subtype", "value", "description")
            .order_by("type", "value")
        )
        result = {}
        for mechanism in queryset:
            mechanismtype = mechanism["type"]
            subtype = mechanism["subtype"]
            value = mechanism["value"]
            description = mechanism["description"]

            if mechanismtype not in result:
                result[mechanismtype] = {}
                # evidence has subtypes
                if mechanismtype == "evidence":
                    result[mechanismtype][subtype] = [{value: description}]
                else:
                    result[mechanismtype] = [{value: description}]
            else:
                if mechanismtype == "evidence":
                    if subtype not in result[mechanismtype]:
                        result[mechanismtype][subtype] = [{value: description}]
                    else:
                        result[mechanismtype][subtype].append({value: description})
                else:
                    result[mechanismtype].append({value: description})

        return Response(result)


@extend_schema(exclude=True)
class VariantTypesList(APIView):
    def get_queryset(self):
        group = Attrib.objects.filter(
            value="variant_type", type__code="ontology_term_group"
        )
        return OntologyTerm.objects.filter(group_type=group.first().id)

    def get(self, request, *args, **kwargs):
        """
        Return all variant types by group.
        Returns a dictionary where the key is the variant group and the value is a list of terms.
        """
        queryset = self.get_queryset()
        list_nmd = []
        list_splice = []
        list_regulatory = []
        list_protein = []
        list = []

        for obj in queryset:
            if "NMD" in obj.term:
                list_nmd.append({"term": obj.term, "accession": obj.accession})
            elif "splice_" in obj.term:
                list_splice.append({"term": obj.term, "accession": obj.accession})
            elif "regulatory" in obj.term or "UTR" in obj.term:
                list_regulatory.append({"term": obj.term, "accession": obj.accession})
            elif (
                "missense" in obj.term
                or "frame" in obj.term
                or "start" in obj.term
                or "stop" in obj.term
            ):
                list_protein.append({"term": obj.term, "accession": obj.accession})
            else:
                list.append({"term": obj.term, "accession": obj.accession})

        return Response(
            {
                "NMD_variants": list_nmd,
                "splice_variants": list_splice,
                "regulatory_variants": list_regulatory,
                "protein_changing_variants": list_protein,
                "other_variants": list,
            }
        )


@extend_schema(
    tags=["G2P record"],
    description=textwrap.dedent("""
    Fetch detailed information about a specific record using the G2P stable ID (stable_id).
    
    A record is a unique Locus-Genotype-Mechanism-Disease-Evidence (LGMDE) thread.
    """),
    examples=[
        OpenApiExample(
            "Example 1",
            description="Fetch detailed information for record with stable_id G2P03507",
            value={
                "locus": {
                    "gene_symbol": "MTFMT",
                    "sequence": "15",
                    "start": 65001512,
                    "end": 65029639,
                    "strand": -1,
                    "reference": "grch38",
                    "ids": {
                        "HGNC": "HGNC:29666",
                        "Ensembl": "ENSG00000103707",
                        "OMIM": "611766",
                    },
                    "synonyms": ["FMT1"],
                },
                "stable_id": "G2P03507",
                "genotype": "biallelic_autosomal",
                "variant_consequence": [
                    {
                        "variant_consequence": "absent gene product",
                        "accession": "SO:0002317",
                        "support": "inferred",
                        "publication": None,
                    },
                    {
                        "variant_consequence": "altered gene product structure",
                        "accession": "SO:0002318",
                        "support": "inferred",
                        "publication": None,
                    },
                ],
                "molecular_mechanism": {
                    "mechanism": "loss of function",
                    "mechanism_support": "evidence",
                    "synopsis": [],
                    "evidence": {
                        "30911575": {
                            "functional_studies": {
                                "Function": ["Biochemical", "Protein Expression"],
                                "Functional Alteration": ["Patient Cells"],
                            },
                            "descriptions": [],
                        },
                        "21907147": {
                            "functional_studies": {
                                "Function": ["Biochemical"],
                                "Functional Alteration": ["Patient Cells"],
                                "Rescue": ["Patient Cells"],
                            },
                            "descriptions": [],
                        },
                        "24461907": {
                            "functional_studies": {
                                "Function": ["Biochemical", "Protein Expression"]
                            },
                            "descriptions": [],
                        },
                        "23499752": {
                            "functional_studies": {
                                "Function": ["Protein Expression"],
                                "Functional Alteration": ["Patient Cells"],
                            },
                            "descriptions": [],
                        },
                    },
                },
                "disease": {
                    "name": "MTFMT-related mitochondrial disease with regression and lactic acidosis",
                    "ontology_terms": [],
                    "synonyms": [],
                },
                "confidence": "definitive",
                "publications": [
                    {
                        "publication": {
                            "pmid": 30911575,
                            "title": "Leigh syndrome caused by mutations in MTFMT is associated with a better prognosis.",
                            "authors": "Hayhurst H et al.",
                            "year": "2019",
                        },
                        "number_of_families": None,
                        "consanguinity": None,
                        "affected_individuals": None,
                        "ancestry": None,
                        "comments": [],
                    },
                    {
                        "publication": {
                            "pmid": 21907147,
                            "title": "Mutations in MTFMT underlie a human disorder of formylation causing impaired mitochondrial translation.",
                            "authors": "Tucker EJ, Hershman SG, Köhrer C, Belcher-Timme CA, Patel J, Goldberger OA, Christodoulou J, Silberstein JM, McKenzie M, Ryan MT, Compton AG, Jaffe JD, Carr SA, Calvo SE, RajBhandary UL, Thorburn DR, Mootha VK.",
                            "year": "2011",
                        },
                        "number_of_families": None,
                        "consanguinity": None,
                        "affected_individuals": None,
                        "ancestry": None,
                        "comments": [],
                    },
                    {
                        "publication": {
                            "pmid": 24461907,
                            "title": "Phenotypic spectrum of eleven patients and five novel MTFMT mutations identified by exome sequencing and candidate gene screening.",
                            "authors": "Haack TB et al.",
                            "year": "2014",
                        },
                        "number_of_families": None,
                        "consanguinity": None,
                        "affected_individuals": None,
                        "ancestry": None,
                        "comments": [],
                    },
                    {
                        "publication": {
                            "pmid": 32133637,
                            "title": "First report of childhood progressive cerebellar atrophy due to compound heterozygous MTFMT variants.",
                            "authors": "Bai R, Haude K, Yang E, Goldstein A, Anselm I.",
                            "year": "2020",
                        },
                        "number_of_families": None,
                        "consanguinity": None,
                        "affected_individuals": None,
                        "ancestry": None,
                        "comments": [],
                    },
                    {
                        "publication": {
                            "pmid": 23499752,
                            "title": "Clinical and functional characterisation of the combined respiratory chain defect in two sisters due to autosomal recessive mutations in MTFMT.",
                            "authors": "Neeve VC, Pyle A, Boczonadi V, Gomez-Duran A, Griffin H, Santibanez-Koref M, Gaiser U, Bauer P, Tzschach A, Chinnery PF, Horvath R.",
                            "year": "2013",
                        },
                        "number_of_families": None,
                        "consanguinity": None,
                        "affected_individuals": None,
                        "ancestry": None,
                        "comments": [],
                    },
                ],
                "mined_publications": [],
                "panels": [{"name": "DD", "description": "Developmental disorders"}],
                "cross_cutting_modifier": [],
                "variant_type": [
                    {
                        "term": "splice_region_variant",
                        "accession": "SO:0001630",
                        "inherited": False,
                        "de_novo": False,
                        "unknown_inheritance": False,
                        "publications": [],
                        "comments": [],
                    },
                    {
                        "term": "frameshift_variant",
                        "accession": "SO:0001589",
                        "inherited": False,
                        "de_novo": False,
                        "unknown_inheritance": False,
                        "publications": [],
                        "comments": [],
                    },
                    {
                        "term": "stop_gained",
                        "accession": "SO:0001587",
                        "inherited": False,
                        "de_novo": False,
                        "unknown_inheritance": False,
                        "publications": [],
                        "comments": [],
                    },
                    {
                        "term": "missense_variant",
                        "accession": "SO:0001583",
                        "inherited": False,
                        "de_novo": False,
                        "unknown_inheritance": False,
                        "publications": [],
                        "comments": [],
                    },
                ],
                "variant_description": [],
                "phenotypes": [],
                "phenotype_summary": [],
                "last_updated": "2025-03-06",
                "date_created": "2024-03-06",
                "comments": [],
                "under_review": False,
            },
        )
    ],
)
class LocusGenotypeDiseaseDetail(BaseAPIView):
    serializer_class = LocusGenotypeDiseaseSerializer

    def get_queryset(self):
        stable_id = self.kwargs["stable_id"]
        user = self.request.user

        # Fetch the G2P stable ID without considering if ID is deleted
        g2p_stable_id = get_object_or_404(G2PStableID, stable_id=stable_id)

        # Authenticated users (curators) can see all entries:
        #   - in visible and non-visible panels
        if user.is_authenticated:
            queryset = LocusGenotypeDisease.objects.filter(
                stable_id=g2p_stable_id, is_deleted=0
            )
        else:
            queryset = LocusGenotypeDisease.objects.filter(
                stable_id=g2p_stable_id, is_deleted=0, lgdpanel__panel__is_visible=1
            ).distinct()

        if not queryset.exists():
            self.handle_no_permission("Entry", stable_id)
        else:
            return queryset

    def get(self, request, *args, **kwargs):
        """
        Return all data for a G2P record.

        Args:
            stable_id (string): G2P stable ID

        Returns a LocusGenotypeDisease object:
            locus (dict)
            stable_id (str)
            genotype (str)
            disease (dict)
            molecular_mechanism (dict)
            phenotypes (list)
            publications (list)
            ...
        """
        stable_id = self.kwargs["stable_id"]

        # Check for merged or deleted records before calling get_queryset
        g2p_stable_id = get_object_or_404(G2PStableID, stable_id=stable_id)
        if g2p_stable_id.is_deleted:
            comment = g2p_stable_id.comment
            # Merged records have a comment that starts with "Merged into"
            if comment and comment.startswith("Merged into"):
                match = re.search(r"G2P\d{5,}", comment)
                return self.handle_merged_record(stable_id, match.group())
            else:
                # No comment or comment with other description is considered to be simply deleted
                return self.handle_deleted_record(stable_id)

        queryset = self.get_queryset().first()
        serializer = LocusGenotypeDiseaseSerializer(
            queryset, context={"user": self.request.user}
        )
        return Response(serializer.data)


### Add or delete data ###
@extend_schema(exclude=True)
class LGDUpdateConfidence(BaseUpdate):
    http_method_names = ["put", "options"]
    serializer_class = LocusGenotypeDiseaseSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        stable_id = self.kwargs["stable_id"]

        g2p_stable_id = get_object_or_404(G2PStableID, stable_id=stable_id)
        # Get the entry for this user
        queryset = LocusGenotypeDisease.objects.filter(
            stable_id=g2p_stable_id, is_deleted=0
        )

        if not queryset.exists():
            self.handle_no_permission("Entry", stable_id)
        else:
            return queryset

    def update(self, request, stable_id):
        """
        This method updates the LGD confidence.

        Mandatory fields to update confidence:
                        - confidence value
                        - confidence_support

        Input example:
                {
                    'confidence': 'definitive',
                    'confidence_support': '',
                    'is_reviewed': None
                }

        Raises:
            No permission to update record
            Invalid confidence value
            G2P record already has same confidence value
            Cannot update confidence value without supporting evidence.
        """
        user = request.user

        # Get G2P entry to be updated
        lgd_obj = self.get_queryset().first()

        # Update data - it replaces the data
        serializer = LocusGenotypeDiseaseSerializer(
            lgd_obj, data=request.data, context={"request": request, "user": user}
        )

        # Check if user has permission to update panel
        user_obj = get_object_or_404(User, email=user, is_active=1)
        serializer_user = UserSerializer(user_obj, context={"user": user})
        user_panel_list = [panel for panel in serializer_user.panels_names(user_obj)]
        has_common = serializer.check_user_permission(lgd_obj, user_panel_list)

        if has_common is False:
            return Response(
                {
                    "error": f"No permission to update record '{lgd_obj.stable_id.stable_id}'"
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        if serializer.is_valid():
            instance = serializer.save()
            return Response(
                {
                    "message": f"Data updated successfully for '{instance.stable_id.stable_id}'"
                },
                status=status.HTTP_200_OK,
            )

        else:
            return Response(
                {"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST
            )


@extend_schema(exclude=True)
class LGDUpdateMechanism(BaseUpdate):
    http_method_names = ["patch", "options"]
    serializer_class = LocusGenotypeDiseaseSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        Retrieves a queryset of LocusGenotypeDisease objects associated with a stable ID
        for the authenticated user.

        Authenticated users can update the mechanism value, support and evidence
        only if mechanism is 'undetermined' or support is 'inferred'. The check is
        done in LocusGenotypeDiseaseSerializer.

        Args:
            stable_id (str): The stable ID from the URL kwargs.

        Returns:
            QuerySet: A queryset of LocusGenotypeDisease objects.

        Raises:
            Http404: If the stable ID does not exist.
            PermissionDenied: If update is not allowed.
        """
        stable_id = self.kwargs["stable_id"]

        g2p_stable_id = get_object_or_404(G2PStableID, stable_id=stable_id)
        # Get the record
        queryset = LocusGenotypeDisease.objects.filter(
            stable_id=g2p_stable_id, is_deleted=0
        )

        if not queryset.exists():
            self.handle_no_permission("Entry", stable_id)

        return queryset

    def patch(self, request, stable_id):
        """
        Partially updates the LGD record with a new molecular mechanism.
        It only allows to update mechanisms with value 'undetermined'
        or support 'inferred'.

        Supporting pmids have to already be linked to the LGD record.

        Args:
            request: new molecular mechanism data
            stable_id (str): The stable ID to update.

        Request example:
                {
                    "molecular_mechanism": {
                        "name": "gain of function",
                        "support": "evidence"
                    },
                    "mechanism_synopsis": [{
                        "name": "destabilising LOF",
                        "support": "evidence"
                    }],
                    "mechanism_evidence": [{'pmid': '25099252', 'description': 'text', 'evidence_types':
                                        [{'primary_type': 'Rescue', 'secondary_type': ['Patient Cells']}]}]
                }
        """
        user = request.user
        mechanism_data = request.data

        # Get G2P entry to be updated
        lgd_obj = self.get_queryset().first()
        serializer = LocusGenotypeDiseaseSerializer(context={"user": user})

        # Check if user has permission to edit this entry
        user_obj = get_object_or_404(User, email=user, is_active=1)
        serializer_user = UserSerializer(user_obj, context={"user": user})
        user_panel_list = [panel for panel in serializer_user.panels_names(user_obj)]
        has_common = serializer.check_user_permission(lgd_obj, user_panel_list)

        if has_common is False:
            return Response(
                {"error": f"No permission to update record '{stable_id}'"},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Validate mechanism data
        molecular_mechanism = mechanism_data.get(
            "molecular_mechanism", None
        )  # mechanism value can be updated if current value is "undetermined"
        mechanism_synopsis = mechanism_data.get("mechanism_synopsis", [])  # optional
        mechanism_evidence = mechanism_data.get("mechanism_evidence", None)  # optional

        # Return error if no data is provided
        if (
            molecular_mechanism is None
            and not mechanism_synopsis
            and mechanism_evidence is None
        ):
            self.handle_missing_data("Mechanism data")

        # Check if mechanism value can be updated
        if (
            molecular_mechanism
            and lgd_obj.mechanism.value != "undetermined"
            and "name" in molecular_mechanism
            and molecular_mechanism["name"] != ""
        ):
            return self.handle_no_update("molecular mechanism", stable_id)

        # If the mechanism support is "evidence" then the evidence has to be provided
        if (
            molecular_mechanism
            and "support" in molecular_mechanism
            and molecular_mechanism["support"] == "evidence"
            and (mechanism_evidence is None or len(mechanism_evidence) == 0)
        ):
            self.handle_missing_data("Mechanism evidence")

        # Separate method to update mechanism
        # Updating the mechanism can be complex, specially if evidence data is provided
        # To avoid problems with other LDG updates, the mechanism is going to be
        # updated in a separate method - this implies extra validation
        try:
            serializer.update_mechanism(lgd_obj, mechanism_data)
        except Exception as e:
            if hasattr(e, "detail") and "error" in e.detail:
                return Response(
                    {"error": e.detail["error"]}, status=status.HTTP_400_BAD_REQUEST
                )
            else:
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response(
                {
                    "message": f"Molecular mechanism updated successfully for '{stable_id}'"
                },
                status=status.HTTP_200_OK,
            )


@extend_schema(exclude=True)
class LGDEditVariantConsequences(CustomPermissionAPIView):
    """
    Add or delete lgd-variant consequence(s).
    """

    http_method_names = ["post", "patch", "options"]

    # Define specific permissions
    method_permissions = {
        "post": [permissions.IsAuthenticated],
        "patch": [permissions.IsAuthenticated, IsSuperUser],
    }

    def get_serializer_class(self, action):
        """
        Returns the appropriate serializer class based on the action.
        To add data use LGDVariantConsequenceListSerializer: it accepts a list of consequences.
        To delete data use LGDVariantGenCCConsequenceSerializer: it accepts one consequence.
        """
        action = action.lower()

        if action == "post":
            return LGDVariantConsequenceListSerializer
        elif action == "patch":
            return LGDVariantGenCCConsequenceSerializer
        else:
            return None

    @transaction.atomic
    def post(self, request, stable_id):
        """
        The post method adds a list of variant GenCC consequences to an existing G2P record (LGD).
        We want to whole process to be done in one db transaction.

        Args:
            request (dict)

            Example:
                {
                    "variant_consequences": [{
                        "variant_consequence": "altered_gene_product_level",
                        "support": "inferred"
                    }]
                }
        """
        lgd = get_object_or_404(
            LocusGenotypeDisease, stable_id__stable_id=stable_id, is_deleted=0
        )
        success_flag = 0

        # Check if user has permission to update panel
        user = self.request.user
        user_obj = get_object_or_404(User, email=user, is_active=1)
        serializer_user = UserSerializer(user_obj, context={"user": user})
        user_panel_list = [panel for panel in serializer_user.panels_names(user_obj)]
        # Calls method check_user_permission() to check the permissions
        # This method requires user info in the context
        has_common = LocusGenotypeDiseaseSerializer(
            lgd, context={"user": user}
        ).check_user_permission(lgd, user_panel_list)
        if has_common is False:
            return Response(
                {"error": f"No permission to update record '{stable_id}'"},
                status=status.HTTP_403_FORBIDDEN,
            )

        # LGDVariantConsequenceListSerializer accepts a list of variant consequences
        serializer_list = LGDVariantConsequenceListSerializer(data=request.data)

        if serializer_list.is_valid():
            variant_consequence_data = serializer_list.validated_data.get(
                "variant_consequences"
            )

            # Check if list of consequences is empty
            if not variant_consequence_data:
                response = Response(
                    {"error": "Empty variant consequence. Please provide valid data."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Add each variant GenCC consequence from the input list
            for var_consequence in variant_consequence_data:
                # The data is created in LGDVariantGenCCConsequenceSerializer
                # Input the expected data format
                serializer_class = LGDVariantGenCCConsequenceSerializer(
                    data={
                        "variant_consequence": var_consequence["variant_consequence"][
                            "term"
                        ],
                        "support": var_consequence["support"]["value"],
                    },
                    context={"lgd": lgd},
                )

                if serializer_class.is_valid():
                    serializer_class.save()
                    success_flag = 1
                    response = Response(
                        {
                            "message": "Variant consequence added to the G2P entry successfully."
                        },
                        status=status.HTTP_201_CREATED,
                    )
                else:
                    response = Response(
                        {"error": serializer_class.errors},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

        else:
            response = Response(
                {"error": serializer_list.errors}, status=status.HTTP_400_BAD_REQUEST
            )

        if success_flag:
            lgd.date_review = get_date_now()
            lgd.save_without_historical_record()

        return response

    @transaction.atomic
    def patch(self, request, stable_id):
        """
        This method deletes a variant GenCC consequence from the LGD record.
        The deletion does not remove the entry from the database, instead
        it sets the flag 'is_deleted' to 1.

        Example: {"variant_consequence": "altered_gene_product_level"}
        """
        # Check if input has the expected value
        if (
            "variant_consequence" not in request.data
            or request.data.get("variant_consequence") == ""
        ):
            return Response(
                {
                    "error": "Empty variant consequence. Please provide the 'variant_consequence'."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        consequence = request.data.get("variant_consequence")

        if consequence is None:
            return Response(
                {"error": "Empty variant consequence"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        consequence = consequence.replace("_", " ")

        # Fecth G2P record to update
        lgd_obj = get_object_or_404(
            LocusGenotypeDisease, stable_id__stable_id=stable_id, is_deleted=0
        )

        # Check if user has permission to update panel
        user = self.request.user
        user_obj = get_object_or_404(User, email=user, is_active=1)
        serializer_user = UserSerializer(user_obj, context={"user": user})
        user_panel_list = [panel for panel in serializer_user.panels_names(user_obj)]
        has_common = LocusGenotypeDiseaseSerializer(
            lgd_obj, context={"user": user}
        ).check_user_permission(lgd_obj, user_panel_list)
        if has_common is False:
            return Response(
                {"error": f"No permission to update record '{stable_id}'"},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Get variant gencc consequence value from ontology_term
        try:
            consequence_obj = OntologyTerm.objects.get(
                term=consequence, group_type__value="variant_type"
            )
        except OntologyTerm.DoesNotExist:
            return Response(
                {"error": f"Invalid variant consequence '{consequence}'"},
                status=status.HTTP_404_NOT_FOUND,
            )
        else:
            try:
                variant_consequence_obj = LGDVariantGenccConsequence.objects.get(
                    lgd=lgd_obj, variant_consequence=consequence_obj, is_deleted=0
                )
            except LGDVariantGenccConsequence.DoesNotExist:
                return Response(
                    {"error": f"Could not find variant consequence '{consequence}' for ID '{stable_id}'"},
                    status=status.HTTP_404_NOT_FOUND,
                )
            else:
                variant_consequence_obj.is_deleted=1
                variant_consequence_obj.save()

            lgd_obj.date_review = get_date_now()
            lgd_obj.save_without_historical_record()

            return Response(
                {
                    "message": f"Variant consequence '{consequence}' successfully deleted for ID '{stable_id}'"
                },
                status=status.HTTP_200_OK,
            )


@extend_schema(exclude=True)
class LGDEditCCM(CustomPermissionAPIView):
    """
    Add or delete LGD-cross cutting modifier(s).
    """

    http_method_names = ["post", "patch", "options"]

    # Define specific permissions
    method_permissions = {
        "post": [permissions.IsAuthenticated],
        "patch": [permissions.IsAuthenticated, IsSuperUser],
    }

    def get_serializer_class(self, action):
        """
        Returns the appropriate serializer class based on the action.
        To add data use LGDCrossCuttingModifierListSerializer: it accepts a list of ccm.
        To delete data use LGDCrossCuttingModifierSerializer: it accepts one ccm.
        """
        action = action.lower()

        if action == "post":
            return LGDCrossCuttingModifierListSerializer
        elif action == "patch":
            return LGDCrossCuttingModifierSerializer
        else:
            return None

    @transaction.atomic
    def post(self, request, stable_id):
        """
        The post method adds a list of cross cutting modifiers to an existing G2P record (LGD).
        We want to whole process to be done in one db transaction.

        Args:
            request (dict)

            Example:
                {
                    "cross_cutting_modifiers": [{"term": "typically mosaic"}]
                }
        """
        lgd = get_object_or_404(
            LocusGenotypeDisease, stable_id__stable_id=stable_id, is_deleted=0
        )

        # Check if user has permission to update panel
        user = self.request.user
        user_obj = get_object_or_404(User, email=user, is_active=1)
        serializer_user = UserSerializer(user_obj, context={"user": user})
        user_panel_list = [panel for panel in serializer_user.panels_names(user_obj)]
        has_common = LocusGenotypeDiseaseSerializer(
            lgd, context={"user": user}
        ).check_user_permission(lgd, user_panel_list)
        if has_common is False:
            return Response(
                {"error": f"No permission to update record '{stable_id}'"},
                status=status.HTTP_403_FORBIDDEN,
            )

        # LGDCrossCuttingModifierListSerializer accepts a list of cross cutting modifiers
        serializer_list = LGDCrossCuttingModifierListSerializer(data=request.data)

        if serializer_list.is_valid():
            ccm_data = serializer_list.validated_data.get("cross_cutting_modifiers")

            # Check if list of consequences is empty
            if not ccm_data:
                return Response(
                    {
                        "error": "Empty cross cutting modifier. Please provide valid data."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Add each cross cutting modifier from the input list
            for ccm in ccm_data:
                # The data is created in LGDCrossCuttingModifierSerializer
                # Input the expected data format
                serializer_class = LGDCrossCuttingModifierSerializer(
                    data={"term": ccm["ccm"]["value"]}, context={"lgd": lgd}
                )

                if serializer_class.is_valid():
                    serializer_class.save()

                    # Update LGD date_review
                    lgd.date_review = get_date_now()
                    lgd.save_without_historical_record()

                    response = Response(
                        {
                            "message": "Cross cutting modifier added to the G2P entry successfully."
                        },
                        status=status.HTTP_201_CREATED,
                    )
                else:
                    response = Response(
                        {"error": serializer_class.errors},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

        else:
            response = Response(
                {"error": serializer_list.errors}, status=status.HTTP_400_BAD_REQUEST
            )

        return response

    @transaction.atomic
    def patch(self, request, stable_id):
        """
        This method deletes a cross cutting modifier from the LGD record.
        The deletion does not remove the entry from the database, instead
        it sets the flag 'is_deleted' to 1.

        Example:
                { "term": "typically mosaic" }
        """
        if "term" not in request.data or request.data.get("term") == "":
            return Response(
                {"error": "Empty cross cutting modifier. Please provide the 'term'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        ccm_tmp = request.data.get("term")
        ccm = ccm_tmp.replace("_", " ")
        user = request.user

        lgd_obj = get_object_or_404(
            LocusGenotypeDisease, stable_id__stable_id=stable_id, is_deleted=0
        )

        # Check if user has permission to update panel
        user_obj = get_object_or_404(User, email=user, is_active=1)
        serializer_user = UserSerializer(user_obj, context={"user": user})
        user_panel_list = [panel for panel in serializer_user.panels_names(user_obj)]
        has_common = LocusGenotypeDiseaseSerializer(
            lgd_obj, context={"user": user}
        ).check_user_permission(lgd_obj, user_panel_list)
        if has_common is False:
            return Response(
                {"error": f"No permission to update record '{stable_id}'"},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            ccm_obj = Attrib.objects.get(value=ccm, type__code="cross_cutting_modifier")
        except Attrib.DoesNotExist:
            return Response(
                {"error": f"Invalid cross cutting modifier '{ccm}'"},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            lgd_ccm = LGDCrossCuttingModifier.objects.get(
                lgd=lgd_obj, ccm=ccm_obj, is_deleted=0
            )
        except LGDCrossCuttingModifier.DoesNotExist:
            return Response(
                {
                    "error": f"Could not find cross cutting modifier '{ccm}' for ID '{stable_id}'"
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        else:
            # Set LGD-cross cutting modifier to deleted
            lgd_ccm.is_deleted = 1
            lgd_ccm.save()

            # The cross cutting modifier was deleted successfully - update the date of last update in the record table
            lgd_obj.date_review = get_date_now()
            lgd_obj.save_without_historical_record()

            return Response(
                {
                    "message": f"Cross cutting modifier '{ccm}' successfully deleted for ID '{stable_id}'"
                },
                status=status.HTTP_200_OK,
            )


@extend_schema(exclude=True)
class LGDEditVariantTypes(CustomPermissionAPIView):
    """
    Add or delete LGD-variant type(s).
    """

    http_method_names = ["post", "patch", "options"]

    # Define specific permissions
    method_permissions = {
        "post": [permissions.IsAuthenticated],
        "patch": [permissions.IsAuthenticated, IsSuperUser],
    }

    def get_serializer_class(self, action):
        """
        Returns the appropriate serializer class based on the action.
        To add data use LGDVariantTypeListSerializer: it accepts a list of variant types.
        To delete data use LGDVariantTypeSerializer: it accepts one variant type.
        """
        action = action.lower()

        if action == "post":
            return LGDVariantTypeListSerializer
        elif action == "patch":
            return LGDVariantTypeSerializer
        else:
            return None

    @transaction.atomic
    def post(self, request, stable_id):
        """
        The post method adds a list of variant types to an existing G2P record (LGD).
        We want to whole process to be done in one db transaction.

        Args:
            request (dict)

            Example:
                {
                    "variant_types": [{
                            "comment": "this is a comment",
                            "de_novo": false,
                            "inherited": true,
                            "nmd_escape": false,
                            "primary_type": "protein_changing",
                            "secondary_type": "stop_gained",
                            "supporting_papers": ["1"],
                            "unknown_inheritance": true
                        }]
                }
        """
        user = self.request.user  # email
        success_flag = 0

        lgd = get_object_or_404(
            LocusGenotypeDisease, stable_id__stable_id=stable_id, is_deleted=0
        )

        # Check if user has permission to update panel
        user_obj = get_object_or_404(User, email=user, is_active=1)
        serializer_user = UserSerializer(user_obj, context={"user": user})
        user_panel_list = [panel for panel in serializer_user.panels_names(user_obj)]
        has_common = LocusGenotypeDiseaseSerializer(
            lgd, context={"user": user}
        ).check_user_permission(lgd, user_panel_list)
        if has_common is False:
            return Response(
                {"error": f"No permission to update record '{stable_id}'"},
                status=status.HTTP_403_FORBIDDEN,
            )

        # LGDVariantTypeListSerializer accepts a list of variant types
        serializer_list = LGDVariantTypeListSerializer(data=request.data)

        if serializer_list.is_valid():
            variant_type_data = serializer_list.validated_data.get("variant_types")

            # Check if list of variants is empty
            if not variant_type_data:
                return Response(
                    {"error": "Empty variant type. Please provide valid data."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Add each variant GenCC consequence from the input list
            for var_type in variant_type_data:
                # The data is created in LGDVariantTypeSerializer
                serializer_class = LGDVariantTypeSerializer(
                    data=var_type, context={"lgd": lgd, "user": user_obj}
                )

                if serializer_class.is_valid():
                    serializer_class.save()
                    success_flag = 1
                    response = Response(
                        {
                            "message": "Variant type added to the G2P entry successfully."
                        },
                        status=status.HTTP_201_CREATED,
                    )
                else:
                    response = Response(
                        {"error": serializer_class.errors},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

        else:
            response = Response(
                {"error": serializer_list.errors}, status=status.HTTP_400_BAD_REQUEST
            )

        # Update the record date_review, if at least one variant type was added successfully
        lgd.date_review = get_date_now()
        lgd.save_without_historical_record()

        return response

    @transaction.atomic
    def patch(self, request, stable_id):
        """
        This method deletes the LGD-variant type.
        The deletion does not remove the entry from the database, instead
        it sets the flag 'is_deleted' to 1.

        Example: { "secondary_type": "stop_gained" }
        """
        # Check if the input has the expected data
        if (
            "secondary_type" not in request.data
            or request.data.get("secondary_type") == ""
        ):
            return Response(
                {"error": "Empty variant type. Please provide the 'secondary_type'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        variant_type = request.data.get("secondary_type")

        lgd_obj = get_object_or_404(
            LocusGenotypeDisease, stable_id__stable_id=stable_id, is_deleted=0
        )

        # Check if user has permission to update record
        user = request.user
        user_obj = get_object_or_404(User, email=user, is_active=1)
        serializer_user = UserSerializer(user_obj, context={"user": user})
        user_panel_list = [panel for panel in serializer_user.panels_names(user_obj)]
        has_common = LocusGenotypeDiseaseSerializer(
            lgd_obj, context={"user": user}
        ).check_user_permission(lgd_obj, user_panel_list)
        if has_common is False:
            return Response(
                {"error": f"No permission to update record '{stable_id}'"},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Get variant type value from ontology_term
        try:
            var_type_obj = OntologyTerm.objects.get(
                term=variant_type, group_type__value="variant_type"
            )
        except OntologyTerm.DoesNotExist:
            return Response(
                {"error": f"Invalid variant type '{variant_type}'"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Get entries to be deleted
        # Different rows mean the lgd-variant type is associated with multiple publications
        # We have to delete all rows
        lgd_var_type_set = LGDVariantType.objects.filter(
            lgd=lgd_obj, variant_type_ot=var_type_obj, is_deleted=0
        )

        if not lgd_var_type_set.exists():
            return Response(
                {
                    "error": f"Could not find variant type '{variant_type}' for ID '{stable_id}'"
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        for lgd_var_type_obj in lgd_var_type_set:
            # Check if the lgd-variant type has comments
            # If so, delete the comments too
            lgd_variant_comments = LGDVariantTypeComment.objects.filter(
                lgd_variant_type=lgd_var_type_obj, is_deleted=0
            )
            for variant_comment in lgd_variant_comments:
                variant_comment.is_deleted = 1
                variant_comment.save()
            lgd_var_type_obj.is_deleted = 1

            try:
                lgd_var_type_obj.save()
            except Exception as e:
                return Response(
                    {
                        "error": f"Could not delete variant type '{variant_type}' for ID '{stable_id}'"
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # Update the date_review of the record
        lgd_obj.date_review = get_date_now()
        lgd_obj.save_without_historical_record()

        return Response(
            {
                "message": f"Variant type '{variant_type}' successfully deleted for ID '{stable_id}'"
            },
            status=status.HTTP_200_OK,
        )


@extend_schema(exclude=True)
class LGDEditVariantTypeDescriptions(CustomPermissionAPIView):
    """
    Add or delete LGD-variant type description(s)
    """

    http_method_names = ["post", "patch", "options"]

    # Define specific permissions
    method_permissions = {
        "post": [permissions.IsAuthenticated],
        "patch": [permissions.IsAuthenticated, IsSuperUser],
    }

    def get_serializer_class(self, action):
        """
        Returns the appropriate serializer class based on the action.
        To add data use LGDVariantTypeDescriptionListSerializer: it accepts a list of variant type descriptions.
        To delete data use LGDVariantTypeDescriptionSerializer: it accepts one variant type description.
        """
        action = action.lower()

        if action == "post":
            return LGDVariantTypeDescriptionListSerializer
        elif action == "patch":
            return LGDVariantTypeDescriptionSerializer
        else:
            return None

    @transaction.atomic
    def post(self, request, stable_id):
        """
        The post method adds a list of variant description (HGVS) to an existing G2P record (LGD).
        We want to whole process to be done in one db transaction.

        Args:
            request (dict)

            Example:
                {
                    "variant_descriptions": [{
                        "publications": [1, 1234],
                        "description": "NM_000546.6:c.794T>C (p.Leu265Pro)"
                    }]
                }
        """
        user = self.request.user

        lgd = get_object_or_404(
            LocusGenotypeDisease, stable_id__stable_id=stable_id, is_deleted=0
        )

        # Check if user has permission to update panel
        user_obj = get_object_or_404(User, email=user, is_active=1)
        serializer_user = UserSerializer(user_obj, context={"user": user})
        user_panel_list = [panel for panel in serializer_user.panels_names(user_obj)]
        has_common = LocusGenotypeDiseaseSerializer(
            lgd, context={"user": user}
        ).check_user_permission(lgd, user_panel_list)
        if has_common is False:
            return Response(
                {"error": f"No permission to update record '{stable_id}'"},
                status=status.HTTP_403_FORBIDDEN,
            )

        # LGDVariantTypeDescriptionListSerializer accepts a list of HGVS
        serializer_list = LGDVariantTypeDescriptionListSerializer(data=request.data)

        if serializer_list.is_valid():
            success_flag = 0
            descriptions_data = request.data.get("variant_descriptions")

            # Check if list of descriptions is empty
            if not descriptions_data:
                return Response(
                    {"error": "Empty variant descriptions. Please provide valid data."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Add each variant description from the input list
            for description in descriptions_data:
                # The data is created in LGDVariantTypeDescriptionSerializer
                # Input the expected data format
                serializer_class = LGDVariantTypeDescriptionSerializer(
                    data=description, context={"lgd": lgd}
                )

                if serializer_class.is_valid():
                    serializer_class.save()
                    success_flag = 1
                    response = Response(
                        {
                            "message": "Variant description added to the G2P entry successfully."
                        },
                        status=status.HTTP_201_CREATED,
                    )
                else:
                    response = Response(
                        {"error": serializer_class.errors},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

            if success_flag:
                # Update the record date last review
                lgd.date_review = get_date_now()
                lgd.save_without_historical_record()

        else:
            response = Response(
                {"error": serializer_list.errors}, status=status.HTTP_400_BAD_REQUEST
            )

        return response

    @transaction.atomic
    def patch(self, request, stable_id):
        """
        This method deletes the LGD-variant type descriptions.
        The deletion does not remove the entry from the database, instead
        it sets the flag 'is_deleted' to 1.

        Example: { "description": "NM_000546.6:c.794T>C (p.Leu265Pro)" }
        """
        # Check if the input has the expected data
        if "description" not in request.data or request.data.get("description") == "":
            return Response(
                {"error": "Empty variant description. Please provide valid data."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        var_desc = request.data.get("description")
        user = request.user

        lgd_obj = get_object_or_404(
            LocusGenotypeDisease, stable_id__stable_id=stable_id, is_deleted=0
        )

        # Check if user has permission to update panel
        user_obj = get_object_or_404(User, email=user, is_active=1)
        serializer_user = UserSerializer(user_obj, context={"user": user})
        user_panel_list = [panel for panel in serializer_user.panels_names(user_obj)]
        has_common = LocusGenotypeDiseaseSerializer(
            lgd_obj, context={"user": user}
        ).check_user_permission(lgd_obj, user_panel_list)
        if has_common is False:
            return Response(
                {"error": f"No permission to update record '{stable_id}'"},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Get entries to be deleted
        # Different rows mean the lgd-variant type description is associated with multiple publications
        # We have to delete all rows
        variant_description_list = LGDVariantTypeDescription.objects.filter(
            lgd=lgd_obj, description=var_desc, is_deleted=0
        )

        if not variant_description_list:
            return Response(
                {
                    "error": f"Variant description '{var_desc}' is not associated with '{stable_id}'"
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        else:
            for variant_description in variant_description_list:
                variant_description.is_deleted = 1
                variant_description.save()

            # Update the record date of last review
            lgd_obj.date_review = get_date_now()
            lgd_obj.save_without_historical_record()

            return Response(
                {
                    "message": f"Variant type description '{var_desc}' successfully deleted for ID '{stable_id}'"
                },
                status=status.HTTP_200_OK,
            )


@extend_schema(exclude=True)
class LGDEditComment(APIView):
    """
    Add or delete a comment to a G2P record (LGD).
    """

    http_method_names = ["post", "patch", "options"]
    serializer_class = LGDCommentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self, action):
        """
        Returns the appropriate serializer class based on the action.
        To add data use LGDCommentListSerializer: it accepts a list of comments.
        To delete data use LGDCommentSerializer: it accepts one comment.
        """
        action = action.lower()

        if action == "post":
            return LGDCommentListSerializer
        else:
            return LGDCommentSerializer

    @transaction.atomic
    def post(self, request, stable_id):
        """
        The post method adds a list of comments.
        It links the current LGD record to the new comment(s).
        We want to whole process to be done in one db transaction.

        Example:
            {
                "comments": [
                    {
                        "comment": "This is a comment",
                        "is_public": 1
                    },
                    {
                        "comment": "This is another comment",
                        "is_public": 0
                    }
                ]
            }
        """
        user = self.request.user

        # Check if G2P ID exists
        lgd = get_object_or_404(
            LocusGenotypeDisease, stable_id__stable_id=stable_id, is_deleted=0
        )
        success_flag = 0

        # Check if user can edit this LGD entry
        lgd_serializer = LocusGenotypeDiseaseSerializer(lgd, context={"user": user})
        lgd_panels = lgd_serializer.get_panels(lgd)
        # Example of lgd_panels:
        # [{'name': 'DD', 'description': 'Developmental disorders'}, {'name': 'Eye', 'description': 'Eye disorders'}]
        user_obj = get_object_or_404(User, email=user, is_active=1)
        user_serializer = UserSerializer(user_obj, context={"user": user})

        if not user_serializer.check_panel_permission(lgd_panels):
            return Response(
                {"error": f"No permission to edit {stable_id}"},
                status=status.HTTP_403_FORBIDDEN,
            )

        # LGDCommentListSerializer accepts a list of comments
        serializer_list = LGDCommentListSerializer(data=request.data)

        if serializer_list.is_valid():
            lgd_comments_data = serializer_list.validated_data.get("comments")

            if not lgd_comments_data:
                return Response(
                    {"error": "Empty comment. Please provide valid data."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            errors = []
            # Add each comment from the input list
            for comment in lgd_comments_data:
                serializer_class = LGDCommentSerializer(
                    data=comment, context={"lgd": lgd, "user": user_obj}
                )

                if serializer_class.is_valid():
                    try:
                        serializer_class.save()
                    except IntegrityError as e:
                        return Response(
                            {"error": f"A database integrity error occurred: {str(e)}"},
                            status=status.HTTP_400_BAD_REQUEST,
                        )
                else:
                    errors.append(serializer_class.errors)

            if errors:
                return Response({"error": errors}, status=status.HTTP_400_BAD_REQUEST)

            success_flag = 1
            response = Response(
                {"message": "Comments added to the G2P entry successfully."},
                status=status.HTTP_201_CREATED,
            )

        else:
            response = Response(
                {"error": serializer_list.errors}, status=status.HTTP_400_BAD_REQUEST
            )

        # At least one comment was added successfully - update record date of the last review
        if success_flag:
            lgd.date_review = get_date_now()
            lgd.save_without_historical_record()

        return response

    @transaction.atomic
    def patch(self, request, stable_id):
        """
        This method deletes the LGD-comment.
        This action is available to all authenticated users.
        """
        comment_id = request.data.get("comment_id", None)
        user = request.user

        if not comment_id:
            return Response(
                {"error": "Missing input key 'comment_id'"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        lgd_obj = get_object_or_404(
            LocusGenotypeDisease, stable_id__stable_id=stable_id, is_deleted=0
        )

        # Check if user has permission to update panel
        user_obj = get_object_or_404(User, email=user, is_active=1)
        serializer_user = UserSerializer(user_obj, context={"user": user})
        user_panel_list = [panel for panel in serializer_user.panels_names(user_obj)]
        has_common = LocusGenotypeDiseaseSerializer(
            lgd_obj, context={"user": user}
        ).check_user_permission(lgd_obj, user_panel_list)
        if has_common is False:
            return Response(
                {"error": f"No permission to update record '{stable_id}'"},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            lgd_comment = LGDComment.objects.get(
                lgd=lgd_obj, id=comment_id, is_deleted=0
            )
        except LGDComment.DoesNotExist:
            return Response(
                {"error": f"Cannot find comment for record '{stable_id}'"},
                status=status.HTTP_404_NOT_FOUND,
            )
        else:
            # Set comment to deleted
            lgd_comment.is_deleted = 1
            lgd_comment.save()
            # Update the date of the last review
            lgd_obj.date_review = get_date_now()
            lgd_obj.save_without_historical_record()

            return Response(
                {"message": f"Comment successfully deleted for record '{stable_id}'"},
                status=status.HTTP_200_OK,
            )


@extend_schema(exclude=True)
class LGDEditReview(APIView):
    http_method_names = ["post", "options"]
    serializer_class = LGDReviewSerializer
    permission_classes = [IsSuperUser]

    @transaction.atomic
    def post(self, request, stable_id):
        """
        The post method updates the review status of the LGD record.
        It updates the value under 'is_reviewed'.
        Input example: {"is_reviewed": false}
        """
        lgd = get_object_or_404(
            LocusGenotypeDisease,
            stable_id__stable_id=stable_id,
            is_deleted=0,
        )

        lgd_panels = LocusGenotypeDiseaseSerializer(
            context={"user": request.user}
        ).get_panels(lgd.id)
        user_obj = get_object_or_404(User, email=request.user, is_active=1)
        if not UserSerializer(
            user_obj, context={"user": request.user}
        ).check_panel_permission(lgd_panels):
            return Response(
                {"error": f"No permission to edit {stable_id}"},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = LGDReviewSerializer(instance=lgd, data=request.data)
        if serializer.is_valid():
            serializer.save()
            state = "reviewed" if lgd.is_reviewed else "under review"
            return Response(
                {"message": f"{stable_id} successfully set to {state}"},
                status=status.HTTP_200_OK,
            )
        else:
            if "is_reviewed" in serializer.errors:
                if "error" in serializer.errors["is_reviewed"]:
                    return Response(
                        {"error": serializer.errors["is_reviewed"]["error"]},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

            return Response(
                {"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST
            )


@extend_schema(exclude=True)
class LocusGenotypeDiseaseDelete(APIView):
    """
    Delete a LGD record
    """
    http_method_names = ["patch", "options"]
    serializer_class = LocusGenotypeDiseaseSerializer
    permission_classes = [permissions.IsAuthenticated, IsSuperUser]

    @transaction.atomic
    def patch(self, request, stable_id):
        """
        This method deletes the LGD record.
        The deletion does not remove the entry from the database, instead
        it sets the flag 'is_deleted' to 1.
        To keep the transaction in the history tables, the update is done by calling save().
        """
        input_data = request.data

        # Validate input data
        if not input_data or not isinstance(input_data, dict) or "comment" not in input_data:
            return Response(
                {
                    "error": "Invalid input data. Please provide a comment why record is being deleted."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Save comment text
        comment = input_data["comment"]
        # Get user
        user = request.user

        stable_id_obj = get_object_or_404(
            G2PStableID, stable_id=stable_id, is_deleted=0
        )
        lgd_obj = get_object_or_404(
            LocusGenotypeDisease, stable_id=stable_id_obj, is_deleted=0
        )

        # Check if user has permission to update panel
        user_obj = get_object_or_404(User, email=user, is_active=1)
        serializer_user = UserSerializer(user_obj, context={"user": user})
        user_panel_list = [panel for panel in serializer_user.panels_names(user_obj)]
        has_common = LocusGenotypeDiseaseSerializer(
            lgd_obj, context={"user": user}
        ).check_user_permission(lgd_obj, user_panel_list)
        if has_common is False:
            return Response(
                {"error": f"No permission to update record '{stable_id}'"},
                status=status.HTTP_403_FORBIDDEN,
            )

        delete_lgd_record(lgd_obj)

        # Delete the stable id used by the LGD record
        stable_id_obj.is_deleted = 1
        stable_id_obj.is_live = 0
        stable_id_obj.comment = comment
        # Save updates
        stable_id_obj.save()

        return Response(
            {"message": f"ID '{stable_id}' successfully deleted"},
            status=status.HTTP_200_OK,
        )


### Merge/Split records ###
@extend_schema(exclude=True)
@api_view(["POST"])
@permission_classes([IsSuperUser])
def MergeRecords(request):
    """
    Merges one or more LGD records ("g2p_ids") into a target record ("final_g2p_id").

    Args:
        request (Request): HTTP request containing a list of records to merge

    Example:
    [
        {"g2p_ids": ["G2P00004"], "final_g2p_id": "G2P00001"},
        {"g2p_ids": ["G2P00005", "G2P00008"], "final_g2p_id": "G2P00006"}
    ]
    """
    records_list = request.data

    if not records_list or not isinstance(records_list, list):
        return Response(
            {"error": "Request should be a list containing the records to merge"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    merged_records = []
    errors = []

    for record in records_list:
        # record = {"g2p_ids": ["G2P00004"], "final_g2p_id": "G2P00001"}
        try:
            g2p_ids = record["g2p_ids"]
        except KeyError:
            errors.append({"error": f"g2p_ids key missing from input data '{record}'"})
        else:
            # Check if the list of IDs to merge is empty
            if len(g2p_ids) == 0:
                errors.append({"error": f"Empty g2p_ids '{record}'"})
            else:
                # Get which of the IDs is going to be kept - save it in "final_g2p_id"
                try:
                    final_g2p_id = record["final_g2p_id"]
                except KeyError:
                    errors.append(
                        {
                            "error": f"final_g2p_id key missing from input data '{record}'"
                        }
                    )
                else:
                    # Check the g2p id to keep is not in the list of g2p ids
                    # This avoids merging a record into itself
                    if final_g2p_id in g2p_ids:
                        g2p_ids.remove(final_g2p_id)

                    # Data to merge:
                    # variant types, variant description, variant consequences, phenotypes,
                    # phenotype summary, publications, comments, panels, cross cutting modifiers,
                    # mechanism synopsis, mechanism evidence

                    # Get the G2P record to keep
                    try:
                        lgd_obj_keep = LocusGenotypeDisease.objects.get(
                            stable_id__stable_id=final_g2p_id, is_deleted=0
                        )
                    except LocusGenotypeDisease.DoesNotExist:
                        errors.append({"error": f"Invalid G2P record {final_g2p_id}"})

                    # Loop through the records to be merged into 'lgd_obj_keep'
                    with transaction.atomic():
                        for g2p_id in g2p_ids:
                            try:
                                lgd_obj = LocusGenotypeDisease.objects.get(
                                    stable_id__stable_id=g2p_id, is_deleted=0
                                )
                            except LocusGenotypeDisease.DoesNotExist:
                                errors.append({"error": f"Invalid G2P record {g2p_id}"})
                            else:
                                # Run checks before the update
                                # Check if the gene and genotypes are the same
                                if lgd_obj_keep.genotype != lgd_obj.genotype:
                                    errors.append(
                                        {
                                            "error": f"Cannot merge records {final_g2p_id} and {g2p_id} with different genotypes"
                                        }
                                    )
                                elif lgd_obj_keep.locus != lgd_obj.locus:
                                    errors.append(
                                        {
                                            "error": f"Cannot merge records {final_g2p_id} and {g2p_id} with different genes"
                                        }
                                    )
                                else:
                                    # Proceed with merge
                                    move_related_objects(
                                        LGDPhenotype,
                                        lgd_obj,
                                        lgd_obj_keep,
                                        ["phenotype", "publication"],
                                    )
                                    move_related_objects(
                                        LGDPhenotypeSummary, lgd_obj, lgd_obj_keep
                                    )
                                    move_related_objects(
                                        LGDVariantTypeDescription, lgd_obj, lgd_obj_keep
                                    )
                                    move_related_objects(
                                        LGDComment, lgd_obj, lgd_obj_keep
                                    )
                                    move_related_objects(
                                        LGDMolecularMechanismSynopsis,
                                        lgd_obj,
                                        lgd_obj_keep,
                                    )
                                    move_related_objects(
                                        LGDPublication,
                                        lgd_obj,
                                        lgd_obj_keep,
                                        ["publication"],
                                    )
                                    move_related_objects(
                                        LGDCrossCuttingModifier,
                                        lgd_obj,
                                        lgd_obj_keep,
                                        ["ccm"],
                                    )
                                    move_related_objects(
                                        LGDVariantType,
                                        lgd_obj,
                                        lgd_obj_keep,
                                        ["variant_type_ot", "publication"],
                                    )
                                    move_related_objects(
                                        LGDMolecularMechanismEvidence,
                                        lgd_obj,
                                        lgd_obj_keep,
                                        ["evidence", "publication"],
                                    )
                                    move_related_objects(
                                        LGDPanel, lgd_obj, lgd_obj_keep, ["panel"]
                                    )
                                    # Variant gencc consequence has support - do not include the support in the check
                                    move_related_objects(
                                        LGDVariantGenccConsequence,
                                        lgd_obj,
                                        lgd_obj_keep,
                                        ["variant_consequence"],
                                    )

                                    delete_lgd_record(lgd_obj)

                                    # Delete the stable id used by the LGD record
                                    try:
                                        stable_id_obj = G2PStableID.objects.get(
                                            id=lgd_obj.stable_id.id
                                        )
                                    except G2PStableID.DoesNotExist:
                                        errors.append(
                                            {"error": f"Invalid G2P record {g2p_id}"}
                                        )
                                    else:
                                        stable_id_obj.is_deleted = 1
                                        stable_id_obj.is_live = 0
                                        stable_id_obj.comment = (
                                            f"Merged into {final_g2p_id}"
                                        )
                                        stable_id_obj.save()

                                    merged_records.append(
                                        {f"{g2p_id} merged into {final_g2p_id}"}
                                    )

    response_data = {}
    if merged_records:
        response_data["merged_records"] = merged_records

    if errors:
        response_data["error"] = errors

    return Response(
        response_data,
        status=status.HTTP_200_OK if merged_records else status.HTTP_400_BAD_REQUEST,
    )


@extend_schema(exclude=True)
def delete_lgd_record(lgd_obj: Model) -> None:
    """
    Method to delete the record from the main table and the data linked to it.
    The deletion is an update of the flag 'is_deleted' to value 0.

    Args:
        lgd_obj (Model): Record to be deleted
    """
    # Delete lgd-cross cutting modifiers
    for ccm in LGDCrossCuttingModifier.objects.filter(lgd=lgd_obj, is_deleted=0):
        ccm.is_deleted = 1
        ccm.save()

    # Delete comments
    for comment in LGDComment.objects.filter(lgd=lgd_obj, is_deleted=0):
        comment.is_deleted = 1
        comment.save()

    # Delete lgd-panels
    for panel in LGDPanel.objects.filter(lgd=lgd_obj, is_deleted=0):
        panel.is_deleted = 1
        panel.save()

    # Delete phenotypes
    for phenotypes in LGDPhenotype.objects.filter(lgd=lgd_obj, is_deleted=0):
        phenotypes.is_deleted = 1
        phenotypes.save()

    # Delete phenotype summary
    for pheno_summary in LGDPhenotypeSummary.objects.filter(lgd=lgd_obj, is_deleted=0):
        pheno_summary.is_deleted = 1
        pheno_summary.save()

    # Delete variant types + comments
    lgd_var_type_set = LGDVariantType.objects.filter(lgd=lgd_obj, is_deleted=0)

    for lgd_var_type_obj in lgd_var_type_set:
        # Check if the lgd-variant type has comments
        # If so, delete the comments too
        for var_comment in LGDVariantTypeComment.objects.filter(
            lgd_variant_type=lgd_var_type_obj, is_deleted=0
        ):
            var_comment.is_deleted = 1
            var_comment.save()
        lgd_var_type_obj.is_deleted = 1
        lgd_var_type_obj.save()

    # Delete variant type description
    for var_description in LGDVariantTypeDescription.objects.filter(
        lgd=lgd_obj, is_deleted=0
    ):
        var_description.is_deleted = 1
        var_description.save()

    # Delete variant consequences
    for var_consequence in LGDVariantGenccConsequence.objects.filter(
        lgd=lgd_obj, is_deleted=0
    ):
        var_consequence.is_deleted = 1
        var_consequence.save()

    # Delete mechanism synopsis
    for mechanism_synopsis in LGDMolecularMechanismSynopsis.objects.filter(
        lgd=lgd_obj, is_deleted=0
    ):
        mechanism_synopsis.is_deleted = 1
        mechanism_synopsis.save()

    # Delete mechanism evidence
    for mechanism_evidence in LGDMolecularMechanismEvidence.objects.filter(
        lgd=lgd_obj, is_deleted=0
    ):
        mechanism_evidence.is_deleted = 1
        mechanism_evidence.save()

    # Delete publications
    for publication in LGDPublication.objects.filter(lgd=lgd_obj, is_deleted=0):
        publication.is_deleted = 1
        publication.save()

    # Delete the LGD record
    lgd_obj.is_deleted = 1
    lgd_obj.save()


@extend_schema(exclude=True)
def move_related_objects(
    model_class: Type[Model],
    lgd_obj: Model,
    lgd_obj_keep: Model,
    unique_fields: List[str] = None,
) -> None:
    """
    Method to reassign related objects from a source LGD record to a target LGD record,
    avoiding duplicates.

    Args:
        model_class (Type[Model]): The Django model class of the related objects
        lgd_obj (Model): The source LocusGenotypeDisease object (to merge from)
        lgd_obj_keep (Model): The target LocusGenotypeDisease object (to merge into)
        unique_fields (List[str]): List of fields (besides 'lgd') that define uniqueness
    """
    # Fetch the objects linked to the record (to merge from)
    objs: QuerySet = model_class.objects.filter(lgd=lgd_obj, is_deleted=0)

    for obj in objs:
        if obj.lgd_id == lgd_obj_keep.id:
            continue
        # Build filter for existing record in target (to merge into)
        if unique_fields:
            filter_args = {"lgd": lgd_obj_keep}
            for field in unique_fields:
                filter_args[field] = getattr(obj, field)
            if model_class.objects.filter(**filter_args).exists():
                continue  # Skip duplicate

        obj.lgd = lgd_obj_keep
        obj.save()
