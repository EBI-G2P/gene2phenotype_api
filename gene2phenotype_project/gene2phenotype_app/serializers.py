import json
from deepdiff import DeepDiff
import copy
from collections import OrderedDict
from rest_framework import serializers
from django.db import connection, transaction
from django.core.exceptions import ObjectDoesNotExist
from datetime import datetime
from django.db.models import Q
from django.utils.timezone import make_aware

from .models import (Panel, User, UserPanel, AttribType, Attrib,
                     LGDPanel, LocusGenotypeDisease, LGDVariantGenccConsequence,
                     LGDCrossCuttingModifier, LGDPublication,
                     LGDPhenotype, LGDVariantType, Locus, Disease,
                     DiseaseOntology, LocusAttrib, DiseaseSynonym, 
                     G2PStableID,LocusIdentifier, PublicationComment, LGDComment,
                     DiseasePublication, LGDMolecularMechanism,
                     OntologyTerm, Source, Publication, GeneDisease,
                     Sequence, UniprotAnnotation, CurationData, PublicationFamilies)

from .utils import clean_string, get_mondo, get_publication, get_authors, validate_gene, validate_phenotype
import re

class G2PStableIDSerializer(serializers.ModelSerializer):
    """
        Serializer for the G2PStableID model.

        This serializer converts G2PStableID instances into JSON representation
        and vice versa. It handles serialization and deserialization of G2PStableID
        objects.
    """
    @transaction.atomic

    def create_stable_id():
        """
            Creates a new stable identifier instance for gene-to-phenotype mapping.

            This function generates a stable identifier based on the current count of G2PStableID instances
            in the database and saves the new instance.

            Returns:
                G2PStableID: The newly created stable identifier instance.

            Raises:
                ObjectDoesNotExist: If there are no existing G2PStableID instances in the database.

            Example:
                Example usage:

                 >>> new_stable_id = create_stable_id()
                >>> print(new_stable_id.stable_id)
                'G2P00001'
        """

        #Generate the sequence numbers as part of the ID 
        try:
            number_obj = G2PStableID.objects.count()
            number_obj = number_obj + 1 
            sequence_id = f"G2P{number_obj:05d}" 
        except ObjectDoesNotExist: 
            sequence_number = 1 
            sequence_id = f"G2P{sequence_number:05d}"
        
        stable_id_instance = G2PStableID(stable_id=sequence_id)
        stable_id_instance.save()

        return stable_id_instance
    
    
    class Meta:
        """
            Metadata options for the G2PStableIDSerializer class.

            This Meta class provides configuration options for the G2PStableIDSerializer
            serializer class. It specifies the model to be used for serialization and
            includes/excludes certain fields from the serialized output.

            Attributes:
                model (Model): The model class associated with this serializer.
                Defines the model whose instances will be serialized and deserialized.
                exclude (list or tuple): A list of fields to be excluded from the serialized output.
                These fields will not be included in the JSON representation of the serialized object.
                In this case, the 'id' field is excluded.
        """
        model = G2PStableID
        fields = ['stable_id']

class PanelDetailSerializer(serializers.ModelSerializer):
    curators = serializers.SerializerMethodField()
    last_updated = serializers.SerializerMethodField()

    # Returns only the curators excluding staff members
    def get_curators(self, id):
        user_panels = UserPanel.objects.filter(panel=id)
        users = []

        for user_panel in user_panels:
            group_queryset = User.groups.through.objects.filter(group__name="curators", user=user_panel.user.id)

            if user_panel.user.is_active == 1 and (user_panel.user.is_staff == 0 or len(group_queryset) > 0):
                first_name = user_panel.user.first_name
                last_name = user_panel.user.last_name
                if first_name is not None and last_name is not None:
                    name = f"{first_name} {last_name}"
                else:
                    user_name = user_panel.user.username.split('_')
                    name = ' '.join(user_name).title()
                users.append(name)
        return users

    def get_last_updated(self, id):
        dates = []
        lgd_panels = LGDPanel.objects.filter(panel=id)
        for lgd_panel in lgd_panels:
            if lgd_panel.lgd.date_review is not None and lgd_panel.lgd.is_reviewed == 1 and lgd_panel.lgd.is_deleted == 0:
                dates.append(lgd_panel.lgd.date_review)
                dates.sort()
        if len(dates) > 0:
            return dates[-1].date()
        else:
            return []

    # Calculates the stats on the fly
    # Returns a JSON object
    def calculate_stats(self, panel):
        lgd_panels = LGDPanel.objects.filter(
            panel=panel.id,
            is_deleted=0
        ).select_related()

        genes = set()
        diseases = set()
        confidences = {}
        attrib_id = Attrib.objects.get(value='gene').id
        for lgd_panel in lgd_panels:
            if lgd_panel.lgd.locus.type.id == attrib_id:
                genes.add(lgd_panel.lgd.locus.name)

            diseases.add(lgd_panel.lgd.disease_id)

            try:
                confidences[lgd_panel.lgd.confidence.value] += 1
            except KeyError:
                confidences[lgd_panel.lgd.confidence.value] = 1

        return {
            'total_records': len(lgd_panels),
            'total_genes': len(genes),
            'total_diseases':len(diseases),
            'by_confidence': confidences
        }

    def records_summary(self, panel):
        lgd_panels = LGDPanel.objects.filter(panel=panel.id).filter(is_deleted=0)

        lgd_panels_selected = lgd_panels.select_related('lgd',
                                                        'lgd__locus',
                                                        'lgd__disease',
                                                        'lgd__genotype',
                                                        'lgd__confidence'
                                                    ).prefetch_related(
                                                        'lgd__lgd_variant_gencc_consequence',
                                                        'lgd__lgd_variant_type',
                                                        'lgd__lgd_molecular_mechanism'
                                                    ).order_by('-lgd__date_review').filter(lgd__is_deleted=0)

        lgd_objects_list = list(lgd_panels_selected.values('lgd__locus__name',
                                                           'lgd__disease__name',
                                                           'lgd__genotype__value',
                                                           'lgd__confidence__value',
                                                           'lgd__lgdvariantgenccconsequence__variant_consequence__term',
                                                           'lgd__lgdvarianttype__variant_type_ot__term',
                                                           'lgd__lgdmolecularmechanism__mechanism__value',
                                                           'lgd__date_review',
                                                           'lgd__stable_id__stable_id'))

        aggregated_data = {}
        number_keys = 0
        for lgd_obj in lgd_objects_list:
            if lgd_obj['lgd__stable_id__stable_id'] not in aggregated_data.keys() and number_keys < 10:
                variant_consequences = []
                variant_types = []
                molecular_mechanism = []

                variant_consequences.append(lgd_obj['lgd__lgdvariantgenccconsequence__variant_consequence__term'])
                # Some records do not have variant types
                if lgd_obj['lgd__lgdvarianttype__variant_type_ot__term'] is not None:
                    variant_types.append(lgd_obj['lgd__lgdvarianttype__variant_type_ot__term'])
                # Some records do not have molecular mechanism
                if lgd_obj['lgd__lgdmolecularmechanism__mechanism__value'] is not None:
                    molecular_mechanism.append(lgd_obj['lgd__lgdmolecularmechanism__mechanism__value'])

                aggregated_data[lgd_obj['lgd__stable_id__stable_id']] = {  'locus':lgd_obj['lgd__locus__name'],
                                                                'disease':lgd_obj['lgd__disease__name'],
                                                                'genotype':lgd_obj['lgd__genotype__value'],
                                                                'confidence':lgd_obj['lgd__confidence__value'],
                                                                'variant_consequence':variant_consequences,
                                                                'variant_type':variant_types,
                                                                'molecular_mechanism':molecular_mechanism,
                                                                'date_review':lgd_obj['lgd__date_review'],
                                                                'stable_id':lgd_obj['lgd__stable_id__stable_id'] }
                number_keys += 1

            elif number_keys < 10:
                if lgd_obj['lgd__lgdvariantgenccconsequence__variant_consequence__term'] not in aggregated_data[lgd_obj['lgd__stable_id__stable_id']]['variant_consequence']:
                    aggregated_data[lgd_obj['lgd__stable_id__stable_id']]['variant_consequence'].append(lgd_obj['lgd__lgdvariantgenccconsequence__variant_consequence__term'])
                if lgd_obj['lgd__lgdvarianttype__variant_type_ot__term'] not in aggregated_data[lgd_obj['lgd__stable_id__stable_id']]['variant_type'] and lgd_obj['lgd__lgdvarianttype__variant_type_ot__term'] is not None:
                    aggregated_data[lgd_obj['lgd__stable_id__stable_id']]['variant_type'].append(lgd_obj['lgd__lgdvarianttype__variant_type_ot__term'])
                if lgd_obj['lgd__lgdmolecularmechanism__mechanism__value'] not in aggregated_data[lgd_obj['lgd__stable_id__stable_id']]['molecular_mechanism'] and lgd_obj['lgd__lgdmolecularmechanism__mechanism__value'] is not None:
                    aggregated_data[lgd_obj['lgd__stable_id__stable_id']]['molecular_mechanism'].append(lgd_obj['lgd__lgdmolecularmechanism__mechanism__value'])

        return aggregated_data.values()

    class Meta:
        model = Panel
        fields = ['name', 'description', 'curators', 'last_updated']

class UserSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()
    email = serializers.CharField(read_only=True)
    panels = serializers.SerializerMethodField()
    is_active = serializers.CharField(read_only=True)

    def get_user_name(self, id):
        user = User.objects.filter(email=id)
        if user.first().first_name is not None and user.first().last_name is not None:
            name = f"{user.first().first_name} {user.first().last_name}"
        else:
            user_name = user.first().username.split('_')
            name = ' '.join(user_name).title()

        return name

    def get_panels(self, id):
        user_login = self.context.get('user')
        user_panels = UserPanel.objects.filter(user=id)
        panels_list = []

        for user_panel in user_panels:
            # Authenticated users can view all panels
            if (user_login and user_login.is_authenticated) or user_panel.panel.is_visible == 1:
                panels_list.append(user_panel.panel.name)

        return panels_list

    class Meta:
        model = User
        fields = ['user_name', 'email', 'is_active', 'panels']

class AttribTypeSerializer(serializers.ModelSerializer):

    def get_all_attribs(self, id):
        queryset = Attrib.objects.filter(type=id)
        code_list = [attrib.value for attrib in queryset]
        return code_list

    class Meta:
        model = AttribType
        fields = ['code']

class AttribSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attrib
        fields = ['value']

class LGDPanelSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="panel.name")
    description = serializers.CharField(source="panel.description", allow_null=True)
    publications = serializers.CharField(source="publication.pmid", allow_null=True)

    def create(self, validated_data):
        lgd = self.context['lgd']
        panel_name = validated_data.get('panel')['name']

        # Check if panel name is valid
        panel_obj = Panel.objects.filter(name=panel_name)

        if not panel_obj.exists():
            raise serializers.ValidationError({"message": f"invalid panel name '{panel_name}'"})
        lgd_panel_obj = LGDPanel.objects.filter(panel=panel_obj.first().id, lgd=lgd.id)

        if lgd_panel_obj.exists():
            if lgd_panel_obj.first().is_deleted == 0:
                raise serializers.ValidationError({"message": f"G2P entry {lgd.stable_id.stable_id} is already linked to panel {panel_name}"})
            else:
                # Entry is not deleted anymore
                lgd_panel_obj.is_deleted = 0
                return lgd_panel_obj

        # Create LGDPanel
        lgd_panel_obj = LGDPanel.objects.create(
            lgd=lgd,
            panel=panel_obj.first(),
            is_deleted=0
        )

        return lgd_panel_obj
    
    class Meta:
        model = LGDPanel
        fields = ['name', 'description', 'publications']

    # Only include publication details if defined in context
    # We want to include the details when creating a new publication
    def __init__(self, *args, **kwargs):
        super(LGDPanelSerializer, self).__init__(*args, **kwargs)

        if 'include_details' in self.context:
            self.fields['publications'].required = self.context['include_details']
        else:
            self.fields['publications'].required = False

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
        locus_attribs = LocusAttrib.objects.filter(locus=id, attrib_type=attrib_type_obj.first().id, is_deleted=0)
        data = []
        for locus_atttrib in locus_attribs:
            data.append(locus_atttrib.value)

        return data

    @transaction.atomic
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
        dates = []
        lgds = LocusGenotypeDisease.objects.filter(locus=id)
        for lgd in lgds:
            if lgd.date_review is not None and lgd.is_reviewed == 1 and lgd.is_deleted == 0:
                dates.append(lgd.date_review)
                dates.sort()
        if len(dates) > 0:
            return dates[-1].date()
        else:
            return []

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

class GeneDiseaseSerializer(serializers.ModelSerializer):
    disease = serializers.CharField()
    identifier = serializers.CharField()
    source = serializers.CharField(source="source.name")

    class Meta:
        model = GeneDisease
        fields = ['disease', 'identifier', 'source']

class LocusGenotypeDiseaseSerializer(serializers.ModelSerializer):
    locus = serializers.SerializerMethodField()
    stable_id = serializers.CharField(source="stable_id.stable_id", read_only=True) #CharField and the source is the stable_id column in the stable_id table
    genotype = serializers.CharField(source="genotype.value", read_only=True)
    variant_consequence = serializers.SerializerMethodField()
    molecular_mechanism = serializers.SerializerMethodField()
    disease = serializers.SerializerMethodField()
    confidence = serializers.CharField(source="confidence.value", read_only=True)
    publications = serializers.SerializerMethodField()
    panels = serializers.SerializerMethodField()
    cross_cutting_modifier = serializers.SerializerMethodField()
    variant_type = serializers.SerializerMethodField()
    phenotypes = serializers.SerializerMethodField()
    last_updated = serializers.SerializerMethodField()
    date_created = serializers.SerializerMethodField()
    comments = serializers.SerializerMethodField()
    is_reviewed = serializers.IntegerField(read_only=True)

    def get_locus(self, id):
        locus = LocusSerializer(id.locus).data
        return locus

    def get_disease(self, id):
        disease = DiseaseSerializer(id.disease).data
        return disease

    def get_last_updated(self, obj):
        if obj.date_review is not None:
            return obj.date_review.strftime("%Y-%m-%d")
        else: 
            return None

    def get_variant_consequence(self, id):
        queryset = LGDVariantGenccConsequence.objects.filter(lgd_id=id)
        return VariantConsequenceSerializer(queryset, many=True).data

    def get_molecular_mechanism(self, id):
        queryset = LGDMolecularMechanism.objects.filter(lgd_id=id)
        return LGDMolecularMechanismSerializer(queryset, many=True).data

    def get_cross_cutting_modifier(self, id):
        queryset = LGDCrossCuttingModifier.objects.filter(lgd_id=id)
        return LGDCrossCuttingModifierSerializer(queryset, many=True).data

    def get_publications(self, id):
        queryset = LGDPublication.objects.filter(lgd_id=id)
        return LGDPublicationSerializer(queryset, many=True).data

    def get_phenotypes(self, id):
        queryset = LGDPhenotype.objects.filter(lgd_id=id)
        return LGDPhenotypeSerializer(queryset, many=True).data

    def get_variant_type(self, id):
        queryset = LGDVariantType.objects.filter(lgd_id=id)
        return VariantTypeSerializer(queryset, many=True).data

    def get_panels(self, id):
        queryset = LGDPanel.objects.filter(lgd_id=id)
        return LGDPanelSerializer(queryset, many=True).data

    def get_comments(self, id):
        lgd_comments = LGDComment.objects.filter(lgd_id=id)
        data = []
        for comment in lgd_comments:
            text = { 'text':comment.comment,
                     'date':comment.date }
            data.append(text)

        return data

    # This method depends on the history table
    # Entries that were migrated from the old db don't have the date when they were created
    def get_date_created(self, id):
        date = None
        lgd_obj = self.instance
        insertion_history_type = '+'
        history_records = lgd_obj.history.all().order_by('history_date').filter(history_type=insertion_history_type)
        if history_records:
            date = history_records.first().history_date.date()

        return date

    class Meta:
        model = LocusGenotypeDisease
        exclude = ['id', 'is_deleted', 'date_review']

class VariantConsequenceSerializer(serializers.ModelSerializer):
    variant_consequence = serializers.CharField(source="variant_consequence.term")
    support = serializers.CharField(source="support.value")
    publication = serializers.CharField(source="publication.title", allow_null=True)

    class Meta:
        model = LGDVariantGenccConsequence
        fields = ['variant_consequence', 'support', 'publication']

class LGDMolecularMechanismSerializer(serializers.ModelSerializer):
    mechanism = serializers.CharField(source="mechanism.value")
    support = serializers.CharField(source="mechanism_support.value")
    description = serializers.CharField(source="mechanism_description", allow_null=True)
    synopsis = serializers.CharField(source="synopsis.value", allow_null=True)
    synopsis_support = serializers.CharField(source="synopsis_support.value", allow_null=True)
    publication = serializers.CharField(source="publication.title", allow_null=True)

    class Meta:
        model = LGDVariantGenccConsequence
        fields = ['mechanism', 'support', 'description', 'synopsis', 'synopsis_support', 'publication']

class LGDCrossCuttingModifierSerializer(serializers.ModelSerializer):
    term = serializers.CharField(source="ccm.value")

    class Meta:
        model = LGDCrossCuttingModifier
        fields = ['term']

class PublicationSerializer(serializers.ModelSerializer):
    pmid = serializers.CharField()
    title = serializers.CharField(read_only=True)
    authors = serializers.CharField(read_only=True)
    year = serializers.CharField(read_only=True)
    comments = serializers.SerializerMethodField()

    def get_comments(self, id):
        data = []
        comments = PublicationComment.objects.filter(publication=id)
        for comment in comments:
            text = { 'text':comment.comment,
                     'date':comment.date }
            data.append(text)

        return data

    def create(self, validated_data):
        pmid = validated_data.get('pmid')

        try:
            publication_obj = Publication.objects.get(pmid=pmid)
            raise serializers.ValidationError({"message": f"publication already exists",
                                                "please check publication":
                                                f"PMID: {pmid}, Title: {publication_obj.title}"})
        except Publication.DoesNotExist:
            response = get_publication(pmid)

            if response['hitCount'] == 0:
                raise serializers.ValidationError({"message": f"invalid pmid",
                                                   "please check id": pmid})

            authors = get_authors(response)
            year = None
            doi = None
            publication_info = response['result']
            title = publication_info['title']
            if 'doi' in publication_info:
                doi = publication_info['doi']
            if 'pubYear' in publication_info:
                year = publication_info['pubYear']

            # Insert publication
            publication_obj = Publication.objects.create(pmid = pmid,
                                                         title = title,
                                                         authors = authors,
                                                         year = year,
                                                         doi = doi)

        return publication_obj

    class Meta:
        model = Publication
        fields = ['pmid', 'title', 'authors', 'year', 'comments']

class LGDPublicationSerializer(serializers.ModelSerializer):
    publication = PublicationSerializer()

    class Meta:
        model = LGDPublication
        fields = ['publication']

class DiseasePublicationSerializer(serializers.ModelSerializer):
    pmid = serializers.CharField(source="publication.pmid")
    title = serializers.CharField(source="publication.title", allow_null=True)
    number_families = serializers.IntegerField(source="families", allow_null=True)
    consanguinity = serializers.CharField(allow_null=True)
    ethnicity = serializers.CharField(allow_null=True)

    class Meta:
        model = DiseasePublication
        fields = ['pmid', 'title', 'number_families', 'consanguinity', 'ethnicity']

class DiseaseOntologySerializer(serializers.ModelSerializer):
    accession = serializers.CharField(source="ontology_term.accession")
    term = serializers.CharField(source="ontology_term.term")
    description = serializers.CharField(source="ontology_term.description", allow_null=True)

    class Meta:
        model = DiseaseOntology
        fields = ['accession', 'term', 'description']

class DiseaseSerializer(serializers.ModelSerializer):
    name = serializers.CharField()
    mim = serializers.CharField()
    ontology_terms = serializers.SerializerMethodField()
    publications = serializers.SerializerMethodField()
    synonyms = serializers.SerializerMethodField()

    def get_ontology_terms(self, id):
        disease_ontologies = DiseaseOntology.objects.filter(disease=id)
        return DiseaseOntologySerializer(disease_ontologies, many=True).data

    def get_publications(self, id):
        disease_publications = DiseasePublication.objects.filter(disease=id)
        return DiseasePublicationSerializer(disease_publications, many=True).data

    def get_synonyms(self, id):
        synonyms = []
        disease_synonyms = DiseaseSynonym.objects.filter(disease=id)
        for d_synonym in disease_synonyms:
            synonyms.append(d_synonym.synonym)
        return synonyms

    class Meta:
        model = Disease
        fields = ['name', 'mim', 'ontology_terms', 'publications', 'synonyms']

class DiseaseDetailSerializer(DiseaseSerializer):
    last_updated = serializers.SerializerMethodField()

    def get_last_updated(self, id):
        dates = []
        filtered_lgd_list = LocusGenotypeDisease.objects.filter(disease=id)
        for lgd in filtered_lgd_list:
            if lgd.date_review is not None and lgd.is_reviewed == 1 and lgd.is_deleted == 0:
                dates.append(lgd.date_review)
                dates.sort()
        if len(dates) > 0:
            return dates[-1].date()
        else:
            return []

    def records_summary(self, id, user):
        lgd_list = LocusGenotypeDisease.objects.filter(disease=id, is_deleted=0)

        if user.is_authenticated:
            lgd_select = lgd_list.select_related('disease', 'genotype', 'confidence'
                                               ).prefetch_related('lgd_panel', 'panel', 'lgd_variant_gencc_consequence', 'lgd_variant_type', 'lgd_molecular_mechanism', 'g2pstable_id'
                                                                  ).order_by('-date_review')

        else:
            lgd_select = lgd_list.select_related('disease', 'genotype', 'confidence'
                                               ).prefetch_related('lgd_panel', 'panel', 'lgd_variant_gencc_consequence', 'lgd_variant_type', 'lgd_molecular_mechanism', 'g2pstable_id'
                                                                  ).order_by('-date_review').filter(lgdpanel__panel__is_visible=1)


        lgd_objects_list = list(lgd_select.values('disease__name',
                                                  'lgdpanel__panel__name',
                                                  'stable_id__stable_id', # to get the stable_id stableID
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

    class Meta:
        model = Disease
        fields = DiseaseSerializer.Meta.fields + ['last_updated']

class CreateDiseaseSerializer(serializers.ModelSerializer):
    ontology_terms = DiseaseOntologySerializer(many=True, required=False)
    publications = DiseasePublicationSerializer(many=True, required=False)

    @transaction.atomic
    def create(self, validated_data):
        disease_name = validated_data.get('name')
        mim = validated_data.get('mim')
        ontologies_list = validated_data.get('ontology_terms')
        publications_list = validated_data.get('publications')

        disease_obj = None

        # Clean disease name
        cleaned_input_disease_name = clean_string(str(disease_name))
        # Check if name already exists
        all_disease_names = Disease.objects.all()
        for disease_db in all_disease_names:
            cleaned_db_disease_name = clean_string(str(disease_db.name))
            if cleaned_db_disease_name == cleaned_input_disease_name:
                disease_obj = disease_db
        all_disease_synonyms = DiseaseSynonym.objects.all()
        for disease_synonym in all_disease_synonyms:
            cleaned_db_disease_syn = clean_string(str(disease_synonym.synonym))
            if cleaned_db_disease_syn == cleaned_input_disease_name:
                disease_obj = disease_synonym.disease

        if disease_obj is None:
            # TODO: check if MIM is valid - need OMIM API access
            # TODO: give disease suggestions

            disease_obj = Disease.objects.create(
                name = disease_name,
                mim = mim
            )

            # Check if ontology is in db
            for ontology in ontologies_list:
                ontology_accession = ontology['ontology_term']['accession']
                ontology_term = ontology['ontology_term']['term']
                ontology_desc = ontology['ontology_term']['description']

                if ontology_accession is not None and ontology_term is not None:
                    try:
                        ontology_obj = OntologyTerm.objects.get(accession=ontology_accession)
                    except OntologyTerm.DoesNotExist:
                        # Check if ontology accession is valid
                        mondo_disease = get_mondo(ontology_accession)
                        if mondo_disease is None:
                            raise serializers.ValidationError({"message": f"invalid mondo id",
                                                            "please check id": ontology_accession})

                        source = Source.objects.get(name="Mondo")

                        # Insert ontology
                        ontology_accession = re.sub(r'\_', ':', ontology_accession)
                        ontology_term = re.sub(r'\_', ':', ontology_term)
                        if ontology_desc is None and len(mondo_disease['description']) > 0:
                            ontology_desc = mondo_disease['description'][0]
                        ontology_obj = OntologyTerm.objects.create(
                            accession = ontology_accession,
                            term = ontology_term,
                            description = ontology_desc,
                            source = source
                        )

                    # Insert disease ontology
                    attrib = Attrib.objects.get(value="Data source")
                    disease_ontology_obj = DiseaseOntology.objects.create(
                        disease = disease_obj,
                        ontology_term = ontology_obj,
                        mapped_by_attrib = attrib
                    )

            # Insert disease publication info
            for publication in publications_list:
                publication_pmid = publication['publication']['pmid']
                publication_title = publication['publication']['title']
                n_families = publication['families']
                consanguinity = publication['consanguinity']
                ethnicity = publication['ethnicity']

                try:
                    publication_obj = Publication.objects.get(pmid=publication_pmid)
                except Publication.DoesNotExist:
                    publication = get_publication(publication_pmid)
                    if publication['hitCount'] == 0:
                        raise serializers.ValidationError({"message": f"invalid pmid",
                                                                    "please check id": publication_pmid})

                    # Insert publication
                    if publication_title is None:
                        publication_title = publication['result']['title']
                    publication_authors = get_authors(publication)
                    publication_doi = None
                    publication_year = None
                    if 'doi' in publication['result']:
                        publication_doi = publication['result']['doi']
                    if 'pubYear' in publication['result']:
                        publication_year = publication['result']['pubYear']

                    publication_obj = Publication.objects.create(
                        pmid = publication_pmid,
                        title = publication_title,
                        authors = publication_authors,
                        doi = publication_doi,
                        year = publication_year
                    )

                # Insert disease_publication
                try:
                    disease_publication_obj = DiseasePublication.objects.get(disease=disease_obj, publication=publication_obj)
                except DiseasePublication.DoesNotExist:
                    disease_publication_obj = DiseasePublication.objects.create(
                        disease = disease_obj,
                        publication = publication_obj,
                        families = n_families,
                        consanguinity = consanguinity,
                        ethnicity = ethnicity,
                        is_deleted = 0
                    )

        else:
            raise serializers.ValidationError({"message": f"disease already exists",
                                               "please select existing disease": disease_obj.name})

        return disease_obj

    class Meta:
        model = Disease
        fields = ['name', 'mim', 'ontology_terms', 'publications']

class PhenotypeSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="term", read_only=True)
    description = serializers.CharField(read_only=True)

    @transaction.atomic
    def create(self, validated_data):
        phenotype_accession = validated_data.get('accession')
        phenotype_description = None

        # Check if accession is valid
        validated_phenotype = validate_phenotype(phenotype_accession)

        if not re.match(r'HP\:\d+', phenotype_accession) or validated_phenotype is None:
            raise serializers.ValidationError({"message": f"invalid phenotype accession",
                                               "please check id": phenotype_accession})

        if validated_phenotype['details']['isObsolete'] == True:
            raise serializers.ValidationError({"message": f"phenotype accession is obsolete",
                                               "please check id": phenotype_accession})

        if 'definition' in validated_phenotype['details']:
            phenotype_description = validated_phenotype['details']['definition']

        source_obj = Source.objects.filter(name='HPO')
        phenotype_obj = OntologyTerm.objects.create(accession=phenotype_accession,
                                                    term=validated_phenotype['details']['name'],
                                                    description=phenotype_description,
                                                    source=source_obj.first())

        return phenotype_obj

    class Meta:
        model = OntologyTerm
        fields = ['name', 'accession', 'description']

class LGDPhenotypeSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="phenotype.term")
    accession = serializers.CharField(source="phenotype.accession")

    class Meta:
        model = LGDPhenotype
        fields = ['name', 'accession']

class VariantTypeSerializer(serializers.ModelSerializer):
    term = serializers.CharField(source="variant_type_ot.term")
    accession = serializers.CharField(source="variant_type_ot.accession")

    class Meta:
        model = LGDVariantType
        fields = ['term', 'accession']

### Curation data ###
class CurationDataSerializer(serializers.ModelSerializer):
    """
        Serializer for CurationData model
    """
    
    def validate(self, data):
        """
            Validate the input data for curation.

            Args:
                data: The data to be validated.
            
            Validation extension step:
                This step is called in AddCurationData of the views.py
                The steps of the validation for the save is
                    -Locus is the minimum requirement needed to save a draft
                    -Draft does not already exist as a draft 
                    -User has permissions to curate on the panel selected 

            Returns:
                The validated data.

            Raises:
                serializers.ValidationError: If the data is already under curation or if the user does not have permission to curate on certain panels.
        """

        data_copy = copy.deepcopy(data) # making a copy of this so any changes to this are only to this 
        
        data_dict = self.convert_to_dict(data_copy)

        user_email = self.context.get('user')
        user_obj = User.objects.get(email=user_email)

        if data_dict["json_data"]["locus"] == "" or data_dict["json_data"]["locus"] is None:
            raise serializers.ValidationError({"message" : "To save a draft, the minimum requirement is a locus entry, Please save this draft with locus information"})
        
        # Check if JSON is already in the table
        curation_entry = self.compare_curation_data(data_dict, user_obj.id)
   
        if curation_entry: # Throw error if data is already stored in table
            raise serializers.ValidationError({"message": f"Data already under curation. Please check session '{curation_entry.session_name}'"})
        if len(data_dict["json_data"]["panels"]) >= 1:
            panels = UserSerializer.get_panels(self,user_obj.id)
            panels = ['Developmental disorders' if panel == "DD" else panel for panel in panels] # turning DD to developmental disorders
            # Check if any panel in data_dict["json_data"]["panels"] is not in the updated panels list
            unauthorized_panels = [panel for panel in data_dict["json_data"]["panels"] if panel.replace(' disorders', '') not in panels]
            if unauthorized_panels:
                unauthorized_panels_str = "', '".join(unauthorized_panels)
                raise serializers.ValidationError({"message" : f"You do not have permission to curate on these panels: '{unauthorized_panels_str}'"})

        return data

    def convert_to_dict(self, data):
        """
            Convert data to a regular dictionary if it is an OrderedDict.

            Parameters:
                data: Data to convert (can be OrderedDict or dict).

            Returns:
                Converted data as a dict.
            Reason:
                If the data is an OrderedDict, which is how Python is reading the JSON, it is turned to a regular dictionary which is what is returned, otherwise it just returns the data gotten
        """
        if isinstance(data, OrderedDict):
            return dict(data)
        
        return data
    
    #using the Deepdiff module, compare JSON data 
    # this still needs to be worked on when we have fixed the user permission issue 
    def compare_curation_data(self, input_json_data, user_obj):
       """"
            Function to compare provided JSON data against JSON data stored in CurationData instances associated with a specific user.
            Only compares the first layer of JSON objects.
                Parameters:
                    input_json_data: JSON data to compare against.
                    user_obj: User object whose associated CurationData instances are to be checked.
                 Returns:
                    If a match is found, returns the corresponding CurationData instance.
                    If no match is found, returns None.
        """
       user_sessions_queryset = CurationData.objects.filter(user=user_obj)
       for curation_data in user_sessions_queryset:
            data_json = curation_data.json_data
            # remove session_name field from input json and compare input json with existing curation json
            input_json_data["json_data"].pop('session_name', None)
            data_json.pop('session_name', None)
            result = DeepDiff(input_json_data["json_data"], data_json)
            
            if not result:
                return curation_data
    
    def check_entry(self, input_json_data):
        """
            Check the validity of the provided JSON data for publishing a curated entry.
        
            Parameters:
                input_json_data (dict): JSON data to be checked.
        
            Raises:
                serializers.ValidationError: If the JSON data is invalid for publishing.
            Future: 
                This is for the publish and will be done differently 
        """
        input_dictionary = input_json_data

        locus = input_dictionary["locus"]
        allelic_requirement = input_dictionary["allelic_requirement"]
        disease = input_dictionary["disease"]["disease_name"]

        if locus and allelic_requirement and disease:
            locus_queryset = Locus.objects.filter(name=locus) # Get locus
            genotype_queryset = Attrib.objects.filter(value=allelic_requirement) # Get genotype value from attrib table
            disease_queryset = Disease.objects.filter(name=disease) # TODO: improve

            # Get LGD: deleted entries are also returned
            # If LGD is deleted then we should warn the curator
            lgd_obj = LocusGenotypeDisease.objects.filter(locus=locus_queryset.first(), genotype=genotype_queryset.first(), disease=disease_queryset.first())

            if len(lgd_obj) > 0:
                if lgd_obj.first().is_deleted == 0:
                    raise serializers.ValidationError({"message": f"Data already submited to G2P '{lgd_obj.stable_id.stable_id}'"})
                else:
                    raise serializers.ValidationError({"message": f"This is an old G2P record '{lgd_obj.stable_id.stable_id}'"})
        
        else:
            raise serializers.ValidationError({"message" : "To publish a curated entry, locus, allelic requirement and disease are neccessary"})
                                    

    @transaction.atomic
    def create(self, validated_data):
        """
            Create a new entry in the CurationData table.
        
            Parameters:
                validated_data (dict): Validated data containing the JSON data to be stored.
        
            Returns:
                CurationData: The newly created CurationData instance.
            Future:
                - update endpoint: updates the JSON data in existing session being curated
                - publish endpoint: add the data to the G2P tables. entry will be live
        """
        json_data = validated_data.get("json_data")
       
        date_created = datetime.now()
        date_reviewed = date_created
        session_name = json_data.get('session_name')
        stable_id = G2PStableIDSerializer.create_stable_id()

        if session_name == "":
            session_name = stable_id.stable_id

         
        user_email = self.context.get('user') # this needs to be looked at 
        user_obj = User.objects.get(email=user_email)
            
        new_curation_data = CurationData.objects.create(
            session_name=session_name,
            json_data=json_data,
            stable_id=stable_id,
            date_created=date_created,
            date_last_update=date_reviewed,
            user=user_obj
        )

        return new_curation_data

    class Meta:
        model = CurationData
        fields = ["json_data"]

