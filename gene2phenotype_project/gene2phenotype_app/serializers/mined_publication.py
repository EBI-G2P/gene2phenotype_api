from rest_framework import serializers

from ..models import LGDMinedPublication, MinedPublication


### G2P record (LGD) - mined publication ###
class LGDMinedPublicationSerializer(serializers.ModelSerializer):
    """
    Serializer for the LGDMinedPublication model.
    Called by: LocusGenotypeDiseaseSerializer(), LGDMinedPublicationListSerializer()
    """

    pmid = serializers.IntegerField(
        source="mined_publication.pmid", allow_null=True, required=False
    )
    title = serializers.CharField(
        source="mined_publication.title", allow_null=True, required=False
    )
    status = serializers.CharField(required=True)
    comment = serializers.CharField(required=True)

    def update(self, instance, validated_data):
        """
        Update an entry in the lgd_mined_publication table.

        Args:
            instance
            (dict) validated_data: Validated data to be updated.

        Returns:
            CurationData: The updated LGDMinedPublication instance.
        """
        instance.status = validated_data.get("status")
        instance.comment = validated_data.get("comment")
        instance.save()

        return instance

    def update_status_to_curated(self, lgd_obj, validated_data):
        """
        Method to only update the status of LGD mined publications to "curated".

        'validated_data' example:
            "publications": [{
                        "publication": {
                            "pmid": 32133637,
                            "title": "First report of childhood progressive cerebellar atrophy due to compound heterozygous MTFMT variants.",
                            "authors": "Bai R, Haude K, Yang E, Goldstein A, Anselm I.",
                            "year": "2020",
                        },
                        "number_of_families": None,
                        "consanguinity": None,
                        "affected_individuals": None,
                        "ancestry": None,
                        "comments": [],
                    }]
        """
        for publication in validated_data:
            pmid = publication.get("publication").get("pmid")

            # Check if the PMID exists in mined_publication table
            try:
                mined_publication_obj = MinedPublication.objects.get(pmid=pmid)
            except MinedPublication.DoesNotExist:
                # If the PMID does not exist then skip update
                continue

            # Check if the lgd - mined publication link already exists in lgd_mined_publication table
            try:
                lgd_mined_publication_obj = LGDMinedPublication.objects.get(
                    lgd=lgd_obj, mined_publication=mined_publication_obj
                )
            except LGDMinedPublication.DoesNotExist:
                # If the lgd - mined publication link does not exist then skip update
                continue
            else:
                # If the lgd - mined publication link already exists then update status to "curated"
                lgd_mined_publication_obj.status = "curated"
                lgd_mined_publication_obj.save()

    class Meta:
        model = LGDMinedPublication
        fields = [
            "pmid",
            "title",
            "status",
            "comment",
        ]


class LGDMinedPublicationListSerializer(serializers.Serializer):
    """
    Serializer to accept a list of mined publications.
    Called by: view LGDEditMinedPublication()
    """

    mined_publications = LGDMinedPublicationSerializer(many=True)
