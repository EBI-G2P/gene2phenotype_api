from rest_framework import permissions, status
from rest_framework.response import Response
from django.http import Http404
from rest_framework.decorators import api_view
import re

from gene2phenotype_app.serializers import PhenotypeOntologyTermSerializer

from gene2phenotype_app.models import OntologyTerm

from .base import BaseAdd

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

    return Response({'results': data, 'count': len(data)})


### Add data
class AddPhenotype(BaseAdd):
    """
        Add new phenotype.
        The create method is in the PhenotypeSerializer.
    """
    serializer_class = PhenotypeOntologyTermSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
