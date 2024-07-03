from rest_framework import serializers
import re

from ..models import (OntologyTerm, Source, LGDPhenotype, Publication)

from ..utils import validate_phenotype


class PhenotypeSerializer(serializers.ModelSerializer):
    """
        Serializer for the OntologyTerm model.
        The phenotypes are represented in OntologyTerm model.
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
                Example:
                        {
                            'phenotype': {'accession': 'HP:0003974'},
                            'publication': {'pmid': 1}
                        }

            Returns:
                    LGDPhenotype object
        """
        lgd = self.context['lgd']
        accession = validated_data.get("phenotype")["accession"] # HPO term
        publication = validated_data.get("publication")["pmid"] # pmid

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
