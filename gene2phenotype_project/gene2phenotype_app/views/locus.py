from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiResponse
import textwrap

from gene2phenotype_app.models import (AttribType, Attrib,
                                       Locus, LocusAttrib)

from gene2phenotype_app.serializers import LocusGeneSerializer

from .base import BaseAPIView


@extend_schema(
description=textwrap.dedent("""
    Fetch information for a specific gene.
    """)
)
class LocusGene(BaseAPIView):
    """
        Fetch information for a specific gene.

        Args:
            (str) `name`: gene symbol or the synonym symbol

        Returns a dictionary with the following values:
                            (str) gene_symbol;
                            (str) sequence;
                            (integer) start;
                            (integer) end;
                            (integer) strand;
                            (str) reference;
                            (list) ids;
                            (list) list of synonyms: gene symbols;
                            (str) last_updated: date of the last update;
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

    def get(self, request, *args, **kwargs):
        queryset = self.get_queryset().first()
        serializer = LocusGeneSerializer(queryset)
        return Response(serializer.data)

@extend_schema(
    description=textwrap.dedent("""
        Fetch latest G2P entries associated with a specific gene.
        """),
    responses={
        200: OpenApiResponse(
            description="Gene summary response",
            response={
                "type": "object",
                "properties": {
                    "gene_symbol": {"type": "string"},
                    "records_summary": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "disease": {"type": "string"},
                                "genotype": {"type": "string"},
                                "confidence": {"type": "string"},
                                "panels": {"type": "array", "items": {"type": "string"}},
                                "variant_consequence": {"type": "array", "items": {"type": "string"}},
                                "variant_type": {"type": "array", "items": {"type": "string"}},
                                "molecular_mechanism": {"type": "string"},
                                "last_updated": {"type": "string"},
                                "stable_id": {"type": "string"}
                            }
                        }
                    }
                }
            }
        )
    }
)
class LocusGeneSummary(BaseAPIView):
    """
        Return a summary of the latest G2P entries associated with the gene.

        Args:
            (str) `name`: gene symbol or the synonym symbol

        Returns a dictionary with the following values:
                (string) `gene_symbol`
                (list) `records_summary`
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

@extend_schema(
    description=textwrap.dedent("""
        Fetch gene product function (imported from UniProt) for a specific gene.
        """),
    responses={
        200: OpenApiResponse(
            description="Gene function response",
            response={
                "type": "object",
                "properties": {
                    "gene_symbol": {"type": "string"},
                    "function": {
                        "type": "object",
                        "properties": {
                            "protein_function": {"type": "string"},
                            "uniprot_accession": {"type": "string"}
                        }
                    },
                    "gene_stats": {
                        "type": "object",
                        "properties": {
                            "dominant_negative_mp": {"type": "number", "format": "double"},
                            "loss_of_function_mp": {"type": "number", "format": "double"},
                            "gain_of_function_mp": {"type": "number", "format": "double"}
                        }
                    }
                }
            }
        )
    }
)
class GeneFunction(BaseAPIView):
    """
        Return the gene product function imported from UniProt.

        Args:
            (str) `name`: gene symbol or the synonym symbol

        Returns a dictionary with the following:
                (string) `gene_symbol`;
                (dict) `function`: gene product function from UniProt;
                (dict) `gene_stats`: gene scores from the Badonyi probabilities
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
