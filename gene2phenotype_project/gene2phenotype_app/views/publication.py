from rest_framework import permissions
from rest_framework.response import Response
from django.http import Http404
from rest_framework.decorators import api_view

from gene2phenotype_app.serializers import PublicationSerializer

from gene2phenotype_app.models import Publication

from .base import BaseAdd

from ..utils import get_publication, get_authors


"""
    Retrieve publication data for a list of PMIDs.
    If PMID is found in G2P then return details from G2P.
    If PMID not found in G2P then returns info from EuropePMC.

    Args:
            request (HttpRequest): HTTP request
            pmids (str): A comma-separated string of PMIDs

    Return:
            Response object includes:
                - results (list): contains publication data for each publication
                                    - pmid
                                    - title
                                    - authors
                                    - year
                                    - source (possible values: 'G2P', 'EuropePMC', 'Not found')
                - count (int): number of PMIDs in the response
            If a PMID is invalid it returns Http404
"""
@api_view(['GET'])
def PublicationDetail(request, pmids):
    id_list = pmids.split(',')
    data = []

    for pmid_str in id_list:
        try:
            pmid = int(pmid_str)

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
                    data.append({
                        'pmid': int(pmid),
                        'error': 'Invalid PMID'
                    })
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

        except:
            raise Http404(f"Invalid PMID:{pmid_str}")

    return Response({'results': data, 'count': len(data)})


### Add data
class AddPublication(BaseAdd):
    """
        Add new publication.
        The create method is in the PublicationSerializer.
    """
    serializer_class = PublicationSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
