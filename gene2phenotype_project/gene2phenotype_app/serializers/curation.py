from rest_framework import serializers
from deepdiff import DeepDiff
from django.utils import timezone
from django.db import transaction
from collections import OrderedDict
from datetime import datetime
import copy
import json
import pytz

from ..models import (CurationData, Disease, User, LocusGenotypeDisease,
                      Locus, Attrib)

from .user import UserSerializer
from .disease import CreateDiseaseSerializer
from .locus_genotype_disease import (LocusGenotypeDiseaseSerializer,
                                     LGDCrossCuttingModifierSerializer,
                                     LGDMolecularMechanismSerializer,
                                     LGDVariantGenCCConsequenceSerializer,
                                     LGDVariantTypeSerializer, LGDVariantTypeDescriptionSerializer)
from .stable_id import G2PStableIDSerializer
from .phenotype import LGDPhenotypeSerializer

class CurationDataSerializer(serializers.ModelSerializer):
    """
        Serializer for CurationData model
    """

    def validate(self, data):
        """
            Validate the input data for curation.

            Validation extension step:
                This step is called in AddCurationData of the views.py
                The steps of the validation for the save is
                    - Locus is the minimum requirement needed to save a draft
                    - Draft does not already exist as a draft 
                    - User has permissions to curate on the selected panel

            Args:
                data: The data to be validated.

            Returns:
                The validated data.

            Raises:
                serializers.ValidationError: If the data is already under curation or 
                if the user does not have permission to curate on certain panels.
        """

        session_name = self.context.get('session_name')
        # making a deep copy of data so any changes made are only applied to data_copy
        data_copy = copy.deepcopy(data)
        data_dict = self.convert_to_dict(data_copy)

        user_email = self.context.get('user')
        user_obj = User.objects.get(email=user_email)

        if ("locus" not in data_dict["json_data"] or data_dict["json_data"]["locus"] == ""
            or data_dict["json_data"]["locus"] is None):
            raise serializers.ValidationError(
                {"message" : "To save a draft, the minimum requirement is a locus entry. Please save this draft with locus information"}
            )

        # Check if JSON is already in the table
        curation_entry = self.compare_curation_data(data_dict, user_obj.id)

        # Throw error if data is already stored in table associated with another curation entry
        if curation_entry and session_name != curation_entry.session_name:
            raise serializers.ValidationError(
                {"message": f"Data already under curation. Please check session '{curation_entry.session_name}'"}
            )

        if "panels" in data_dict["json_data"] and len(data_dict["json_data"]["panels"]) >= 1:
            panels = UserSerializer.get_panels(self, user_obj.id)
            # Check if any panel in data_dict["json_data"]["panels"] is not in the updated panels list
            unauthorized_panels = [panel for panel in data_dict["json_data"]["panels"] if panel not in panels]
            if unauthorized_panels:
                unauthorized_panels_str = "', '".join(unauthorized_panels)
                raise serializers.ValidationError(
                    {"message" : f"You do not have permission to curate on these panels: '{unauthorized_panels_str}'"}
                )

        return data

    def validate_to_publish(self, data):
        """
            Second step to validate the JSON data.
            This validation is done before a record is published.
            The following fields are mandatory to publish a record:
                - locus (validated in the first validation step)
                - disease
                - genotype/allelic requirement
                - molecular mechanism
                - panel(s)
                - confidence
                - publication(s)
            
            Args:
                (CurationData obj) data: data to be validated
        """

        json_data = data.json_data
        missing_data = []

        if "disease" not in json_data or json_data["disease"]["disease_name"] == "":
            missing_data.append("disease")

        if "confidence" not in json_data or json_data["confidence"]["level"] == "":
            missing_data.append("confidence")

        if "publications" not in json_data or len(json_data["publications"]) == 0:
            missing_data.append("publication")

        if "panels" not in json_data or not json_data["panels"]:
            missing_data.append("panel")

        if "allelic_requirement" not in json_data or json_data["allelic_requirement"] == "":
            missing_data.append("allelic_requirement")

        if "molecular_mechanism" not in json_data or json_data["molecular_mechanism"]["name"] == "":
            missing_data.append("molecular_mechanism")

        if missing_data:
            missing_data_str = ', '.join(missing_data)
            raise serializers.ValidationError(
                {"message" : f"The following mandatory fields are missing: {missing_data_str}"}
            )

        # Check if locus data is stored in G2P
        # Locus - we only accept locus already stored in G2P
        try:
            locus_obj = Locus.objects.get(name=json_data["locus"])
        except Locus.DoesNotExist:
            raise serializers.ValidationError({"message" : f"Invalid locus {json_data['locus']}"})

        # Check if G2P record (LGD) is already published
        # TODO update this check
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
            return locus_obj

    def convert_to_dict(self, data):
        """
            Convert data to a regular dictionary if it is an OrderedDict.

            Args:
                data: Data to convert (can be OrderedDict or dict).

            Returns:
                Converted data as a dict.
            Reason:
                If the data is an OrderedDict, which is how Python is reading the JSON, 
                it is turned to a regular dictionary which is what is returned, otherwise it just returns the data gotten.
        """

        if isinstance(data, OrderedDict):
            return dict(data)
        
        return data
    
    # using the Deepdiff module to compare JSON data 
    # TODO: this still needs to be worked on when we have fixed the user permission issue 
    def compare_curation_data(self, input_json_data, user_obj):
       """"
            Function to compare provided JSON data against JSON data stored in CurationData instances 
            associated with a specific user.
            Only compares the first layer of JSON objects.

            Args:
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
        
            Args:
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
        
            Args:
                (dict) validated_data: Validated data containing the JSON data to be stored.
        
            Returns:
                CurationData: The newly created CurationData instance.
        """

        json_data = validated_data.get("json_data")

        date_created = datetime.now()
        date_reviewed = date_created
        session_name = json_data.get('session_name')
        stable_id = G2PStableIDSerializer.create_stable_id()

        if session_name is None or session_name == "":
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

            Args:
                instance
                (dict) validated_data: Validated data containing the updated JSON data to be stored.

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

        # Get user object
        try:
            user_obj = User.objects.get(email=user, is_active=1)

        except User.DoesNotExist:
            raise serializers.ValidationError({
                "message" : f"Invalid user '{user}'"
            })

        ### Publications ###
        for publication in data.json_data["publications"]:
            if publication["families"] is None:
                family = None
            else: 
                family = { "families": publication["families"], 
                            "consanguinity": publication["consanguineous"], 
                            "ancestries": publication["ancestries"], 
                            "affected_individuals": publication["affectedIndividuals"]
                         }

            if publication["comment"] is None or publication["comment"] == "":
                comment = None
            else:
                comment = {"comment": publication["comment"], "is_public": 1}

            # format the publication data according to the expected format in PublicationSerializer
            publication_data = { "pmid": publication["pmid"],
                                 "comment": comment,
                                 "families": family
                               }

            publications_list.append(publication_data)
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
                cross_references.append(ontology_term)

        # Use CreateDiseaseSerializer to get or create disease
        disease = {
            "name": data.json_data["disease"]["disease_name"],
            "ontology_terms": cross_references, # if we have more ids the serializer should add them
        }

        # The CreateDiseaseSerializer is going to first check if the disease is stored in G2P
        # It only inserts data that is not in G2P
        disease_serializer = CreateDiseaseSerializer(data=disease)
        # Validate the input data
        if disease_serializer.is_valid(raise_exception=True):
            # save and create
            disease_obj = disease_serializer.save()
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

        lgd_obj = LocusGenotypeDiseaseSerializer(context={'user':user_obj}).create(lgd_data, disease_obj, publications_list)
        ##############################

        ### Insert data attached to the record Locus-Genotype-Disease ###

        ### Phenotypes ###
        # Phenotype format: {
        #      'pmid': '1',
        #      'summary': 'This is the summary of these phenotypes.',
        #      'hpo_terms': [
        #          {
        #             'term': 'Sclerosis of the middle phalanx of the 5th finger',
        #             'accession': 'HP:0100907', 'description': ''
        #         }, {
        #             'term': 'Abnormal proximal phalanx morphology of the hand', 
        #             'accession': 'HP:0009834', 'description': ''
        #             }
        #         ]
        # }
        for phenotype_pmid in data.json_data["phenotypes"]:
            # TODO add summary
            # TODO improve this method to send a list of phenotypes to LGDPhenotypeSerializer
            hpo_terms = phenotype_pmid['hpo_terms']
            for hpo in hpo_terms:
                phenotype_data = {
                    "accession": hpo["accession"],
                    "publication": phenotype_pmid["pmid"]
                }

                lgd_phenotype_serializer = LGDPhenotypeSerializer(
                    data = phenotype_data,
                    context = {'lgd': lgd_obj}
                )

                # Validate the input data
                if lgd_phenotype_serializer.is_valid(raise_exception=True):
                    # save() is going to call create()
                    lgd_phenotype_serializer.save()

        ### Cross cutting modifier ###
        # "cross_cutting_modifier" is an array of strings
        for ccm in data.json_data["cross_cutting_modifier"]:
            lgd_ccm_serializer = LGDCrossCuttingModifierSerializer(
                data={"term":ccm}, # valid fields is 'term'
                context={"lgd": lgd_obj}
            )

            # Validate the input data
            if lgd_ccm_serializer.is_valid(raise_exception=True):
                # save() is going to call create()
                lgd_ccm_serializer.save()

        ### Variant (GenCC) consequences ###
        # Example: 'variant_consequences': [{'variant_consequence': 'altered_gene_product_level', 'support': 'inferred'}]
        for var_consequence in data.json_data["variant_consequences"]:
            lgd_var_cons_serializer = LGDVariantGenCCConsequenceSerializer(
                data=var_consequence,
                context={'lgd': lgd_obj}
            )

            # Validate the input data
            if lgd_var_cons_serializer.is_valid(raise_exception=True):
                # save() is going to call create()
                lgd_var_cons_serializer.save()
 
        ### Variant types ###
        # Example: {'comment': 'This is a frameshift', 'inherited': false, 'de_novo': false, 
        # 'unknown_inheritance': false, 'nmd_escape': True, 'primary_type': 'protein_changing',
        # 'secondary_type': 'frameshift_variant', 'supporting_papers': [38737272, 38768424]}
        for variant_type in data.json_data["variant_types"]:
            LGDVariantTypeSerializer(context={'lgd': lgd_obj, 'user': user_obj}).create(variant_type)

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
