from rest_framework import serializers
from django.db.models import Q
import re

from ..models import (
    Disease,
    DiseaseOntologyTerm,
    DiseaseSynonym,
    Attrib,
    LocusGenotypeDisease,
    OntologyTerm,
    Source,
    GeneDisease
)

from ..utils import (
    clean_string,
    get_ontology,
    get_ontology_source
)


class DiseaseOntologyTermSerializer(serializers.ModelSerializer):
    """
        Serializer for the DiseaseOntologyTerm model.
        Links the disease to ontology terms imported from external ontology sources.
    """

    accession = serializers.CharField(source="ontology_term.accession")
    term = serializers.CharField(source="ontology_term.term", required=True)
    description = serializers.CharField(source="ontology_term.description", allow_null=True, required=False) # the description is optional
    source = serializers.CharField(source="ontology_term.source.name", required=True) # external source (ex: OMIM)

    def create(self, validated_data):
        """
            Add new disease-ontology term.

            This method is only called if the data passes the validation.

            Args:
                validate_data: ontology_term (dict)

            Returns:
                    DiseaseOntologyTerm object
        """

        disease_obj = self.context["disease"]
        # Get mandatory fields
        ontology_accession = validated_data.get("ontology_term")["accession"]
        ontology_term = validated_data.get("ontology_term")["term"]
        ontology_source = validated_data.get("ontology_term")["source"]
        # Get optional fields
        ontology_desc = None
        if "description" in validated_data.get("ontology_term"):
            ontology_desc = validated_data.get("ontology_term")["description"]

        disease_ontology_obj = None

        # Check if ontology is in db
        # The disease ontology is saved in the db as attrib type 'disease'
        try:
            ontology_obj = OntologyTerm.objects.get(accession=ontology_accession)

        except OntologyTerm.DoesNotExist:
            source = Source.objects.get(name=ontology_source["name"])
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

        try:
            attrib = Attrib.objects.get(
                value="Data source",
                type__code = "ontology_mapping"
            )
        except Attrib.DoesNotExist:
            raise serializers.ValidationError({
                "message": f"Cannot find attrib 'Data source'"
            })

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

        return disease_ontology_obj

    class Meta:
        model = DiseaseOntologyTerm
        fields = ['accession', 'term', 'description', 'source']

class DiseaseOntologyTermListSerializer(serializers.Serializer):
    """
        Serializer to accept a list of disease ontologies.
        Called by: view DiseaseUpdateReferences()
    """
    disease_ontologies = DiseaseOntologyTermSerializer(many=True)

class DiseaseSerializer(serializers.ModelSerializer):
    """
        Serializer for the Disease model.
        This serializer returns the ontology terms associated with the disease
        and synonyms names.
    """

    name = serializers.CharField()
    ontology_terms = serializers.SerializerMethodField()
    synonyms = serializers.SerializerMethodField()

    def get_ontology_terms(self, id):
        """
            Returns the ontology terms associated with the disease.
        """
        disease_ontologies = DiseaseOntologyTerm.objects.filter(disease=id)
        return DiseaseOntologyTermSerializer(disease_ontologies, many=True).data

    def get_synonyms(self, id):
        """
            Returns disease synonyms used in other sources.
        """
        synonyms = []
        disease_synonyms = DiseaseSynonym.objects.filter(disease=id)
        for d_synonym in disease_synonyms:
            synonyms.append(d_synonym.synonym)
        return synonyms

    class Meta:
        model = Disease
        fields = ['name', 'ontology_terms', 'synonyms']

class DiseaseDetailSerializer(DiseaseSerializer):
    """
        Serializer for the Disease model - extra fields.
    """
    last_updated = serializers.SerializerMethodField()

    def get_last_updated(self, id):
        """
            Returns the date an entry linked to the disease has been updated.
        """
        disease_last_update = None

        filtered_lgd_list = LocusGenotypeDisease.objects.filter(
            disease=id,
            is_reviewed=1,
            is_deleted=0,
            date_review__isnull=False
            ).order_by('-date_review')

        if filtered_lgd_list:
            disease_last_update = filtered_lgd_list.first().date_review

        return disease_last_update.date() if disease_last_update else None

    def records_summary(self, id, user):
        """
            Returns a summary of the LGD records associated with the disease.
            If the user is non-authenticated:
                - only returns records linked to visible panels
        """
        if user.is_authenticated:
            lgd_select = LocusGenotypeDisease.objects.filter(disease=id, is_deleted=0).select_related('locus', 'genotype', 'confidence', 'mechanism'
                                               ).prefetch_related('lgd_panel', 'panel', 'lgd_variant_gencc_consequence', 'lgd_variant_type', 'g2pstable_id'
                                                                  ).order_by('-date_review')

        else:
            lgd_select = LocusGenotypeDisease.objects.filter(disease=id, is_deleted=0, lgdpanel__panel__is_visible=1).select_related(
                'locus', 'genotype', 'confidence', 'mechanism'
                ).prefetch_related('lgd_panel', 'panel', 'lgd_variant_gencc_consequence', 'lgd_variant_type', 'g2pstable_id'
                                    ).order_by('-date_review')

        lgd_objects_list = list(lgd_select.values('locus__name',
                                                  'lgdpanel__panel__name',
                                                  'stable_id__stable_id', # to get the stable_id stableID
                                                  'genotype__value',
                                                  'confidence__value',
                                                  'lgdvariantgenccconsequence__variant_consequence__term',
                                                  'lgdvarianttype__variant_type_ot__term',
                                                  'mechanism__value'))

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

                aggregated_data[lgd_obj['stable_id__stable_id']] = { 'locus':lgd_obj['locus__name'],
                                                          'genotype':lgd_obj['genotype__value'],
                                                          'confidence':lgd_obj['confidence__value'],
                                                          'panels':panels,
                                                          'variant_consequence':variant_consequences,
                                                          'variant_type':variant_types,
                                                          'molecular_mechanism':lgd_obj['mechanism__value'],
                                                          'stable_id':lgd_obj['stable_id__stable_id'] }

            else:
                if lgd_obj['lgdpanel__panel__name'] not in aggregated_data[lgd_obj['stable_id__stable_id']]['panels']:
                    aggregated_data[lgd_obj['stable_id__stable_id']]['panels'].append(lgd_obj['lgdpanel__panel__name'])
                if lgd_obj['lgdvariantgenccconsequence__variant_consequence__term'] not in aggregated_data[lgd_obj['stable_id__stable_id']]['variant_consequence']:
                    aggregated_data[lgd_obj['stable_id__stable_id']]['variant_consequence'].append(lgd_obj['lgdvariantgenccconsequence__variant_consequence__term'])
                if lgd_obj['lgdvarianttype__variant_type_ot__term'] not in aggregated_data[lgd_obj['stable_id__stable_id']]['variant_type'] and lgd_obj['lgdvarianttype__variant_type_ot__term'] is not None:
                    aggregated_data[lgd_obj['stable_id__stable_id']]['variant_type'].append(lgd_obj['lgdvarianttype__variant_type_ot__term'])

        return aggregated_data.values()

    class Meta:
        model = Disease
        fields = DiseaseSerializer.Meta.fields + ['last_updated']

class CreateDiseaseSerializer(serializers.ModelSerializer):
    """
        Serializer to add new disease.
    """
    ontology_terms = DiseaseOntologyTermSerializer(many=True, required=False)

    # Add synonyms

    def create(self, validated_data):
        """
            Add new disease and associated ontology terms (optional).

            This method is only called if the disease passes the validation.
            One of the constraints is the unique 'name'.

            To avoid duplicated names caused by really similar names,
            this method cleans the disease name and tries to find it in the db:
                it checks if the disease name or the synonym name is already stored in G2P.
                If so, returns existing disease.

            If applicable, it associates the ontology terms to the disease.

            Args:
                validate_data: disease data to be inserted
                               keys are 'name' (string) and 'ontology_terms' (list of dict)

            Returns:
                    disease object
        """

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

class GeneDiseaseSerializer(serializers.ModelSerializer):
    """
        Serializer for the GeneDisease model.
        The GeneDisease model stores external gene-disease associations.
    """
    disease = serializers.CharField()
    identifier = serializers.CharField() # external identifier
    source = serializers.CharField(source="source.name")

    class Meta:
        model = GeneDisease
        fields = ['disease', 'identifier', 'source']
