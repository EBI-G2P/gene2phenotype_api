from rest_framework import serializers

from ..models import LGDMinedPublication, MinedPublication


### G2P record (LGD) - mined publication ###
class LGDMinedPublicationSerializer(serializers.ModelSerializer):
    """
    Serializer for the LGDMinedPublication model.
    Called by: LocusGenotypeDiseaseSerializer(), LGDMinedPublicationListSerializer()
    """
    pmid = serializers.IntegerField(source="mined_publication.pmid", required=False)
    title = serializers.CharField(source="mined_publication.title", required=False)
    status = serializers.CharField()
    comment = serializers.CharField(allow_blank=True, allow_null=True, required=False)
    score = serializers.CharField()
    score_comment = serializers.CharField(allow_blank=True, allow_null=True, required=False)

    def get_fields(self):
        fields = super().get_fields()
        user = self.context.get("user")

        # Hide scores for non authenticated users
        if not user or not user.is_authenticated:
            fields.pop("score", None)
            fields.pop("score_comment", None)

        return fields

    def update(self, instance, validated_data):
        """
        Update an entry in the lgd_mined_publication table.

        Args:
            instance
            (dict) validated_data: Validated data to be updated.

        Returns:
            CurationData: The updated LGDMinedPublication instance.
        """
        valid_statuses = ["mined", "curated", "rejected"]
        if validated_data.get("status") not in valid_statuses:
            raise serializers.ValidationError(
                {
                    "error": f"Invalid status. Valid statuses are: {', '.join(valid_statuses)}"
                }
            )

        instance.status = validated_data.get("status")
        input_comment = validated_data.get("comment")
        if input_comment == "":
            instance.comment = None
        else:
            instance.comment = input_comment
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
            "score",
            "score_comment",
        ]


class LGDMinedPublicationListSerializer(serializers.Serializer):
    """
    Serializer to accept a list of mined publications.
    Called by: view LGDEditMinedPublication()
    """

    mined_publications = LGDMinedPublicationSerializer(many=True)
