import json
from deepdiff import DeepDiff
import copy
from collections import OrderedDict
from rest_framework import serializers
from django.db import connection, transaction
from django.core.exceptions import ObjectDoesNotExist
from datetime import datetime
from django.utils import timezone
import pytz

from .models import (Panel, User, UserPanel, AttribType, Attrib,
                     LGDPanel, LocusGenotypeDisease, LGDVariantGenccConsequence,
                     LGDCrossCuttingModifier, LGDPublication,
                     LGDPhenotype, LGDVariantType, Locus, Disease,
                     DiseaseOntologyTerm, LocusAttrib, DiseaseSynonym, 
                     G2PStableID,LocusIdentifier, PublicationComment, LGDComment,
                     LGDMolecularMechanism, LGDMolecularMechanismEvidence,
                     OntologyTerm, Source, Publication, GeneDisease,
                     Sequence, UniprotAnnotation, CurationData, PublicationFamilies,
                     LGDVariantTypeDescription, CVMolecularMechanism)

from .utils import (clean_string, get_ontology, get_publication, get_authors, validate_gene,
                    validate_phenotype, get_ontology_source)
import re

class G2PStableIDSerializer(serializers.ModelSerializer):
    """
        Serializer for the G2PStableID model.

        This serializer converts G2PStableID instances into JSON representation
        and vice versa. It handles serialization and deserialization of G2PStableID
        objects.
    """

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
    
    def update_g2p_id_status(self, is_live):
        """
            Update the status of the G2P stable id.
            Set 'is_live' to:
                0: entry is not published (live)
                OR
                1: entry is published (live)
        """
        stable_id = self.context['stable_id']

        try:
            g2p_id_obj = G2PStableID.objects.get(stable_id=stable_id)
        except G2PStableID.DoesNotExist:
            raise serializers.ValidationError({"message": f"G2P ID not found '{stable_id}'"})

        g2p_id_obj.is_live = is_live
        g2p_id_obj.save()

        return g2p_id_obj

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
        user_panels = UserPanel.objects.filter(
            panel=id,
            user__is_active=1
            ).select_related('user')

        # TODO: decide how to define the curators group
        curators_group = set(
            User.groups.through.objects.filter(
            group__name="curators"
            ).values_list('user_id', flat=True)
        )

        users = []

        for user_panel in user_panels:
            if not user_panel.user.is_staff or user_panel.user.id in curators_group:
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
        lgd_panel = LGDPanel.objects.filter(
            panel=id,
            lgd__is_reviewed=1,
            lgd__is_deleted=0,
            lgd__date_review__isnull=False
            ).select_related('lgd'
                             ).latest('lgd__date_review'
                                      ).lgd.date_review

        return lgd_panel.date() if lgd_panel else []

    # Calculates the stats on the fly
    # Returns a JSON object
    def calculate_stats(self, panel):
        lgd_panels = LGDPanel.objects.filter(
            panel=panel.id,
            is_deleted=0
        ).select_related()

        genes = set()
        confidences = {}
        attrib_id = Attrib.objects.get(value='gene').id
        for lgd_panel in lgd_panels:
            if lgd_panel.lgd.locus.type.id == attrib_id:
                genes.add(lgd_panel.lgd.locus.name)

            try:
                confidences[lgd_panel.lgd.confidence.value] += 1
            except KeyError:
                confidences[lgd_panel.lgd.confidence.value] = 1

        return {
            'total_records': len(lgd_panels),
            'total_genes': len(genes),
            'by_confidence': confidences
        }

    def records_summary(self, panel):
        lgd_panels = LGDPanel.objects.filter(panel=panel.id, is_deleted=0)

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
        """
            Get a list of panels the user has permission to edit.
            It returns the panel descriptions i.e. full name.
            Output example: ["Developmental disorders", "Ear disorders"]
        """
        user_login = self.context.get('user')
        if user_login and user_login.is_authenticated:
            user_panels = UserPanel.objects.filter(
                user=id
                ).select_related('panel'
                                 ).values_list('panel__description', flat=True)
        else:
            user_panels = UserPanel.objects.filter(
                user=id, panel__is_visible=1
                ).select_related('panel'
                                 ).values_list('panel__description', flat=True)

        return user_panels

    def panels_names(self, id):
        """
            Get a list of panels the user has permission to edit.
            It returns the panel names i.e. short name.
            Output example: ["DD", "Ear"]
        """
        user_login = self.context.get('user')
        if user_login and user_login.is_authenticated:
            user_panels = UserPanel.objects.filter(
                user=id
                ).select_related('panel'
                                 ).values_list('panel__name', flat=True)
        else:
            user_panels = UserPanel.objects.filter(
                user=id, panel__is_visible=1
                ).select_related('panel'
                                 ).values_list('panel__name', flat=True)

        return user_panels

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
    description = serializers.CharField(source="panel.description", allow_null=True, required = False)

    def create(self, validated_data):
        lgd = self.context['lgd']
        panel_name = validated_data.get('panel')['name']

        # Check if panel name is valid
        panel_obj = Panel.objects.filter(name=panel_name)

        if not panel_obj.exists():
            raise serializers.ValidationError({"message": f"Invalid panel name '{panel_name}'"})
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
        fields = ['name', 'description']

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

class GeneDiseaseSerializer(serializers.ModelSerializer):
    disease = serializers.CharField()
    identifier = serializers.CharField()
    source = serializers.CharField(source="source.name")

    class Meta:
        model = GeneDisease
        fields = ['disease', 'identifier', 'source']

class LocusGenotypeDiseaseSerializer(serializers.ModelSerializer):
    locus = serializers.SerializerMethodField()
    stable_id = serializers.CharField(source="stable_id.stable_id") #CharField and the source is the stable_id column in the stable_id table
    genotype = serializers.CharField(source="genotype.value")
    variant_consequence = serializers.SerializerMethodField(allow_null=True)
    molecular_mechanism = serializers.SerializerMethodField(allow_null=True)
    disease = serializers.SerializerMethodField()
    confidence = serializers.CharField(source="confidence.value")
    publications = serializers.SerializerMethodField()
    panels = serializers.SerializerMethodField()
    cross_cutting_modifier = serializers.SerializerMethodField(allow_null=True)
    variant_type = serializers.SerializerMethodField(allow_null=True)
    variant_description = serializers.SerializerMethodField(allow_null=True)
    phenotypes = serializers.SerializerMethodField(allow_null=True)
    last_updated = serializers.SerializerMethodField()
    date_created = serializers.SerializerMethodField()
    comments = serializers.SerializerMethodField(allow_null=True)
    is_reviewed = serializers.IntegerField()

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
        return LGDVariantGenCCConsequenceSerializer(queryset, many=True).data

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
        data = {}

        for lgd_phenotype in queryset:
            accession = lgd_phenotype.phenotype.accession

            if accession in data and lgd_phenotype.publication:
                data[accession]["publications"].append(lgd_phenotype.publication.pmid)
            else:
                publication_list = []
                if lgd_phenotype.publication:
                    publication_list = [lgd_phenotype.publication.pmid]

                data[accession] = {"term": lgd_phenotype.phenotype.term,
                                   "accession": accession,
                                   "publications": publication_list}

        return data.values()

    def get_variant_type(self, id):
        # The variant type can be linked to several publications
        # Format the output to return the list of publications
        queryset = LGDVariantType.objects.filter(lgd_id=id)
        data = {}

        for lgd_variant in queryset:
            accession = lgd_variant.variant_type_ot.accession

            if accession in data and lgd_variant.publication:
                data[accession]["publications"].append(lgd_variant.publication.pmid)
            else:
                publication_list = []
                if lgd_variant.publication:
                    publication_list = [lgd_variant.publication.pmid]

                data[accession] = {"term": lgd_variant.variant_type_ot.term,
                                   "accession": accession,
                                   "inherited": lgd_variant.inherited,
                                   "de_novo": lgd_variant.de_novo,
                                   "unknown_inheritance": lgd_variant.unknown_inheritance,
                                   "publications": publication_list}
        return data.values()

    def get_variant_description(self, id):
        queryset = LGDVariantTypeDescription.objects.filter(lgd_id=id)
        data = {}

        for lgd_variant in queryset:
            if lgd_variant.description in data and lgd_variant.publication:
                data[lgd_variant.description]["publications"].append(lgd_variant.publication.pmid)
            else:
                publication_list = []
                if lgd_variant.publication:
                    publication_list = [lgd_variant.publication.pmid]
                data[lgd_variant.description] = {
                    "description": lgd_variant.description,
                    "publications": publication_list
                }

        return data.values()

    def get_panels(self, id):
        queryset = LGDPanel.objects.filter(lgd_id=id)
        return LGDPanelSerializer(queryset, many=True).data

    def get_comments(self, id):
        # TODO check if comment is public
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
        history_records = lgd_obj.history.all().order_by('history_date').filter(
            history_type=insertion_history_type)

        if history_records:
            date = history_records.first().history_date.date()

        return date

    def create(self, data, disease_obj, publications_list):
        """
            Create a G2P record.
            A record is always linked to one or more panels and publications.

            Mandatory data:
                            - locus
                            - G2P stable_id
                            - disease
                            - genotype (allelic requeriment)
                            - mechanism (TODO)
                            - panel(s)
                            - confidence
                            - publications
        """

        locus_name = data.get('locus') # Usually this is the gene symbol
        stable_id_obj = data.get('stable_id') # stable id obj
        genotype = data.get('allelic_requirement') # allelic requirement
        panels = data.get('panels') # Array of panel names
        confidence = data.get('confidence') # confidence level and justification

        if not panels or not publications_list:
            raise serializers.ValidationError({"message": f"Missing data to create the G2P record {stable_id_obj.stable_id}"})

        # Check if record (LGD) is already inserted
        try:
            lgd_obj = LocusGenotypeDisease.objects.get(stable_id=stable_id_obj)
            return lgd_obj

        except LocusGenotypeDisease.DoesNotExist:

            # Get locus object
            try:
                locus_obj = Locus.objects.get(name=locus_name)
            except Locus.DoesNotExist:
                raise serializers.ValidationError({"message": f"Invalid locus {locus_name}"})

            # Get genotype
            try:
                genotype_obj = Attrib.objects.get(
                    value = genotype,
                    type__code = "genotype"
                )
            except Attrib.DoesNotExist:
                raise serializers.ValidationError({"message": f"Invalid genotype value {genotype}"})

            # Get confidence
            try:
                confidence_obj = Attrib.objects.get(
                    value = confidence["level"],
                    type__code = "confidence_category"
                )
            except Attrib.DoesNotExist:
                raise serializers.ValidationError({"message": f"Invalid confidence value {confidence['level']}"})

            # Text to justify the confidence value (optional)
            if confidence["justification"] == "":
                confidence_support = None
            else:
                confidence_support = confidence["justification"]

            # Insert new G2P record (LGD)
            lgd_obj = LocusGenotypeDisease.objects.create(
                locus = locus_obj,
                stable_id = stable_id_obj,
                genotype = genotype_obj,
                disease = disease_obj,
                confidence = confidence_obj,
                confidence_support = confidence_support,
                is_reviewed = 1,
                is_deleted = 0,
                date_review = datetime.now()
            )

            # Insert panels
            for panel in panels:
                try:
                    # Get name from description
                    panel_obj = Panel.objects.get(description=panel)
                    data_panel = {"panel": {"name": panel_obj.name}}
                    # The LGDPanelSerializer fetches the object LGD from its context
                    LGDPanelSerializer(context={'lgd': lgd_obj}).create(data_panel)
                
                except Panel.DoesNotExist:
                    raise serializers.ValidationError({"message": f"Invalid panel {panel}"})

            # Insert LGD-publications
            for publication_obj in publications_list:
                data_publication = {"publication": publication_obj}
                LGDPublicationSerializer(context={'lgd': lgd_obj}).create(data_publication)

        return lgd_obj

    class Meta:
        model = LocusGenotypeDisease
        exclude = ['id', 'is_deleted', 'date_review']

class LGDVariantGenCCConsequenceSerializer(serializers.ModelSerializer):
    variant_consequence = serializers.CharField(source="variant_consequence.term")
    support = serializers.CharField(source="support.value")
    publication = serializers.CharField(source="publication.pmid", allow_null=True)

    def create(self, variant_consequence):
        lgd = self.context['lgd']
        term = variant_consequence.get("name").replace("_", " ")
        support = variant_consequence.get("support").lower()

        # Get variant gencc consequence value from ontology_term
        try:
            consequence_obj = OntologyTerm.objects.get(
                term = term, # TODO check
                group_type__value = "variant_type"
            )
        except OntologyTerm.DoesNotExist:
            raise serializers.ValidationError({"message": f"Invalid variant consequence '{term}'"})

        # Get support value from attrib
        try:
            support_obj = Attrib.objects.get(
                value = support,
                type__code = "support"
            )
        except Attrib.DoesNotExist:
            raise serializers.ValidationError({"message": f"Invalid support value {support}"})

        lgd_var_consequence_obj = LGDVariantGenccConsequence.objects.get_or_create(
                variant_consequence = consequence_obj,
                support = support_obj,
                lgd = lgd,
                is_deleted = 0
            )
        
        return lgd_var_consequence_obj

    class Meta:
        model = LGDVariantGenccConsequence
        fields = ['variant_consequence', 'support', 'publication']

class LGDMolecularMechanismSerializer(serializers.ModelSerializer):
    mechanism = serializers.CharField(source="mechanism.value")
    support = serializers.CharField(source="mechanism_support.value")
    description = serializers.CharField(source="mechanism_description", allow_null=True)
    synopsis = serializers.CharField(source="synopsis.value", allow_null=True)
    synopsis_support = serializers.CharField(source="synopsis_support.value", allow_null=True)
    evidence = serializers.SerializerMethodField()

    def get_evidence(self, id):
        evidence_list = LGDMolecularMechanismEvidence.objects.filter(
            molecular_mechanism=id
            ).select_related('evidence', 'publication').values(
                'publication__pmid',
                'evidence__value',
                'evidence__subtype'
            ).order_by('publication')

        data = {}

        for evidence in evidence_list:
            evidence_value = evidence["evidence__value"]
            evidence_type = evidence["evidence__subtype"]
            pmid = evidence["publication__pmid"]

            if pmid not in data:
                data[pmid] = {}
                data[pmid][evidence_type] = [evidence_value]
            elif evidence_type not in data[pmid]:
                data[pmid][evidence_type] = [evidence_value]
            else:
                data[pmid][evidence_type].append(evidence_value)
        
        return data

    def create(self, mechanism, mechanism_synopsis, mechanism_evidence):
        lgd = self.context['lgd']
        mechanism_name = mechanism["name"]
        mechanism_support = mechanism["support"]
        synopsis_name = mechanism_synopsis["name"] # optional
        synopsis_support = mechanism_synopsis["support"] # optional
        synopsis_obj = None
        synopsis_support_obj = None

        if mechanism_support == "evidence" and not mechanism_evidence:
            raise serializers.ValidationError({"message": f"Mechanism is missing the evidence"})

        # Get mechanism value from attrib
        try:
            mechanism_obj = CVMolecularMechanism.objects.get(
                value = mechanism_name,
                type = "mechanism"
            )
        except CVMolecularMechanism.DoesNotExist:
            raise serializers.ValidationError({"message": f"Invalid mechanism value '{mechanism_name}'"})

        # Get mechanism support from attrib
        try:
            mechanism_support_obj = CVMolecularMechanism.objects.get(
                value = mechanism_support,
                type = "support"
            )
        except CVMolecularMechanism.DoesNotExist:
            raise serializers.ValidationError({"message": f"Invalid mechanism support value '{mechanism_support}'"})

        if synopsis_name:
            # Get mechanism synopsis value from attrib
            try:
                synopsis_obj = CVMolecularMechanism.objects.get(
                    value = synopsis_name,
                    type = "mechanism_synopsis"
                )
            except CVMolecularMechanism.DoesNotExist:
                raise serializers.ValidationError({"message": f"Invalid mechanism synopsis value '{synopsis_name}'"})

            # Get mechanism synopsis support from attrib
            try:
                synopsis_support_obj = CVMolecularMechanism.objects.get(
                    value = synopsis_support,
                    type = "support"
                )
            except CVMolecularMechanism.DoesNotExist:
                raise serializers.ValidationError({"message": f"Invalid mechanism synopsis support value '{synopsis_support}'"})

        # Create new LGD-molecular mechanism
        lgd_mechanism = LGDMolecularMechanism.objects.create(
            lgd = lgd,
            mechanism = mechanism_obj,
            mechanism_support = mechanism_support_obj,
            synopsis = synopsis_obj,
            synopsis_support = synopsis_support_obj,
            is_deleted = 0
        )

        # Insert the mechanism evidence
        if mechanism_support == "evidence":
            # for each publication (pmid) there is one or more evidence values
            for evidence in mechanism_evidence:
                publication_obj = None

                try:
                    publication_obj = Publication.objects.get(pmid=evidence["pmid"])

                except Publication.DoesNotExist:
                    raise serializers.ValidationError({"message": f"Could not find publication for PMID '{evidence['pmid']}'"})

                else:
                    # Get the evidence values
                    for evidence_type in evidence["evidence_types"]:
                        # type can be: function, rescue, functional alteration or models
                        subtype = evidence_type["primary_type"].replace(" ", "_")
                        values = evidence_type["secondary_type"]

                        # Values are stored in attrib table
                        for v in values:
                            try:
                                evidence_value = CVMolecularMechanism.objects.get(
                                    value = v.lower(),
                                    type = "evidence",
                                    subtype = subtype.lower()
                                )
                            except CVMolecularMechanism.DoesNotExist:
                                raise serializers.ValidationError({"message": f"Invalid mechanism evidence value '{v.lower()}'"})

                            else:
                                lgd_mechanism_evidence = LGDMolecularMechanismEvidence.objects.create(
                                molecular_mechanism = lgd_mechanism,
                                evidence = evidence_value,
                                publication = publication_obj,
                                is_deleted = 0
                            )

        return lgd_mechanism

    class Meta:
        model = LGDMolecularMechanism
        fields = ['mechanism', 'support', 'description', 'synopsis', 'synopsis_support', 'evidence']

class LGDCrossCuttingModifierSerializer(serializers.ModelSerializer):
    term = serializers.CharField(source="ccm.value")

    def create(self, term):
        lgd = self.context['lgd']

        # Get cross cutting modifier from attrib
        try:
            ccm_obj = Attrib.objects.get(
                value = term,
                type__code = 'cross_cutting_modifier'
            )
        except Attrib.DoesNotExist:
            raise serializers.ValidationError({"message": f"Invalid cross cutting modifier {term}"})

        # Check if LGD-cross cutting modifier already exists
        try:
            lgd_ccm_obj = LGDCrossCuttingModifier.objects.get(
                ccm = ccm_obj,
                lgd = lgd
            )
        except LGDCrossCuttingModifier.DoesNotExist:
            lgd_ccm_obj = LGDCrossCuttingModifier.objects.create(
                ccm = ccm_obj,
                lgd = lgd,
                is_deleted = 0
            )

        return lgd_ccm_obj

    class Meta:
        model = LGDCrossCuttingModifier
        fields = ['term']

class PublicationCommentSerializer(serializers.ModelSerializer):

    def create(self, data, publication):
        comment_text = data.get("comment")
        is_public = data.get("is_public")
        user_obj = self.context['user']

        # Check if comment is already stored. We consider same comment if they have the same:
        #   publication, comment text, user and it's not deleted TODO
        # Filter can return multiple values - this can happen if we have duplicated entries
        publication_comment_list = PublicationComment.objects.filter(comment = comment_text,
                                                                     user = user_obj,
                                                                     is_deleted = 0)

        publication_comment_obj = publication_comment_list.first()

        # Comment was not found in table - insert new comment
        if len(publication_comment_list) == 0:
            publication_comment_obj = PublicationComment.objects.create(comment = comment_text,
                                                                        is_public = is_public,
                                                                        is_deleted = 0,
                                                                        date = datetime.now(),
                                                                        publication = publication,
                                                                        user = user_obj)

        return publication_comment_obj

    class Meta:
        model = PublicationComment

class PublicationFamiliesSerializer(serializers.ModelSerializer):

    def create(self, validated_data, publication):
        """
            Create a PublicationFamilies object.

            Fields:
                    - families: number of families reported in the publication (mandatory)
                    - consanguinity: consanguinity (default: unknown)
                    - ancestries: ancestry free text
                    - affected_individuals: number of affected individuals reported in the publication
        """
        families = validated_data.get("families")
        consanguinity = validated_data.get("consanguinity")
        ancestries = validated_data.get("ancestries")
        affected_individuals = validated_data.get("affected_individuals")

        # Check if there is data
        if families == "" or families is None:
            return None

        # Get consanguinity from attrib
        try:
            consanguinity_obj = Attrib.objects.get(
                value = consanguinity,
                type__code = "consanguinity"
            )
        except Attrib.DoesNotExist:
            raise serializers.ValidationError({"message": f"Invalid consanguinity value {consanguinity}"})

        # Check if LGD-publication families is already stored
        try:
            publication_families_obj = PublicationFamilies.objects.get(
                publication = publication,
                families = families,
                consanguinity = consanguinity_obj,
                ancestries = ancestries,
                affected_individuals = affected_individuals
            )

        except PublicationFamilies.DoesNotExist:
            # Data was not found in table - insert families data
            publication_families_obj = PublicationFamilies.objects.create(
                publication = publication,
                families = families,
                consanguinity = consanguinity_obj,
                ancestries = ancestries,
                affected_individuals = affected_individuals
            )

        return publication_families_obj

    class Meta:
        model = PublicationFamilies

class PublicationSerializer(serializers.ModelSerializer):
    pmid = serializers.IntegerField()
    title = serializers.CharField(read_only=True)
    authors = serializers.CharField(read_only=True)
    year = serializers.CharField(read_only=True)
    comments = PublicationCommentSerializer(many=True, required=False)
    number_of_families = PublicationFamiliesSerializer(many=True, required=False)

    def create(self, validated_data):
        """
            Create a publication.
            If PMID is already stored in G2P, add the new comment and number of 
            families to the existing PMID.
            This method is called when publishing a record.

            Fields:
                    - pmid: publications PMID (mandatory)
                    - comments: list of comments
                    - number_of_families: list of families
        """

        pmid = validated_data.get('pmid')
        comments = validated_data.get('comments')
        number_of_families = validated_data.get('number_of_families')

        try:
            publication_obj = Publication.objects.get(pmid=pmid)

        except Publication.DoesNotExist:
            response = get_publication(pmid)

            if response['hitCount'] == 0:
                raise serializers.ValidationError({"message": "Invalid PMID",
                                                   "Please check ID": pmid})

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

        # Add new comments and/or number of families
        for comment in comments:
            if comment != "":
                PublicationCommentSerializer(
                    context={'user': self.context.get('user')}
                ).create(comment, publication_obj)

        for family in number_of_families:
            PublicationFamiliesSerializer().create(family, publication_obj)

        return publication_obj

    class Meta:
        model = Publication
        fields = ['pmid', 'title', 'authors', 'year', 'comments', 'number_of_families']

class LGDPublicationSerializer(serializers.ModelSerializer):
    publication = PublicationSerializer()

    def create(self, validated_data):
        lgd = self.context['lgd']
        publication_obj = validated_data.get('publication') # TODO REVIEW

        try:
            lgd_publication_obj = LGDPublication.objects.get(
                lgd = lgd,
                publication = publication_obj
            )

            # The entry can be deleted
            if lgd_publication_obj.is_deleted == 1:
                raise serializers.ValidationError(
                    {"message": f"Record {lgd.stable_id.stable_id} is already linked to publication {publication_obj.pmid}"}
                )

        except LGDPublication.DoesNotExist:
            # Insert new LGD-publication entry
            lgd_publication_obj = LGDPublication.objects.create(
                lgd = lgd,
                publication = publication_obj,
                is_deleted = 0
            )

        return lgd_publication_obj

    class Meta:
        model = LGDPublication
        fields = ['publication']

class DiseaseOntologyTermSerializer(serializers.ModelSerializer):
    accession = serializers.CharField(source="ontology_term.accession")
    term = serializers.CharField(source="ontology_term.term")
    description = serializers.CharField(source="ontology_term.description", allow_null=True)
    source = serializers.CharField(source="ontology_term.source.name")

    class Meta:
        model = DiseaseOntologyTerm
        fields = ['accession', 'term', 'description', 'source']

class DiseaseSerializer(serializers.ModelSerializer):
    name = serializers.CharField()
    ontology_terms = serializers.SerializerMethodField()
    synonyms = serializers.SerializerMethodField()

    def get_ontology_terms(self, id):
        disease_ontologies = DiseaseOntologyTerm.objects.filter(disease=id)
        return DiseaseOntologyTermSerializer(disease_ontologies, many=True).data

    def get_synonyms(self, id):
        synonyms = []
        disease_synonyms = DiseaseSynonym.objects.filter(disease=id)
        for d_synonym in disease_synonyms:
            synonyms.append(d_synonym.synonym)
        return synonyms

    class Meta:
        model = Disease
        fields = ['name', 'ontology_terms', 'synonyms']

class DiseaseDetailSerializer(DiseaseSerializer):
    last_updated = serializers.SerializerMethodField()

    def get_last_updated(self, id):
        filtered_lgd_list = LocusGenotypeDisease.objects.filter(
            disease=id,
            is_reviewed=1,
            is_deleted=0,
            date_review__isnull=False
            ).latest('date_review'
                     ).date_review

        return filtered_lgd_list.date() if filtered_lgd_list else []

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
    ontology_terms = DiseaseOntologyTermSerializer(many=True, required=False)

    # Add synonyms

    def create(self, validated_data):
        disease_name = validated_data.get('name')
        ontologies_list = validated_data.get('ontology_terms')

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
            # TODO: give disease suggestions

            disease_obj = Disease.objects.create(
                name = disease_name
            )

        # Check if ontology is in db
        # The disease ontology is saved in the db as attrib type 'disease'
        for ontology in ontologies_list:
            ontology_accession = ontology['ontology_term']['accession']
            ontology_term = ontology['ontology_term']['term']
            ontology_desc = ontology['ontology_term']['description']
            disease_ontology_obj = None

            if ontology_accession is not None and ontology_term is not None:
                try:
                    ontology_obj = OntologyTerm.objects.get(accession=ontology_accession)

                except OntologyTerm.DoesNotExist:
                    # Check if ontology is from OMIM or Mondo
                    source = get_ontology_source(ontology_accession)

                    if source is None:
                        raise serializers.ValidationError({
                            "message": f"Invalid ID '{ontology_accession}' please input a valid ID from OMIM or Mondo"
                            })

                    elif source == "Mondo":
                        # Check if ontology accession is valid
                        mondo_disease = get_ontology(ontology_accession, source)
                        if mondo_disease is None:
                            raise serializers.ValidationError({"message": "Invalid Mondo ID",
                                                                   "Please check ID": ontology_accession})
                        elif mondo_disease == "query failed":
                            raise serializers.ValidationError({"message": f"Cannot query Mondo ID {ontology_accession}"})

                    # Replace '_' from mondo ID
                    ontology_accession = re.sub(r'\_', ':', ontology_accession)
                    ontology_term = re.sub(r'\_', ':', ontology_term)
                    # Insert ontology
                    if ontology_desc is None and len(mondo_disease['description']) > 0:
                        ontology_desc = mondo_disease['description'][0]

                    elif source == "OMIM":
                        omim_disease = get_ontology(ontology_accession, source)
                        # TODO: check if we can use the OMIM API in the future
                        if omim_disease == "query failed":
                            raise serializers.ValidationError({"message": f"Cannot query OMIM ID {ontology_accession}"})

                        if ontology_desc is None and omim_disease is not None and len(omim_disease['description']) > 0:
                            ontology_desc = omim_disease['description'][0]

                    source = Source.objects.get(name=source)
                    # Get attrib 'disease'
                    attrib_disease = Attrib.objects.get(
                        value = "disease",
                        type__code = "ontology_term_group"
                    )

                    ontology_obj = OntologyTerm.objects.create(
                                accession = ontology_accession,
                                term = ontology_term,
                                description = ontology_desc,
                                source = source,
                                group_type = attrib_disease
                    )

                attrib = Attrib.objects.get(
                    value="Data source",
                    type__code = "ontology_mapping"
                )

                try:
                    # Check if disease-ontology is stored in G2P
                    disease_ontology_obj = DiseaseOntologyTerm.objects.get(
                        disease = disease_obj,
                        ontology_term = ontology_obj,
                        mapped_by_attrib = attrib,
                    )
                except DiseaseOntologyTerm.DoesNotExist:
                    # Insert disease-ontology
                    disease_ontology_obj = DiseaseOntologyTerm.objects.create(
                        disease = disease_obj,
                        ontology_term = ontology_obj,
                        mapped_by_attrib = attrib,
                    )

        return disease_obj

    class Meta:
        model = Disease
        fields = ['name', 'ontology_terms']

class PhenotypeSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="term", read_only=True)
    description = serializers.CharField(read_only=True)

    def create(self, accession):
        """
            Create a phenotype based on the accession.
        """
        phenotype_accession = accession["accession"]
        phenotype_description = None

        # Check if accession is valid - query HPO API
        validated_phenotype = validate_phenotype(phenotype_accession)

        if not re.match(r'HP\:\d+', phenotype_accession) or validated_phenotype is None:
            raise serializers.ValidationError({"message": f"Invalid phenotype accession",
                                               "Please check ID": phenotype_accession})

        # TODO check if the new API has 'isObsolete'
        # if validated_phenotype['isObsolete'] == True:
        #     raise serializers.ValidationError({"message": f"Phenotype accession is obsolete",
        #                                        "Please check id": phenotype_accession})

        # Check if phenotype is already in G2P
        try:
            phenotype_obj = OntologyTerm.objects.get(accession=phenotype_accession)

        except OntologyTerm.DoesNotExist:
            try:
                source_obj = Source.objects.get(name='HPO')
            except Source.DoesNotExist:
                raise serializers.ValidationError({"message": f"Problem fetching the phenotype source 'HPO'"})

            if 'definition' in validated_phenotype:
                phenotype_description = validated_phenotype['definition']

            phenotype_obj = OntologyTerm.objects.create(accession=phenotype_accession,
                                                        term=validated_phenotype['name'],
                                                        description=phenotype_description,
                                                        source=source_obj)

        return phenotype_obj

    class Meta:
        model = OntologyTerm
        fields = ['name', 'accession', 'description']

class LGDPhenotypeSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="phenotype.term")
    accession = serializers.CharField(source="phenotype.accession")
    publication = serializers.IntegerField(source="publication.pmid", allow_null=True) # TODO check how to support several publications

    def create(self, validated_data):
        lgd = self.context['lgd']
        accession = validated_data.get("accession") # HPO term
        publication = validated_data.get("publication") # pmid

        # This method 'create' behaves like 'get_or_create'
        # If phenotype is already stored in G2P then it returns the object
        pheno_obj = PhenotypeSerializer().create({"accession": accession})

        # TODO insert if not found?
        publication_obj = Publication.objects.get(pmid=publication)

        lgd_phenotype_obj = LGDPhenotype.objects.create(
            lgd = lgd,
            phenotype = pheno_obj,
            is_deleted = 0,
            publication = publication_obj
        )

        return lgd_phenotype_obj

    class Meta:
        model = LGDPhenotype
        fields = ['name', 'accession', 'publication']

class LGDVariantTypeSerializer(serializers.ModelSerializer):
    term = serializers.CharField(source="variant_type_ot.term")
    accession = serializers.CharField(source="variant_type_ot.accession")
    inherited = serializers.BooleanField(allow_null=True)
    de_novo = serializers.BooleanField(allow_null=True)
    unknown_inheritance = serializers.BooleanField(allow_null=True)
    publication = serializers.IntegerField(source="publication.pmid", allow_null=True)

    def create(self, validated_data):
        lgd = self.context['lgd']
        inherited = validated_data.get("inherited")
        de_novo = validated_data.get("de_novo")
        unknown_inheritance = validated_data.get("unknown_inheritance")
        var_type = validated_data.get("secondary_type")
        publications = validated_data.get("supporting_papers")

        # Get variant type from ontology_term
        # nmd_escape list: frameshift_variant, stop_gained, splice_region_variant?, splice_acceptor_variant,
        # splice_donor_variant
        # We save the variant types already with the NMD_escape attached to the term
        if validated_data.get("nmd_escape") is True:
            var_type = f"{var_type}_NMD_escaping"

        try:
            var_type_obj = OntologyTerm.objects.get(
                term = var_type,
                group_type__value = "variant_type"
            )
        except OntologyTerm.DoesNotExist:
            raise serializers.ValidationError({"message": f"Invalid variant type {var_type}"})

        # A single variant type can be attached to several publications
        for publication in publications:
            # TODO: get or create
            publication_obj = Publication.objects.get(pmid=publication)

            lgd_variant_type = LGDVariantType.objects.get_or_create(
                lgd = lgd,
                variant_type_ot = var_type_obj,
                inherited = inherited,
                de_novo = de_novo,
                unknown_inheritance = unknown_inheritance,
                publication = publication_obj,
                is_deleted = 0
            )

        # TODO return all objects created
        return lgd_variant_type

    class Meta:
        model = LGDVariantType
        fields = ['term', 'accession', 'inherited', 'de_novo', 'unknown_inheritance', 'publication']

class LGDVariantTypeDescriptionSerializer(serializers.ModelSerializer):
    publication = serializers.IntegerField(source="publication.pmid")
    description = serializers.CharField()

    def create(self, validated_data):
        lgd = self.context['lgd']
        pmid = validated_data.get("pmid")
        description = validated_data.get("description")

        publication_obj = Publication.objects.get(pmid=pmid)

        lgd_variant_type_desc = LGDVariantTypeDescription.objects.get_or_create(
                lgd = lgd,
                description = description,
                publication = publication_obj,
                is_deleted = 0
            )
        
        return lgd_variant_type_desc

    class Meta:
        model = LGDVariantTypeDescription
        fields = ['publication', 'description']

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
            # Check if any panel in data_dict["json_data"]["panels"] is not in the updated panels list
            unauthorized_panels = [panel for panel in data_dict["json_data"]["panels"] if panel not in panels]
            if unauthorized_panels:
                unauthorized_panels_str = "', '".join(unauthorized_panels)
                raise serializers.ValidationError({"message" : f"You do not have permission to curate on these panels: '{unauthorized_panels_str}'"})

        return data

    def validate_to_publish(self, data):
        """
            Second step to validate the JSON data.
            This validation is done before a record is published.
            There are mandatory fields to publish a record:
                - locus (validated in the first validation step)
                - disease
                - genotype/allelic requirement
                - molecular mechanism
                - panel(s)
                - confidence
                - publication(s)
            
            data (CurationData obj): data to be validated
        """

        json_data = data.json_data
        missing_data = []

        # Check if G2P record (LGD) is already published
        try:
            lgd_obj = LocusGenotypeDisease.objects.get(
                locus__name = json_data["locus"],
                genotype__value = json_data["allelic_requirement"],
                disease__name = json_data["disease"]["disease_name"]
            )

            raise serializers.ValidationError({
                "message": "Found another record with same locus, genotype and disease",
                "Please check G2P record": lgd_obj.stable_id.stable_id
            })

        except LocusGenotypeDisease.DoesNotExist:
            if json_data["disease"]["disease_name"] == "":
                missing_data.append("disease")
            
            if json_data["confidence"]["level"] == "":
                missing_data.append("confidence")
            
            if len(json_data["publications"]) == 0:
                missing_data.append("publication")
            
            if not json_data["panels"]:
                missing_data.append("panel")
            
            if json_data["allelic_requirement"] == "":
                missing_data.append("allelic_requirement")

            if json_data["molecular_mechanism"]["name"] == "":
                missing_data.append("molecular_mechanism")

            if missing_data:
                missing_data_str = ', '.join(missing_data)
                raise serializers.ValidationError({"message" : f"The following mandatory fields are missing: {missing_data_str}"})

            # Check if data is stored in G2P
            # Locus - we only accept locus already stored in G2P
            try:
                locus_obj = Locus.objects.get(name=json_data["locus"])
            except Locus.DoesNotExist:
                raise serializers.ValidationError({"message" : f"Invalid locus {json_data['locus']}"})

        return locus_obj


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
                - publish endpoint: add the data to the G2P tables. entry will be live
        """
        json_data = validated_data.get("json_data")

        date_created = datetime.now()
        date_reviewed = date_created
        session_name = json_data.get('session_name')
        stable_id = G2PStableIDSerializer.create_stable_id()

        if session_name == "":
            session_name = stable_id.stable_id

        try:
            CurationData.objects.get(session_name=session_name)
            raise serializers.ValidationError({
                "message" : f"Curation data with the '{session_name}' already exists. Please change the session name and try again"
            })

        except:
            user_email = self.context.get('user') # TODO: this needs to be looked at
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

    @transaction.atomic
    def update(self, instance, validated_data):
        """
            Update an entry in the curation table.
            It replaces the json data object with the latest data and updates the 'date_last_update'. 

            Parameters:
                instance
                validated_data (dict): Validated data containing the updated JSON data to be stored.

            Returns:
                CurationData: The updated CurationData instance.
        """
        instance.json_data = validated_data.get('json_data')
        instance.date_last_update = timezone.now().astimezone(pytz.timezone("Europe/London"))
        instance.save()

        return instance

    @transaction.atomic
    def publish(self, data):
        """
            Publish a record under curation.
            This method is wrapped in a single transation (@transaction.atomic) ensuring
            that all related database operations are treated as a single unit.

            Args:
                data: CurationData object to publish
        """
        user = self.context.get('user')
        publications_list = []

        ### Publications ###
        for publication in data.json_data["publications"]:
            if publication["families"] is None:
                family = []
            else: 
                family = [{ "families": publication["families"], 
                            "consanguinity": publication["consanguineous"], 
                            "ancestries": publication["ancestries"], 
                            "affected_individuals": publication["affectedIndividuals"]
                        }]

            # format the publication data according to the expected format in PublicationSerializer
            publication_data = { "pmid": publication["pmid"],
                                "comments": [{"comment": publication["comment"], "is_public": 1}],
                                "number_of_families": family
                            }

            publication_obj = PublicationSerializer(context={'user': user}).create(publication_data)
            publications_list.append(publication_obj)
        ####################

        ### Disease ###
        # The disease IDs (ontology terms) are saved under cross_references
        """ cross_references element example:
                {
                    "source": "OMIM",
                    "identifier": "114480",
                    "disease_name": "breast cancer",
                    "original_disease_name": "BREAST CANCER"
                }
        """
        cross_references = []
        if "cross_references" in data.json_data["disease"]:
            for cr in data.json_data["disease"]["cross_references"]:
                ontology_term = {
                    "accession": cr["identifier"],
                    "term": cr["identifier"], # TODO This should be the disease name
                    "description": cr["original_disease_name"] # TODO This should be the full description
                }
                # Format the cross_reference dictionary according to the expected format in CreateDiseaseSerializer
                cross_references.append({"ontology_term": ontology_term})

        # Use CreateDiseaseSerializer to get or create disease
        disease = {
            "name": data.json_data["disease"]["disease_name"],
            "ontology_terms": cross_references, # if we have more ids the serializer should add them
            "publications": [] # TODO review if necessary
        }

        # The CreateDiseaseSerializer is going to first check if the disease is stored in G2P
        # It only inserts data that is not in G2P
        disease_obj = CreateDiseaseSerializer().create(disease)
        ###############

        ### Locus-Genotype-Disease ###
        lgd_data = {"locus": data.json_data["locus"],
                    "stable_id": data.stable_id, # stable id obj
                    "allelic_requirement": data.json_data["allelic_requirement"], # value string
                    "panels": data.json_data["panels"],
                    "confidence": data.json_data["confidence"],
                    "phenotypes": data.json_data["phenotypes"],
                    "variant_types": data.json_data["variant_types"]
                }

        lgd_obj = LocusGenotypeDiseaseSerializer().create(lgd_data, disease_obj, publications_list)
        ##############################

        ### Insert data attached to the record Locus-Genotype-Disease ###

        ### Phenotypes ###
        for phenotype in data.json_data["phenotypes"]:
            LGDPhenotypeSerializer(context={'lgd': lgd_obj}).create({
                "accession": phenotype["summary"], # TODO update variable name
                "publication": phenotype["pmid"] # optional
                })

        ### Cross cutting modifier ###
        # "cross_cutting_modifier" is an array of strings
        for ccm in data.json_data["cross_cutting_modifier"]:
            LGDCrossCuttingModifierSerializer(context={'lgd': lgd_obj}).create(ccm)

        ### Variant (GenCC) consequences ###
        # Example: 'variant_consequences': [{'name': 'altered_gene_product_level', 'support': ''}
        for var_consequence in data.json_data["variant_consequences"]:
            LGDVariantGenCCConsequenceSerializer(context={'lgd': lgd_obj}).create(var_consequence)

        ### Variant types ###
        # Example: {'comment': 'This is a frameshift', 'inherited': false, 'de_novo': false, 
        # 'unknown_inheritance': false, 'nmd_escape': True, 'primary_type': 'protein_changing',
        # 'secondary_type': 'frameshift_variant', 'supporting_papers': [38737272, 38768424]}
        for variant_type in data.json_data["variant_types"]:
            LGDVariantTypeSerializer(context={'lgd': lgd_obj}).create(variant_type)

        # Variant description (HGVS)
        for variant_type_desc in data.json_data["variant_descriptions"]:
            LGDVariantTypeDescriptionSerializer(context={'lgd': lgd_obj}).create(variant_type_desc)

        # TODO: add comment

        ### Mechanism ###
        # The curation form only supports one mechanism
        # Curators cannot create a record with multiple mechanisms
        if data.json_data["molecular_mechanism"]:
            LGDMolecularMechanismSerializer(context={'lgd': lgd_obj}).create(
                data.json_data["molecular_mechanism"],
                data.json_data["mechanism_synopsis"],
                data.json_data["mechanism_evidence"] # array of evidence values for each publication
            )

        #################################################################

        # Update stable_id status to live (is_live=1)
        G2PStableIDSerializer(context={'stable_id': data.stable_id.stable_id}).update_g2p_id_status(1)

        return lgd_obj

    class Meta:
        model = CurationData
        fields = ["json_data"]
