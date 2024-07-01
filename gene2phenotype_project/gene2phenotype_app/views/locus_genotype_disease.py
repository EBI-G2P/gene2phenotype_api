from rest_framework import generics, status, permissions
from rest_framework.response import Response
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.db import transaction


from gene2phenotype_app.serializers import (UserSerializer,
                                            LocusGenotypeDiseaseSerializer,
                                            LGDPanelSerializer)

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
        serializer = LocusGenotypeDiseaseSerializer(queryset)
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

        g2p_stable_id = get_object_or_404(G2PStableID, stable_id=stable_id) #using the g2p stable id information to get the lgd 
        lgd = get_object_or_404(LocusGenotypeDisease, stable_id=g2p_stable_id, is_deleted=0)
        serializer_class = LGDPanelSerializer(data={"name": panel_name_input}, context={'lgd': lgd})

        if serializer_class.is_valid():
            serializer_class.save()
            response = Response({'message': 'Panel added to the G2P entry successfully.'}, status=status.HTTP_200_OK)
        else:
            response = Response({"message": "Error adding a panel", "details": serializer_class.errors}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return response
