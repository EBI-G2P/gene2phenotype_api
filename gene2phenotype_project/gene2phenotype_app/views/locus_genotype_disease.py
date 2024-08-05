from rest_framework import generics, status, permissions
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import permission_classes
from rest_framework.response import Response
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.views.decorators.http import require_http_methods


from gene2phenotype_app.serializers import (UserSerializer, LGDPublicationSerializer,
                                            LocusGenotypeDiseaseSerializer,
                                            LGDPanelSerializer, LGDPublicationListSerializer,
                                            LGDPhenotypeListSerializer, LGDPhenotypeSerializer,
                                            LGDCommentSerializer, LGDVariantConsequenceListSerializer,
                                            LGDVariantGenCCConsequenceSerializer)

from gene2phenotype_app.models import (User, Attrib,
                                       LocusGenotypeDisease, OntologyTerm,
                                       G2PStableID, CVMolecularMechanism)

from .base import BaseView, BaseAdd


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


### Add data
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
        serializer = UserSerializer(user_obj, context={'user' : user})
        user_panel_list_lower = [panel.lower() for panel in serializer.panels_names(user_obj)]

        panel_name_input = request.data.get('name', None)

        if panel_name_input is None:
            return Response({"message": f"Please enter a panel name"}, status=status.HTTP_400_BAD_REQUEST)

        if panel_name_input.lower() not in user_panel_list_lower:
            return Response({"message": f"No permission to update panel {panel_name_input}"}, status=status.HTTP_403_FORBIDDEN)

        lgd = get_object_or_404(LocusGenotypeDisease, stable_id__stable_id=stable_id, is_deleted=0)

        serializer_class = LGDPanelSerializer(data={"name": panel_name_input}, context={'lgd': lgd})

        if serializer_class.is_valid():
            serializer_class.save()
            response = Response({'message': 'Panel added to the G2P entry successfully.'}, status=status.HTTP_200_OK)
        else:
            response = Response({"message": "Error adding a panel", "details": serializer_class.errors}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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
            response = Response({"message": "Error adding the comment", "details": serializer_class.errors}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return response

class LocusGenotypeDiseaseAddPublications(BaseAdd):
    """
        Add a list of publications to an existing G2P record (LGD).
        When adding a publication it can also add:
            - comment
            - family info as reported in the publication
    """

    serializer_class = LGDPublicationListSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    @transaction.atomic
    def post(self, request, stable_id):
        """
            The post method creates an association between the current LGD record and a list of publications.
            We want to whole process to be done in one db transaction.

            Args:
                (dict) request
                
                Example:
                { "publications":[
                    {
                    "publication": { "pmid": 1234 },
                    "comment": { "comment": "this is a comment", "is_public": 1 },
                    "families": { "families": 2, "consanguinity": "unknown", "ancestries": "african", "affected_individuals": 1 }
                    }
                    ]
                }
        """

        user = self.request.user

        if not user.is_authenticated:
            return Response({"message": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)

        lgd = get_object_or_404(LocusGenotypeDisease, stable_id__stable_id=stable_id, is_deleted=0)

        # LGDPublicationListSerializer accepts a list of publications
        serializer_list = LGDPublicationListSerializer(data=request.data)

        if serializer_list.is_valid():
            publications_data = serializer_list.validated_data.get('publications')

            for publication in publications_data:
                # the comment and family info are inputted in the context
                comment = None
                families = None

                # get extra data: comments, families
                # "comment": {"comment": "comment text", "is_public": 1},
                # "families": {
                #               "families": 5, 
                #               "consanguinity": "", 
                #               "ancestries": "", 
                #               "affected_individuals": 5
                #              }
                if "comment" in publication:
                    comment = publication.get("comment")

                if "families" in publication:
                    families = publication.get("families")

                serializer_class = LGDPublicationSerializer(
                    data=publication,
                    context={"lgd": lgd, "user": user, "comment": comment, "families": families}
                )

                if serializer_class.is_valid():
                    serializer_class.save()
                    response = Response({'message': 'Publication added to the G2P entry successfully.'}, status=status.HTTP_200_OK)
                else:
                    response = Response({"message": "Error adding publication", "details": serializer_class.errors}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        else:
            response = Response({"message": "Error adding publications", "details": serializer_list.errors}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return response

class LocusGenotypeDiseaseAddPhenotypes(BaseAdd):
    """
        Add a list of phenotypes to an existing G2P record (LGD).
    """

    serializer_class = LGDPhenotypeListSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    @transaction.atomic
    def post(self, request, stable_id):
        """
            The post method creates an association between the current LGD record and a list of phenotypes.
            We want to whole process to be done in one db transaction.

            Args:
                (dict) request
                
                Example:
                    {
                        "phenotypes": [{
                            "accession": "HP:0003974",
                            "publication": 1
                        }]
                    }
        """

        user = self.request.user

        if not user.is_authenticated:
            return Response({"message": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)
        
        lgd = get_object_or_404(LocusGenotypeDisease, stable_id__stable_id=stable_id, is_deleted=0)

        # LGDPhenotypeListSerializer accepts a list of phenotypes
        serializer_list = LGDPhenotypeListSerializer(data=request.data)

        if serializer_list.is_valid():
            phenotypes_data = serializer_list.validated_data.get('phenotypes')

            if(not phenotypes_data):
                response = Response(
                    {"message": "Empty phenotype. Please provide valid data."},
                     status=status.HTTP_400_BAD_REQUEST
                )

            # Add each phenotype from the input list
            for phenotype in phenotypes_data:
                # Format data to be accepted by LGDPhenotypeSerializer
                phenotype_input = phenotype.get("phenotype")
                phenotype_input["publication"] = phenotype.get("publication")["pmid"]

                serializer_class = LGDPhenotypeSerializer(
                    data=phenotype_input,
                    context={"lgd": lgd}
                )

                if serializer_class.is_valid():
                    serializer_class.save()
                    response = Response({"message": "Phenotype added to the G2P entry successfully."}, status=status.HTTP_200_OK)
                else:
                    response = Response({"message": "Error adding phenotype", "details": serializer_class.errors}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        else:
            response = Response({"message": "Error adding phenotypes", "details": serializer_list.errors}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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
                        {"message": "Error adding variant consequence",
                         "details": serializer_class.errors}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )

        else:
            response = Response({"message": "Error adding variant consequences", "details": serializer_list.errors}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return response