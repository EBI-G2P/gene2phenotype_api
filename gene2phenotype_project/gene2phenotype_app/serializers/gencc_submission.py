from rest_framework import serializers
from ..models import GenCCSubmission, G2PStableID, LocusGenotypeDisease
from django.db.models import OuterRef, Exists, Subquery, DateField, ExpressionWrapper, F
from typing import Any
from django.db.models.query import QuerySet
from django.core.exceptions import ObjectDoesNotExist


class CreateGenCCSubmissionSerializer(serializers.ModelSerializer):
    """Serializer for the GenCCSubmission"""

    g2p_stable_id = serializers.CharField()

    def create(self, validated_data: dict[str, Any]) -> GenCCSubmission:
        """Creates a GenCCSubmission object after resolving G2PStableID from stable_id"""
        stable_id_value = validated_data.pop("g2p_stable_id")

        try:
            g2p_stable = G2PStableID.objects.get(stable_id=stable_id_value)
        except ObjectDoesNotExist:
            raise serializers.ValidationError(
                f"G2PStableID with stable_id '{stable_id_value}' does not exist."
            )

        validated_data["g2p_stable_id"] = g2p_stable
        return GenCCSubmission.objects.create(**validated_data)

    class Meta:
        model = GenCCSubmission
        fields = [
            "submission_id",
            "date_of_submission",
            "type_of_submission",
            "g2p_stable_id",
        ]


class GenCCSubmissionSerializer(serializers.ModelSerializer):
    @staticmethod
    def fetch_list_of_unsubmitted_stable_id() -> QuerySet[G2PStableID]:
        """Fetch List of unsubmitted stable id from the G2PStableID by comparing whats in the GenCCSubmission table

        Returns:
            QuerySet: A queryset
        """
        return G2PStableID.objects.annotate(
            has_submission=Exists(
                GenCCSubmission.objects.filter(g2p_stable_id=OuterRef("id"))
            )
        ).filter(has_submission=False, is_live=1)

    @staticmethod
    def fetch_stable_ids_with_later_review_date() -> QuerySet[G2PStableID]:
        """Fetches Stable ID that has been updated since the last GenCC submission

        Returns:
            QuerySet: A queryset
        """
        return GenCCSubmission.objects.filter(
            Exists(
                LocusGenotypeDisease.objects.filter(
                    stable_id=OuterRef("g2p_stable_id_id"),
                    date_review__gt=OuterRef("date_of_submission"),
                )
            ),
            g2p_stable_id__is_live=1
        ).values_list("submission_id", flat=True)
    

    @staticmethod
    def get_stable_ids(submission_id: str) -> QuerySet[G2PStableID]:
        """Get stable ids associated with the submission id

        Args:
            submission_id (str): Submission id

        Returns:
            QuerySet: Returns G2P stable id objects
        """
        return GenCCSubmission.objects.filter(submission_id=submission_id).values_list(
            "g2p_stable_id__stable_id", flat=True
        )
