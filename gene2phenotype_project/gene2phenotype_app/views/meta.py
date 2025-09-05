from rest_framework import permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from django.db.models import Q, Max
from drf_spectacular.utils import extend_schema, OpenApiResponse
import textwrap

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
)

from gene2phenotype_app.serializers import MetaSerializer

from .base import BaseView


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
    permission_classes = [permissions.IsAuthenticated]

    def get_data(self):
        """
        Return the history data for all tables associated with the LGD record.
        """
        stable_id = self.request.query_params.get("stable_id", None)

        if stable_id is None:
            self.handle_missing_input("stable_id", stable_id)

        try:
            G2PStableID.objects.get(stable_id=stable_id, is_deleted=0)
        except G2PStableID.DoesNotExist:
            self.handle_no_permission("stable_id", stable_id)

        try:
            lgd_obj = LocusGenotypeDisease.objects.get(
                stable_id__stable_id=stable_id, is_deleted=0
            )
        except LocusGenotypeDisease.DoesNotExist:
            self.handle_no_permission("G2P record", stable_id)

        # Define the filter
        filter_query = Q(lgd_id=lgd_obj.id)

        history_records_lgdpanel = LGDPanel.history.filter(filter_query).values(
            "history_user__first_name",
            "history_user__last_name",
            "history_date",
            "history_type",
            "panel_id__name",
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
            "is_deleted",
        )

        history_records_phenotype = LGDPhenotype.history.filter(filter_query).values(
            "history_user__first_name",
            "history_user__last_name",
            "history_date",
            "history_type",
            "phenotype_id__accession",
            "publication_id__pmid",
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
            "is_deleted",
        )

        history_records_var_type = LGDVariantType.history.filter(filter_query).values(
            "history_user__first_name",
            "history_user__last_name",
            "history_date",
            "history_type",
            "variant_type_ot_id__term",
            "publication_id__pmid",
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
                "is_deleted",
            )
        )

        # Get the disease info
        history_records_disease = Disease.history.filter(id=lgd_obj.disease.id).values(
            "history_user__first_name",
            "history_user__last_name",
            "history_date",
            "history_type",
            "name",
        )

        return (
            history_records_lgdpanel,
            history_records_lgdpublication,
            history_records_ccm,
            history_records_phenotype,
            history_records_phenotype_sum,
            history_records_consequence,
            history_records_var_type,
            history_records_var_desc,
            history_records_mechanism_evidence,
            history_records_mechanism_synopsis,
            history_records_disease,
        )

    def list(self, request, *args, **kwargs):
        """
        Returns a dictionary where key is the type of data and value is a list of activities.
        """
        (
            history_records_lgdpanel,
            history_records_lgdpublication,
            history_records_ccm,
            history_records_phenotype,
            history_records_phenotype_sum,
            history_records_consequence,
            history_records_var_type,
            history_records_var_desc,
            history_records_mechanism_evidence,
            history_records_mechanism_synopsis,
            history_records_disease,
        ) = self.get_data()
        type_of_change = {"~": "updated", "+": "created", "-": "deleted"}

        output_data = {}
        output_data["panels"] = []
        output_data["publications"] = []
        output_data["cross_cutting_modifier"] = []
        output_data["phenotypes"] = []
        output_data["phenotype_summary"] = []
        output_data["variant_consequence"] = []
        output_data["variant_type"] = []
        output_data["variant_description"] = []
        output_data["molecular_mechanism_evidence"] = []
        output_data["molecular_mechanism_synopsis"] = []
        output_data["disease"] = []

        # Get panel history
        for log in history_records_lgdpanel:
            date_formatted = log.get("history_date").strftime("%Y-%m-%d %H:%M:%S")
            log_data = {}
            log_data["user"] = (
                f"{log.get('history_user__first_name')} {log.get('history_user__last_name')}"
            )
            log_data["change_type"] = type_of_change[log.get("history_type")]
            log_data["date"] = date_formatted
            log_data["panel"] = log.get("panel_id__name")
            log_data["is_deleted"] = log.get("is_deleted")

            output_data["panels"].append(log_data)

        # Get publication history
        for log in history_records_lgdpublication:
            date_formatted = log.get("history_date").strftime("%Y-%m-%d %H:%M:%S")
            log_data = {}
            log_data["user"] = (
                f"{log.get('history_user__first_name')} {log.get('history_user__last_name')}"
            )
            log_data["change_type"] = type_of_change[log.get("history_type")]
            log_data["date"] = date_formatted
            log_data["publication"] = log.get("publication_id__pmid")
            log_data["is_deleted"] = log.get("is_deleted")

            output_data["publications"].append(log_data)

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
            log_data["is_deleted"] = log.get("is_deleted")

            output_data["cross_cutting_modifier"].append(log_data)

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
            log_data["publication"] = log.get("publication_id__pmid")
            log_data["is_deleted"] = log.get("is_deleted")

            output_data["phenotypes"].append(log_data)

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
            log_data["publication"] = log.get("publication_id__pmid")
            log_data["is_deleted"] = log.get("is_deleted")

            output_data["phenotype_summary"].append(log_data)

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
            log_data["is_deleted"] = log.get("is_deleted")

            output_data["variant_consequence"].append(log_data)

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
            log_data["publication"] = log.get("publication_id__pmid")
            log_data["inherited"] = log.get("inherited")
            log_data["de_novo"] = log.get("de_novo")
            log_data["unknown_inheritance"] = log.get("unknown_inheritance")
            log_data["is_deleted"] = log.get("is_deleted")

            output_data["variant_type"].append(log_data)

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
            log_data["publication"] = log.get("publication_id__pmid")
            log_data["is_deleted"] = log.get("is_deleted")

            output_data["variant_description"].append(log_data)

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
            log_data["publication"] = log.get("publication_id__pmid")
            log_data["evidence"] = log.get("evidence_id__value")
            log_data["evidence_type"] = log.get("evidence_id__subtype")
            log_data["is_deleted"] = log.get("is_deleted")

            output_data["molecular_mechanism_evidence"].append(log_data)

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
            log_data["is_deleted"] = log.get("is_deleted")

            output_data["molecular_mechanism_synopsis"].append(log_data)

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

            output_data["disease"].append(log_data)

        return Response(output_data)
