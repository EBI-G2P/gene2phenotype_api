from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from django.http import Http404
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.db import transaction


from gene2phenotype_app.serializers import (UserSerializer, LocusGenotypeDiseaseSerializer,
                                            LGDCrossCuttingModifierSerializer,
                                            LGDCommentSerializer, LGDVariantConsequenceListSerializer,
                                            LGDVariantGenCCConsequenceSerializer, LGDCrossCuttingModifierListSerializer,
                                            LGDVariantTypeListSerializer, LGDVariantTypeSerializer,
                                            LGDVariantTypeDescriptionListSerializer, LGDVariantTypeDescriptionSerializer)

from gene2phenotype_app.models import (User, Attrib, LocusGenotypeDisease, OntologyTerm,
                                       G2PStableID, CVMolecularMechanism, LGDCrossCuttingModifier, 
                                       LGDVariantGenccConsequence, LGDVariantType, LGDVariantTypeComment,
                                       LGDVariantTypeDescription, LGDPanel, LGDPhenotype, LGDPhenotypeSummary,
                                       LGDMolecularMechanism, LGDMolecularMechanismEvidence, LGDPublication,
                                       LGDComment)

from .base import BaseView, BaseAdd, BaseUpdate


class ListMolecularMechanisms(generics.ListAPIView):
    """
        Display the molecular mechanisms terms by type and subtype (if applicable).
        Only type 'evidence' has a defined subtype.

        Returns:
            Returns:
                (dict) response: list of molecular mechanisms by type and subtype.
    """

    queryset = CVMolecularMechanism.objects.all().values('type', 'subtype', 'value').order_by('type')

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        result = {}
        for mechanism in queryset:
            mechanismtype = mechanism["type"]
            subtype = mechanism["subtype"]
            value = mechanism["value"]

            if mechanismtype not in result:
                result[mechanismtype] = {}
                # evidence has subtypes
                if mechanismtype == "evidence":
                    result[mechanismtype][subtype] = [value]
                else:
                    result[mechanismtype] = [value]
            else:
                if mechanismtype == "evidence":
                    if subtype not in result[mechanismtype]:
                        result[mechanismtype][subtype] = [value]
                    else:
                        result[mechanismtype][subtype].append(value)
                else:
                    result[mechanismtype].append(value)

        return Response(result)

class VariantTypesList(generics.ListAPIView):
    """
        Display all variant types by group.

        Returns:
            Returns:
                (dict) response: variant types by group
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
        return Response({'NMD_variants': list_nmd,
                         'splice_variants': list_splice,
                         'regulatory_variants': list_regulatory,
                         'protein_changing_variants': list_protein,
                         'other_variants': list})

class LocusGenotypeDiseaseDetail(generics.ListAPIView):
    """
        Display all data for a specific G2P stable ID.

        Args:
            (string) stable_id

        Returns:
                Response containing the LocusGenotypeDisease object
                    - locus
                    - stable_id
                    - genotype
                    - disease
                    - molecular_mechanism
                    - phenotypes
                    - publications
                    - etc
    """

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
            raise Http404(f"No matching Entry found for: {stable_id}")
        else:
            return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset().first()
        serializer = LocusGenotypeDiseaseSerializer(queryset, context={'user': self.request.user})
        return Response(serializer.data)


### Add or delete data ###
class LGDUpdateConfidence(generics.UpdateAPIView):
    http_method_names = ['put', 'options']
    serializer_class = LocusGenotypeDiseaseSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        stable_id = self.kwargs['stable_id']
        user = self.request.user

        g2p_stable_id = get_object_or_404(G2PStableID, stable_id=stable_id)
        # Get the entry for this user
        queryset = LocusGenotypeDisease.objects.filter(stable_id=g2p_stable_id)

        if not queryset.exists():
            self.handle_no_permission('Entry', stable_id)
        else:
            return queryset

    def update(self, request, *args, **kwargs):
        """
            This method updates the LGD confidence.

            Input example:
                    {
                        'confidence': 'definitive',
                        'confidence_support': '',
                        'is_reviewed': None
                    }

            Raises:
                Invalid confidence value
                G2P record already has same confidence value
        """
        user = self.request.user

        # Get G2P entry to be updated
        lgd_obj = self.get_queryset().first()

        # Update data - it replaces the data
        serializer = LocusGenotypeDiseaseSerializer(
            lgd_obj,
            data=request.data,
            context={'user': user}
        )

        if serializer.is_valid():
            instance = serializer.save()
            return Response(
                {"message": f"Data updated successfully for '{instance.stable_id.stable_id}'"},
                 status=status.HTTP_200_OK)

        else:
            return Response({"errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

class LGDEditVariantConsequences(APIView):
    """
        Add or delete lgd-variant consequence(s).

        Add data (action: POST)
            Add a list of variant GenCC consequences to an existing G2P record (LGD).

        Delete data (action: UPDATE)
            Delete a variant GenCC consequence associated with the LGD.
            The deletion does not remove the entry from the database, instead
            it sets the flag 'is_deleted' to 1.
    """
    http_method_names = ['post', 'update', 'options']
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_serializer_class(self, action):
        """
            Returns the appropriate serializer class based on the action.
            To add data use LGDVariantConsequenceListSerializer: it accepts a list of consequences.
            To delete data use LGDVariantGenCCConsequenceSerializer: it accepts one consequence.
        """
        action = action.lower()

        if action == "post":
            return LGDVariantConsequenceListSerializer
        elif action == "update":
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

        user = self.request.user
        if not user.is_authenticated:
            return Response({"message": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)

        lgd = get_object_or_404(LocusGenotypeDisease, stable_id__stable_id=stable_id, is_deleted=0)

        # LGDVariantConsequenceListSerializer accepts a list of variant consequences
        serializer_list = LGDVariantConsequenceListSerializer(data=request.data)

        if serializer_list.is_valid():
            variant_consequence_data = serializer_list.validated_data.get('variant_consequences')

            # Check if list of consequences is empty
            if(not variant_consequence_data):
                response = Response(
                    {"message": "Empty variant consequence. Please provide valid data."},
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
                        status=status.HTTP_200_OK
                    )
                else:
                    response = Response(
                        {"errors": serializer_class.errors}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )

        else:
            response = Response(
                {"errors": serializer_list.errors}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return response

    @transaction.atomic
    def update(self, request, stable_id):
        """
            This method deletes the LGD-variant gencc consequence.

            Example: {"variant_consequence": "altered_gene_product_level"}
        """
        # Check if input has the expected value
        if "variant_consequence" not in request.data or request.data.get('variant_consequence') == "":
            return Response(
                {"errors": f"Empty variant consequence. Please provide the 'variant_consequence'."},
                status=status.HTTP_400_BAD_REQUEST
            )

        consequence = request.data.get('variant_consequence')
        user = self.request.user # TODO check if user has permission

        if consequence is None:
            return Response(
                {"errors": f"Empty variant consequence"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        consequence = consequence.replace("_", " ")

        # Fecth G2P record to update
        lgd_obj = get_object_or_404(LocusGenotypeDisease, stable_id__stable_id=stable_id, is_deleted=0)

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
                {"errors": f"Could not delete variant consequence '{consequence}' for ID '{stable_id}'"},
                status=status.HTTP_400_BAD_REQUEST
            )
        else:
            return Response(
                {"message": f"Variant consequence '{consequence}' successfully deleted for ID '{stable_id}'"},
                status=status.HTTP_200_OK)

class LGDEditCCM(APIView):
    """
        Add or delete LGD-cross cutting modifier(s).

        Add data (action: POST)
            Add a list of cross cutting modifiers to an existing G2P record (LGD).

        Delete data (action: UPDATE)
            Delete a cross cutting modifier associated with the LGD.
            The deletion does not remove the entry from the database, instead
            it sets the flag 'is_deleted' to 1.
    """
    http_method_names = ['post', 'update', 'options']
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_serializer_class(self, action):
        """
            Returns the appropriate serializer class based on the action.
            To add data use LGDCrossCuttingModifierListSerializer: it accepts a list of ccm.
            To delete data use LGDCrossCuttingModifierSerializer: it accepts one ccm.
        """
        action = action.lower()

        if action == "post":
            return LGDCrossCuttingModifierListSerializer
        elif action == "update":
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
        user = self.request.user
        if not user.is_authenticated:
            return Response({"message": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)

        lgd = get_object_or_404(LocusGenotypeDisease, stable_id__stable_id=stable_id, is_deleted=0)

        # LGDCrossCuttingModifierListSerializer accepts a list of cross cutting modifiers
        serializer_list = LGDCrossCuttingModifierListSerializer(data=request.data)

        if serializer_list.is_valid():
            ccm_data = serializer_list.validated_data.get('cross_cutting_modifiers')

            # Check if list of consequences is empty
            if(not ccm_data):
                response = Response(
                    {"message": "Empty cross cutting modifier. Please provide valid data."},
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
                        status=status.HTTP_200_OK
                    )
                else:
                    response = Response(
                        {"errors": serializer_class.errors}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )

        else:
            response = Response(
                {"errors": serializer_list.errors}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return response

    @transaction.atomic
    def update(self, request, stable_id):
        """
            This method deletes the LGD-cross cutting modifier.
            Example:
                    { "term": "typically mosaic" }
        """
        if "term" not in request.data or request.data.get('term') == "":
            return Response({"errors": f"Empty cross cutting modifier. Please provide the 'term'."}, status=status.HTTP_400_BAD_REQUEST)

        ccm_tmp = request.data.get('term')
        ccm = ccm_tmp.replace("_", " ")
        user = request.user # TODO check if user has permission

        lgd_obj = get_object_or_404(LocusGenotypeDisease, stable_id__stable_id=stable_id, is_deleted=0)

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
                {"errors": f"Could not delete cross cutting modifier '{ccm}' for ID '{stable_id}'"},
                status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response(
                {"message": f"Cross cutting modifier '{ccm}' successfully deleted for ID '{stable_id}'"},
                 status=status.HTTP_200_OK)

class LGDEditVariantTypes(APIView):
    """
        Add or delete LGD-variant type(s).

        Add data (action: POST)
            Add a list of variant types to an existing G2P record (LGD).

        Delete data (action: UPDATE)
            Delete a variant type associated with the LGD.
            The deletion does not remove the entry from the database, instead
            it sets the flag 'is_deleted' to 1.
    """
    http_method_names = ['post', 'update', 'options']
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_serializer_class(self, action):
        """
            Returns the appropriate serializer class based on the action.
            To add data use LGDVariantTypeListSerializer: it accepts a list of variant types.
            To delete data use LGDVariantTypeSerializer: it accepts one variant type.
        """
        action = action.lower()

        if action == "post":
            return LGDVariantTypeListSerializer
        elif action == "update":
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
        if not user.is_authenticated:
            return Response({"message": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)

        # Get user object
        user_obj = User.objects.get(email=user, is_active=1)

        lgd = get_object_or_404(LocusGenotypeDisease, stable_id__stable_id=stable_id, is_deleted=0)

        # LGDVariantTypeListSerializer accepts a list of variant types
        serializer_list = LGDVariantTypeListSerializer(data=request.data)

        if serializer_list.is_valid():
            variant_type_data = serializer_list.validated_data.get('variant_types')

            # Check if list of variants is empty
            if(not variant_type_data):
                response = Response(
                    {"message": "Empty variant type. Please provide valid data."},
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
                        status=status.HTTP_200_OK
                    )
                else:
                    response = Response(
                        {"errors": serializer_class.errors}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )

        else:
            response = Response(
                {"errors": serializer_list.errors}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return response

    @transaction.atomic
    def update(self, request, stable_id):
        """
            This method deletes the LGD-variant type.

            Example: { "secondary_type": "stop_gained" }
        """
        # Check if the input has the expected data
        if "secondary_type" not in request.data or request.data.get('secondary_type') == "":
            return Response({"errors": f"Empty variant type. Please provide the 'secondary_type'."}, status=status.HTTP_400_BAD_REQUEST)

        variant_type = request.data.get('secondary_type')
        user = request.user # TODO check if user has permission

        lgd_obj = get_object_or_404(LocusGenotypeDisease, stable_id__stable_id=stable_id, is_deleted=0)

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
            return Response({"errors": f"Could not find variant type '{variant_type}' for ID '{stable_id}'"},
                            status=status.HTTP_404_NOT_FOUND)

        for lgd_var_type_obj in lgd_var_type_set:
            # Check if the lgd-variant type has comments
            # If so, delete the comments too
            LGDVariantTypeComment.objects.filter(lgd_variant_type=lgd_var_type_obj, is_deleted=0).update(is_deleted=1)
            lgd_var_type_obj.is_deleted = 1

            try:
                lgd_var_type_obj.save()
            except:
                return Response({"errors": f"Could not delete variant type '{variant_type}' for ID '{stable_id}'"}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
                {"message": f"Variant type '{variant_type}' successfully deleted for ID '{stable_id}'"},
                status=status.HTTP_200_OK)

class LGDEditVariantTypeDescriptions(APIView):
    """
        Add or delete LGD-variant type(s)

        Add data (action: POST)
            Add a list of variant description (HGVS) to an existing G2P record (LGD).

        Delete data (action: UPDATE)
            Delete a variant type description associated with the LGD.
            The deletion does not remove the entry from the database, instead
            it sets the flag 'is_deleted' to 1.
    """
    http_method_names = ['post', 'update', 'options']
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_serializer_class(self, action):
        """
            Returns the appropriate serializer class based on the action.
            To add data use LGDVariantTypeDescriptionListSerializer: it accepts a list of variant type descriptions.
            To delete data use LGDVariantTypeDescriptionSerializer: it accepts one variant type description.
        """
        action = action.lower()

        if action == "post":
            return LGDVariantTypeDescriptionListSerializer
        elif action == "update":
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
        if not user.is_authenticated:
            return Response({"message": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)

        lgd = get_object_or_404(LocusGenotypeDisease, stable_id__stable_id=stable_id, is_deleted=0)

        # LGDVariantTypeDescriptionListSerializer accepts a list of HGVS
        serializer_list = LGDVariantTypeDescriptionListSerializer(data=request.data)

        if serializer_list.is_valid():
            descriptions_data = serializer_list.validated_data.get('variant_descriptions')

            # Check if list of consequences is empty
            if(not descriptions_data):
                response = Response(
                    {"message": "Empty variant descriptions. Please provide valid data."},
                     status=status.HTTP_400_BAD_REQUEST
                )

            # Add each cross cutting modifier from the input list
            for description in descriptions_data:
                # The data is created in LGDCrossCuttingModifierSerializer
                # Input the expected data format
                serializer_class = LGDVariantTypeDescriptionSerializer(
                    data=description,
                    context={"lgd": lgd}
                )

                if serializer_class.is_valid():
                    serializer_class.save()
                    response = Response(
                        {"message": "Variant description added to the G2P entry successfully."},
                        status=status.HTTP_200_OK
                    )
                else:
                    response = Response(
                        {"errors": serializer_class.errors}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )

        else:
            response = Response(
                {"errors": serializer_list.errors}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return response

    @transaction.atomic
    def update(self, request, stable_id):
        """
            This method deletes the LGD-variant type descriptions.

            Example: { "description": "NM_000546.6:c.794T>C (p.Leu265Pro)" }
        """
        # Check if the input has the expected data
        if "description" not in request.data or request.data.get('description') == "":
            return Response({"errors": f"Empty variant type description. Please provide the 'description'."}, status=status.HTTP_400_BAD_REQUEST)

        var_desc = request.data.get('description')
        user = request.user # TODO check if user has permission

        lgd_obj = get_object_or_404(LocusGenotypeDisease, stable_id__stable_id=stable_id, is_deleted=0)
        # Get entries to be deleted
        # Different rows mean the lgd-variant type description is associated with multiple publications
        # We have to delete all rows
        try:
            LGDVariantTypeDescription.objects.filter(lgd=lgd_obj, description=var_desc, is_deleted=0).update(is_deleted=1)
        except:
            return Response(
                {"errors": f"Could not delete variant type description '{var_desc}' for ID '{stable_id}'"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            return Response(
                {"message": f"Variant type description '{var_desc}' successfully deleted for ID '{stable_id}'"},
                status=status.HTTP_200_OK)

class LGDEditComment(APIView):
    """
        Add or delete a comment to a G2P record (LGD).

        Example:
                {
                    "comment": "This is a comment",
                    "is_public": 1
                }
    """
    http_method_names = ['post', 'update', 'options']
    serializer_class = LGDCommentSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    @transaction.atomic
    def post(self, request, stable_id):
        """
            The post method adds a comment.
            It links the current LGD record to the new comment.
            We want to whole process to be done in one db transaction.
        """
        user = self.request.user

        if not user.is_authenticated:
            return Response({"message": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)

        # Check if G2P ID exists
        lgd = get_object_or_404(LocusGenotypeDisease, stable_id__stable_id=stable_id, is_deleted=0)

        # Check if user can edit this LGD entry
        lgd_serializer = LocusGenotypeDiseaseSerializer(lgd)
        lgd_panels = lgd_serializer.get_panels(lgd)
        # Example of lgd_panels:
        # [{'name': 'DD', 'description': 'Developmental disorders'}, {'name': 'Eye', 'description': 'Eye disorders'}]
        user_obj = get_object_or_404(User, email=user)
        user_serializer = UserSerializer(user_obj, context={"user": user})

        if not user_serializer.check_panel_permission(lgd_panels):
            return Response({"message": f"No permission to edit {stable_id}"}, status=status.HTTP_403_FORBIDDEN)

        comment = request.data.get("comment", None)
        is_public = request.data.get("is_public", None)

        serializer_class = LGDCommentSerializer(data={"comment": comment, "is_public": is_public},
                                                context={"lgd": lgd, "user": user})

        if serializer_class.is_valid():
            serializer_class.save()
            response = Response({"message": "Comment added to the G2P entry successfully."}, status=status.HTTP_200_OK)
        else:
            response = Response({"errors": serializer_class.errors}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return response

    @transaction.atomic
    def update(self, request, stable_id):
        """
            This method deletes the LGD-comment.

            Example: { "comment": "This is a comment" }
        """
        comment = request.data.get('comment')
        user = request.user # TODO check if user has permission

        lgd_obj = get_object_or_404(LocusGenotypeDisease, stable_id__stable_id=stable_id, is_deleted=0)

        try:
            LGDComment.objects.filter(lgd=lgd_obj, comment=comment, is_deleted=0).update(is_deleted=1)
        except:
            return Response(
                {"message": f"Cannot delete comment for ID '{stable_id}'"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            return Response(
                    {"message": f"Comment successfully deleted for ID '{stable_id}'"},
                    status=status.HTTP_200_OK)

class LocusGenotypeDiseaseDelete(APIView):
    """
        Delete a LGD record
    """
    http_method_names = ['update', 'options']
    serializer_class = LocusGenotypeDiseaseSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    @transaction.atomic
    def update(self, request, stable_id):
        """
            This method deletes the LGD record.
            The deletion does not remove the entry from the database, instead
            it sets the flag 'is_deleted' to 1.
        """
        user = request.user # TODO check if user has permission

        stable_id_obj = get_object_or_404(G2PStableID, stable_id=stable_id, is_deleted=0)
        lgd_obj = get_object_or_404(LocusGenotypeDisease, stable_id=stable_id_obj, is_deleted=0)

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

        # Delete molecular mechanism + evidence (if applicable)
        lgd_mechanism_set = LGDMolecularMechanism.objects.filter(lgd=lgd_obj, is_deleted=0)

        for lgd_mechanism_obj in lgd_mechanism_set:
            LGDMolecularMechanismEvidence.objects.filter(molecular_mechanism=lgd_mechanism_obj, is_deleted=0).update(is_deleted=1)
            lgd_mechanism_obj.is_deleted = 1
            lgd_mechanism_obj.save()

        # Delete publications
        LGDPublication.objects.filter(lgd=lgd_obj, is_deleted=0).update(is_deleted=1)

        return Response(
                {"message": f"ID '{stable_id}' successfully deleted"},
                status=status.HTTP_200_OK)