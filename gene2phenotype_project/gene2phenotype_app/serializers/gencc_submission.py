from rest_framework import serializers
from ..models import GenCCSubmission, G2PStableID, LocusGenotypeDisease
from django.db.models import OuterRef, Exists
from typing import Any
from django.db.models.query import QuerySet
from django.core.exceptions import ObjectDoesNotExist


class GenCCSubmissionListSerializer(serializers.ListSerializer):
    """GenCCSubmissionListSerializer"""

    def validate(self, data: list) -> list:
        """Validation of the data

        Args:
            data (list): The list data

        Raises:
            serializers.ValidationError: If G2P stable id does not exist

        Returns:
            list: Returns the validated list
        """
        for item in data:
            stable_id_value = item.pop("g2p_stable_id")
            try:
                g2p_stable = G2PStableID.objects.get(stable_id=stable_id_value)
            except ObjectDoesNotExist:
                raise serializers.ValidationError(
                    f"G2PStableID with stable_id '{stable_id_value}' does not exist."
                )
            item["g2p_stable_id"] = g2p_stable
        return data

    def create(self, validated_data: list) -> GenCCSubmission:
        """For bulk creation

        Args:
            validated_data (list): list of validated data

        Returns:
            GenCCSubmission:  created GenCCSubmission object
        """
        instances = [GenCCSubmission(**item) for item in validated_data]
        return GenCCSubmission.objects.bulk_create(instances)


class CreateGenCCSubmissionSerializer(serializers.ModelSerializer):
    """Serializer for the GenCCSubmission"""

    g2p_stable_id = serializers.CharField()

    def create(self, validated_data: dict[str, Any]) -> GenCCSubmission:
        """Create the GenCCSubmission

        Args:
            validated_data (dict[str, Any]): Validated data

        Returns:
            GenCCSubmission: A created GenCCSubmission object
        """
        return GenCCSubmission.objects.create(**validated_data)

    class Meta:
        model = GenCCSubmission
        fields = [
            "submission_id",
            "date_of_submission",
            "type_of_submission",
            "g2p_stable_id",
        ]
        list_serializer_class = GenCCSubmissionListSerializer


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
        """Fetches the stable ID that has been updated since the last GenCC submission"""
        return GenCCSubmission.objects.filter(
            Exists(
                LocusGenotypeDisease.objects.filter(
                    stable_id=OuterRef("g2p_stable_id_id"),
                    date_review__gt=OuterRef("date_of_submission"),
                )
            ),
            g2p_stable_id__is_live=1,
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
