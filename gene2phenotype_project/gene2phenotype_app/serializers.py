from rest_framework import serializers

from .models import (Panel, User, UserPanel, AttribType, Attrib,
                     LGDPanel, LocusGenotypeDisease, LGDVariantGenccConsequence,
                     LGDCrossCuttingModifier, LGDPublication,
                     LGDPhenotype, LGDVariantType, Locus, Disease,
                     DiseaseOntology, LocusGenotypeDiseaseHistory,
                     LocusIdentifier, PublicationComment, LGDComment,
                     DiseasePublication)

class PanelSerializer(serializers.ModelSerializer):
    name = serializers.CharField(read_only=True)
    description = serializers.CharField(read_only=True)

    class Meta:
        model = Panel
        fields = ['name', 'description']

class PanelDetailSerializer(PanelSerializer):
    curators = serializers.SerializerMethodField()
    last_updated = serializers.SerializerMethodField()

    def get_curators(self, id):
        x = UserPanel.objects.filter(panel=id)
        users = []
        for u in x:
            if u.user.is_active == 1:
                users.append(u.user.username)
        return users

    def get_diseases(self, id):
        diseases = 0
        uniq_diseases = {}
        x = LGDPanel.objects.filter(panel=id)
        for lgd_panel in x:
            if lgd_panel.lgd.disease_id not in uniq_diseases:
                diseases += 1
                uniq_diseases = { lgd_panel.lgd.disease_id:1 }
        return diseases

    def get_last_updated(self, id):
        dates = []
        x = LGDPanel.objects.filter(panel=id)
        for lgd_panel in x:
            if lgd_panel.lgd.date_review is not None and lgd_panel.lgd.is_reviewed == 1 and lgd_panel.lgd.is_deleted == 0:
                dates.append(lgd_panel.lgd.date_review)
                dates.sort()
        if len(dates) > 0:
            return dates[-1]
        else:
            return []

    def calculate_stats(self, panel):
        lgd_panels = LGDPanel.objects.filter(panel=panel.id)
        num_records = 0
        genes = 0
        uniq_genes = {}
        diseases = 0
        uniq_diseases = {}
        attrib_id = Attrib.objects.get(value='gene').id
        for lgd_panel in lgd_panels:
            if lgd_panel.is_deleted == 0:
                num_records += 1
            if lgd_panel.lgd.locus.type.id == attrib_id and lgd_panel.lgd.locus.name not in uniq_genes:
                genes += 1
                uniq_genes = { lgd_panel.lgd.locus.name:1 }
            if lgd_panel.lgd.disease_id not in uniq_diseases:
                diseases += 1
                uniq_diseases = { lgd_panel.lgd.disease_id:1 }

        stats = {
            'number of records': num_records,
            'number of genes': genes,
            'number of disease':diseases
            }

        return stats

    def records_summary(self, panel):
        lgd_panels = LGDPanel.objects.filter(panel=panel.id).filter(is_deleted=0)

        lgd_panels_sel = lgd_panels.select_related('lgd', 'lgd__locus', 'lgd__disease', 'lgd__genotype', 'lgd__confidence'
                                               ).prefetch_related('lgd__lgd_variant_gencc_consequence', 'lgd__lgd_variant_type').order_by('-lgd__date_review')[:100]

        lgd_objects_list = list(lgd_panels_sel.values('lgd__locus__name',
                                                      'lgd__disease__name',
                                                      'lgd__genotype__value',
                                                      'lgd__confidence__value',
                                                      'lgd__lgdvariantgenccconsequence__variant_consequence__term',
                                                      'lgd__lgdvarianttype__variant_type_ot__term',
                                                      'lgd__date_review',
                                                      'lgd__stable_id'))

        aggregated_data = {}
        n_keys = 0
        for o in lgd_objects_list:
            if o['lgd__stable_id'] not in aggregated_data.keys() and n_keys < 10:
                variant_consequences = []
                variant_types = []

                variant_consequences.append(o['lgd__lgdvariantgenccconsequence__variant_consequence__term'])
                # Some records do not have variant types
                if o['lgd__lgdvarianttype__variant_type_ot__term'] is not None:
                    variant_types.append(o['lgd__lgdvarianttype__variant_type_ot__term'])

                aggregated_data[o['lgd__stable_id']] = { 'locus':o['lgd__locus__name'],
                                                         'disease':o['lgd__disease__name'],
                                                         'genotype':o['lgd__genotype__value'],
                                                         'confidence':o['lgd__confidence__value'],
                                                         'variant consequence':variant_consequences,
                                                         'variant type':variant_types,
                                                         'date review':o['lgd__date_review'],
                                                         'stable id':o['lgd__stable_id'] }
                n_keys += 1

            elif n_keys < 10:
                if o['lgd__lgdvariantgenccconsequence__variant_consequence__term'] not in aggregated_data[o['lgd__stable_id']]['variant consequence']:
                    aggregated_data[o['lgd__stable_id']]['variant consequence'].append(o['lgd__lgdvariantgenccconsequence__variant_consequence__term'])
                if o['lgd__lgdvarianttype__variant_type_ot__term'] not in aggregated_data[o['lgd__stable_id']]['variant type'] and o['lgd__lgdvarianttype__variant_type_ot__term'] is not None:
                    aggregated_data[o['lgd__stable_id']]['variant type'].append(o['lgd__lgdvarianttype__variant_type_ot__term'])

        return aggregated_data.values()

    class Meta:
        model = Panel
        fields = PanelSerializer.Meta.fields + ['curators', 'last_updated']

class UserSerializer(serializers.ModelSerializer):
    user = serializers.CharField(read_only=True, source="username")
    email = serializers.CharField(read_only=True)
    panels = serializers.SerializerMethodField()
    is_active = serializers.CharField(read_only=True)

    def get_panels(self, id):
        x = UserPanel.objects.filter(user=id)
        panels_list = []
        for p in x:
            panels_list.append(p.panel.name)
        return panels_list

    class Meta:
        model = User
        fields = ['user', 'email', 'is_active', 'panels']

class AttribTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttribType
        fields = ['code']

class AttribSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attrib
        fields = ['value']

class LGDPanelSerializer(serializers.ModelSerializer):
    panel = serializers.CharField(source="panel.name")

    class Meta:
        model = LGDPanel
        fields = ['panel']

class LocusSerializer(serializers.ModelSerializer):
    sequence = serializers.CharField(read_only=True, source="sequence.name")
    reference = serializers.CharField(read_only=True, source="sequence.reference.value")
    ids = serializers.SerializerMethodField()

    def get_ids(self, id):
        locus_ids = LocusIdentifier.objects.filter(locus=id)
        data = {}
        for id in locus_ids:
            data[id.source.name] = id.identifier

        return data

    class Meta:
        model = Locus
        fields = ['name', 'sequence', 'start', 'end', 'strand', 'reference', 'ids']

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
            return dates[-1]
        else:
            return []

    def records_summary(self):
        lgd_list = LocusGenotypeDisease.objects.filter(locus=self.id)
        lgd_select = lgd_list.select_related('disease', 'genotype', 'confidence'
                                               ).prefetch_related('lgd_panel', 'panel', 'lgd_variant_gencc_consequence', 'lgd_variant_type'
                                                                  ).order_by('-date_review')

        lgd_objects_list = list(lgd_select.values('disease__name',
                                                  'lgdpanel__panel__name',
                                                  'stable_id',
                                                  'genotype__value',
                                                  'confidence__value',
                                                  'lgdvariantgenccconsequence__variant_consequence__term',
                                                  'lgdvarianttype__variant_type_ot__term'))

        aggregated_data = {}
        for o in lgd_objects_list:
            if o['stable_id'] not in aggregated_data.keys():
                variant_consequences = []
                variant_types = []
                panels = []

                panels.append(o['lgdpanel__panel__name'])
                variant_consequences.append(o['lgdvariantgenccconsequence__variant_consequence__term'])
                if o['lgdvarianttype__variant_type_ot__term'] is not None:
                    variant_types.append(o['lgdvarianttype__variant_type_ot__term'])

                aggregated_data[o['stable_id']] = { 'disease':o['disease__name'],
                                                     'genotype':o['genotype__value'],
                                                     'confidence':o['confidence__value'],
                                                     'panels':panels,
                                                     'variant consequence':variant_consequences,
                                                     'variant type':variant_types,
                                                     'stable id':o['stable_id'] }

            else:
                if o['lgdpanel__panel__name'] not in aggregated_data[o['stable_id']]['panels']:
                    aggregated_data[o['stable_id']]['panels'].append(o['lgdpanel__panel__name'])
                if o['lgdvariantgenccconsequence__variant_consequence__term'] not in aggregated_data[o['stable_id']]['variant consequence']:
                    aggregated_data[o['stable_id']]['variant consequence'].append(o['lgdvariantgenccconsequence__variant_consequence__term'])
                if o['lgdvarianttype__variant_type_ot__term'] not in aggregated_data[o['stable_id']]['variant type'] and o['lgdvarianttype__variant_type_ot__term'] is not None:
                    aggregated_data[o['stable_id']]['variant type'].append(o['lgdvarianttype__variant_type_ot__term'])

        return aggregated_data.values()

    class Meta:
        model = Locus
        fields = LocusSerializer.Meta.fields + ['last_updated']

class LocusGenotypeDiseaseSerializer(serializers.ModelSerializer):
    locus = serializers.SerializerMethodField()
    genotype = serializers.CharField(source="genotype.value")
    mechanism = serializers.SerializerMethodField()
    disease = serializers.SerializerMethodField()
    confidence = serializers.CharField(source="confidence.value")
    publications = serializers.SerializerMethodField()
    panels = serializers.SerializerMethodField()
    cross_cutting_modifier = serializers.SerializerMethodField()
    variant_type = serializers.SerializerMethodField()
    phenotypes = serializers.SerializerMethodField()
    last_updated = serializers.CharField(source="date_review")
    created = serializers.SerializerMethodField()
    comments = serializers.SerializerMethodField()

    def get_locus(self, id):
        locus = LocusSerializer(id.locus).data
        return locus

    def get_disease(self, id):
        disease = DiseaseSerializer(id.disease).data
        return disease

    def get_mechanism(self, id):
        x = LGDVariantGenccConsequence.objects.filter(lgd_id=id)
        return MechanismSerializer(x, many=True).data

    def get_cross_cutting_modifier(self, id):
        x = LGDCrossCuttingModifier.objects.filter(lgd_id=id)
        return LGDCrossCuttingModifierSerializer(x, many=True).data

    def get_publications(self, id):
        x = LGDPublication.objects.filter(lgd_id=id)
        return LGDPublicationSerializer(x, many=True).data

    def get_phenotypes(self, id):
        x = LGDPhenotype.objects.filter(lgd_id=id)
        return LGDPhenotypeSerializer(x, many=True).data

    def get_variant_type(self, id):
        x = LGDVariantType.objects.filter(lgd_id=id)
        return VariantTypeSerializer(x, many=True).data

    def get_panels(self, id):
        x = LGDPanel.objects.filter(lgd_id=id)
        return LGDPanelSerializer(x, many=True).data

    def get_comments(self, id):
        lgd_comments = LGDComment.objects.filter(lgd_id=id)
        data = []
        for comment in lgd_comments:
            text = { 'text':comment.comment,
                     'date':comment.date }
            data.append(text)

        return data

    # This method depends on the history table
    # Leave it for now
    def get_created(self, id):
        x = LocusGenotypeDiseaseHistory.objects.filter(lgd_id=id.id)

        return ""

    class Meta:
        model = LocusGenotypeDisease
        exclude = ['id', 'is_deleted', 'date_review']
        read_only_fields = ['stable_id']

class MechanismSerializer(serializers.ModelSerializer):
    variant_consequence = serializers.CharField(source="variant_consequence.term")
    support = serializers.CharField(source="support.value")
    publication = serializers.CharField(source="publication.title", allow_null=True)

    class Meta:
        model = LGDVariantGenccConsequence
        fields = ['variant_consequence', 'support', 'publication']

class LGDCrossCuttingModifierSerializer(serializers.ModelSerializer):
    term = serializers.CharField(source="ccm.value")

    class Meta:
        model = LGDCrossCuttingModifier
        fields = ['term']

class LGDPublicationSerializer(serializers.ModelSerializer):
    pmid = serializers.CharField(source="publication.pmid")
    title = serializers.CharField(source="publication.title")
    publication_comments = serializers.SerializerMethodField()

    def get_publication_comments(self, id):
        data = []
        comments = PublicationComment.objects.filter(publication=id.publication.id)
        for comment in comments:
            text = { 'text':comment.comment,
                     'date':comment.date }
            data.append(text)

        return data

    class Meta:
        model = LGDPublication
        fields = ['pmid', 'title', 'publication_comments']

class DiseaseSerializer(serializers.ModelSerializer):
    name = serializers.CharField()
    mim = serializers.CharField()
    ontology_terms = serializers.SerializerMethodField()
    publications = serializers.SerializerMethodField()

    def get_ontology_terms(self, id):
        disease_ontologies = DiseaseOntology.objects.filter(disease=id)
        return DiseaseOntologySerializer(disease_ontologies, many=True).data

    def get_publications(self, id):
        disease_publications = DiseasePublication.objects.filter(disease=id)
        return DiseasePublicationSerializer(disease_publications, many=True).data

    class Meta:
        model = Disease
        fields = ['name', 'mim', 'ontology_terms', 'publications']

class DiseasePublicationSerializer(serializers.ModelSerializer):
    pmid = serializers.CharField(source="publication.pmid")
    title = serializers.CharField(source="publication.title")
    number_families = serializers.IntegerField(source="families")
    consanguinity = serializers.CharField()
    ethnicity = serializers.CharField()

    class Meta:
        model = DiseasePublication
        fields = ['pmid', 'title', 'number_families', 'consanguinity', 'ethnicity']

class DiseaseOntologySerializer(serializers.ModelSerializer):
    accession = serializers.CharField(source="ontology_term.accession")
    term = serializers.CharField(source="ontology_term.term")
    description = serializers.CharField(source="ontology_term.description")

    class Meta:
        model = DiseaseOntology
        fields = ['accession', 'term', 'description']

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