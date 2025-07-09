from rest_framework import serializers
from django.db import IntegrityError
from typing import Optional
from datetime import date

from ..models import Panel, LGDPanel, Attrib


class PanelCreateSerializer(serializers.ModelSerializer):
    """
    Panel Creation Serializer

    Args:
        name: short name of the panel (mandatory)
        description: complete name of the panel (mandatory)
        is_visible: panel visible to authenticated or non authenticated users

    Raises:
        serializers.ValidationError: Raises a validation error when the panel exists

    Returns:
        Panel: A created panel
    """

    name = serializers.CharField(required=True)
    description = serializers.CharField(required=True)
    is_visible = serializers.BooleanField(required=True)

    def validate(self, attrs):
        """
        Validate the request data

        Args:
            attrs (dict): A dictionary like object containing the request data

        Raises:
            serializers.ValidationError: Raises a validation error when the panel exists

        Returns:
            Request: A validated request object
        """
        name = attrs.get("name")
        if Panel.objects.filter(name=name, is_visible=1).exists():
            raise serializers.ValidationError(
                {"message": "Can not create an existing panel"}
            )

        return attrs

    def create(self, validated_data):
        """
        Creation of the panel if panel does not exist
        Updating the panel if is_visible = 0

        Args:
            validated_data (dict): validated request object

        Returns:
            Panel: Created panel object
        """
        name = validated_data.get("name")
        description = validated_data.get("description")
        is_visible = validated_data.get("is_visible")
        try:
            panel = Panel.objects.get(name=name)

            if panel.is_visible:
                raise serializers.ValidationError({"message": f"{name} exists!"})

            if not panel.is_visible:
                raise serializers.ValidationError(
                    {
                        "message": f"{name} exist. It is only visible to authenticated users"
                    }
                )

        except Panel.DoesNotExist:
            try:
                panel = Panel.objects.create(
                    name=name, description=description, is_visible=is_visible
                )
                return panel
            except IntegrityError as e:
                raise serializers.ValidationError(
                    {"message": f"Database error: {str(e)}"}
                )

    class Meta:
        model = Panel
        fields = ["name", "description", "is_visible"]


class PanelDetailSerializer(serializers.ModelSerializer):
    """
    Serializer for the Panel model.
    It returns the panel info including extra data:
        - data of the last update
        - some stats: total number of records linked to the panel, etc.
        - summary of records associated with panel
    """

    last_updated = serializers.SerializerMethodField()

    def get_last_updated(self, id: int) -> Optional[date]:
        """
        Retrives the date of the last time a record associated with the panel was updated.
        """
        panel_last_update = None

        queryset = (
            LGDPanel.objects.filter(
                panel=id, lgd__is_deleted=0, lgd__date_review__isnull=False
            )
            .select_related("lgd")
            .order_by("-lgd__date_review")
        )

        if queryset:
            panel_last_update = queryset.first().lgd.date_review

        return panel_last_update.date() if panel_last_update else None

    # Calculates the stats on the fly
    # Returns a JSON object
    def calculate_stats(self, panel):
        """
        Returns stats for the panel:
            - total number of records associated with panel
            - total number of genes associated with panel
            - total number of records by confidence
        """
        lgd_panels = LGDPanel.objects.filter(
            panel=panel.id, is_deleted=0
        ).select_related()

        genes = set()
        confidences = {}
        attrib_id = Attrib.objects.get(value="gene").id
        for lgd_panel in lgd_panels:
            if lgd_panel.lgd.locus.type.id == attrib_id:
                genes.add(lgd_panel.lgd.locus.name)

            try:
                confidences[lgd_panel.lgd.confidence.value] += 1
            except KeyError:
                confidences[lgd_panel.lgd.confidence.value] = 1

        return {
            "total_records": len(lgd_panels),
            "total_genes": len(genes),
            "by_confidence": confidences,
        }

    def records_summary(self, panel, user):
        """
        A summary of the last 10 records associated with the panel.
        If the user is non-authenticated:
            - only returns records linked to visible panels
        """
        if user.is_authenticated:
            lgd_panels_selected = (
                LGDPanel.objects.select_related(
                    "lgd",
                    "lgd__locus",
                    "lgd__disease",
                    "lgd__genotype",
                    "lgd__confidence",
                    "lgd__mechanism",
                )
                .prefetch_related(
                    "lgd__lgd_variant_gencc_consequence", "lgd__lgd_variant_type"
                )
                .order_by("-lgd__date_review")
                .filter(panel=panel.id, is_deleted=0, lgd__is_deleted=0)
            )
        else:
            lgd_panels_selected = (
                LGDPanel.objects.filter(
                    panel=panel.id, is_deleted=0, lgd__is_deleted=0, panel__is_visible=1
                )
                .select_related(
                    "lgd",
                    "lgd__locus",
                    "lgd__disease",
                    "lgd__genotype",
                    "lgd__confidence",
                    "lgd__mechanism",
                )
                .prefetch_related(
                    "lgd__lgd_variant_gencc_consequence", "lgd__lgd_variant_type"
                )
                .order_by("-lgd__date_review")
            )

        lgd_objects_list = list(
            lgd_panels_selected.values(
                "lgd__locus__name",
                "lgd__disease__name",
                "lgd__genotype__value",
                "lgd__confidence__value",
                "lgd__lgdvariantgenccconsequence__variant_consequence__term",
                "lgd__lgdvarianttype__variant_type_ot__term",
                "lgd__mechanism__value",
                "lgd__date_review",
                "lgd__stable_id__stable_id",
            )
        )

        aggregated_data = {}
        number_keys = 0
        for lgd_obj in lgd_objects_list:
            # Return the last 10 records
            if (
                lgd_obj["lgd__stable_id__stable_id"] not in aggregated_data.keys()
                and number_keys < 10
            ):
                variant_consequences = []
                variant_types = []

                variant_consequences.append(
                    lgd_obj[
                        "lgd__lgdvariantgenccconsequence__variant_consequence__term"
                    ]
                )
                # Some records do not have variant types
                if lgd_obj["lgd__lgdvarianttype__variant_type_ot__term"] is not None:
                    variant_types.append(
                        lgd_obj["lgd__lgdvarianttype__variant_type_ot__term"]
                    )

                date_review = None
                if lgd_obj["lgd__date_review"] is not None:
                    date_review = lgd_obj["lgd__date_review"].strftime("%Y-%m-%d")

                aggregated_data[lgd_obj["lgd__stable_id__stable_id"]] = {
                    "locus": lgd_obj["lgd__locus__name"],
                    "disease": lgd_obj["lgd__disease__name"],
                    "genotype": lgd_obj["lgd__genotype__value"],
                    "confidence": lgd_obj["lgd__confidence__value"],
                    "variant_consequence": variant_consequences,
                    "variant_type": variant_types,
                    "molecular_mechanism": lgd_obj["lgd__mechanism__value"],
                    "last_updated": date_review,
                    "stable_id": lgd_obj["lgd__stable_id__stable_id"],
                }
                number_keys += 1

            elif number_keys < 10:
                if (
                    lgd_obj[
                        "lgd__lgdvariantgenccconsequence__variant_consequence__term"
                    ]
                    not in aggregated_data[lgd_obj["lgd__stable_id__stable_id"]][
                        "variant_consequence"
                    ]
                ):
                    aggregated_data[lgd_obj["lgd__stable_id__stable_id"]][
                        "variant_consequence"
                    ].append(
                        lgd_obj[
                            "lgd__lgdvariantgenccconsequence__variant_consequence__term"
                        ]
                    )
                if (
                    lgd_obj["lgd__lgdvarianttype__variant_type_ot__term"]
                    not in aggregated_data[lgd_obj["lgd__stable_id__stable_id"]][
                        "variant_type"
                    ]
                    and lgd_obj["lgd__lgdvarianttype__variant_type_ot__term"]
                    is not None
                ):
                    aggregated_data[lgd_obj["lgd__stable_id__stable_id"]][
                        "variant_type"
                    ].append(lgd_obj["lgd__lgdvarianttype__variant_type_ot__term"])

        return aggregated_data.values()

    class Meta:
        model = Panel
        fields = ["name", "description", "last_updated"]


### G2P record (LGD) - panels ###
class LGDPanelSerializer(serializers.ModelSerializer):
    """
    Serializer for the LGDPanel model.
    The LGDPanel model represents the panels associated with LGD entries.
    """

    name = serializers.CharField(source="panel.name")
    description = serializers.CharField(
        source="panel.description", allow_null=True, required=False
    )

    def create(self, validated_data):
        """
        Add a LGD record to a panel.

        Args:
            (dict) validated_data: panel name
            Example:
                    { "name": panel_name }

        Returns:
                LGDPanel obj
        Raises:
            Raise error if panel name is invalid
            Raise error if LGDPanel already exists
        """

        lgd = self.context["lgd"]
        panel_name = validated_data.get("panel")[
            "name"
        ]  # panel short name (example: 'DD')

        # Check if panel name is valid
        panel_obj = Panel.objects.filter(name=panel_name)

        if not panel_obj.exists():
            raise serializers.ValidationError(
                {"message": f"Invalid panel name '{panel_name}'"}
            )

        try:
            lgd_panel_obj = LGDPanel.objects.get(panel=panel_obj.first().id, lgd=lgd.id)

        except LGDPanel.DoesNotExist:
            # Create LGDPanel
            lgd_panel_obj = LGDPanel.objects.create(
                lgd=lgd, panel=panel_obj.first(), is_deleted=0
            )

        else:
            # The LGDPanel exists
            # If not deleted then the entry already exists
            if lgd_panel_obj.is_deleted == 0:
                raise serializers.ValidationError(
                    {
                        "message": f"G2P entry {lgd.stable_id.stable_id} is already linked to panel {panel_name}"
                    }
                )
            else:
                # If deleted then update to not deleted
                lgd_panel_obj.is_deleted = 0
                lgd_panel_obj.save()

        return lgd_panel_obj

    class Meta:
        model = LGDPanel
        fields = ["name", "description"]
