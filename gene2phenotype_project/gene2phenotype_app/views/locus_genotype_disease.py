from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from django.http import Http404
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.db import transaction, IntegrityError
from drf_spectacular.utils import extend_schema, OpenApiResponse


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
    LGDCommentListSerializer
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
    LGDComment
)

from .base import (
    BaseUpdate,
    CustomPermissionAPIView,
    IsSuperUser
)

@extend_schema(
    responses={
        200: OpenApiResponse(
            description="Molecular mechanisms response",
            response={
                "type": "object",
                "properties": {
                    "evidence": {"type": "object"},
                    "mechanism": {"type": "array", "items": {"type": "object"}},
                    "mechanism_synopsis": {"type": "array", "items": {"type": "object"}},
                    "support": {"type": "array", "items": {"type": "object"}}
                }
            }
        )
    }
)
class ListMolecularMechanisms(generics.ListAPIView):
    """
        Return the molecular mechanisms terms by type and subtype (if applicable).

        Returns a dictionary where the key is the type the value is a list.
    """

    queryset = CVMolecularMechanism.objects.all().values('type', 'subtype', 'value', 'description').order_by('type')

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
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
                        result[mechanismtype][subtype] = [{value:description}]
                    else:
                        result[mechanismtype][subtype].append({value:description})
                else:
                    result[mechanismtype].append({value:description})

        return Response(result)

@extend_schema(
    responses={
        200: OpenApiResponse(
            description="Variant types response",
            response={
                "type": "object",
                "properties": {
                    "NMD_variants": {"type": "array", "items": {"type": "object"}},
                    "splice_variants": {"type": "array", "items": {"type": "object"}},
                    "regulatory_variants": {"type": "array", "items": {"type": "object"}},
                    "protein_changing_variants": {"type": "array", "items": {"type": "object"}},
                    "other_variants": {"type": "array", "items": {"type": "object"}}
                }
            }
        )
    }
)
class VariantTypesList(generics.ListAPIView):
    """
        Return all variant types by group.

        Returns a dictionary where the key is the variant group and the value is a list of terms
    """

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

        return Response(
            {
                'NMD_variants': list_nmd,
                'splice_variants': list_splice,
                'regulatory_variants': list_regulatory,
                'protein_changing_variants': list_protein,
                'other_variants': list
            }
        )

class LocusGenotypeDiseaseDetail(generics.ListAPIView):
    """
        Return all data for a G2P record.

        Args:
            (string) `stable_id`: G2P stable ID

        Returns a LocusGenotypeDisease object:
            (dict) locus;
            (str) stable_id;
            (str) genotype;
            (dict) disease;
            (dict) molecular_mechanism;
            (list) phenotypes;
            (list) publications;
            ...
    """
    serializer_class = LocusGenotypeDiseaseSerializer

    def get_queryset(self):
        stable_id = self.kwargs['stable_id']
        user = self.request.user

        g2p_stable_id = get_object_or_404(G2PStableID, stable_id=stable_id)

        # Authenticated users (curators) can see all entries:
        #   - in visible and non-visible panels
        #   - entries flagged as not reviewed (is_reviewed=0)
        if user.is_authenticated:
            queryset = LocusGenotypeDisease.objects.filter(stable_id=g2p_stable_id, is_deleted=0)
        else:
            queryset = LocusGenotypeDisease.objects.filter(stable_id=g2p_stable_id, is_reviewed=1, is_deleted=0, lgdpanel__panel__is_visible=1).distinct()

        if not queryset.exists():
            raise Http404(f"No matching Entry found for: {stable_id}")
        else:
            return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset().first()
        serializer = LocusGenotypeDiseaseSerializer(queryset, context={'user': self.request.user})
        return Response(serializer.data)


### Add or delete data ###
@extend_schema(exclude=True)
class LGDUpdateConfidence(BaseUpdate):
    http_method_names = ['put', 'options']
    serializer_class = LocusGenotypeDiseaseSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        stable_id = self.kwargs['stable_id']

        g2p_stable_id = get_object_or_404(G2PStableID, stable_id=stable_id)
        # Get the entry for this user
        queryset = LocusGenotypeDisease.objects.filter(stable_id=g2p_stable_id, is_deleted=0)

        if not queryset.exists():
            self.handle_no_permission('Entry', stable_id)
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
            lgd_obj,
            data=request.data,
            context={'user': user}
        )

        # Check if user has permission to update panel
        user_obj = get_object_or_404(User, email=user, is_active=1)
        serializer_user = UserSerializer(user_obj, context={"user" : user})
        user_panel_list = [panel for panel in serializer_user.panels_names(user_obj)]
        has_common = serializer.check_user_permission(lgd_obj, user_panel_list)

        if has_common is False:
            return Response(
                {"error": f"No permission to update record '{lgd_obj.stable_id.stable_id}'"},
                status=status.HTTP_403_FORBIDDEN
            )

        if serializer.is_valid():
            instance = serializer.save()
            return Response(
                {"message": f"Data updated successfully for '{instance.stable_id.stable_id}'"},
                 status=status.HTTP_200_OK)

        else:
            return Response(
                {"error": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

@extend_schema(exclude=True)
class LGDUpdateMechanism(BaseUpdate):
    http_method_names = ['patch', 'options']
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
        stable_id = self.kwargs['stable_id']

        g2p_stable_id = get_object_or_404(G2PStableID, stable_id=stable_id)
        # Get the record
        queryset = LocusGenotypeDisease.objects.filter(stable_id=g2p_stable_id, is_deleted=0)

        if not queryset.exists():
            self.handle_no_permission('Entry', stable_id)

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
        serializer = LocusGenotypeDiseaseSerializer()

        # Check if user has permission to edit this entry
        user_obj = get_object_or_404(User, email=user, is_active=1)
        serializer_user = UserSerializer(user_obj, context={"user" : user})
        user_panel_list = [panel for panel in serializer_user.panels_names(user_obj)]
        has_common = serializer.check_user_permission(lgd_obj, user_panel_list)

        if has_common is False:
            return Response(
                {"error": f"No permission to update record '{stable_id}'"},
                status=status.HTTP_403_FORBIDDEN
            )

        # Validate mechanism data
        molecular_mechanism = mechanism_data.get("molecular_mechanism", None) # mechanism value can be updated if current value is "undetermined"
        mechanism_synopsis = mechanism_data.get("mechanism_synopsis", []) # optional
        mechanism_evidence = mechanism_data.get("mechanism_evidence", None) # optional

        # Return error if no data is provided
        if(molecular_mechanism is None and not mechanism_synopsis and 
           mechanism_evidence is None):
            self.handle_missing_data("Mechanism data")

        # Check if mechanism value can be updated
        if(molecular_mechanism and lgd_obj.mechanism.value != "undetermined" and 
           "name" in molecular_mechanism and molecular_mechanism["name"] != ""):
            return self.handle_no_update("molecular mechanism", stable_id)

        # If the mechanism support is "evidence" then the evidence has to be provided
        if(mechanism_evidence is None and molecular_mechanism and "support" in molecular_mechanism and 
           molecular_mechanism["support"] == "evidence"):
            self.handle_missing_data("Mechanism evidence")

        # Separate method to update mechanism
        # Updating the mechanism can be complex, specially if evidence data is provided
        # To avoid problems with other LDG updates, the mechanism is going to be
        # updated in a separate method - this implies extra validation
        try:
            serializer.update_mechanism(lgd_obj, mechanism_data)
        except Exception as e:
            if hasattr(e, "detail") and "message" in e.detail:
                return Response(
                {"error": f"Error while updating molecular mechanism: {e.detail['message']}"},
                status=status.HTTP_400_BAD_REQUEST
            )
            else:
                return Response(
                    {"error": f"Error while updating molecular mechanism {e}"},
                    status=status.HTTP_400_BAD_REQUEST
                )
        else:
            return Response(
                {"message": f"Molecular mechanism updated successfully for '{stable_id}'"},
                status=status.HTTP_200_OK
            )

@extend_schema(exclude=True)
class LGDEditVariantConsequences(CustomPermissionAPIView):
    """
        Add or delete lgd-variant consequence(s).

        Add data (action: POST)
            Add a list of variant GenCC consequences to an existing G2P record (LGD).

        Delete data (action: UPDATE)
            Delete a variant GenCC consequence associated with the LGD.
            The deletion does not remove the entry from the database, instead
            it sets the flag 'is_deleted' to 1.
    """
    http_method_names = ['post', 'patch', 'options']

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
            The post method creates an association between the current LGD record and a list of variant consequences.
            We want to whole process to be done in one db transaction.

            Args:
                (dict) request

                Example:
                    {
                        "variant_consequences": [{
                            "variant_consequence": "altered_gene_product_level",
                            "support": "inferred"
                        }]
                    }
        """
        lgd = get_object_or_404(LocusGenotypeDisease, stable_id__stable_id=stable_id, is_deleted=0)

        # Check if user has permission to update panel
        user = self.request.user
        user_obj = get_object_or_404(User, email=user, is_active=1)
        serializer_user = UserSerializer(user_obj, context={"user" : user})
        user_panel_list = [panel for panel in serializer_user.panels_names(user_obj)]
        has_common = LocusGenotypeDiseaseSerializer(lgd).check_user_permission(lgd, user_panel_list)
        if has_common is False:
            return Response({"error": f"No permission to update record '{stable_id}'"}, status=status.HTTP_403_FORBIDDEN)

        # LGDVariantConsequenceListSerializer accepts a list of variant consequences
        serializer_list = LGDVariantConsequenceListSerializer(data=request.data)

        if serializer_list.is_valid():
            variant_consequence_data = serializer_list.validated_data.get('variant_consequences')

            # Check if list of consequences is empty
            if(not variant_consequence_data):
                response = Response(
                    {"error": "Empty variant consequence. Please provide valid data."},
                     status=status.HTTP_400_BAD_REQUEST
                )

            # Add each variant GenCC consequence from the input list
            for var_consequence in variant_consequence_data:
                # The data is created in LGDVariantGenCCConsequenceSerializer
                # Input the expected data format
                serializer_class = LGDVariantGenCCConsequenceSerializer(
                    data={
                        "variant_consequence": var_consequence["variant_consequence"]["term"],
                        "support": var_consequence["support"]["value"]
                    },
                    context={"lgd": lgd}
                )

                if serializer_class.is_valid():
                    serializer_class.save()
                    response = Response(
                        {"message": "Variant consequence added to the G2P entry successfully."},
                        status=status.HTTP_201_CREATED
                    )
                else:
                    response = Response(
                        {"error": serializer_class.errors}, status=status.HTTP_400_BAD_REQUEST
                    )

        else:
            response = Response(
                {"error": serializer_list.errors}, status=status.HTTP_400_BAD_REQUEST
            )

        return response

    @transaction.atomic
    def patch(self, request, stable_id):
        """
            This method deletes the LGD-variant gencc consequence.

            Example: {"variant_consequence": "altered_gene_product_level"}
        """
        # Check if input has the expected value
        if "variant_consequence" not in request.data or request.data.get('variant_consequence') == "":
            return Response(
                {"error": f"Empty variant consequence. Please provide the 'variant_consequence'."},
                status=status.HTTP_400_BAD_REQUEST
            )

        consequence = request.data.get('variant_consequence')

        if consequence is None:
            return Response(
                {"error": f"Empty variant consequence"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        consequence = consequence.replace("_", " ")

        # Fecth G2P record to update
        lgd_obj = get_object_or_404(LocusGenotypeDisease, stable_id__stable_id=stable_id, is_deleted=0)

        # Check if user has permission to update panel
        user = self.request.user
        user_obj = get_object_or_404(User, email=user, is_active=1)
        serializer_user = UserSerializer(user_obj, context={"user" : user})
        user_panel_list = [panel for panel in serializer_user.panels_names(user_obj)]
        has_common = LocusGenotypeDiseaseSerializer(lgd_obj).check_user_permission(lgd_obj, user_panel_list)
        if has_common is False:
            return Response({"error": f"No permission to update record '{stable_id}'"}, status=status.HTTP_403_FORBIDDEN)

        # Get variant gencc consequence value from ontology_term
        try:
            consequence_obj = OntologyTerm.objects.get(
                term = consequence,
                group_type__value = "variant_type"
            )
        except OntologyTerm.DoesNotExist:
            raise Http404(f"Invalid variant consequence '{consequence}'")

        try:
            LGDVariantGenccConsequence.objects.filter(lgd=lgd_obj, variant_consequence=consequence_obj, is_deleted=0).update(is_deleted=1)
        except:
            return Response(
                {"error": f"Could not delete variant consequence '{consequence}' for ID '{stable_id}'"},
                status=status.HTTP_400_BAD_REQUEST
            )
        else:
            return Response(
                {"message": f"Variant consequence '{consequence}' successfully deleted for ID '{stable_id}'"},
                status=status.HTTP_200_OK)

@extend_schema(exclude=True)
class LGDEditCCM(CustomPermissionAPIView):
    """
        Add or delete LGD-cross cutting modifier(s).

        Add data (action: POST)
            Add a list of cross cutting modifiers to an existing G2P record (LGD).

        Delete data (action: UPDATE)
            Delete a cross cutting modifier associated with the LGD.
            The deletion does not remove the entry from the database, instead
            it sets the flag 'is_deleted' to 1.
    """
    http_method_names = ['post', 'patch', 'options']

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
            The post method creates an association between the current LGD record and a list of cross cutting modifiers.
            We want to whole process to be done in one db transaction.

            Args:
                (dict) request

                Example:
                    {
                        "cross_cutting_modifiers": [{"term": "typically mosaic"}]
                    }
        """
        lgd = get_object_or_404(LocusGenotypeDisease, stable_id__stable_id=stable_id, is_deleted=0)

        # Check if user has permission to update panel
        user = self.request.user
        user_obj = get_object_or_404(User, email=user, is_active=1)
        serializer_user = UserSerializer(user_obj, context={"user" : user})
        user_panel_list = [panel for panel in serializer_user.panels_names(user_obj)]
        has_common = LocusGenotypeDiseaseSerializer(lgd).check_user_permission(lgd, user_panel_list)
        if has_common is False:
            return Response(
                {"error": f"No permission to update record '{stable_id}'"},
                status=status.HTTP_403_FORBIDDEN
            )

        # LGDCrossCuttingModifierListSerializer accepts a list of cross cutting modifiers
        serializer_list = LGDCrossCuttingModifierListSerializer(data=request.data)

        if serializer_list.is_valid():
            ccm_data = serializer_list.validated_data.get('cross_cutting_modifiers')

            # Check if list of consequences is empty
            if not ccm_data :
                return Response(
                    {"error": "Empty cross cutting modifier. Please provide valid data."},
                     status=status.HTTP_400_BAD_REQUEST
                )

            # Add each cross cutting modifier from the input list
            for ccm in ccm_data:
                # The data is created in LGDCrossCuttingModifierSerializer
                # Input the expected data format
                serializer_class = LGDCrossCuttingModifierSerializer(
                    data={"term": ccm["ccm"]["value"]},
                    context={"lgd": lgd}
                )

                if serializer_class.is_valid():
                    serializer_class.save()
                    response = Response(
                        {"message": "Cross cutting modifier added to the G2P entry successfully."},
                        status=status.HTTP_201_CREATED
                    )
                else:
                    response = Response(
                        {"error": serializer_class.errors}, status=status.HTTP_400_BAD_REQUEST
                    )

        else:
            response = Response(
                {"error": serializer_list.errors}, status=status.HTTP_400_BAD_REQUEST
            )

        return response

    @transaction.atomic
    def patch(self, request, stable_id):
        """
            This method deletes the LGD-cross cutting modifier.
            Example:
                    { "term": "typically mosaic" }
        """
        if "term" not in request.data or request.data.get('term') == "":
            return Response({"error": f"Empty cross cutting modifier. Please provide the 'term'."}, status=status.HTTP_400_BAD_REQUEST)

        ccm_tmp = request.data.get('term')
        ccm = ccm_tmp.replace("_", " ")
        user = request.user

        lgd_obj = get_object_or_404(LocusGenotypeDisease, stable_id__stable_id=stable_id, is_deleted=0)

        # Check if user has permission to update panel
        user_obj = get_object_or_404(User, email=user, is_active=1)
        serializer_user = UserSerializer(user_obj, context={"user" : user})
        user_panel_list = [panel for panel in serializer_user.panels_names(user_obj)]
        has_common = LocusGenotypeDiseaseSerializer(lgd_obj).check_user_permission(lgd_obj, user_panel_list)
        if has_common is False:
            return Response(
                {"error": f"No permission to update record '{stable_id}'"},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            ccm_obj = Attrib.objects.get(
                value = ccm,
                type__code = 'cross_cutting_modifier'
            )
        except Attrib.DoesNotExist:
            raise Http404(f"Invalid cross cutting modifier '{ccm}'")

        try:
            LGDCrossCuttingModifier.objects.filter(lgd=lgd_obj, ccm=ccm_obj, is_deleted=0).update(is_deleted=1)
        except:
            return Response(
                {"error": f"Could not delete cross cutting modifier '{ccm}' for ID '{stable_id}'"},
                status=status.HTTP_400_BAD_REQUEST
            )
        else:
            return Response(
                {"message": f"Cross cutting modifier '{ccm}' successfully deleted for ID '{stable_id}'"},
                 status=status.HTTP_200_OK
            )

@extend_schema(exclude=True)
class LGDEditVariantTypes(CustomPermissionAPIView):
    """
        Add or delete LGD-variant type(s).

        Add data (action: POST)
            Add a list of variant types to an existing G2P record (LGD).

        Delete data (action: UPDATE)
            Delete a variant type associated with the LGD.
            The deletion does not remove the entry from the database, instead
            it sets the flag 'is_deleted' to 1.
    """
    http_method_names = ['post', 'patch', 'options']

    # Define specific permissions
    method_permissions = {
        "post": [permissions.IsAuthenticated],
        "patch": [permissions.IsAuthenticated, IsSuperUser]
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
            The post method creates an association between the current LGD record and a list of
            variant types.
            We want to whole process to be done in one db transaction.

            Args:
                (dict) request

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
        user = self.request.user # email

        lgd = get_object_or_404(LocusGenotypeDisease, stable_id__stable_id=stable_id, is_deleted=0)

        # Check if user has permission to update panel
        user_obj = get_object_or_404(User, email=user, is_active=1)
        serializer_user = UserSerializer(user_obj, context={"user" : user})
        user_panel_list = [panel for panel in serializer_user.panels_names(user_obj)]
        has_common = LocusGenotypeDiseaseSerializer(lgd).check_user_permission(lgd, user_panel_list)
        if has_common is False:
            return Response(
                {"error": f"No permission to update record '{stable_id}'"},
                status=status.HTTP_403_FORBIDDEN
            )

        # LGDVariantTypeListSerializer accepts a list of variant types
        serializer_list = LGDVariantTypeListSerializer(data=request.data)

        if serializer_list.is_valid():
            variant_type_data = serializer_list.validated_data.get('variant_types')

            # Check if list of variants is empty
            if not variant_type_data :
                return Response(
                    {"error": "Empty variant type. Please provide valid data."},
                     status=status.HTTP_400_BAD_REQUEST
                )

            # Add each variant GenCC consequence from the input list
            for var_type in variant_type_data:
                # The data is created in LGDVariantTypeSerializer
                serializer_class = LGDVariantTypeSerializer(
                    data=var_type,
                    context={"lgd": lgd, "user": user_obj}
                )

                if serializer_class.is_valid():
                    serializer_class.save()
                    response = Response(
                        {"message": "Variant type added to the G2P entry successfully."},
                        status=status.HTTP_201_CREATED
                    )
                else:
                    response = Response(
                        {"error": serializer_class.errors}, status=status.HTTP_400_BAD_REQUEST
                    )

        else:
            response = Response(
                {"error": serializer_list.errors}, status=status.HTTP_400_BAD_REQUEST
            )

        return response

    @transaction.atomic
    def patch(self, request, stable_id):
        """
            This method deletes the LGD-variant type.

            Example: { "secondary_type": "stop_gained" }
        """
        # Check if the input has the expected data
        if "secondary_type" not in request.data or request.data.get('secondary_type') == "":
            return Response(
                {"error": f"Empty variant type. Please provide the 'secondary_type'."},
                status=status.HTTP_400_BAD_REQUEST
            )

        variant_type = request.data.get('secondary_type')

        lgd_obj = get_object_or_404(LocusGenotypeDisease, stable_id__stable_id=stable_id, is_deleted=0)

        # Check if user has permission to update panel
        user = request.user
        user_obj = get_object_or_404(User, email=user, is_active=1)
        serializer_user = UserSerializer(user_obj, context={"user" : user})
        user_panel_list = [panel for panel in serializer_user.panels_names(user_obj)]
        has_common = LocusGenotypeDiseaseSerializer(lgd_obj).check_user_permission(lgd_obj, user_panel_list)
        if has_common is False:
            return Response(
                {"error": f"No permission to update record '{stable_id}'"},
                status=status.HTTP_403_FORBIDDEN
            )

        # Get variant type value from ontology_term
        try:
            var_type_obj = OntologyTerm.objects.get(
                term = variant_type,
                group_type__value = "variant_type"
            )
        except OntologyTerm.DoesNotExist:
            raise Http404(f"Invalid variant type '{variant_type}'")

        # Get entries to be deleted
        # Different rows mean the lgd-variant type is associated with multiple publications
        # We have to delete all rows
        lgd_var_type_set = LGDVariantType.objects.filter(lgd=lgd_obj, variant_type_ot=var_type_obj, is_deleted=0)

        if not lgd_var_type_set.exists():
            return Response(
                {"error": f"Could not find variant type '{variant_type}' for ID '{stable_id}'"},
                status=status.HTTP_404_NOT_FOUND
            )

        for lgd_var_type_obj in lgd_var_type_set:
            # Check if the lgd-variant type has comments
            # If so, delete the comments too
            LGDVariantTypeComment.objects.filter(lgd_variant_type=lgd_var_type_obj, is_deleted=0).update(is_deleted=1)
            lgd_var_type_obj.is_deleted = 1

            try:
                lgd_var_type_obj.save()
            except:
                return Response(
                    {"error": f"Could not delete variant type '{variant_type}' for ID '{stable_id}'"},
                    status=status.HTTP_400_BAD_REQUEST
                )

        return Response(
                {"message": f"Variant type '{variant_type}' successfully deleted for ID '{stable_id}'"},
                status=status.HTTP_200_OK
            )

@extend_schema(exclude=True)
class LGDEditVariantTypeDescriptions(CustomPermissionAPIView):
    """
        Add or delete LGD-variant type(s)

        Add data (action: POST)
            Add a list of variant description (HGVS) to an existing G2P record (LGD).

        Delete data (action: UPDATE)
            Delete a variant type description associated with the LGD.
            The deletion does not remove the entry from the database, instead
            it sets the flag 'is_deleted' to 1.
    """
    http_method_names = ['post', 'patch', 'options']

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
            The post method creates an association between the current LGD record and a list of 
            variant type descriptions (HGVS).
            We want to whole process to be done in one db transaction.

            Args:
                (dict) request

                Example:
                    {
                        "variant_descriptions": [{
                                "publications": [1, 1234],
                                "description": "NM_000546.6:c.794T>C (p.Leu265Pro)"
                        }]
                    }
        """
        user = self.request.user

        lgd = get_object_or_404(LocusGenotypeDisease, stable_id__stable_id=stable_id, is_deleted=0)

        # Check if user has permission to update panel
        user_obj = get_object_or_404(User, email=user, is_active=1)
        serializer_user = UserSerializer(user_obj, context={"user" : user})
        user_panel_list = [panel for panel in serializer_user.panels_names(user_obj)]
        has_common = LocusGenotypeDiseaseSerializer(lgd).check_user_permission(lgd, user_panel_list)
        if has_common is False:
            return Response({"error": f"No permission to update record '{stable_id}'"}, status=status.HTTP_403_FORBIDDEN)

        # LGDVariantTypeDescriptionListSerializer accepts a list of HGVS
        serializer_list = LGDVariantTypeDescriptionListSerializer(data=request.data)

        if serializer_list.is_valid():
            descriptions_data = request.data.get('variant_descriptions')

            # Check if list of descriptions is empty
            if not descriptions_data:
                return Response(
                    {"error": "Empty variant descriptions. Please provide valid data."},
                     status=status.HTTP_400_BAD_REQUEST
                )

            # Add each variant description from the input list
            for description in descriptions_data:
                # The data is created in LGDVariantTypeDescriptionSerializer
                # Input the expected data format
                serializer_class = LGDVariantTypeDescriptionSerializer(
                    data=description,
                    context={"lgd": lgd}
                )

                if serializer_class.is_valid():
                    serializer_class.save()
                    response = Response(
                        {"message": "Variant description added to the G2P entry successfully."},
                        status=status.HTTP_201_CREATED
                    )
                else:
                    response = Response(
                        {"error": serializer_class.errors}, status=status.HTTP_400_BAD_REQUEST
                    )

        else:
            response = Response(
                {"error": serializer_list.errors}, status=status.HTTP_400_BAD_REQUEST
            )

        return response

    @transaction.atomic
    def patch(self, request, stable_id):
        """
            This method deletes the LGD-variant type descriptions.

            Example: { "description": "NM_000546.6:c.794T>C (p.Leu265Pro)" }
        """
        # Check if the input has the expected data
        if "description" not in request.data or request.data.get('description') == "":
            return Response({"error": f"Empty variant type description. Please provide the 'description'."}, status=status.HTTP_400_BAD_REQUEST)

        var_desc = request.data.get('description')
        user = request.user

        lgd_obj = get_object_or_404(LocusGenotypeDisease, stable_id__stable_id=stable_id, is_deleted=0)

        # Check if user has permission to update panel
        user_obj = get_object_or_404(User, email=user, is_active=1)
        serializer_user = UserSerializer(user_obj, context={"user" : user})
        user_panel_list = [panel for panel in serializer_user.panels_names(user_obj)]
        has_common = LocusGenotypeDiseaseSerializer(lgd_obj).check_user_permission(lgd_obj, user_panel_list)
        if has_common is False:
            return Response({"error": f"No permission to update record '{stable_id}'"}, status=status.HTTP_403_FORBIDDEN)

        # Get entries to be deleted
        # Different rows mean the lgd-variant type description is associated with multiple publications
        # We have to delete all rows
        try:
            LGDVariantTypeDescription.objects.filter(lgd=lgd_obj, description=var_desc, is_deleted=0).update(is_deleted=1)
        except:
            return Response(
                {"error": f"Could not delete variant type description '{var_desc}' for ID '{stable_id}'"},
                status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response(
                {"message": f"Variant type description '{var_desc}' successfully deleted for ID '{stable_id}'"},
                status=status.HTTP_200_OK)

@extend_schema(exclude=True)
class LGDEditComment(CustomPermissionAPIView):
    """
        Add or delete a comment to a G2P record (LGD).
    """
    http_method_names = ['post', 'patch', 'options']
    serializer_class = LGDCommentSerializer

    # Define specific permissions
    method_permissions = {
        "post": [permissions.IsAuthenticated],
        "patch": [permissions.IsAuthenticated, IsSuperUser]
    }

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
        lgd = get_object_or_404(LocusGenotypeDisease, stable_id__stable_id=stable_id, is_deleted=0)

        # Check if user can edit this LGD entry
        lgd_serializer = LocusGenotypeDiseaseSerializer(lgd)
        lgd_panels = lgd_serializer.get_panels(lgd)
        # Example of lgd_panels:
        # [{'name': 'DD', 'description': 'Developmental disorders'}, {'name': 'Eye', 'description': 'Eye disorders'}]
        user_obj = get_object_or_404(User, email=user, is_active=1)
        user_serializer = UserSerializer(user_obj, context={"user": user})

        if not user_serializer.check_panel_permission(lgd_panels):
            return Response({"error": f"No permission to edit {stable_id}"}, status=status.HTTP_403_FORBIDDEN)

        # LGDCommentListSerializer accepts a list of comments
        serializer_list = LGDCommentListSerializer(data=request.data)

        if serializer_list.is_valid():
            lgd_comments_data = serializer_list.validated_data.get("comments")

            if not lgd_comments_data:
                return Response(
                    {"error": "Empty comment. Please provide valid data."},
                     status=status.HTTP_400_BAD_REQUEST
                )

            errors = []
            # Add each comment from the input list
            for comment in lgd_comments_data:
                serializer_class = LGDCommentSerializer(
                    data=comment,
                    context={"lgd": lgd, "user": user_obj}
                )

                if serializer_class.is_valid():
                    try:
                        serializer_class.save()
                    except IntegrityError as e:
                        return Response(
                            {"error": f"A database integrity error occurred: {str(e)}"},
                            status=status.HTTP_400_BAD_REQUEST
                        )
                else:
                    errors.append(serializer_class.errors)

            if errors:
                return Response(
                    {"error": errors},
                    status=status.HTTP_400_BAD_REQUEST
                )

            response = Response(
                {"message": f"Comments added to the G2P entry successfully."},
                status=status.HTTP_201_CREATED
            )

        else:
            response = Response(
                {"error": serializer_list.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        return response

    @transaction.atomic
    def patch(self, request, stable_id):
        """
            This method deletes the LGD-comment.

            Example: { "comment": "This is a comment" }
        """
        comment = request.data.get('comment')
        user = request.user

        lgd_obj = get_object_or_404(LocusGenotypeDisease, stable_id__stable_id=stable_id, is_deleted=0)

        # Check if user has permission to update panel
        user_obj = get_object_or_404(User, email=user, is_active=1)
        serializer_user = UserSerializer(user_obj, context={"user" : user})
        user_panel_list = [panel for panel in serializer_user.panels_names(user_obj)]
        has_common = LocusGenotypeDiseaseSerializer(lgd_obj).check_user_permission(lgd_obj, user_panel_list)
        if has_common is False:
            return Response(
                {"error": f"No permission to update record '{stable_id}'"},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            LGDComment.objects.filter(lgd=lgd_obj, comment=comment, is_deleted=0).update(is_deleted=1)
        except:
            return Response(
                {"error": f"Cannot delete comment for ID '{stable_id}'"},
                status=status.HTTP_400_BAD_REQUEST
            )
        else:
            return Response(
                {"message": f"Comment successfully deleted for ID '{stable_id}'"},
                status=status.HTTP_200_OK
            )

@extend_schema(exclude=True)
class LocusGenotypeDiseaseDelete(APIView):
    """
        Delete a LGD record
    """
    http_method_names = ['patch', 'options']
    serializer_class = LocusGenotypeDiseaseSerializer
    permission_classes = [permissions.IsAuthenticated, IsSuperUser]

    @transaction.atomic
    def patch(self, request, stable_id):
        """
            This method deletes the LGD record.
            The deletion does not remove the entry from the database, instead
            it sets the flag 'is_deleted' to 1.
        """
        user = request.user

        stable_id_obj = get_object_or_404(G2PStableID, stable_id=stable_id, is_deleted=0)
        lgd_obj = get_object_or_404(LocusGenotypeDisease, stable_id=stable_id_obj, is_deleted=0)

        # Check if user has permission to update panel
        user_obj = get_object_or_404(User, email=user, is_active=1)
        serializer_user = UserSerializer(user_obj, context={"user" : user})
        user_panel_list = [panel for panel in serializer_user.panels_names(user_obj)]
        has_common = LocusGenotypeDiseaseSerializer(lgd_obj).check_user_permission(lgd_obj, user_panel_list)
        if has_common is False:
            return Response(
                {"error": f"No permission to update record '{stable_id}'"},
                status=status.HTTP_403_FORBIDDEN
            )

        # Delete the LGD record
        lgd_obj.is_deleted = 1
        lgd_obj.save()

        # Delete the stable id used by the LGD record
        stable_id_obj.is_deleted = 1
        stable_id_obj.is_live = 0
        stable_id_obj.save()

        # Delete lgd-cross cutting modifiers
        LGDCrossCuttingModifier.objects.filter(lgd=lgd_obj, is_deleted=0).update(is_deleted=1)
 
        # Delete comments
        LGDComment.objects.filter(lgd=lgd_obj, is_deleted=0).update(is_deleted=1)

        # Delete lgd-panels
        LGDPanel.objects.filter(lgd=lgd_obj, is_deleted=0).update(is_deleted=1)

        # Delete phenotypes
        LGDPhenotype.objects.filter(lgd=lgd_obj, is_deleted=0).update(is_deleted=1)

        # Delete phenotype summary
        LGDPhenotypeSummary.objects.filter(lgd=lgd_obj, is_deleted=0).update(is_deleted=1)

        # Delete variant types + comments
        lgd_var_type_set = LGDVariantType.objects.filter(lgd=lgd_obj, is_deleted=0)

        for lgd_var_type_obj in lgd_var_type_set:
            # Check if the lgd-variant type has comments
            # If so, delete the comments too
            LGDVariantTypeComment.objects.filter(lgd_variant_type=lgd_var_type_obj, is_deleted=0).update(is_deleted=1)
            lgd_var_type_obj.is_deleted = 1
            lgd_var_type_obj.save()

        # Delete variant type description
        LGDVariantTypeDescription.objects.filter(lgd=lgd_obj, is_deleted=0).update(is_deleted=1)

        # Delete variant consequences
        LGDVariantGenccConsequence.objects.filter(lgd=lgd_obj, is_deleted=0).update(is_deleted=1)

        # Delete mechanism synopsis + evidence
        LGDMolecularMechanismSynopsis.objects.filter(lgd=lgd_obj, is_deleted=0).update(is_deleted=1)
        LGDMolecularMechanismEvidence.objects.filter(lgd=lgd_obj, is_deleted=0).update(is_deleted=1)

        # Delete publications
        LGDPublication.objects.filter(lgd=lgd_obj, is_deleted=0).update(is_deleted=1)

        return Response(
            {"message": f"ID '{stable_id}' successfully deleted"},
            status=status.HTTP_200_OK
        )