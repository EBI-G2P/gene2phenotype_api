from rest_framework import permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import api_view
from django.db import transaction
from django.shortcuts import get_object_or_404

from gene2phenotype_app.serializers import (PublicationSerializer, LGDPublicationSerializer,
                                            LGDPublicationListSerializer)

from gene2phenotype_app.models import (Publication, LocusGenotypeDisease, LGDPublication,
                                       LGDPhenotype, LGDPhenotypeSummary, LGDVariantType,
                                       LGDVariantTypeDescription, MolecularMechanism,
                                       MolecularMechanismEvidence)

from .base import BaseAdd, BaseUpdate

from ..utils import get_publication, get_authors


"""
    Retrieve publication data for a list of PMIDs.
    If PMID is found in G2P then return details from G2P.
    If PMID not found in G2P then returns info from EuropePMC.

    Args:
            (HttpRequest) request: HTTP request
            (str) pmids: A comma-separated string of PMIDs

    Returns:
            Response object includes:
                (list) results: contains publication data for each publication
                                    - pmid
                                    - title
                                    - authors
                                    - year
                                    - source (possible values: 'G2P', 'EuropePMC')
                (int) count: number of PMIDs
    
    Raises:
            Invalid PMID
"""
@api_view(['GET'])
def PublicationDetail(request, pmids):
    id_list = pmids.split(',')
    data = []
    invalid_pmids = []

    for pmid_str in id_list:
        try:
            pmid = int(pmid_str)

        except:
            invalid_pmids.append(pmid_str)

        else:
            # The PMID has the correct format
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
                    invalid_pmids.append(pmid_str)
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

    # if any of the PMIDs is invalid raise error and display all invalid IDs
    if invalid_pmids:
        pmid_list = ", ".join(invalid_pmids)
        response = Response({'detail': f"Invalid PMID(s): {pmid_list}"}, status=status.HTTP_404_NOT_FOUND)

    else:
        response = Response({'results': data, 'count': len(data)})

    return response


### Add publication ###
class AddPublication(BaseAdd):
    """
        Add new publication.
        The create method is in the PublicationSerializer.
    """
    serializer_class = PublicationSerializer
    permission_classes = [permissions.IsAuthenticated]

### LGD-publication ###
# Add or delete data
class LGDEditPublications(APIView):
    """
        Add or delete lgd-publication.

        Add data (action: POST)
            Add a list of publications to an existing G2P record (LGD).
            When adding a publication it can also add:
                - comment
                - family info as reported in the publication
        
        Delete data (action: UPDATE)
            Delete a publication associated with the LGD.
            The deletion does not remove the entry from the database, instead
            it sets the flag 'is_deleted' to 1.
    """
    http_method_names = ['post', 'update', 'options']
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self, action):
        """
            Returns the appropriate serializer class based on the action.
            To add data use LGDPublicationListSerializer: it accepts a list of publications.
            To delete data use LGDPublicationSerializer: it accepts one publication.
        """
        action = action.lower()

        if action == "post":
            return LGDPublicationListSerializer
        elif action == "update":
            return LGDPublicationSerializer
        else:
            return None

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

        lgd = get_object_or_404(LocusGenotypeDisease, stable_id__stable_id=stable_id, is_deleted=0)

        # LGDPublicationListSerializer accepts a list of publications
        serializer_list = LGDPublicationListSerializer(data=request.data)

        if serializer_list.is_valid():
            publications_data = serializer_list.validated_data.get('publications')

            for publication in publications_data:
                serializer_class = LGDPublicationSerializer(
                    data=publication,
                    context={"lgd": lgd, "user": user}
                )

                if serializer_class.is_valid():
                    serializer_class.save()
                    response = Response({'message': 'Publication added to the G2P entry successfully.'}, status=status.HTTP_201_CREATED)
                else:
                    response = Response({"errors": serializer_class.errors}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        else:
            response = Response({"errors": serializer_list.errors}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return response

    @transaction.atomic
    def update(self, request, stable_id):
        """
            This method deletes the LGD-publication.

            Args:
                { "pmid": 1234 }
        """
        pmid = request.data.get("pmid", None)
        user = request.user # TODO check if user has permission

        lgd_obj = get_object_or_404(LocusGenotypeDisease, stable_id__stable_id=stable_id, is_deleted=0)
        publication_obj = get_object_or_404(Publication, pmid=pmid)

        try:
            lgd_publication_obj = LGDPublication.objects.get(lgd=lgd_obj, publication=publication_obj, is_deleted=0)
        except LGDPublication.DoesNotExist:
            return Response(
                {"errors": f"Could not find publication '{pmid}' for ID '{stable_id}'"},
                status=status.HTTP_404_NOT_FOUND)

        # Before deleting this publication check if LGD record is linked to other publications
        queryset_all = LGDPublication.objects.filter(lgd=lgd_publication_obj.lgd, is_deleted=0)

        # TODO: if we are going to delete the last publication then delete LGD record
        if(queryset_all.exists() and len(queryset_all) == 1):
            return Response(
                {"errors": f"Could not delete PMID '{pmid}' for ID '{stable_id}'"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Remove the publication from the LGD
        lgd_publication_obj.is_deleted = 1

        try:
            lgd_publication_obj.save()
        except:
            return Response(
                {"errors": f"Could not delete PMID '{pmid}' for ID '{stable_id}'"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Delete publication from other tables
        # lgd_phenotype - different phenotypes can be linked to the same publication
        try:
            LGDPhenotype.objects.filter(
                lgd=lgd_publication_obj.lgd,
                publication=lgd_publication_obj.publication,
                is_deleted=0).update(is_deleted=1)
        except:
            return Response(
                {"errors": f"Could not delete PMID '{pmid}' for ID '{stable_id}'"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # lgd_phenotype_summary - the phenotype summary is directly associated with the LGD record
        # A LGD record should only have one phenotype summary but to make sure we delete everything correctly
        # we'll run the filter to catch all objects
        try:
            LGDPhenotypeSummary.objects.filter(
                lgd=lgd_publication_obj.lgd,
                publication=lgd_publication_obj.publication,
                is_deleted=0).update(is_deleted=1)
        except:
            return Response(
                {"errors": f"Could not delete PMID '{pmid}' for ID '{stable_id}'"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # lgd_variant_type - different variant types can be linked to the same publication
        try:
            LGDVariantType.objects.filter(
                lgd=lgd_publication_obj.lgd,
                publication=lgd_publication_obj.publication,
                is_deleted=0).update(is_deleted=1)
        except:
            return Response(
                {"errors": f"Could not delete PMID '{pmid}' for ID '{stable_id}'"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # lgd_variant_type_description - different descriptions can be linked to the same publication
        try:
            LGDVariantTypeDescription.objects.filter(
                lgd=lgd_publication_obj.lgd,
                publication=lgd_publication_obj.publication,
                is_deleted=0).update(is_deleted=1)
        except:
            return Response(
                {"errors": f"Could not delete PMID '{pmid}' for ID '{stable_id}'"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # molecular_mechanism_evidence - only the molecular mechanism evidence is linked to a publication
        lgd_mechanism_obj = lgd_publication_obj.lgd.molecular_mechanism

        # If the mechanism support is evidence then get the list of MolecularMechanismEvidence
        # Different types of evidence can be linked to the same publication
        if(lgd_mechanism_obj and lgd_mechanism_obj.mechanism_support.value == "evidence"):
            MolecularMechanismEvidence.objects.filter(
                molecular_mechanism=lgd_mechanism_obj,
                publication=lgd_publication_obj.publication,
                is_deleted=0).update(is_deleted=1)

            # Check if MolecularMechanism has evidence linked to other publications
            lgd_check_evidence_set = MolecularMechanismEvidence.objects.filter(
                molecular_mechanism=lgd_mechanism_obj,
                is_deleted=0)

            # # There are no other evidence for this lgd-mechanism
            # # In this case, delete the mechanism
            # if(not lgd_check_evidence_set.exists()):
            #     lgd_mechanism_obj.is_deleted=1 # TODO if there is no mechanism then delete LGD record
            #     lgd_mechanism_obj.save()

        return Response(
                {"message": f"Publication '{pmid}' successfully deleted for ID '{stable_id}'"},
                 status=status.HTTP_200_OK)

