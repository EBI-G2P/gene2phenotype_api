from rest_framework import permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiResponse
from rest_framework.exceptions import ValidationError
from django.db.models import Q, Max
from django.utils import timezone
import textwrap
from datetime import datetime

from gene2phenotype_app.models import (
    Disease,
    G2PStableID,
    Meta,
    LocusGenotypeDisease,
    LGDPanel,
    LGDPublication,
    LGDCrossCuttingModifier,
    LGDPhenotype,
    LGDVariantGenccConsequence,
    LGDVariantType,
    LGDVariantTypeDescription,
    LGDMolecularMechanismEvidence,
    LGDMolecularMechanismSynopsis,
    LGDPhenotypeSummary,
    LGDComment,
)

from gene2phenotype_app.serializers import MetaSerializer

from .base import BaseView, CustomPagination


@extend_schema(
    tags=["Reference data"],
    description=textwrap.dedent("""
    Fetch list of all reference data used in G2P with their respective versions.
    """),
    responses={
        200: OpenApiResponse(
            description="Reference data response",
            response={
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "key": {"type": "string"},
                        "source": {"type": "string"},
                        "version": {"type": "string"},
                    },
                },
            },
        )
    },
)
class MetaView(APIView):
    def get_queryset(self):
        """
        Method to get a queryset containing the latest records for each unique key

        Returns:
            QuerySet: a queryset containing the latest records
        """
        # to group by key to create a queryset containing the key and the latest date
        latest_records = Meta.objects.values("key").annotate(
            latest_date=Max("date_update")
        )

        # then we use a list comprehension to check using the new column latest date
        queryset = Meta.objects.filter(
            date_update__in=[record["latest_date"] for record in latest_records]
        )

        return queryset

    def get(self, request):
        """
        Return a list of the reference data used in G2P with their respective versions.

        Returns:
            Response: A serialized list of the latest meta records.
        """
        queryset = self.get_queryset()
        serializer = MetaSerializer(queryset, many=True)

        # Format the OMIM and Mondo versions
        for query_data in queryset:
            if query_data.key == "import_gene_disease_omim":
                query_data.source.name = "Added by curators"
                query_data.version = ""  # we don't have a specific version
            elif query_data.key == "import_gene_disease_mondo":
                query_data.source.name = "Added by curators"
                query_data.version = f"Checked against version {query_data.version}"

        return Response(serializer.data)


@extend_schema(exclude=True)
class ActivityLogs(BaseView):
    pagination_class = CustomPagination
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request, *args, **kwargs):
        """
        Returns a dictionary where key is the type of data and value is a list of activities.
        Options:
            stable_id
            date_cutoff

        Examples:
            gene2phenotype/api/activity_logs/?stable_id=G2P03520
            gene2phenotype/api/activity_logs/?stable_id=G2P03520&date_cutoff=2025-06-06
            gene2phenotype/api/activity_logs/?date_cutoff=2025-06-06
        """
        stable_id = self.request.query_params.get("stable_id", None)
        start_date = self.request.query_params.get("date_cutoff", None)

        if start_date:
            try:
                date_formatted = datetime.strptime(start_date, "%Y-%m-%d")
                date_input = timezone.make_aware(
                    date_formatted, timezone.get_current_timezone()
                )
            except ValueError:
                raise ValidationError(
                    f"Date format '{start_date}' does not match YYYY-MM-DD"
                )

        if stable_id:
            try:
                G2PStableID.objects.get(stable_id=stable_id)
            except G2PStableID.DoesNotExist:
                self.handle_no_permission("stable_id", stable_id)

            try:
                lgd_obj = LocusGenotypeDisease.objects.get(
                    stable_id__stable_id=stable_id
                )
            except LocusGenotypeDisease.DoesNotExist:
                self.handle_no_permission("G2P record", stable_id)

        # Define the filters
        filter_query = Q()
        filter_query_disease = Q()
        filter_query_record = Q()
        if stable_id:
            filter_query &= Q(lgd_id=lgd_obj.id)
            filter_query_disease &= Q(id=lgd_obj.disease.id)
            filter_query_record &= Q(stable_id__stable_id=stable_id)
        # Add the date to filter the results by date
        if start_date:
            filter_query &= Q(history_date__gte=date_input)
            filter_query_disease &= Q(history_date__gte=date_input)
            filter_query_record &= Q(history_date__gte=date_input)

        history_records_lgdpanel = LGDPanel.history.filter(filter_query).values(
            "history_user__first_name",
            "history_user__last_name",
            "history_date",
            "history_type",
            "panel_id__name",
            "lgd_id__stable_id__stable_id",
            "is_deleted",
        )

        history_records_lgdpublication = LGDPublication.history.filter(
            filter_query
        ).values(
            "history_user__first_name",
            "history_user__last_name",
            "history_date",
            "history_type",
            "publication_id__pmid",
            "lgd_id__stable_id__stable_id",
            "is_deleted",
        )

        history_records_ccm = LGDCrossCuttingModifier.history.filter(
            filter_query
        ).values(
            "history_user__first_name",
            "history_user__last_name",
            "history_date",
            "history_type",
            "ccm_id__value",
            "lgd_id__stable_id__stable_id",
            "is_deleted",
        )

        history_records_phenotype = LGDPhenotype.history.filter(filter_query).values(
            "history_user__first_name",
            "history_user__last_name",
            "history_date",
            "history_type",
            "phenotype_id__accession",
            "publication_id__pmid",
            "lgd_id__stable_id__stable_id",
            "is_deleted",
        )

        history_records_phenotype_sum = LGDPhenotypeSummary.history.filter(
            filter_query
        ).values(
            "history_user__first_name",
            "history_user__last_name",
            "history_date",
            "history_type",
            "summary",
            "publication_id__pmid",
            "lgd_id__stable_id__stable_id",
            "is_deleted",
        )

        history_records_consequence = LGDVariantGenccConsequence.history.filter(
            filter_query
        ).values(
            "history_user__first_name",
            "history_user__last_name",
            "history_date",
            "history_type",
            "variant_consequence_id__term",
            "lgd_id__stable_id__stable_id",
            "is_deleted",
        )

        history_records_var_type = LGDVariantType.history.filter(filter_query).values(
            "history_user__first_name",
            "history_user__last_name",
            "history_date",
            "history_type",
            "variant_type_ot_id__term",
            "publication_id__pmid",
            "lgd_id__stable_id__stable_id",
            "inherited",
            "de_novo",
            "unknown_inheritance",
            "is_deleted",
        )

        history_records_var_desc = LGDVariantTypeDescription.history.filter(
            filter_query
        ).values(
            "history_user__first_name",
            "history_user__last_name",
            "history_date",
            "history_type",
            "description",
            "publication_id__pmid",
            "lgd_id__stable_id__stable_id",
            "is_deleted",
        )

        history_records_mechanism_evidence = (
            LGDMolecularMechanismEvidence.history.filter(filter_query).values(
                "history_user__first_name",
                "history_user__last_name",
                "history_date",
                "history_type",
                "description",
                "publication_id__pmid",
                "lgd_id__stable_id__stable_id",
                "evidence_id__value",
                "evidence_id__subtype",
                "is_deleted",
            )
        )

        history_records_mechanism_synopsis = (
            LGDMolecularMechanismSynopsis.history.filter(filter_query).values(
                "history_user__first_name",
                "history_user__last_name",
                "history_date",
                "history_type",
                "synopsis_id__value",
                "synopsis_support_id__value",
                "lgd_id__stable_id__stable_id",
                "is_deleted",
            )
        )

        history_records_comments = LGDComment.history.filter(filter_query).values(
            "history_user__first_name",
            "history_user__last_name",
            "history_date",
            "history_type",
            "comment",
            "is_public",
            "lgd_id__stable_id__stable_id",
            "is_deleted",
        )

        # Get the main record sorted by history date
        history_records_lgd = (
            LocusGenotypeDisease.history.filter(filter_query_record)
            .order_by("-history_date")
            .values(
                "history_user__first_name",
                "history_user__last_name",
                "history_date",
                "history_type",
                "confidence_id__value",
                "genotype_id__value",
                "mechanism_id__value",
                "mechanism_support_id__value",
                "disease_id__name",
                "is_reviewed",
                "stable_id__stable_id",
                "is_deleted",
            )
        )

        # Updating the date_review has been triggering history rows
        # This means we have to clean these rows from this results before we report them
        new_history_records_lgd = self.remove_duplicates_history(history_records_lgd)

        # Get the disease info
        history_records_disease = Disease.history.filter(filter_query_disease).values(
            "history_user__first_name",
            "history_user__last_name",
            "history_date",
            "history_type",
            "name",
        )

        type_of_change = {"~": "updated", "+": "created", "-": "deleted"}

        output_data = []

        # Get panel history
        for log in history_records_lgdpanel:
            date_formatted = log.get("history_date").strftime("%Y-%m-%d %H:%M:%S")
            log_data = {}
            log_data["user"] = (
                f"{log.get('history_user__first_name')} {log.get('history_user__last_name')}"
            )
            log_data["change_type"] = type_of_change[log.get("history_type")]
            log_data["date"] = date_formatted
            log_data["panel_name"] = log.get("panel_id__name")
            log_data["g2p_id"] = log.get("lgd_id__stable_id__stable_id")
            log_data["is_deleted"] = log.get("is_deleted")
            log_data["data_type"] = "panel"

            output_data.append(log_data)

        # Get publication history
        for log in history_records_lgdpublication:
            date_formatted = log.get("history_date").strftime("%Y-%m-%d %H:%M:%S")
            log_data = {}
            log_data["user"] = (
                f"{log.get('history_user__first_name')} {log.get('history_user__last_name')}"
            )
            log_data["change_type"] = type_of_change[log.get("history_type")]
            log_data["date"] = date_formatted
            log_data["publication_pmid"] = log.get("publication_id__pmid")
            log_data["g2p_id"] = log.get("lgd_id__stable_id__stable_id")
            log_data["is_deleted"] = log.get("is_deleted")
            log_data["data_type"] = "publication"

            output_data.append(log_data)

        # Get ccm history
        for log in history_records_ccm:
            date_formatted = log.get("history_date").strftime("%Y-%m-%d %H:%M:%S")
            log_data = {}
            log_data["user"] = (
                f"{log.get('history_user__first_name')} {log.get('history_user__last_name')}"
            )
            log_data["change_type"] = type_of_change[log.get("history_type")]
            log_data["date"] = date_formatted
            log_data["ccm"] = log.get("ccm_id__value")
            log_data["g2p_id"] = log.get("lgd_id__stable_id__stable_id")
            log_data["is_deleted"] = log.get("is_deleted")
            log_data["data_type"] = "cross_cutting_modifier"

            output_data.append(log_data)

        # Get phenotype history
        for log in history_records_phenotype:
            date_formatted = log.get("history_date").strftime("%Y-%m-%d %H:%M:%S")
            log_data = {}
            log_data["user"] = (
                f"{log.get('history_user__first_name')} {log.get('history_user__last_name')}"
            )
            log_data["change_type"] = type_of_change[log.get("history_type")]
            log_data["date"] = date_formatted
            log_data["phenotype"] = log.get("phenotype_id__accession")
            log_data["publication_pmid"] = log.get("publication_id__pmid")
            log_data["g2p_id"] = log.get("lgd_id__stable_id__stable_id")
            log_data["is_deleted"] = log.get("is_deleted")
            log_data["data_type"] = "phenotype"

            output_data.append(log_data)

        # Get phenotype summary history
        for log in history_records_phenotype_sum:
            date_formatted = log.get("history_date").strftime("%Y-%m-%d %H:%M:%S")
            log_data = {}
            log_data["user"] = (
                f"{log.get('history_user__first_name')} {log.get('history_user__last_name')}"
            )
            log_data["change_type"] = type_of_change[log.get("history_type")]
            log_data["date"] = date_formatted
            log_data["summary"] = log.get("summary")
            log_data["publication_pmid"] = log.get("publication_id__pmid")
            log_data["g2p_id"] = log.get("lgd_id__stable_id__stable_id")
            log_data["is_deleted"] = log.get("is_deleted")
            log_data["data_type"] = "phenotype_summary"

            output_data.append(log_data)

        # Get variant gencc consequence history
        for log in history_records_consequence:
            date_formatted = log.get("history_date").strftime("%Y-%m-%d %H:%M:%S")
            log_data = {}
            log_data["user"] = (
                f"{log.get('history_user__first_name')} {log.get('history_user__last_name')}"
            )
            log_data["change_type"] = type_of_change[log.get("history_type")]
            log_data["date"] = date_formatted
            log_data["variant_consequence"] = log.get("variant_consequence_id__term")
            log_data["g2p_id"] = log.get("lgd_id__stable_id__stable_id")
            log_data["is_deleted"] = log.get("is_deleted")
            log_data["data_type"] = "variant_consequence"

            output_data.append(log_data)

        # Get variant type history
        for log in history_records_var_type:
            date_formatted = log.get("history_date").strftime("%Y-%m-%d %H:%M:%S")
            log_data = {}
            log_data["user"] = (
                f"{log.get('history_user__first_name')} {log.get('history_user__last_name')}"
            )
            log_data["change_type"] = type_of_change[log.get("history_type")]
            log_data["date"] = date_formatted
            log_data["variant_type"] = log.get("variant_type_ot_id__term")
            log_data["publication_pmid"] = log.get("publication_id__pmid")
            log_data["g2p_id"] = log.get("lgd_id__stable_id__stable_id")
            log_data["inherited"] = log.get("inherited")
            log_data["de_novo"] = log.get("de_novo")
            log_data["unknown_inheritance"] = log.get("unknown_inheritance")
            log_data["is_deleted"] = log.get("is_deleted")
            log_data["data_type"] = "variant_type"

            output_data.append(log_data)

        # Get variant description (HGVS) history
        for log in history_records_var_desc:
            date_formatted = log.get("history_date").strftime("%Y-%m-%d %H:%M:%S")
            log_data = {}
            log_data["user"] = (
                f"{log.get('history_user__first_name')} {log.get('history_user__last_name')}"
            )
            log_data["change_type"] = type_of_change[log.get("history_type")]
            log_data["date"] = date_formatted
            log_data["description"] = log.get("description")
            log_data["publication_pmid"] = log.get("publication_id__pmid")
            log_data["g2p_id"] = log.get("lgd_id__stable_id__stable_id")
            log_data["is_deleted"] = log.get("is_deleted")
            log_data["data_type"] = "variant_description"

            output_data.append(log_data)

        # Get mechanism evidence
        for log in history_records_mechanism_evidence:
            date_formatted = log.get("history_date").strftime("%Y-%m-%d %H:%M:%S")
            log_data = {}
            log_data["user"] = (
                f"{log.get('history_user__first_name')} {log.get('history_user__last_name')}"
            )
            log_data["change_type"] = type_of_change[log.get("history_type")]
            log_data["date"] = date_formatted
            log_data["description"] = log.get("description")
            log_data["publication_pmid"] = log.get("publication_id__pmid")
            log_data["g2p_id"] = log.get("lgd_id__stable_id__stable_id")
            log_data["evidence"] = log.get("evidence_id__value")
            log_data["evidence_type"] = log.get("evidence_id__subtype")
            log_data["is_deleted"] = log.get("is_deleted")
            log_data["data_type"] = "mechanism_evidence"

            output_data.append(log_data)

        # Get mechanism synopsis
        for log in history_records_mechanism_synopsis:
            date_formatted = log.get("history_date").strftime("%Y-%m-%d %H:%M:%S")
            log_data = {}
            log_data["user"] = (
                f"{log.get('history_user__first_name')} {log.get('history_user__last_name')}"
            )
            log_data["change_type"] = type_of_change[log.get("history_type")]
            log_data["date"] = date_formatted
            log_data["synopsis"] = log.get("synopsis_id__value")
            log_data["support"] = log.get("synopsis_support_id__value")
            log_data["g2p_id"] = log.get("lgd_id__stable_id__stable_id")
            log_data["is_deleted"] = log.get("is_deleted")
            log_data["data_type"] = "mechanism_synopsis"

            output_data.append(log_data)

        # Get lgd comments
        for log in history_records_comments:
            date_formatted = log.get("history_date").strftime("%Y-%m-%d %H:%M:%S")
            log_data = {}
            log_data["user"] = (
                f"{log.get('history_user__first_name')} {log.get('history_user__last_name')}"
            )
            log_data["change_type"] = type_of_change[log.get("history_type")]
            log_data["date"] = date_formatted
            log_data["comment"] = log.get("comment")
            log_data["is_public"] = log.get("is_public")
            log_data["g2p_id"] = log.get("lgd_id__stable_id__stable_id")
            log_data["is_deleted"] = log.get("is_deleted")
            log_data["data_type"] = "record_comment"

            output_data.append(log_data)

        # Get record info
        for log in new_history_records_lgd:
            date_formatted = log.get("history_date").strftime("%Y-%m-%d %H:%M:%S")
            log_data = {}
            log_data["user"] = (
                f"{log.get('history_user__first_name')} {log.get('history_user__last_name')}"
            )
            log_data["change_type"] = type_of_change[log.get("history_type")]
            log_data["date"] = date_formatted
            log_data["confidence"] = log.get("confidence_id__value")
            log_data["genotype"] = log.get("genotype_id__value")
            log_data["mechanism"] = log.get("mechanism_id__value")
            log_data["mechanism_support"] = log.get("mechanism_support_id__value")
            log_data["disease"] = log.get("disease_id__name")
            log_data["is_reviewed"] = log.get("is_reviewed")
            log_data["g2p_id"] = log.get("stable_id__stable_id")
            log_data["is_deleted"] = log.get("is_deleted")
            log_data["data_type"] = "record"

            output_data.append(log_data)

        # Get disease
        for log in history_records_disease:
            date_formatted = log.get("history_date").strftime("%Y-%m-%d %H:%M:%S")
            log_data = {}
            log_data["user"] = (
                f"{log.get('history_user__first_name')} {log.get('history_user__last_name')}"
            )
            log_data["change_type"] = type_of_change[log.get("history_type")]
            log_data["date"] = date_formatted
            log_data["name"] = log.get("name")
            log_data["data_type"] = "disease"

            output_data.append(log_data)

        # Sort the results by date
        sorted_output_data = sorted(
            output_data,
            key=lambda x: datetime.strptime(x["date"], "%Y-%m-%d %H:%M:%S"),
            reverse=True,
        )

        paginated_output = self.paginate_queryset(sorted_output_data)

        if paginated_output is not None:
            return self.get_paginated_response(paginated_output)

        return Response(
            {"results": sorted_output_data, "count": len(sorted_output_data)}
        )

    def remove_duplicates_history(self, history_records_lgd):
        """
        Remove duplicates from the list of LocusGenotypeDisease history records
        where a duplicate is defined as:
            - the current element matches the previous element in all fields
            except 'history_date', 'history_user__first_name' and 'history_user__last_name'.
        """
        if not history_records_lgd:
            return []

        # Keep the first element
        result = [history_records_lgd[0]]
        prev = history_records_lgd[0]

        for current in history_records_lgd[1:]:
            # Compare all keys except date and user
            filtered_prev = {
                k: v
                for k, v in prev.items()
                if k
                not in (
                    "history_date",
                    "history_user__first_name",
                    "history_user__last_name",
                )
            }
            filtered_curr = {
                k: v
                for k, v in current.items()
                if k
                not in (
                    "history_date",
                    "history_user__first_name",
                    "history_user__last_name",
                )
            }

            if filtered_prev != filtered_curr:
                result.append(current)
                # update the previous only if it is not duplicate
                prev = current

        return result
