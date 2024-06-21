from rest_framework import serializers
from django.db import connection
from django.core.exceptions import ObjectDoesNotExist
from datetime import datetime

from ..models import (Panel, Attrib,
                     LGDPanel, LocusGenotypeDisease, LGDVariantGenccConsequence,
                     LGDCrossCuttingModifier, LGDPublication,
                     LGDPhenotype, LGDVariantType, Locus,
                     G2PStableID, LGDComment,
                     LGDMolecularMechanism, LGDMolecularMechanismEvidence,
                     OntologyTerm, Publication,
                     LGDVariantTypeDescription, CVMolecularMechanism)


from .publication import PublicationSerializer
from .locus import LocusSerializer
from .phenotype import PhenotypeSerializer
from .disease import DiseaseSerializer


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

                new_stable_id = create_stable_id()
                print(new_stable_id.stable_id)
                > 'G2P00001'
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

class LGDPanelSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="panel.name")
    description = serializers.CharField(source="panel.description", allow_null=True, required=False)

    def create(self, validated_data):
        """
            
        """

        lgd = self.context['lgd']
        panel_name = validated_data.get('panel')['name']

        # Check if panel name is valid
        panel_obj = Panel.objects.filter(name=panel_name)

        if not panel_obj.exists():
            raise serializers.ValidationError({"message": f"Invalid panel name '{panel_name}'"})

        try:
            lgd_panel_obj = LGDPanel.objects.get(panel=panel_obj.first().id, lgd=lgd.id)

        except LGDPanel.DoesNotExist:
            # Create LGDPanel
            lgd_panel_obj = LGDPanel.objects.create(
                lgd=lgd,
                panel=panel_obj.first(),
                is_deleted=0
            )

        else:
            # The LGDPanel exists
            # Is it deleted? If not deleted then the entry already exists
            if lgd_panel_obj.is_deleted == 0:
                raise serializers.ValidationError({"message": f"G2P entry {lgd.stable_id.stable_id} is already linked to panel {panel_name}"})
            else:
                # If deleted then update to not deleted
                lgd_panel_obj.is_deleted = 0
                lgd_panel_obj.save()
        
        return lgd_panel_obj

    class Meta:
        model = LGDPanel
        fields = ['name', 'description']

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
        queryset = LGDPanel.objects.filter(lgd_id=id, is_deleted=0)
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

        if synopsis_name != "":
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
