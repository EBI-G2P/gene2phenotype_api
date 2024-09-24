from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework.views import APIView
from django.http import Http404
from django.db import transaction
from django.shortcuts import get_object_or_404
import re

from gene2phenotype_app.serializers import (PhenotypeOntologyTermSerializer, LGDPhenotypeSerializer,
                                            LGDPhenotypeSummarySerializer, LGDPhenotypeListSerializer)

from gene2phenotype_app.models import (OntologyTerm, LGDPhenotype, LocusGenotypeDisease,
                                       LGDPhenotypeSummary)

from .base import BaseAdd, BaseUpdate

from ..utils import validate_phenotype

"""
    Retrieve phenotypes for a list of HPO IDs.
    The phenotype info is fetched from the HPO API.

    Args:
            (HttpRequest) request: HTTP request
            (str) hpo_list: A comma-separated string of HPO IDs

    Returns:
            Response object includes:
                (list) results: contains phenotype data for each HPO
                                    - accession
                                    - term
                                    - description
                (int) count: number of HPO IDs

    Raises:
            Invalid HPO
"""
@api_view(['GET'])
def PhenotypeDetail(request, hpo_list):
    id_list = hpo_list.split(',')
    data = []
    invalid_hpos = []

    for hpo in id_list:
        # HPO has invalid format
        if not re.match(r'HP\:\d+', hpo):
            invalid_hpos.append(hpo)

        else:
            # HPO has the correct format
            response = validate_phenotype(hpo)

            if not response:
                invalid_hpos.append(hpo)
            else:
                # check if phenotype has a description
                if 'definition' in response:
                    phenotype_description = response['definition']
                else:
                    phenotype_description = None

                data.append({
                    'accession': hpo,
                    'term': response['name'],
                    'description': phenotype_description
                })

    # if any of the HPO IDs is invalid raise error and display all invalid IDs
    if invalid_hpos:
        hpo_list = ", ".join(invalid_hpos)
        response = Response({'detail': f"Invalid HPO term(s): {hpo_list}"}, status=status.HTTP_404_NOT_FOUND)

    else:
        response = Response({'results': data, 'count': len(data)})

    return response


### LGD-phenotype ###
# Add or delete data
class LGDEditPhenotypes(APIView):
    """
        Add or delete lgd-phenotype.

        Add data (action: POST)
            Add a list of phenotypes to an existing G2P record (LGD).

        Delete data (action: UPDATE)
            Delete a phenotype associated with the LGD.
            The deletion does not remove the entry from the database, instead
            it sets the flag 'is_deleted' to 1.
    """
    http_method_names = ['post', 'update', 'options']
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self, action):
        """
            Returns the appropriate serializer class based on the action.
            To add data use LGDPhenotypeListSerializer: it accepts a list of phenotypes.
            To delete data use LGDPhenotypeSerializer: it accepts one phenotype.
        """
        action = action.lower()

        if action == "post":
            return LGDPhenotypeListSerializer
        elif action == "update":
            return LGDPhenotypeSerializer
        else:
            return None

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
                    response = Response({"message": "Phenotype added to the G2P entry successfully."}, status=status.HTTP_201_CREATED)
                else:
                    response = Response({"errors": serializer_class.errors}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        else:
            response = Response({"errors": serializer_list.errors}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return response

    @transaction.atomic
    def update(self, request, stable_id):
        """
            This method deletes the LGD-phenotypes
        """
        accession = request.data.get('accession')
        user = self.request.user # TODO check if user has permission

        lgd_obj = get_object_or_404(LocusGenotypeDisease, stable_id__stable_id=stable_id, is_deleted=0)

        # Fetch phenotype from Ontology Term
        try:
            phenotype_obj = OntologyTerm.objects.get(accession=accession)
        except OntologyTerm.DoesNotExist:
            raise Http404(f"Cannot find phenotype for accession '{accession}'")

        # Fetch LGD-phenotype list
        # Each phenotype can be linked to several publications
        try:
            LGDPhenotype.objects.filter(lgd=lgd_obj, phenotype=phenotype_obj, is_deleted=0).update(is_deleted=1)
        except:
            return Response(
                {"errors": f"Could not delete phenotype '{accession}' for ID '{stable_id}'"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            return Response(
                {"message": f"Phenotype '{accession}' successfully deleted for ID '{stable_id}'"},
                status=status.HTTP_200_OK)

class LGDEditPhenotypeSummary(APIView):
    """
        Add or delete a LGD-phenotype summary

        Add data (action: POST)
            Add a phenotype summary to an existing G2P record (LGD).

        Delete data (action: UPDATE)
            Delete the phenotype summary associated with the LGD.
            The deletion does not remove the entry from the database, instead
            it sets the flag 'is_deleted' to 1.
    """
    http_method_names = ['post', 'update', 'options']
    serializer_class = LGDPhenotypeSummarySerializer
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def post(self, request, stable_id):
        """
            The post method creates an association between the current LGD record and a summary of phenotypes.
            A summary can be linked to one or more publications.

            We want to whole process to be done in one db transaction.

            Args:
                (dict) request:
                                - (string) summary: phenotype summary text
                                - (list) publication: list of pmids

                Example:
                    {
                        "summary": "This is a summary",
                        "publication": [1, 12345]
                    }
        """
        user = self.request.user

        lgd = get_object_or_404(LocusGenotypeDisease, stable_id__stable_id=stable_id, is_deleted=0)

        # LGDPhenotypeSummarySerializer accepts a summary of phenotypes associated with pmids
        serializer = LGDPhenotypeSummarySerializer(data=request.data, context={"lgd": lgd})

        if serializer.is_valid():
            serializer.save()
            response = Response({"message": "Phenotype added to the G2P entry successfully."}, status=status.HTTP_201_CREATED)
        else:
            response = Response({"errors": serializer.errors}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return response

    @transaction.atomic
    def update(self, request, stable_id):
        """
            This method deletes the LGD-phenotype summary
        """
        summary = request.data.get('summary')

        # Get G2P entries to be deleted
        lgd_obj = get_object_or_404(LocusGenotypeDisease, stable_id__stable_id=stable_id, is_deleted=0)

        # Fetch LGD-phenotype summary list
        # Different rows mean the lgd-phenotype summary is associated with multiple publications
        # We have to delete all rows
        try:
            LGDPhenotypeSummary.objects.filter(lgd=lgd_obj, summary=summary, is_deleted=0).update(is_deleted=1)
        except:
            return Response(
                {"errors": f"Could not delete phenotype summary for ID '{stable_id}'"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            return Response(
                {"message": f"Phenotype summary successfully deleted for ID '{stable_id}'"},
                status=status.HTTP_200_OK)

### Add phenotype ###
class AddPhenotype(BaseAdd):
    """
        Add new phenotype.
        The create method is in the PhenotypeSerializer.

        Called by: endpoint add/phenotype/
    """
    serializer_class = PhenotypeOntologyTermSerializer
    permission_classes = [permissions.IsAuthenticated]
