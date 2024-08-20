from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import api_view
from django.db import transaction
from django.shortcuts import get_object_or_404

from gene2phenotype_app.serializers import (PublicationSerializer, LGDPublicationSerializer,
                                            LGDPublicationListSerializer)

from gene2phenotype_app.models import (Publication, LocusGenotypeDisease, LGDPublication)

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
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

### LGD-publication ###
# Add data
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
                    response = Response({"errors": serializer_class.errors}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        else:
            response = Response({"errors": serializer_list.errors}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return response

# Delete data
class LGDDeletePublication(BaseUpdate):
    """
        Delete a publication associated with the LGD.
        The deletion does not remove the entry from the database, instead
        it sets the flag 'is_deleted' to 1.
    """

    http_method_names = ['put', 'options']
    serializer_class = LGDPublicationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
            Fetch the list of LGD-publication
        """
        stable_id = self.kwargs['stable_id']
        pmid = self.kwargs['pmid']
        user = self.request.user # TODO check if user has permission

        lgd_obj = get_object_or_404(LocusGenotypeDisease, stable_id__stable_id=stable_id, is_deleted=0)
        publication_obj = get_object_or_404(Publication, pmid=pmid)

        queryset = LGDPublication.objects.filter(lgd=lgd_obj, publication=publication_obj, is_deleted=0)

        if not queryset.exists():
            self.handle_no_permission(pmid, stable_id)
        else:
            return queryset

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        """
            This method 'deletes' the LGD-publication.

            Raises:
                Invalid confidence value
                G2P record already has same confidence value
        """
        stable_id = self.kwargs['stable_id']
        pmid = self.kwargs['pmid']

        # Get G2P entry to be updated
        lgd_publication_obj = self.get_queryset().first()

        lgd_publication_obj.is_deleted = 1

        try:
            lgd_publication_obj.save()
        except:
            return Response({"errors": f"Could not delete PMID '{pmid}' for ID '{stable_id}'"}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
                {"message": f"Publication '{pmid}' successfully deleted for ID '{stable_id}'"},
                 status=status.HTTP_200_OK)
