from rest_framework import serializers
from django.db import connection
from datetime import datetime

from ..models import (Panel, Attrib,
                     LGDPanel, LocusGenotypeDisease, LGDVariantGenccConsequence,
                     LGDCrossCuttingModifier, LGDPublication,
                     LGDPhenotype, LGDVariantType, Locus,
                     LGDComment, LGDVariantTypeComment,
                     LGDMolecularMechanism, LGDMolecularMechanismEvidence,
                     OntologyTerm, Publication, LGDPhenotypeSummary,
                     LGDVariantTypeDescription, CVMolecularMechanism)


from .publication import LGDPublicationSerializer
from .locus import LocusSerializer
from .disease import DiseaseSerializer
from .panel import LGDPanelSerializer


class LocusGenotypeDiseaseSerializer(serializers.ModelSerializer):
    """
        Serializer for the LocusGenotypeDisease model.
        LocusGenotypeDisease represents a G2P record.
    """

    locus = serializers.SerializerMethodField() # part of the unique entry
    stable_id = serializers.CharField(source="stable_id.stable_id", read_only=True) #CharField and the source is the stable_id column in the stable_id table
    genotype = serializers.CharField(source="genotype.value", read_only=True) # part of the unique entry
    variant_consequence = serializers.SerializerMethodField(allow_null=True)
    molecular_mechanism = serializers.SerializerMethodField(allow_null=True)
    disease = serializers.SerializerMethodField() # part of the unique entry
    confidence = serializers.CharField(source="confidence.value")
    confidence_support = serializers.CharField(allow_blank=True, required=False)
    publications = serializers.SerializerMethodField()
    panels = serializers.SerializerMethodField()
    cross_cutting_modifier = serializers.SerializerMethodField(allow_null=True)
    variant_type = serializers.SerializerMethodField(allow_null=True)
    variant_description = serializers.SerializerMethodField(allow_null=True)
    phenotypes = serializers.SerializerMethodField(allow_null=True)
    phenotype_summary = serializers.SerializerMethodField(allow_null=True)
    last_updated = serializers.SerializerMethodField()
    date_created = serializers.SerializerMethodField()
    comments = serializers.SerializerMethodField(allow_null=True)
    is_reviewed = serializers.IntegerField(allow_null=True, required=False)

    def get_locus(self, id):
        """
            Locus linked to the LGD record.
            It can be a gene, variant or region.
        """
        locus = LocusSerializer(id.locus).data
        return locus

    def get_disease(self, id):
        """
            Disease associated with the LGD record.
        """
        disease = DiseaseSerializer(id.disease).data
        return disease

    def get_last_updated(self, obj):
        """
            Date last time the LGD record was updated by a curator.
        """
        if obj.date_review is not None:
            return obj.date_review.strftime("%Y-%m-%d")
        else: 
            return None

    def get_variant_consequence(self, id):
        """
            Variant consequences linked to the LGD record.
            This is the GenCC level of variant consequence: altered_gene_product_level, etc.
        """
        queryset = LGDVariantGenccConsequence.objects.filter(lgd_id=id, is_deleted=0)
        return LGDVariantGenCCConsequenceSerializer(queryset, many=True).data

    def get_molecular_mechanism(self, id):
        """
            Molecular mechanisms associated with the LGD record.
        """
        queryset = LGDMolecularMechanism.objects.filter(lgd_id=id, is_deleted=0)
        return LGDMolecularMechanismSerializer(queryset, many=True).data

    def get_cross_cutting_modifier(self, id):
        """
            Cross cutting modifier terms associated with the LGD record.
        """
        queryset = LGDCrossCuttingModifier.objects.filter(lgd_id=id, is_deleted=0)
        return LGDCrossCuttingModifierSerializer(queryset, many=True).data

    def get_publications(self, id):
        """
            Publications associated with the LGD record.
        """
        queryset = LGDPublication.objects.filter(lgd_id=id, is_deleted=0)
        # It is necessary to send the user to return public/private comments
        return LGDPublicationSerializer(queryset, context={'user': self.context.get('user')}, many=True).data

    def get_phenotypes(self, id):
        """
            Phenotypes associated with the LGD record.
            The response includes the list of publications associated with the phenotype.
        """
        queryset = LGDPhenotype.objects.filter(lgd_id=id, is_deleted=0).prefetch_related()
        data = {}

        for lgd_phenotype in queryset:
            accession = lgd_phenotype.phenotype.accession
            publication = lgd_phenotype.publication

            if accession in data and publication:
                data[accession]["publications"].append(publication.pmid)
            else:
                publication_list = []
                if publication:
                    publication_list = [publication.pmid]

                data[accession] = {"term": lgd_phenotype.phenotype.term,
                                   "accession": accession,
                                   "publications": publication_list}

        return data.values()

    def get_phenotype_summary(self, id):
        """
            A summary about the phenotypes associated with the LGD record.
            The response includes the list of publications associated with the summary.
        """
        # The LGD record is supposed to have one summary
        # but one summary can be linked to several publications
        queryset = LGDPhenotypeSummary.objects.filter(lgd_id=id, is_deleted=0).prefetch_related()
        data = {}

        for summary_obj in queryset:
            summary_text = summary_obj.summary
            publication = summary_obj.publication

            if summary_text in data and publication:
                data[summary_text]["publications"].append(publication.pmid)
            else:
                publication_list = []
                if publication:
                    publication_list = [publication.pmid]

                data[summary_text] = { "summary": summary_text, "publications": publication_list }

        return data.values()

    def get_variant_type(self, id):
        """
            Variant types associated with the LGD record.
            The variant type can be linked to several publications therefore response 
            includes the list of publications associated with the variant type.
        """
        queryset = LGDVariantType.objects.filter(lgd_id=id, is_deleted=0).prefetch_related()
        data = {}

        for lgd_variant in queryset:
            accession = lgd_variant.variant_type_ot.accession

            if accession in data and lgd_variant.publication:
                data[accession]["publications"].append(lgd_variant.publication.pmid)
            else:
                publication_list = []
                if lgd_variant.publication:
                    publication_list = [lgd_variant.publication.pmid]

                data[accession] = {
                    "term": lgd_variant.variant_type_ot.term,
                    "accession": accession,
                    "inherited": lgd_variant.inherited,
                    "de_novo": lgd_variant.de_novo,
                    "unknown_inheritance": lgd_variant.unknown_inheritance,
                    "publications": publication_list
                }

        return data.values()

    def get_variant_description(self, id):
        """
            Variant HGVS description linked to the LGD record and publication(s).
            The response includes a list of publications associated with the HGVS description.
        """
        queryset = LGDVariantTypeDescription.objects.filter(lgd_id=id, is_deleted=0).prefetch_related()
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
        """
            Panel(s) associated with the LGD record.
        """
        queryset = LGDPanel.objects.filter(lgd_id=id, is_deleted=0)
        return LGDPanelSerializer(queryset, many=True).data

    def get_comments(self, id):
        """
            LGD record comments.
            Comments can be public or private. Private comments can only be
            seen by curators.
        """
        # TODO check if comment is public
        lgd_comments = LGDComment.objects.filter(lgd_id=id, is_deleted=0).prefetch_related()
        data = []
        for comment in lgd_comments:
            text = { 'text':comment.comment,
                     'date':comment.date }
            data.append(text)

        return data

    def get_date_created(self, id):
        """
            Date the LGD record was created.
            Dependency: this method depends on the history table.
            
            Note: entries that were migrated from the old db don't have the date when they were created.
        """
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
            Method to create a G2P record (LGD record).
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
                except Panel.DoesNotExist:
                    raise serializers.ValidationError({"message": f"Invalid panel {panel}"})
                else:
                    data_panel = {"name": panel_obj.name}

                    # The LGDPanelSerializer fetches the object LGD from its context
                    lgd_panel_serializer = LGDPanelSerializer(data=data_panel, context={'lgd': lgd_obj})

                    # Validate the input data
                    if lgd_panel_serializer.is_valid(raise_exception=True):
                        # Save the lgd-panel data, which will call the create method
                        lgd_panel_serializer.save()

            # Insert LGD-publications
            # If the publication (PMID) is not in G2P, it will create the Publication obj
            # Example: publications_list = [{ "pmid": 1234,
            #                                 "comment": {"comment": "comment text", "is_public": 1},
            #                                 "families": {
            #                                        "families": 5, 
            #                                        "consanguinity": "", 
            #                                        "ancestries": "", 
            #                                        "affected_individuals": 5
            #                                  }
            #                              }]
            for publication_data in publications_list:
                # PublicationSerializer is instantiated with the publication data and context
                lgd_publication_serializer = LGDPublicationSerializer(
                    # the data argument accepts all the publication data (pmid, families, comment)
                    # pass the user info and the lgd obj as context
                    data={'publication':publication_data},
                    context={
                        'lgd': lgd_obj,
                        'user': self.context.get('user')
                        }
                )

                # Validate the publication data
                if lgd_publication_serializer.is_valid(raise_exception=True):
                    # Save the lgd-publication data which will call the create method
                    lgd_publication_serializer.save()

        return lgd_obj

    def update(self, instance, validated_data):
        # validated_data example:
        # {'confidence': {'value': 'definitive'}, 'confidence_support': '', 'is_reviewed': None}
        confidence = validated_data.get("confidence")["value"]
        confidence_support = validated_data.get("confidence_support")
        is_reviewed = validated_data.get("is_reviewed")

        # Get confidence
        try:
            confidence_obj = Attrib.objects.get(
                value = confidence,
                type__code = "confidence_category"
            )
        except Attrib.DoesNotExist:
            raise serializers.ValidationError({"message": f"Invalid confidence value {confidence}"})

        # Check new confidence is not the same as current value
        if(instance.confidence == confidence_obj):
            raise serializers.ValidationError(
                {"message": f"G2P record '{instance.stable_id.stable_id}' already has confidence value {confidence}"}
            )

        # Update confidence
        instance.confidence = confidence_obj

        if(confidence_support != ""):
            # Update confidence support
            instance.confidence_support = confidence_support

        # is_reviewed only accepts 1 or 0
        if(is_reviewed is not None and (is_reviewed == 1 or is_reviewed == 0)):
            instance.is_reviewed = is_reviewed

        # Save all updates
        instance.save()

        return instance

    class Meta:
        model = LocusGenotypeDisease
        exclude = ['id', 'is_deleted', 'date_review']

class LGDCommentSerializer(serializers.ModelSerializer):
    """
        Serializer for the LGDComment model.
    """

    def create(self, data):
        """
            Method to add a comment to a G2P entry.
        """

        comment = data.get("comment")
        is_public = data.get("is_public")
        lgd = self.context["lgd"]
        user = self.context["user"]

        # Check if this comment is already linked to the G2P entry
        lgd_comments = LGDComment.objects.filter(lgd_id=lgd, is_deleted=0, comment=comment)

        if lgd_comments:
            raise serializers.ValidationError({"message": f"Comment is already associated with {lgd.stable_id.stable_id}"})

        else:
            lgd_comment_obj = LGDComment.objects.create(
                    lgd = lgd,
                    comment = comment,
                    is_public = is_public,
                    is_deleted = 0,
                    user = user,
                    date = datetime.now()
                )

        return lgd_comment_obj

    class Meta:
        model = LGDComment
        exclude = ['id', 'is_deleted', 'lgd', 'date', 'user']

class LGDVariantGenCCConsequenceSerializer(serializers.ModelSerializer):
    """
        Serializer for the LGDVariantGenccConsequence model.
    """

    variant_consequence = serializers.CharField(source="variant_consequence.term")
    support = serializers.CharField(source="support.value")
    publication = serializers.CharField(source="publication.pmid", allow_null=True, required=False)

    def create(self, validated_data):
        """
            Add a Variant GenCC consequence to a LGD record.

            Args:
                (dict) validated data: variant_consequence and support
                Example:
                        {
                            'support': 'inferred',
                            'variant_consequence': 'altered_gene_product_structure'
                        }

            Output: 
                LGDVariantGenCCConsequence object
            
            Raises:
                Raise error if variant consequence term is invalid
                Raise error if support value is invalid
        """

        lgd = self.context['lgd']
        term = validated_data.get("variant_consequence")["term"].replace("_", " ")
        support = validated_data.get("support")["value"].lower()

        # Get variant gencc consequence value from ontology_term
        # Possible values: absent gene product, altered gene product structure, etc.
        try:
            consequence_obj = OntologyTerm.objects.get(
                term = term, # TODO check
                group_type__value = "variant_type"
            )
        except OntologyTerm.DoesNotExist:
            raise serializers.ValidationError({"message": f"Invalid variant consequence '{term}'"})

        # Get support value from attrib
        # Values: evidence or inferred
        try:
            support_obj = Attrib.objects.get(
                value = support,
                type__code = "support"
            )
        except Attrib.DoesNotExist:
            raise serializers.ValidationError({"message": f"Invalid support value '{support}'"})

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

class LGDVariantConsequenceListSerializer(serializers.Serializer):
    """
        Serializer to accept a list of variant GenCC consequences.
        Called by: LGDAddVariantConsequences()
    """
    variant_consequences = LGDVariantGenCCConsequenceSerializer(many=True)

class LGDMolecularMechanismSerializer(serializers.ModelSerializer):
    """
        Serializer for the LGDMolecularMechanism model.
        A molecular mechanism can have a synopsis and/or evidence(s).
        If the support is 'evidence' then the type of evidence has to
        be provided.
        By default, support is 'inferred'.
    """
    mechanism = serializers.CharField(source="mechanism.value") # Foreign Key to CVMolecularMechanism
    support = serializers.CharField(source="mechanism_support.value") # default value = 'inferred'
    description = serializers.CharField(source="mechanism_description", allow_null=True) # optional
    synopsis = serializers.CharField(source="synopsis.value", allow_null=True) # optional
    synopsis_support = serializers.CharField(source="synopsis_support.value", allow_null=True) # optional
    evidence = serializers.SerializerMethodField() # only necessary if support = 'evidence'

    def get_evidence(self, id):
        """
            Return the mechanism evidence associated with the LGDMolecularMechanism by publication.
            There are different types of evidence: function, models, rescue, etc.

            Output example:
                            "evidence": {
                                "11235": {
                                    "function": [
                                        "biochemical",
                                        "protein interaction"
                                    ],
                                    "functional_alteration": [
                                        "patient cells"
                                    ]
                                }
                            }
        """
        evidence_list = LGDMolecularMechanismEvidence.objects.filter(
            molecular_mechanism=id,
            is_deleted=0
            ).select_related('evidence', 'publication').values(
                'publication__pmid',
                'evidence__value',
                'evidence__subtype'
            ).order_by('publication')

        data = {}

        for evidence in evidence_list:
            evidence_value = evidence["evidence__value"]
            # The evidence subtype is always populated
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
        """
            Create LGDMolecularMechanism and LGDMolecularMechanismEvidence (if support = 'evidence')
        """
    
        lgd = self.context['lgd']
        mechanism_name = mechanism["name"]
        mechanism_support = mechanism["support"]
        synopsis_name = mechanism_synopsis["name"] # optional
        synopsis_support = mechanism_synopsis["support"] # optional
        synopsis_obj = None
        synopsis_support_obj = None

        # If the mechanism support is 'evidence' then the evidence has to be provided
        # Check if data has been provided
        if mechanism_support == "evidence" and not mechanism_evidence:
            raise serializers.ValidationError({"message": f"Mechanism is missing the evidence"})

        # Get mechanism value from controlled vocabulary table for molecular mechanism
        try:
            mechanism_obj = CVMolecularMechanism.objects.get(
                value = mechanism_name,
                type = "mechanism"
            )
        except CVMolecularMechanism.DoesNotExist:
            raise serializers.ValidationError({"message": f"Invalid mechanism value '{mechanism_name}'"})

        # Get mechanism support from controlled vocabulary table for molecular mechanism
        try:
            mechanism_support_obj = CVMolecularMechanism.objects.get(
                value = mechanism_support,
                type = "support"
            )
        except CVMolecularMechanism.DoesNotExist:
            raise serializers.ValidationError({"message": f"Invalid mechanism support value '{mechanism_support}'"})

        # Synopsis is optional
        if synopsis_name:
            # Get mechanism synopsis value from controlled vocabulary table for molecular mechanism
            try:
                synopsis_obj = CVMolecularMechanism.objects.get(
                    value = synopsis_name,
                    type = "mechanism_synopsis"
                )
            except CVMolecularMechanism.DoesNotExist:
                raise serializers.ValidationError({"message": f"Invalid mechanism synopsis value '{synopsis_name}'"})

            # Get mechanism synopsis support from controlled vocabulary table for molecular mechanism
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

        # Insert the mechanism evidence (if applicable)
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

                        # Values are stored in cv_molecular_mechanism table
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
    """
        Serializer for the LGDCrossCuttingModifier model.
        A G2P record can be linked to one or more cross cutting modifier.
    """

    term = serializers.CharField(source="ccm.value")

    def create(self, validate_data):
        """
            Add cross cutting modifier to LGD record.

            Args:
                (string) cross cutting modifier value

            Returns:
                LGDCrossCuttingModifier object

            Raises:
                Raise error if cross cutting modifier value is invalid
                Raise error if cross cutting modifier already linked to LGD record
        """

        lgd = self.context['lgd']
        term = validate_data.get("ccm")["value"]

        # Get cross cutting modifier from attrib
        try:
            ccm_obj = Attrib.objects.get(
                value = term,
                type__code = 'cross_cutting_modifier'
            )
        except Attrib.DoesNotExist:
            raise serializers.ValidationError({"message": f"Invalid cross cutting modifier '{term}'"})

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
        else:
            # LGD-cross cutting modifier already exists
            # If not deleted then the entry already exists
            if lgd_ccm_obj.is_deleted == 0:
                raise serializers.ValidationError({"message": f"G2P entry {lgd.stable_id.stable_id} is already linked to cross cutting modifier '{term}'"})
            else:
                # If deleted then update it to not deleted
                lgd_ccm_obj.is_deleted = 0
                lgd_ccm_obj.save()

        return lgd_ccm_obj

    class Meta:
        model = LGDCrossCuttingModifier
        fields = ['term']

class LGDCrossCuttingModifierListSerializer(serializers.Serializer):
    """
        Serializer to accept a list of cross cutting modifiers.
        Called by: LocusGenotypeDiseaseAddCCM()
    """
    cross_cutting_modifiers = LGDCrossCuttingModifierSerializer(many=True)

class LGDVariantTypeCommentSerializer(serializers.ModelSerializer):
    """
        Serializer for the LGDVariantTypeComment model.
        Comment associated with the variant type that is linked to the G2P record.
        A comment can be public or private. Private comments can only be seen
        by curators.
    """
    comment = serializers.CharField()
    user = serializers.CharField(source="user.username")
    date = serializers.CharField()

    class Meta:
        model = LGDVariantTypeComment
        fields = ['comment', 'user', 'date']

class LGDVariantTypeSerializer(serializers.ModelSerializer):
    """
        Serializer for the LGDVariantType model.

        Types of variants reported in publications:
            missense_variant, frameshift_variant, stop_gained, etc.
        Sequence ontology terms are used to describe variant types.
    """

    term = serializers.CharField(source="variant_type_ot.term", required=False)
    accession = serializers.CharField(source="variant_type_ot.accession", required=False) # Sequence ontology term
    inherited = serializers.BooleanField(allow_null=True)
    de_novo = serializers.BooleanField(allow_null=True)
    unknown_inheritance = serializers.BooleanField(allow_null=True)
    publication = serializers.IntegerField(source="publication.pmid", allow_null=True, required=False)
    comments = LGDVariantTypeCommentSerializer(many=True, required=False)
    # Extra fields for the create() method
    secondary_type = serializers.CharField(write_only=True) # variant type term (used by curation)
    supporting_papers = serializers.ListField(write_only=True) # list of pmids (used by curation)
    nmd_escape = serializers.BooleanField(write_only=True) # flag (used by curation)
    comment = serializers.CharField(write_only=True, allow_blank=True) # single comment (used by curation)

    def create(self, validated_data):
        """
            Method to create LGDVariantType object.
            A G2P record can be associated with one or more variant types.

            Returns:
                    LGDVariantType object
        """

        user_obj = self.context['user']
        lgd = self.context['lgd']
        inherited = validated_data.get("inherited")
        de_novo = validated_data.get("de_novo")
        unknown_inheritance = validated_data.get("unknown_inheritance")
        var_type = validated_data.get("secondary_type", None) # Used by curation
        publications = validated_data.get("supporting_papers", None) # Used by curation
        comment = validated_data.get("comment", None)  # Used by curation

        # Get variant type from ontology_term
        # nmd_escape list: frameshift_variant, stop_gained, splice_region_variant?, splice_acceptor_variant,
        # splice_donor_variant
        # We save the variant types already with the NMD_escape attached to the term
        if validated_data.get("nmd_escape", None) is True:
            var_type = f"{var_type}_NMD_escaping"

        try:
            var_type_obj = OntologyTerm.objects.get(
                term = var_type,
                group_type__value = "variant_type"
            )
        except OntologyTerm.DoesNotExist:
            raise serializers.ValidationError({"message": f"Invalid variant type '{var_type}'"})

        # Variants are supposed to be linked to publications
        # But if there is no publication then create the object without a pmid
        if not publications:
            try:
                lgd_variant_type_obj = LGDVariantType.objects.get(
                    lgd = lgd,
                    variant_type_ot = var_type_obj,
                    inherited = inherited,
                    de_novo = de_novo,
                    unknown_inheritance = unknown_inheritance,
                    publication = None,
                    is_deleted = 0
                )
            except LGDVariantType.DoesNotExist:
                lgd_variant_type_obj = LGDVariantType.objects.create(
                    lgd = lgd,
                    variant_type_ot = var_type_obj,
                    inherited = inherited,
                    de_novo = de_novo,
                    unknown_inheritance = unknown_inheritance,
                    is_deleted = 0
                )

            # The LGDPhenotypeSummary is created - next step is to create the LGDVariantTypeComment
            if(comment != ""):
                try:
                    lgd_comment_obj = LGDVariantTypeComment.objects.get(
                        comment = comment,
                        lgd_variant_type = lgd_variant_type_obj,
                        is_public = 1, # TODO: update
                        user = user_obj,
                    )
                except LGDVariantTypeComment.DoesNotExist:
                    lgd_comment_obj = LGDVariantTypeComment.objects.create(
                        comment = comment,
                        lgd_variant_type = lgd_variant_type_obj,
                        is_public = 1, # TODO: update
                        is_deleted = 0,
                        user = user_obj,
                        date = datetime.now()
                    ) 
                else:
                    if(lgd_comment_obj.is_deleted == 1):
                        lgd_comment_obj.is_deleted = 0
                        lgd_comment_obj.save()

        else:
            # Variant type is linked to publication(s)
            # A single variant type can be attached to several publications - create an object for each pmid
            for publication in publications:
                try:
                    # The publication is supposed to be stored in the G2P db
                    publication_obj = Publication.objects.get(pmid=publication)

                except Publication.DoesNotExist:
                    raise serializers.ValidationError(
                        {"message": f"Invalid publication '{publication}'"}
                    )

                else:
                    # The publication is valid
                    # Check if LGDVariantType object already exists in db
                    try:
                        lgd_variant_type_obj = LGDVariantType.objects.get(
                            lgd = lgd,
                            variant_type_ot = var_type_obj,
                            inherited = inherited,
                            de_novo = de_novo,
                            unknown_inheritance = unknown_inheritance,
                            publication = publication_obj,
                            is_deleted = 0
                        )
                    except LGDVariantType.DoesNotExist:
                        # Check if LGDVariantType object already exists in db without a publication
                        try:
                            lgd_variant_type_obj = LGDVariantType.objects.get(
                                lgd = lgd,
                                variant_type_ot = var_type_obj,
                                inherited = inherited,
                                de_novo = de_novo,
                                unknown_inheritance = unknown_inheritance,
                                publication = None, # no publication attached to entry
                                is_deleted = 0
                            )
                        except LGDVariantType.DoesNotExist:
                            # LGDVariantType does not exist with or without publication
                            # Create LGDVariantType object with publication
                            lgd_variant_type_obj = LGDVariantType.objects.create(
                                lgd = lgd,
                                variant_type_ot = var_type_obj,
                                inherited = inherited,
                                de_novo = de_novo,
                                unknown_inheritance = unknown_inheritance,
                                publication = publication_obj,
                                is_deleted = 0
                            )
                        else:
                            # LGDVariantType already exists in the db without a publication
                            # Add publication to existing object
                            lgd_variant_type_obj.publication = publication_obj
                            lgd_variant_type_obj.save()

                    # The LGDPhenotypeSummary is created - next step is to create the LGDVariantTypeComment
                    if(comment != ""):
                        try:
                            lgd_comment_obj = LGDVariantTypeComment.objects.get(
                                comment = comment,
                                lgd_variant_type = lgd_variant_type_obj,
                                is_public = 1, # TODO: update
                                user = user_obj,
                            )
                        except LGDVariantTypeComment.DoesNotExist:
                            lgd_comment_obj = LGDVariantTypeComment.objects.create(
                                comment = comment,
                                lgd_variant_type = lgd_variant_type_obj,
                                is_public = 1, # TODO: update
                                is_deleted = 0,
                                user = user_obj,
                                date = datetime.now()
                            ) 
                        else:
                            if(lgd_comment_obj.is_deleted == 1):
                                lgd_comment_obj.is_deleted = 0
                                lgd_comment_obj.save()

        return 1

    class Meta:
        model = LGDVariantType
        fields = ['term', 'accession', 'inherited', 'de_novo', 'unknown_inheritance', 
                  'publication', 'comments', 'secondary_type', 'supporting_papers', 'nmd_escape', 'comment']

class LGDVariantTypeListSerializer(serializers.Serializer):
    """
        Serializer to accept a list of variant types.
        Called by: LGDAddVariantTypes()
    """
    variant_types = LGDVariantTypeSerializer(many=True)

class LGDVariantTypeDescriptionSerializer(serializers.ModelSerializer):
    """
        The variant HGVS description is linked to:
            - LGD record (mandatory)
            - publication (mandatory)

        This serializer is called by curation and LGDAddVariantTypeDescriptions.
        In the curation data, the description is linked to one pmid (multiple pmids
        are represented multiple times attached to the same description).
        Meanwhile in LGDAddVariantTypeDescriptions the description is linked to a list of pmids.
    """

    publication = serializers.IntegerField(required=False) # Used by curation
    description = serializers.CharField() # HGVS description following HGVS standard
    # Extra fields for create() method
    publications = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False
    ) # Used by views.LGDAddVariantTypeDescriptions

    def create(self, validated_data):
        """
            Method to create LGDVariantTypeDescription object.
            LGDVariantTypeDescription represents the variant HGVS 
            linked to the LGD record and the publication.
            The HGVS is not directly linked to the variant type.

            Returns: 1

            Raises: Invalid publication
        """

        lgd = self.context['lgd']
        publication = validated_data.get("publication") # Used by curation
        description = validated_data.get("description")
        list_publications = validated_data.get("publications", []) # Used by views.LGDAddVariantTypeDescriptions

        # Create the list of pmids from the single publication sent by curation
        if(not list_publications and publication):
            list_publications.append(publication)

        # Insert data based on the pmids
        # The variant description is supposed to be linked to publications
        for pmid in list_publications:
            try:
                publication_obj = Publication.objects.get(pmid=pmid)
            except Publication.DoesNotExist:
                raise serializers.ValidationError(
                        {"message": f"Invalid publication '{publication}'"}
                    )

            # Check if LGDVariantTypeDescription exists
            try:
                lgd_variant_type_desc = LGDVariantTypeDescription.objects.get(
                    lgd = lgd,
                    description = description,
                    publication = publication_obj
                )
            except LGDVariantTypeDescription.DoesNotExist:
                lgd_variant_type_desc = LGDVariantTypeDescription.objects.create(
                    lgd = lgd,
                    description = description,
                    publication = publication_obj,
                    is_deleted = 0
                )
            else:
                # If LGDVariantTypeDescription exists and it is deleted
                # then set existing entry to not deleted
                if(lgd_variant_type_desc.is_deleted == 1):
                    lgd_variant_type_desc.is_deleted = 0
                    lgd_variant_type_desc.save()
        
        return 1

    class Meta:
        model = LGDVariantTypeDescription
        fields = ['publication', 'description', 'publications']

class LGDVariantTypeDescriptionListSerializer(serializers.Serializer):
    """
        Serializer to accept a list of variant type descriptions (HGVS).
        Called by: LGDAddVariantTypeDescriptions()
    """
    variant_descriptions = LGDVariantTypeDescriptionSerializer(many=True)
