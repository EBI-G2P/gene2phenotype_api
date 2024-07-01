from rest_framework import serializers
import re

from ..models import (OntologyTerm, Source)

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
