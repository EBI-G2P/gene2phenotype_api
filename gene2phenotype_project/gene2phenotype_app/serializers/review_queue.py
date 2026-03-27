from django.db import transaction
from rest_framework import serializers

from ..models import (
    LocusGenotypeDisease,
    User,
    LGDReviewCase,
    LGDReviewItem,
)
from ..utils import get_date_now


class LGDReviewItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = LGDReviewItem
        fields = ["component", "details", "status", "comment"]


class LGDReviewCaseSerializer(serializers.ModelSerializer):
    stable_id = serializers.SerializerMethodField()
    created_by = serializers.SerializerMethodField()
    assigned_to = serializers.SerializerMethodField()
    date_created = serializers.SerializerMethodField()
    date_last_update = serializers.SerializerMethodField()
    items = serializers.SerializerMethodField()

    def get_stable_id(self, obj):
        return obj.lgd.stable_id.stable_id

    def get_created_by(self, obj):
        return obj.created_by.email

    def get_assigned_to(self, obj):
        if not obj.assigned_to:
            return None
        return obj.assigned_to.email

    def get_date_created(self, obj):
        return obj.date_created.strftime("%Y-%m-%d %H:%M") if obj.date_created else None

    def get_date_last_update(self, obj):
        return (
            obj.date_last_update.strftime("%Y-%m-%d %H:%M")
            if obj.date_last_update
            else None
        )

    def get_items(self, obj):
        queryset = LGDReviewItem.objects.filter(review_case=obj).order_by("component")
        return LGDReviewItemSerializer(queryset, many=True).data

    class Meta:
        model = LGDReviewCase
        fields = [
            "id",
            "stable_id",
            "summary",
            "status",
            "created_by",
            "assigned_to",
            "date_created",
            "date_last_update",
            "items",
        ]


class LGDReviewCaseCreateSerializer(serializers.Serializer):
    stable_id = serializers.CharField()
    summary = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    assigned_to = serializers.EmailField(required=False, allow_null=True)
    items = LGDReviewItemSerializer(many=True)

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError("At least one item must be provided.")
        components = [item["component"] for item in value]
        if len(components) != len(set(components)):
            raise serializers.ValidationError(
                "Duplicate components are not allowed in the same review case."
            )
        return value

    @transaction.atomic
    def create(self, validated_data):
        user_ref = self.context.get("user")
        user_email = user_ref.email if isinstance(user_ref, User) else user_ref
        try:
            created_by = User.objects.get(email=user_email, is_active=1)
        except User.DoesNotExist:
            raise serializers.ValidationError({"error": f"Invalid user '{user_email}'"})

        stable_id = validated_data.get("stable_id")
        try:
            lgd_obj = LocusGenotypeDisease.objects.get(stable_id__stable_id=stable_id)
        except LocusGenotypeDisease.DoesNotExist:
            raise serializers.ValidationError(
                {"error": f"Could not find active LGD record '{stable_id}'"}
            )

        if LGDReviewCase.objects.filter(
            lgd=lgd_obj, status__in=["open", "under_review"]
        ).exists():
            raise serializers.ValidationError(
                {"error": f"Record '{stable_id}' already has an active review case."}
            )

        assigned_to_email = validated_data.get("assigned_to")
        assigned_to = None
        if assigned_to_email:
            try:
                assigned_to = User.objects.get(email=assigned_to_email, is_active=1)
            except User.DoesNotExist:
                raise serializers.ValidationError(
                    {"error": f"Assigned user '{assigned_to_email}' does not exist."}
                )

        date_now = get_date_now()
        review_case = LGDReviewCase.objects.create(
            lgd=lgd_obj,
            summary=validated_data.get("summary"),
            created_by=created_by,
            assigned_to=assigned_to,
            date_created=date_now,
            date_last_update=date_now,
        )

        for item in validated_data.get("items", []):
            LGDReviewItem.objects.create(
                review_case=review_case,
                component=item["component"],
                details=item.get("details"),
            )

        return review_case


class LGDReviewCaseUpdateSerializer(serializers.Serializer):
    """
    Update items of a LGD flagged for review.
    It only updates existing items.
    """

    summary = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    status = serializers.ChoiceField(
        choices=["open", "under_review", "resolved"], required=True
    )
    assigned_to = serializers.EmailField(required=False, allow_null=True)
    items = LGDReviewItemSerializer(many=True, required=False)

    def validate_items(self, value):
        components = [item["component"] for item in value]
        if len(components) != len(set(components)):
            raise serializers.ValidationError(
                "Duplicate components are not allowed in the same review case."
            )
        return value

    @transaction.atomic
    def update(self, instance, validated_data):
        user_ref = self.context.get("user")
        user_email = user_ref.email if isinstance(user_ref, User) else user_ref
        if not User.objects.filter(email=user_email, is_active=1).exists():
            raise serializers.ValidationError({"error": f"Invalid user '{user_email}'"})

        date_now = get_date_now()
        if "summary" in validated_data:
            instance.summary = validated_data.get("summary")

        if "status" in validated_data:
            new_status = validated_data.get("status")

            # To set the status to resolved all items must be resolved too
            if new_status == "resolved":
                # Check if all items are resolved
                if LGDReviewItem.objects.filter(
                    review_case=instance, status__in=["open", "under_review"]
                ).exists():
                    raise serializers.ValidationError(
                        {"error": "Cannot update case status to resolved: some items are still open or under review"}
                    )

            instance.status = new_status

        if "assigned_to" in validated_data:
            assigned_to_email = validated_data.get("assigned_to")
            if assigned_to_email:
                try:
                    assigned_to_obj = User.objects.get(
                        email=assigned_to_email, is_active=1
                    )
                except User.DoesNotExist:
                    raise serializers.ValidationError(
                        {
                            "error": f"Assigned user '{assigned_to_email}' does not exist."
                        }
                    )
                instance.assigned_to = assigned_to_obj
            else:
                instance.assigned_to = None

        if "items" in validated_data:
            input_items = validated_data.get("items", [])

            for item in input_items:
                try:
                    # If the component ("disease", "mechanism", etc.) is already is the db
                    # then just update the details and the status
                    lgd_item = LGDReviewItem.objects.get(
                        review_case=instance,
                        component=item["component"],
                    )
                except LGDReviewItem.DoesNotExist:
                    # Create new component
                    LGDReviewItem.objects.create(
                        review_case=instance,
                        component=item["component"],
                        status=item["status"],
                        details=item.get("details", None),
                        comment=item.get("comment", None),
                    )
                else:
                    if "details" in item:
                        lgd_item.details = item["details"]
                    if "comment" in item:
                        lgd_item.comment = item["comment"]
                    lgd_item.status = item["status"]
                    lgd_item.save()

        instance.date_last_update = date_now
        instance.save()

        return instance
