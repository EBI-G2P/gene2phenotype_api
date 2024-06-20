from rest_framework import serializers
from ..models import (Locus, LocusIdentifier, LocusAttrib,
                      Attrib, AttribType, Sequence, UniprotAnnotation,
                      GeneDisease, Source, LocusGenotypeDisease)

from ..utils import validate_gene


class LocusSerializer(serializers.ModelSerializer):
    gene_symbol = serializers.CharField(source="name")
    sequence = serializers.CharField(source="sequence.name")
    reference = serializers.CharField(read_only=True, source="sequence.reference.value")
    ids = serializers.SerializerMethodField()
    synonyms = serializers.SerializerMethodField()

    def get_ids(self, id):
        locus_ids = LocusIdentifier.objects.filter(locus=id)
        data = {}
        for id in locus_ids:
            data[id.source.name] = id.identifier

        return data

    def get_synonyms(self, id):
        attrib_type_obj = AttribType.objects.filter(code='gene_synonym')
        locus_attribs = LocusAttrib.objects.filter(
            locus=id,
            attrib_type=attrib_type_obj.first().id,
            is_deleted=0).values_list('value', flat=True)

        return locus_attribs

    def create(self, validated_data):
        gene_symbol = validated_data.get('name')
        sequence_name = validated_data.get('sequence')['name']
        start = validated_data.get('start')
        end = validated_data.get('end')
        strand = validated_data.get('strand')

        locus_obj = None
        try:
            locus_obj = Locus.objects.get(name=gene_symbol)
            raise serializers.ValidationError({"message": f"gene already exists",
                                               "please select existing gene": f"{locus_obj.name} {locus_obj.sequence.name}:{locus_obj.start}-{locus_obj.end}"})
        except Locus.DoesNotExist:
            try:
                # Check if gene symbol is a synonym
                synonym_obj = LocusAttrib.objects.get(value=gene_symbol)
                raise serializers.ValidationError({"message": f"gene already exists as a synonym",
                                               "please select existing gene": f"{synonym_obj.locus.name} {synonym_obj.locus.sequence.name}:{synonym_obj.locus.start}-{synonym_obj.locus.end}"})
            except LocusAttrib.DoesNotExist:
                # Validate gene before insertion
                validated = validate_gene(gene_symbol)
                if validated == None:
                    raise serializers.ValidationError({"message": f"invalid gene symbol",
                                                       "please check symbol": gene_symbol})

                # Insert locus gene
                sequence = Sequence.objects.filter(name=sequence_name)
                type = Attrib.objects.filter(value='gene')

                locus_obj = Locus.objects.create(name = gene_symbol,
                                                 sequence = sequence.first(),
                                                 start = start,
                                                 end = end,
                                                 strand = strand,
                                                 type = type.first())

                # Insert gene-disease associations from OMIM
                source_omim = Source.objects.filter(name='OMIM')
                if 'mim' in validated.keys():
                    for mim in validated['mim']:
                        gene_disease_obj = GeneDisease.objects.create(disease=mim['disease'],
                                                                      gene=locus_obj,
                                                                      source=source_omim.first(),
                                                                      identifier=mim['id'])

                # Insert locus gene synonyms
                if 'synonyms' in validated.keys():
                    attrib_type_obj = AttribType.objects.filter(code='gene_synonym')
                    for synonym in validated['synonyms']:
                        locus_attrib_obj = LocusAttrib.objects.create(value=synonym,
                                                                      locus=locus_obj,
                                                                      attrib_type=attrib_type_obj.first(),
                                                                      is_deleted=0)

                # Insert locus gene ids
                source_hgnc = Source.objects.filter(name='HGNC')
                source_ensembl = Source.objects.filter(name='Ensembl')
                locus_identifier_obj = LocusIdentifier.objects.create(identifier=validated['primary_id'],
                                                                      locus=locus_obj,
                                                                      source=source_hgnc.first())
                locus_identifier_obj = LocusIdentifier.objects.create(identifier=validated['ensembl_id'],
                                                                      locus=locus_obj,
                                                                      source=source_ensembl.first())

        return locus_obj

    class Meta:
        model = Locus
        fields = ['gene_symbol', 'sequence', 'start', 'end', 'strand', 'reference', 'ids', 'synonyms']

class LocusGeneSerializer(LocusSerializer):
    last_updated = serializers.SerializerMethodField()

    def get_last_updated(self, id):
        lgd = LocusGenotypeDisease.objects.filter(
            locus=id,
            is_reviewed=1,
            is_deleted=0,
            date_review__isnull=False
            ).latest('date_review'
                     ).date_review

        return lgd.date() if lgd else []

    def records_summary(self, user):
        lgd_list = LocusGenotypeDisease.objects.filter(locus=self.id, is_deleted=0)

        if user.is_authenticated:
            lgd_select = lgd_list.select_related('disease', 'genotype', 'confidence'
                                               ).prefetch_related('lgd_panel', 'panel', 'lgd_variant_gencc_consequence', 'lgd_variant_type', 'lgd_molecular_mechanism'
                                                                  ).order_by('-date_review')

        else:
            lgd_select = lgd_list.select_related('disease', 'genotype', 'confidence'
                                               ).prefetch_related('lgd_panel', 'panel', 'lgd_variant_gencc_consequence', 'lgd_variant_type', 'lgd_molecular_mechanism'
                                                                  ).order_by('-date_review').filter(lgdpanel__panel__is_visible=1)

        lgd_objects_list = list(lgd_select.values('disease__name',
                                                  'lgdpanel__panel__name',
                                                  'stable_id__stable_id',
                                                  'genotype__value',
                                                  'confidence__value', 
                                                  'lgdvariantgenccconsequence__variant_consequence__term',
                                                  'lgdvarianttype__variant_type_ot__term',
                                                  'lgdmolecularmechanism__mechanism__value'))

        aggregated_data = {}
        for lgd_obj in lgd_objects_list:
            if lgd_obj['stable_id__stable_id'] not in aggregated_data.keys():
                variant_consequences = []
                variant_types = []
                molecular_mechanism = []
                panels = []

                panels.append(lgd_obj['lgdpanel__panel__name'])
                variant_consequences.append(lgd_obj['lgdvariantgenccconsequence__variant_consequence__term'])
                if lgd_obj['lgdvarianttype__variant_type_ot__term'] is not None:
                    variant_types.append(lgd_obj['lgdvarianttype__variant_type_ot__term'])
                if lgd_obj['lgdmolecularmechanism__mechanism__value'] is not None:
                    molecular_mechanism.append(lgd_obj['lgdmolecularmechanism__mechanism__value'])

                aggregated_data[lgd_obj['stable_id__stable_id']] = { 'disease':lgd_obj['disease__name'],
                                                          'genotype':lgd_obj['genotype__value'],
                                                          'confidence':lgd_obj['confidence__value'],
                                                          'panels':panels,
                                                          'variant_consequence':variant_consequences,
                                                          'variant_type':variant_types,
                                                          'molecular_mechanism':molecular_mechanism,
                                                          'stable_id':lgd_obj['stable_id__stable_id'] }

            else:
                if lgd_obj['lgdpanel__panel__name'] not in aggregated_data[lgd_obj['stable_id__stable_id']]['panels']:
                    aggregated_data[lgd_obj['stable_id__stable_id']]['panels'].append(lgd_obj['lgdpanel__panel__name'])
                if lgd_obj['lgdvariantgenccconsequence__variant_consequence__term'] not in aggregated_data[lgd_obj['stable_id__stable_id']]['variant_consequence']:
                    aggregated_data[lgd_obj['stable_id__stable_id']]['variant_consequence'].append(lgd_obj['lgdvariantgenccconsequence__variant_consequence__term'])
                if lgd_obj['lgdvarianttype__variant_type_ot__term'] not in aggregated_data[lgd_obj['stable_id__stable_id']]['variant_type'] and lgd_obj['lgdvarianttype__variant_type_ot__term'] is not None:
                    aggregated_data[lgd_obj['stable_id__stable_id']]['variant_type'].append(lgd_obj['lgdvarianttype__variant_type_ot__term'])
                if lgd_obj['lgdmolecularmechanism__mechanism__value'] not in aggregated_data[lgd_obj['stable_id__stable_id']]['molecular_mechanism'] and lgd_obj['lgdmolecularmechanism__mechanism__value'] is not None:
                    aggregated_data[lgd_obj['stable_id__stable_id']]['molecular_mechanism'].append(lgd_obj['lgdmolecularmechanism__mechanism__value'])

        return aggregated_data.values()

    def function(self):
        result_data = {}
        uniprot_annotation_objs = UniprotAnnotation.objects.filter(gene=self.id)

        for function_obj in uniprot_annotation_objs:
            result_data['protein_function'] = function_obj.protein_function
            result_data['uniprot_accession'] = function_obj.uniprot_accession

        return result_data

    class Meta:
        model = Locus
        fields = LocusSerializer.Meta.fields + ['last_updated']
