from rest_framework.response import Response

from gene2phenotype_app.models import (AttribType, Attrib,
                                       Locus, LocusAttrib)

from gene2phenotype_app.serializers import LocusGeneSerializer

from .base import BaseView


class LocusGene(BaseView):
    """
        Display the gene data.

        Args:
            (str) gene_name: gene symbol or the synonym symbol

        Returns:
            LocusGene object data:
                            - gene_symbol
                            - sequence
                            - start
                            - end
                            - strand
                            - reference
                            - ids
                            - list of synonyms (gene symbols)
                            - last_updated (date of the last update)
    """

    lookup_field = 'name'
    serializer_class = LocusGeneSerializer

    def get_queryset(self):
        name = self.kwargs['name']
        attrib_type = AttribType.objects.filter(code='locus_type')
        attrib = Attrib.objects.filter(type=attrib_type.first().id, value='gene')
        queryset = Locus.objects.filter(name=name, type=attrib.first().id)

        if not queryset.exists():
            # Try to find gene in locus_attrib (gene synonyms)
            attrib_type = AttribType.objects.filter(code='gene_synonym')
            queryset = LocusAttrib.objects.filter(value=name, attrib_type=attrib_type.first().id, is_deleted=0)

            if not queryset.exists():
                self.handle_no_permission('Gene', name)

            queryset = Locus.objects.filter(id=queryset.first().locus.id)

        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset().first()
        serializer = LocusGeneSerializer(queryset)
        return Response(serializer.data)

class LocusGeneSummary(BaseView):
    """
        Display a summary of the latest G2P entries associated with gene.

        Args:
            (str) gene_name: gene symbol or the synonym symbol

        Returns:
            Response object includes:
                            (string) gene_symbol
                            (list) records_summary
    """

    serializer_class = LocusGeneSerializer

    def get(self, request, name, *args, **kwargs):
        attrib_type = AttribType.objects.filter(code='locus_type')
        attrib = Attrib.objects.filter(type=attrib_type.first().id, value='gene')
        queryset = Locus.objects.filter(name=name, type=attrib.first().id)

        if not queryset.exists():
            # Try to find gene in locus_attrib (gene synonyms)
            attrib_type = AttribType.objects.filter(code='gene_synonym')
            queryset = LocusAttrib.objects.filter(value=name, attrib_type=attrib_type.first().id, is_deleted=0)

            if not queryset.exists():
                self.handle_no_permission('Gene', name)

            queryset = Locus.objects.filter(id=queryset.first().locus.id)

        serializer = LocusGeneSerializer
        summmary = serializer.records_summary(queryset.first(), self.request.user)
        response_data = {
            'gene_symbol': queryset.first().name,
            'records_summary': summmary,
        }

        return Response(response_data)

class GeneFunction(BaseView):
    """
        Display the gene product function.
        Data retrieved from UniProt API.

        Args:
            (str) gene_name: gene symbol or the synonym symbol

        Returns:
            Response object includes:
                            (string) gene_symbol
                            (dict) function: gene product function from UniProt
    """

    serializer_class = LocusGeneSerializer

    def get(self, request, name, *args, **kwargs):
        attrib_type = AttribType.objects.filter(code='locus_type')
        attrib = Attrib.objects.filter(type=attrib_type.first().id, value='gene')
        queryset = Locus.objects.filter(name=name, type=attrib.first().id)

        if not queryset.exists():
            # Try to find gene in locus_attrib (gene synonyms)
            attrib_type = AttribType.objects.filter(code='gene_synonym')
            queryset = LocusAttrib.objects.filter(value=name, attrib_type=attrib_type.first().id, is_deleted=0)

            if not queryset.exists():
                self.handle_no_permission('Gene', name)

            queryset = Locus.objects.filter(id=queryset.first().locus.id)

        serializer = LocusGeneSerializer
        summmary = serializer.function(queryset.first())
        gene_stats = serializer.badonyi_score(queryset.first())
        response_data = {
            'gene_symbol': queryset.first().name,
            'function': summmary,
            'gene_stats': gene_stats
        }

        return Response(response_data)
