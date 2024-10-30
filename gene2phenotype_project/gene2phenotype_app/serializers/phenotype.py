from rest_framework import serializers
import re

from ..models import (OntologyTerm, Source, LGDPhenotype, Publication,
                      LGDPhenotypeSummary)

from ..utils import validate_phenotype


class PhenotypeOntologyTermSerializer(serializers.ModelSerializer):
    """
        Serializer for the OntologyTerm model.
        The phenotypes are represented in OntologyTerm model.

        Called by:
                - AddPhenotype()
                - LGDPhenotypeSerializer()
    """

    name = serializers.CharField(source="term", read_only=True)
    description = serializers.CharField(read_only=True)

    def create(self, accession):
        """
            Create a phenotype based on the accession.

            Returns:
                    OntologyTerm object
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

### G2P record (LGD) - phenotype ###
class LGDPhenotypeSerializer(serializers.ModelSerializer):
    """
        Serializer for the LGDPhenotype model.
        A G2P record is linked to one or more phenotypes (supported by publications).
    """

    name = serializers.CharField(source="phenotype.term", required=False)
    accession = serializers.CharField(source="phenotype.accession")
    publication = serializers.IntegerField(source="publication.pmid", allow_null=True) # TODO support array of pmids

    def create(self, validated_data):
        """
            Method to create LGD-phenotype association.

            Args:
                (dict) validated_data

            Returns:
                    LGDPhenotype object
        """
        lgd = self.context['lgd']
        accession = validated_data.get("phenotype")["accession"] # HPO term
        publication = validated_data.get("publication")["pmid"] # pmid

        # This method 'create' behaves like 'get_or_create'
        # If phenotype is already stored in G2P then it returns the object
        pheno_obj = PhenotypeOntologyTermSerializer().create({"accession": accession})

        # When we add a new phenotype to the G2P record, the publication
        # already has to be associated with the record
        # If the publication does not exist then we won't add the lgd-phenotype
        publication_obj = Publication.objects.get(pmid=publication)

        # Check if LGD-phenotype already exists
        try:
            lgd_phenotype_obj = LGDPhenotype.objects.get(
                lgd = lgd,
                phenotype = pheno_obj,
                publication = publication_obj
            )
        except LGDPhenotype.DoesNotExist:
            lgd_phenotype_obj = LGDPhenotype.objects.create(
                lgd = lgd,
                phenotype = pheno_obj,
                is_deleted = 0,
                publication = publication_obj
            )
        else:
            # The LGD-phenotype can be deleted
            # If it is deleted then update to not deleted
            if lgd_phenotype_obj.is_deleted != 0:
                lgd_phenotype_obj.is_deleted = 0
                lgd_phenotype_obj.save()

        return lgd_phenotype_obj

    class Meta:
        model = LGDPhenotype
        fields = ['name', 'accession', 'publication']

class LGDPhenotypeListSerializer(serializers.Serializer):
    """
        Serializer to accept a list of phenotypes.
        Called by: LocusGenotypeDiseaseAddPhenotypes() and view LGDEditPhenotypes()
    """
    phenotypes = LGDPhenotypeSerializer(many=True)

class LGDPhenotypeSummarySerializer(serializers.ModelSerializer):
    """
        Serializer for the LGDPhenotypeSummary model.
        It represents the summary of the phenotypes reported in a publication 
        for a G2P record.

        Called by:
    """

    summary = serializers.CharField()
    publication = serializers.ListField(
        child=serializers.IntegerField()
    )

    def create(self, validated_data):
        """
            Create an entry LGDPhenotypeSummary.

            Input example:
                    {
                        "summary": "This is a summary",
                        "publication": [1, 12345]
                    }

            Returns:
                    LGDPhenotypeSummary object
        """
        lgd = self.context['lgd']

        summary = validated_data.get("summary")
        list_pmids = validated_data.get("publication")

        # Create a LGD phenotype summary for each pmid
        for pmid in list_pmids:
            try:
                # Get publication object
                # The G2P entry (LGD) is linked to publications
                # When we add a phenotype summary the publications are
                # already supposed to be inserted into the db 
                publication_obj = Publication.objects.get(pmid=pmid)

                # Check if LGD phenotype summary already exists
                try:
                    lgd_phenotype_summary = LGDPhenotypeSummary.objects.get(
                        lgd = lgd,
                        summary = summary,
                        publication = publication_obj
                    )
                except LGDPhenotypeSummary.DoesNotExist:
                    lgd_phenotype_summary = LGDPhenotypeSummary.objects.create(
                        lgd = lgd,
                        summary = summary,
                        is_deleted = 0,
                        publication = publication_obj
                    )
                else:
                    # The LGD phenotype summary can be deleted
                    # If it is deleted then update to not deleted
                    if lgd_phenotype_summary.is_deleted != 0:
                        lgd_phenotype_summary.is_deleted = 0
                        lgd_phenotype_summary.save()

            except Publication.DoesNotExist:
                raise serializers.ValidationError(
                    {"message": f"Problem fetching the publication '{pmid}'"}
                )

        return 1

    class Meta:
        model = LGDPhenotypeSummary
        fields = ['summary', 'publication']