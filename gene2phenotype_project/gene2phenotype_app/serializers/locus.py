from rest_framework import serializers
from django.db.models import Q
from typing import Any, Optional
from datetime import date

from ..models import (Locus, LocusIdentifier, LocusAttrib,
                      AttribType, UniprotAnnotation, GeneStats,
                      LocusGenotypeDisease)

from ..utils import validate_gene

"""
    Locus represents a gene, variant or region.
    In a first phase, G2P records are associated with genes.
"""

class LocusSerializer(serializers.ModelSerializer):
    """
        Serializer for the Locus model.
        If the locus is a gene then the name is the gene symbol.
        The sequence is the chromosome overlapping the locus.
    """
    gene_symbol = serializers.CharField(source="name")
    sequence = serializers.CharField(source="sequence.name")
    reference = serializers.CharField(read_only=True, source="sequence.reference.value")
    ids = serializers.SerializerMethodField()
    synonyms = serializers.SerializerMethodField()

    def get_ids(self, id: int) -> dict[str, str]:
        """
            Locus IDs from external sources.
            It can be the HGNC ID for a gene.
        """
        locus_ids = LocusIdentifier.objects.filter(locus=id)
        data = {}
        for id in locus_ids:
            data[id.source.name] = id.identifier

        return data

    def get_synonyms(self, id: int) -> list[str]:
        """
            Returns the locus synonyms.
            The locus synonym can be an old gene symbol.
        """
        attrib_type_obj = AttribType.objects.filter(code='gene_synonym')
        locus_attribs = LocusAttrib.objects.filter(
            locus=id,
            attrib_type=attrib_type_obj.first().id,
            is_deleted=0).values_list('value', flat=True)

        return locus_attribs if locus_attribs else None

    class Meta:
        model = Locus
        fields = ['gene_symbol', 'sequence', 'start', 'end', 'strand', 'reference', 'ids', 'synonyms']

class LocusGeneSerializer(LocusSerializer):
    """
        Serializer for the LocusSerializer model extra data.
        It returns the Locus data and the date of the last update.
        It can also include:
         - summary of records associated with the locus (method records_summary)
         - gene product function from UniProt (method function)
    """

    last_updated = serializers.SerializerMethodField()

    def get_last_updated(self, id: int) -> Optional[date]:
        """
            Returns the date last time the locus was updated.
        """
        final_date = None

        # Get all G2P records associated with the gene
        lgd = LocusGenotypeDisease.objects.filter(
            locus=id,
            is_reviewed=1,
            is_deleted=0,
            date_review__isnull=False
            )

        # Checks if there are G2P records, some genes do not have associated records
        if lgd:
            date = lgd.latest('date_review').date_review
            final_date = date.date()

        return final_date

    def records_summary(self, user):
        """
            Returns a summary of the G2P records associated with the locus.
            If the user is non-authenticated:
                - only returns records linked to visible panels
        """
        if user.is_authenticated:
            lgd_select = LocusGenotypeDisease.objects.filter(locus=self.id,
                                                             is_deleted=0).select_related(
                                                                 'disease', 'genotype', 'confidence', 'mechanism'
                                                                 ).prefetch_related('lgd_panel', 'panel', 'lgd_variant_gencc_consequence', 'lgd_variant_type'
                                                                 ).order_by('-date_review')

        else:
            lgd_select = LocusGenotypeDisease.objects.filter(locus=self.id,
                                                             is_deleted=0,
                                                             lgdpanel__panel__is_visible=1).select_related(
                                                                 'disease', 'genotype', 'confidence', 'mechanism'
                                                                 ).prefetch_related('lgd_panel', 'panel', 'lgd_variant_gencc_consequence', 'lgd_variant_type'
                                                                 ).order_by('-date_review')

        lgd_objects_list = list(lgd_select.values('disease__name',
                                                  'lgdpanel__panel__name',
                                                  'stable_id__stable_id',
                                                  'genotype__value',
                                                  'confidence__value',
                                                  'lgdvariantgenccconsequence__variant_consequence__term',
                                                  'lgdvarianttype__variant_type_ot__term',
                                                  'mechanism__value',
                                                  'date_review'))

        aggregated_data = {}
        for lgd_obj in lgd_objects_list:
            if lgd_obj['stable_id__stable_id'] not in aggregated_data.keys():
                variant_consequences = []
                variant_types = []
                panels = []

                panels.append(lgd_obj['lgdpanel__panel__name'])
                variant_consequences.append(lgd_obj['lgdvariantgenccconsequence__variant_consequence__term'])
                if lgd_obj['lgdvarianttype__variant_type_ot__term'] is not None:
                    variant_types.append(lgd_obj['lgdvarianttype__variant_type_ot__term'])

                date_review = None
                if lgd_obj['date_review'] is not None:
                    date_review = lgd_obj['date_review'].strftime("%Y-%m-%d")

                aggregated_data[lgd_obj['stable_id__stable_id']] = { 'disease':lgd_obj['disease__name'],
                                                          'genotype':lgd_obj['genotype__value'],
                                                          'confidence':lgd_obj['confidence__value'],
                                                          'panels':panels,
                                                          'variant_consequence':variant_consequences,
                                                          'variant_type':variant_types,
                                                          'molecular_mechanism':lgd_obj['mechanism__value'],
                                                          'last_updated':date_review,
                                                          'stable_id':lgd_obj['stable_id__stable_id'] }

            else:
                if lgd_obj['lgdpanel__panel__name'] not in aggregated_data[lgd_obj['stable_id__stable_id']]['panels']:
                    aggregated_data[lgd_obj['stable_id__stable_id']]['panels'].append(lgd_obj['lgdpanel__panel__name'])
                if lgd_obj['lgdvariantgenccconsequence__variant_consequence__term'] not in aggregated_data[lgd_obj['stable_id__stable_id']]['variant_consequence']:
                    aggregated_data[lgd_obj['stable_id__stable_id']]['variant_consequence'].append(lgd_obj['lgdvariantgenccconsequence__variant_consequence__term'])
                if lgd_obj['lgdvarianttype__variant_type_ot__term'] not in aggregated_data[lgd_obj['stable_id__stable_id']]['variant_type'] and lgd_obj['lgdvarianttype__variant_type_ot__term'] is not None:
                    aggregated_data[lgd_obj['stable_id__stable_id']]['variant_type'].append(lgd_obj['lgdvarianttype__variant_type_ot__term'])

        return aggregated_data.values()

    def function(self):
        """
            Returns the gene product function from UniProt.

            Returns:
                    (dict) result_data: it includes the protein function description and the uniprot accession
        """
        result_data = {}
        uniprot_annotation_objs = UniprotAnnotation.objects.filter(gene=self.id)

        for function_obj in uniprot_annotation_objs:
            result_data['protein_function'] = function_obj.protein_function
            result_data['uniprot_accession'] = function_obj.uniprot_accession

        return result_data


    def badonyi_score(self):
        """
            Retrieve the Badonyi scores for the current gene, organizing the results
            in a dictionary where each key is the score's attribute (description_attrib.value)
            and the value is the score rounded to three decimal places.

            Returns:
                dictionary
                    - Key: The value of `description_attrib` (score's attribute) from each `GeneStats` object.
                    - Value: The score associated with that attribute.
        """

        result_data = {}
        badonyi_stats_objs = GeneStats.objects.filter(gene=self.id)

        for badonyi_obj in badonyi_stats_objs:
            key = badonyi_obj.description_attrib.value
            result_data[key] = round(badonyi_obj.score, 3)

        return result_data


    class Meta:
        model = Locus
        fields = LocusSerializer.Meta.fields + ['last_updated']
