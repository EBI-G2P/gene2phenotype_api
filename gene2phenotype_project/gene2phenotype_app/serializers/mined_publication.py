from rest_framework import serializers

from ..models import LGDMinedPublication

### G2P record (LGD) - mined publication ###
class LGDMinedPublicationSerializer(serializers.ModelSerializer):
    """
    Serializer for the LGDMinedPublication model.
    Called by: LocusGenotypeDiseaseSerializer()
    """
    pmid = serializers.IntegerField(source="mined_publication.pmid")
    title = serializers.CharField(source="mined_publication.title")
    status = serializers.CharField()
    comment = serializers.CharField()

    class Meta:
        model = LGDMinedPublication
        fields = [
            "pmid",
            "title",
            "status",
            "comment",
        ]

