from rest_framework import permissions

from gene2phenotype_app.serializers import PhenotypeSerializer

from .base import BaseAdd


class AddPhenotype(BaseAdd):
    """
        Add new phenotype.
        The create method is in the PhenotypeSerializer.
    """
    serializer_class = PhenotypeSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
