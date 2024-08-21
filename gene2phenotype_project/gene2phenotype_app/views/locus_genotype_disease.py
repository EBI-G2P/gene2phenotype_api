from rest_framework import generics, status, permissions
from rest_framework.response import Response
from django.http import Http404
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.db import transaction


from gene2phenotype_app.serializers import (UserSerializer, LocusGenotypeDiseaseSerializer,
                                            LGDPanelSerializer, LGDCrossCuttingModifierSerializer,
                                            LGDCommentSerializer, LGDVariantConsequenceListSerializer,
                                            LGDVariantGenCCConsequenceSerializer, LGDCrossCuttingModifierListSerializer,
                                            LGDVariantTypeListSerializer, LGDVariantTypeSerializer,
                                            LGDVariantTypeDescriptionListSerializer, LGDVariantTypeDescriptionSerializer)

from gene2phenotype_app.models import (User, Attrib, LocusGenotypeDisease, OntologyTerm,
                                       G2PStableID, CVMolecularMechanism, LGDCrossCuttingModifier, 
                                       LGDVariantGenccConsequence, LGDVariantType, LGDVariantTypeComment,
                                       LGDVariantTypeDescription)

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

class LocusGenotypeDiseaseDetail(BaseView):
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
            self.handle_no_permission('Entry', stable_id)
        else:
            return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset().first()
        serializer = LocusGenotypeDiseaseSerializer(queryset, context={'user': self.request.user})
        return Response(serializer.data)


### Update data ###
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

### Add data ###
class LocusGenotypeDiseaseAddPanel(BaseAdd):
    """
        Add panel to an existing G2P record (LGD).
        A single record can be linked to more than one panel.
    """
    serializer_class = LGDPanelSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    @transaction.atomic
    def post(self, request, stable_id):
        """
            The post method links the current LGD record to the panel.
            We want to whole process to be done in one db transaction.
        """
        user = self.request.user

        if not user.is_authenticated:
            return Response({"message": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)

        # Check if user can update panel
        user_obj = get_object_or_404(User, email=user)
        serializer = UserSerializer(user_obj, context={"user" : user})
        user_panel_list_lower = [panel.lower() for panel in serializer.panels_names(user_obj)]

        panel_name_input = request.data.get("name", None)

        if panel_name_input is None:
            return Response({"message": f"Please enter a panel name"}, status=status.HTTP_400_BAD_REQUEST)

        if panel_name_input.lower() not in user_panel_list_lower:
            return Response({"message": f"No permission to update panel {panel_name_input}"}, status=status.HTTP_403_FORBIDDEN)

        lgd = get_object_or_404(LocusGenotypeDisease, stable_id__stable_id=stable_id, is_deleted=0)

        serializer_class = LGDPanelSerializer(data={"name": panel_name_input}, context={"lgd": lgd})

        if serializer_class.is_valid():
            serializer_class.save()
            response = Response({"message": "Panel added to the G2P entry successfully."}, status=status.HTTP_200_OK)
        else:
            response = Response({"errors": serializer_class.errors}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return response

class LocusGenotypeDiseaseAddComment(BaseAdd):
    """
        Add a comment to a G2P record (LGD).
    """
    serializer_class = LGDCommentSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    @transaction.atomic
    def post(self, request, stable_id):
        """
            The post method links the current LGD record to the new comment.
            We want to whole process to be done in one db transaction.
        """
        user = self.request.user

        if not user.is_authenticated:
            return Response({"message": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)

        # Check if G2P ID exists
        lgd = get_object_or_404(LocusGenotypeDisease, stable_id__stable_id=stable_id, is_deleted=0)

        # Check if user can edit this LGD entry
        permission = 0
        lgd_serializer = LocusGenotypeDiseaseSerializer(lgd)
        lgd_panels = lgd_serializer.get_panels(lgd)
        # Example of lgd_panels:
        # [{'name': 'DD', 'description': 'Developmental disorders'}, {'name': 'Eye', 'description': 'Eye disorders'}]
        user_obj = get_object_or_404(User, email=user)
        user_serializer = UserSerializer(user_obj, context={"user": user})
        for panel_name in lgd_panels:
            if user_serializer.check_panel_permission(panel_name["name"]):
                permission = 1

        if(not permission):
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

class LGDAddVariantConsequences(BaseAdd):
    """
        Add a list of variant GenCC consequences to an existing G2P record (LGD).
    """

    serializer_class = LGDVariantConsequenceListSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

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

class LGDAddVariantTypes(BaseAdd):
    """
        Add a list of variant types to an existing G2P record (LGD).
    """

    serializer_class = LGDVariantTypeListSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

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

class LocusGenotypeDiseaseAddCCM(BaseAdd):
    """
        Add a list of cross cutting modifiers to an existing G2P record (LGD).
    """

    serializer_class = LGDCrossCuttingModifierListSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

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

class LGDAddVariantTypeDescriptions(BaseAdd):
    """
        Add a list of variant description (HGVS) to an existing G2P record (LGD).
    """

    serializer_class = LGDVariantTypeDescriptionListSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

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

### Delete data ###
class LGDDeleteCCM(BaseUpdate):
    """
        Delete a cross cutting modifier associated with the LGD.
        The deletion does not remove the entry from the database, instead
        it sets the flag 'is_deleted' to 1.
    """

    http_method_names = ['put', 'options']
    serializer_class = LGDCrossCuttingModifierSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
            Fetch the list of LGD-cross cutting modifiers
        """
        stable_id = self.kwargs['stable_id']
        ccm = self.kwargs['ccm']
        user = self.request.user # TODO check if user has permission

        lgd_obj = get_object_or_404(LocusGenotypeDisease, stable_id__stable_id=stable_id, is_deleted=0)

        try:
            ccm_obj = Attrib.objects.get(
                value = ccm,
                type__code = 'cross_cutting_modifier'
            )
        except Attrib.DoesNotExist:
            raise Http404(f"Invalid cross cutting modifier '{ccm}'")

        queryset = LGDCrossCuttingModifier.objects.filter(lgd=lgd_obj, ccm=ccm_obj, is_deleted=0)

        if not queryset.exists():
            self.handle_no_permission(ccm, stable_id)
        else:
            return queryset

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        """
            This method deletes the LGD-cross cutting modifier.
        """
        stable_id = self.kwargs['stable_id']
        ccm = self.kwargs['ccm']

        # Get G2P entry to be updated
        lgd_ccm_obj = self.get_queryset().first()

        lgd_ccm_obj.is_deleted = 1

        try:
            lgd_ccm_obj.save()
        except:
            return Response({"errors": f"Could not delete cross cutting modifier '{ccm}' for ID '{stable_id}'"}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
                {"message": f"Cross cutting modifier '{ccm}' successfully deleted for ID '{stable_id}'"},
                 status=status.HTTP_200_OK)

class LGDDeleteVariantConsequence(BaseUpdate):
    """
        Delete a variant GenCC consequence associated with the LGD.
        The deletion does not remove the entry from the database, instead
        it sets the flag 'is_deleted' to 1.
    """

    http_method_names = ['put', 'options']
    serializer_class = LGDVariantGenCCConsequenceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
            Fetch the list of LGD-variant GenCC consequences
        """
        stable_id = self.kwargs['stable_id']
        consequence = self.kwargs['consequence'].replace("_", " ")
        user = self.request.user # TODO check if user has permission

        lgd_obj = get_object_or_404(LocusGenotypeDisease, stable_id__stable_id=stable_id, is_deleted=0)

        # Get variant gencc consequence value from ontology_term
        try:
            consequence_obj = OntologyTerm.objects.get(
                term = consequence,
                group_type__value = "variant_type"
            )
        except OntologyTerm.DoesNotExist:
            raise Http404(f"Invalid variant consequence '{consequence}'")

        queryset = LGDVariantGenccConsequence.objects.filter(lgd=lgd_obj, variant_consequence=consequence_obj, is_deleted=0)

        if not queryset.exists():
            self.handle_no_permission(consequence, stable_id)
        else:
            return queryset

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        """
            This method deletes the LGD-variant gencc consequence.
        """
        stable_id = self.kwargs['stable_id']
        consequence = self.kwargs['consequence']

        # Get G2P entry to be updated
        lgd_consequence_obj = self.get_queryset().first()

        lgd_consequence_obj.is_deleted = 1

        try:
            lgd_consequence_obj.save()
        except:
            return Response({"errors": f"Could not delete variant GenCC consequence '{consequence}' for ID '{stable_id}'"}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
                {"message": f"Variant GenCC consequence '{consequence}' successfully deleted for ID '{stable_id}'"},
                 status=status.HTTP_200_OK)

class LGDDeleteVariantType(BaseUpdate):
    """
        Delete a variant type associated with the LGD.
        The deletion does not remove the entry from the database, instead
        it sets the flag 'is_deleted' to 1.
    """

    http_method_names = ['put', 'options']
    serializer_class = LGDVariantTypeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
            Fetch the list of LGD-variant types
        """
        stable_id = self.kwargs['stable_id']
        variant_type = self.kwargs['type']
        user = self.request.user # TODO check if user has permission

        lgd_obj = get_object_or_404(LocusGenotypeDisease, stable_id__stable_id=stable_id, is_deleted=0)

        # Get variant type value from ontology_term
        try:
            var_type_obj = OntologyTerm.objects.get(
                term = variant_type,
                group_type__value = "variant_type"
            )
        except OntologyTerm.DoesNotExist:
            raise Http404(f"Invalid variant type '{variant_type}'")

        queryset = LGDVariantType.objects.filter(lgd=lgd_obj, variant_type_ot=var_type_obj, is_deleted=0)

        if not queryset.exists():
            self.handle_no_permission(variant_type, stable_id)
        else:
            return queryset

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        """
            This method deletes the LGD-variant type
        """
        stable_id = self.kwargs['stable_id']
        variant_type = self.kwargs['type']

        # Get G2P entries to be deleted
        # Different rows mean the lgd-variant type is associated with multiple publications
        # We have to delete all rows
        lgd_var_type_set = self.get_queryset()

        for lgd_var_type_obj in lgd_var_type_set:
            # Check if the lgd-variant type has comments
            # If so, delete the comments too
            comments_set = LGDVariantTypeComment.objects.filter(lgd_variant_type=lgd_var_type_obj, is_deleted=0)

            if comments_set.exists():
                for comment in comments_set:
                    comment.is_deleted = 1
                    comment.save()

            lgd_var_type_obj.is_deleted = 1

            try:
                lgd_var_type_obj.save()
            except:
                return Response({"errors": f"Could not delete variant type '{variant_type}' for ID '{stable_id}'"}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
                {"message": f"Variant type '{variant_type}' successfully deleted for ID '{stable_id}'"},
                status=status.HTTP_200_OK)

class LGDDeleteVariantTypeDesc(BaseUpdate):
    """
        Delete a variant type description associated with the LGD.
        The deletion does not remove the entry from the database, instead
        it sets the flag 'is_deleted' to 1.
    """

    http_method_names = ['put', 'options']
    serializer_class = LGDVariantTypeDescriptionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
            Fetch the list of LGD-variant type descriptions
        """
        stable_id = self.kwargs['stable_id']
        var_desc = self.kwargs['var_desc']
        user = self.request.user # TODO check if user has permission

        lgd_obj = get_object_or_404(LocusGenotypeDisease, stable_id__stable_id=stable_id, is_deleted=0)

        queryset = LGDVariantTypeDescription.objects.filter(lgd=lgd_obj, description=var_desc, is_deleted=0)

        if not queryset.exists():
            self.handle_no_permission(var_desc, stable_id)
        else:
            return queryset

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        """
            This method deletes the LGD-variant type descriptions
        """
        stable_id = self.kwargs['stable_id']
        var_desc = self.kwargs['var_desc']

        # Get G2P entries to be deleted
        # Different rows mean the lgd-variant type description is associated with multiple publications
        # We have to delete all rows
        lgd_var_desc_set = self.get_queryset()

        for lgd_var_desc_obj in lgd_var_desc_set:
            lgd_var_desc_obj.is_deleted = 1

            try:
                lgd_var_desc_obj.save()
            except:
                return Response({"errors": f"Could not delete variant type description '{var_desc}' for ID '{stable_id}'"}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
                {"message": f"Variant type description '{var_desc}' successfully deleted for ID '{stable_id}'"},
                status=status.HTTP_200_OK)
