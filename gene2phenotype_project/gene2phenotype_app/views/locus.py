from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiExample
import textwrap

from gene2phenotype_app.models import AttribType, Attrib, Locus, LocusAttrib

from gene2phenotype_app.serializers import LocusGeneSerializer

from .base import BaseAPIView


@extend_schema(exclude=True)
class LocusGene(BaseAPIView):
    lookup_field = "name"
    serializer_class = LocusGeneSerializer

    def get_queryset(self):
        name = self.kwargs["name"]
        attrib_type = AttribType.objects.filter(code="locus_type")
        attrib = Attrib.objects.filter(type=attrib_type.first().id, value="gene")
        queryset = Locus.objects.filter(name=name, type=attrib.first().id)

        if not queryset.exists():
            # Try to find gene in locus_attrib (gene synonyms)
            attrib_type = AttribType.objects.filter(code="gene_synonym")
            queryset = LocusAttrib.objects.filter(
                value=name, attrib_type=attrib_type.first().id, is_deleted=0
            )

            if not queryset.exists():
                self.handle_no_permission("Gene", name)

            queryset = Locus.objects.filter(id=queryset.first().locus.id)

        return queryset

    def get(self, request, *args, **kwargs):
        """
        Fetch information for a specific gene.

        Args:
            name (str): gene symbol or the synonym symbol

        Returns a dictionary with the following values:
                            gene_symbol (str)
                            sequence (str)
                            start (integer)
                            end (integer)
                            strand (integer)
                            reference (str)
                            ids (list)
                            list of synonyms (list): gene symbols
                            last_updated (str): date of the last update
        """
        queryset = self.get_queryset().first()
        serializer = LocusGeneSerializer(queryset)
        return Response(serializer.data)


@extend_schema(
    tags=["Fetch G2P summary records by gene"],
    description=textwrap.dedent("""
        Fetch latest records associated with a specific gene by using the gene symbol.
        """),
    examples=[
        OpenApiExample(
            "gene FBN1",
            description="Fetch latest records associated with gene FBN1",
            value={
                "gene_symbol": "FBN1",
                "records_summary": [
                    {
                        "disease": "FBN1-related isolated ectopia lentis",
                        "genotype": "monoallelic_autosomal",
                        "confidence": "limited",
                        "panels": ["Eye", "Skin"],
                        "variant_consequence": ["altered gene product structure"],
                        "variant_type": [
                            "missense_variant",
                            "inframe_deletion",
                            "inframe_insertion",
                        ],
                        "molecular_mechanism": "undetermined",
                        "last_updated": "2024-08-20",
                        "stable_id": "G2P02104",
                    },
                    {
                        "disease": "FBN1-related Weill-Marchesani syndrome",
                        "genotype": "monoallelic_autosomal",
                        "confidence": "strong",
                        "panels": ["DD", "Eye", "Skin", "Skeletal"],
                        "variant_consequence": ["altered gene product structure"],
                        "variant_type": [
                            "missense_variant",
                            "inframe_deletion",
                            "inframe_insertion",
                        ],
                        "molecular_mechanism": "undetermined",
                        "last_updated": "2024-08-20",
                        "stable_id": "G2P01563",
                    },
                    {
                        "disease": "FBN1-related Marfan syndrome",
                        "genotype": "biallelic_autosomal",
                        "confidence": "definitive",
                        "panels": ["DD", "Eye", "Skin", "Skeletal"],
                        "variant_consequence": [
                            "absent gene product",
                            "altered gene product structure",
                        ],
                        "variant_type": [
                            "splice_region_variant",
                            "frameshift_variant",
                            "missense_variant",
                        ],
                        "molecular_mechanism": "loss of function",
                        "last_updated": "2024-05-13",
                        "stable_id": "G2P03125",
                    },
                    {
                        "disease": "FBN1-related Marfan syndrome",
                        "genotype": "monoallelic_autosomal",
                        "confidence": "definitive",
                        "panels": ["DD", "Eye", "Skin", "Skeletal"],
                        "variant_consequence": [
                            "absent gene product",
                            "altered gene product structure",
                        ],
                        "variant_type": [],
                        "molecular_mechanism": "loss of function",
                        "last_updated": "2023-05-24",
                        "stable_id": "G2P01013",
                    },
                ],
            },
        )
    ],
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
                                "panels": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                },
                                "variant_consequence": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                },
                                "variant_type": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                },
                                "molecular_mechanism": {"type": "string"},
                                "last_updated": {"type": "string"},
                                "stable_id": {"type": "string"},
                            },
                        },
                    },
                },
            },
        )
    },
)
class LocusGeneSummary(BaseAPIView):
    serializer_class = LocusGeneSerializer

    def get(self, request, name, *args, **kwargs):
        """
        Return a summary of the G2P entries associated with the gene.

        Args:
            name (str): gene symbol or the synonym symbol

        Returns a dictionary with the following values:
                gene_symbol (string)
                records_summary (list)
        """
        attrib_type = AttribType.objects.filter(code="locus_type")
        attrib = Attrib.objects.filter(type=attrib_type.first().id, value="gene")
        queryset = Locus.objects.filter(name=name, type=attrib.first().id)

        if not queryset.exists():
            # Try to find gene in locus_attrib (gene synonyms)
            attrib_type = AttribType.objects.filter(code="gene_synonym")
            queryset = LocusAttrib.objects.filter(
                value=name, attrib_type=attrib_type.first().id, is_deleted=0
            )

            if not queryset.exists():
                self.handle_no_permission("Gene", name)

            queryset = Locus.objects.filter(id=queryset.first().locus.id)

        serializer = LocusGeneSerializer
        summmary = serializer.records_summary(queryset.first(), self.request.user)
        response_data = {
            "gene_symbol": queryset.first().name,
            "records_summary": summmary,
        }

        return Response(response_data)


@extend_schema(exclude=True)
class GeneFunction(BaseAPIView):
    serializer_class = LocusGeneSerializer

    def get(self, request, name, *args, **kwargs):
        """
        Return the gene product function imported from UniProt.

        Args:
            name (str): gene symbol or the synonym symbol

        Returns a dictionary with the following:
                gene_symbol (string);
                function (dict): gene product function from UniProt;
                gene_stats (dict): gene scores (Badonyi probabilities and gnomAD constraint metrics scores)
        """
        attrib_type = AttribType.objects.filter(code="locus_type")
        attrib = Attrib.objects.filter(type=attrib_type.first().id, value="gene")
        queryset = Locus.objects.filter(name=name, type=attrib.first().id)

        if not queryset.exists():
            # Try to find gene in locus_attrib (gene synonyms)
            attrib_type = AttribType.objects.filter(code="gene_synonym")
            queryset = LocusAttrib.objects.filter(
                value=name, attrib_type=attrib_type.first().id, is_deleted=0
            )

            if not queryset.exists():
                self.handle_no_permission("Gene", name)

            queryset = Locus.objects.filter(id=queryset.first().locus.id)

        serializer = LocusGeneSerializer
        summmary = serializer.function(queryset.first())
        gene_stats = serializer.gene_scores(queryset.first())
        response_data = {
            "gene_symbol": queryset.first().name,
            "function": summmary,
            "gene_stats": gene_stats,
        }

        return Response(response_data)
