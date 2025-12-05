from typing import Any
from rest_framework import serializers
from django.db.models import OuterRef, Exists, Max, F, Subquery
from django.db.models.query import QuerySet
from django.core.exceptions import ObjectDoesNotExist

from ..models import (
    GenCCSubmission,
    G2PStableID,
    LocusGenotypeDisease,
    LGDPanel,
)


class GenCCSubmissionListSerializer(serializers.ListSerializer):
    def validate(self, data: list) -> list:
        """
        Method to validate multiple GenCCSubmission objects

        Args:
            data (list): The list data

        Raises:
            serializers.ValidationError: If G2P stable id does not exist

        Returns:
            list: Returns the validated list
        """
        for item in data:
            stable_id_value = item.get("g2p_stable_id")
            try:
                g2p_stable = G2PStableID.objects.get(stable_id=stable_id_value)
            except ObjectDoesNotExist:
                raise serializers.ValidationError(
                    f"G2PStableID with stable_id '{stable_id_value}' does not exist."
                )
            item["g2p_stable_id"] = g2p_stable

        return data

    def create(self, validated_data: list) -> list[GenCCSubmission]:
        """
        Method to create multiple GenCCSubmission objects

        Args:
            validated_data (list): list of validated data

        Returns:
            GenCCSubmission: list of created GenCCSubmission objects
        """
        instances = [GenCCSubmission(**item) for item in validated_data]
        return GenCCSubmission.objects.bulk_create(instances)


class CreateGenCCSubmissionSerializer(serializers.ModelSerializer):
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
        """
        Fetch list of unsubmitted G2P ids by comparing the IDs from the gencc_submission table.
        Only returns live stable IDs whose records are in public panels.

        Returns:
            QuerySet[G2PStableID]: A queryset
        """
        public_records = LGDPanel.objects.filter(panel__is_visible=1).values_list(
            "lgd_id__stable_id", flat=True
        )

        return G2PStableID.objects.annotate(
            has_submission=Exists(
                GenCCSubmission.objects.filter(g2p_stable_id=OuterRef("id"))
            )
        ).filter(has_submission=False, is_live=1, id__in=public_records)

    def fetch_list_of_deleted_stable_id() -> dict:
        """
        Fetch list of records that have been submitted to GenCC but are now deleted.

        Returns:
            dict: Dictionary with stable_id as key and submission_id as value
        """
        final_list = {}

        deleted_records_queryset = GenCCSubmission.objects.filter(
            g2p_stable_id__is_live=0
        ).values(
            "g2p_stable_id__stable_id",
            "submission_id",
        )

        for record in deleted_records_queryset:
            final_list[record["g2p_stable_id__stable_id"]] = record["submission_id"]

        return final_list

    @staticmethod
    def fetch_stable_ids_with_later_review_date() -> dict:
        """Fetches the records that has been updated since the last GenCC submission"""
        final_list = {}

        latest_submission_date = (
            GenCCSubmission.objects.filter(g2p_stable_id=OuterRef("g2p_stable_id"))
            .order_by()
            .values("g2p_stable_id")
            .annotate(latest=Max("date_of_submission"))
            .values("latest")[:1]
        )

        queryset = (
            GenCCSubmission.objects.annotate(
                latest_date=Subquery(latest_submission_date)
            )
            .filter(
                g2p_stable_id__is_live=True,
                date_of_submission=F("latest_date"),
            )
            .annotate(
                has_new_review=Exists(
                    LocusGenotypeDisease.objects.filter(
                        stable_id=OuterRef("g2p_stable_id_id"),
                        date_review__gt=OuterRef("date_of_submission"),
                    )
                )
            )
            .filter(has_new_review=True)
            .values(
                "g2p_stable_id__stable_id",
                "submission_id",
            )
        )

        for record in queryset:
            final_list[record["g2p_stable_id__stable_id"]] = record["submission_id"]

        return final_list
