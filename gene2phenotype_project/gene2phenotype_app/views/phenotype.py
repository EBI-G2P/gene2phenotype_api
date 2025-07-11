from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.decorators import api_view
from django.http import Http404
from django.db import transaction
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
import re

from gene2phenotype_app.serializers import (
    PhenotypeOntologyTermSerializer,
    LGDPhenotypeSerializer,
    LGDPhenotypeSummarySerializer,
    LGDPhenotypeListSerializer,
    LGDPhenotypeSummaryListSerializer,
)

from gene2phenotype_app.models import (
    OntologyTerm,
    LGDPhenotype,
    LocusGenotypeDisease,
    LGDPhenotypeSummary,
)

from .base import BaseAdd, CustomPermissionAPIView, IsSuperUser

from ..utils import validate_phenotype, get_date_now


@extend_schema(exclude=True)
@api_view(["GET"])
def PhenotypeDetail(request, hpo_list):
    """
    Retrieve phenotypes for a list of HPO IDs.
    The phenotype info is fetched from the HPO API.

    Args:
        hpo_list (str): A comma-separated string of HPO IDs

    Returns a dictionary with the following format:
        results (list): list of the phenotype data
        count (int): number of HPO IDs in the response

    Raises: Invalid HPO
    """
    id_list = hpo_list.split(",")
    data = []
    invalid_hpos = []

    for hpo in id_list:
        # HPO has invalid format
        if not re.match(r"HP\:\d+", hpo):
            invalid_hpos.append(hpo)

        else:
            # HPO has the correct format
            response = validate_phenotype(hpo)

            if not response:
                invalid_hpos.append(hpo)
            else:
                # check if phenotype has a description
                if "definition" in response:
                    phenotype_description = response["definition"]
                else:
                    phenotype_description = None

                data.append(
                    {
                        "accession": hpo,
                        "term": response["name"],
                        "description": phenotype_description,
                    }
                )

    # if any of the HPO IDs is invalid raise error and display all invalid IDs
    if invalid_hpos:
        hpo_list = ", ".join(invalid_hpos)
        response = Response(
            {"detail": f"Invalid HPO term(s): {hpo_list}"},
            status=status.HTTP_404_NOT_FOUND,
        )

    else:
        response = Response({"results": data, "count": len(data)})

    return response


### LGD-phenotype ###
# Add or delete data
@extend_schema(exclude=True)
class LGDEditPhenotypes(CustomPermissionAPIView):
    http_method_names = ["post", "patch", "options"]

    # Define specific permissions
    method_permissions = {
        "post": [permissions.IsAuthenticated],
        "patch": [permissions.IsAuthenticated, IsSuperUser],
    }

    def get_serializer_class(self, action):
        """
        Returns the appropriate serializer class based on the action.
        To add data use LGDPhenotypeListSerializer: it accepts a list of phenotypes.
        To delete data use LGDPhenotypeSerializer: it accepts one phenotype.
        """
        action = action.lower()

        if action == "post":
            return LGDPhenotypeListSerializer
        elif action == "patch":
            return LGDPhenotypeSerializer
        else:
            return None

    @transaction.atomic
    def post(self, request, stable_id):
        """
        The post method adds a list of phenotypes to an existing G2P record (LGD).
        It also adds phenotype summaries.
        We want to whole process to be done in one db transaction.

        Args:
            request (dict):
                - hpo_terms: list of phenotypes (optional)
                - summaries: list of phenotype summaries (optional)

            Example:
                {
                    "hpo_terms": [{
                        "accession": "HP:0003974",
                        "publication": 1
                    }],
                    "summaries": [{
                        "summary": "This is a summary",
                        "publication": [1, 12345]
                    }]
                }
        """
        lgd = get_object_or_404(
            LocusGenotypeDisease, stable_id__stable_id=stable_id, is_deleted=0
        )

        if not request.data:
            return Response(
                {"error": "Empty data. Please provide valid data."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Prepare the response in case the data does not follow correct format
        response = Response(
            {"error": "Invalid data format. Please provide valid data."},
            status=status.HTTP_400_BAD_REQUEST,
        )

        # Check and prepare data structure the send to the serializer
        # LGDPhenotypeListSerializer accepts the phenotypes in a specific struture
        if "hpo_terms" in request.data:
            success_flag = 0  # flag if at least one phenotype is updated successfully
            # LGDPhenotypeListSerializer accepts a list of phenotypes
            serializer_list = LGDPhenotypeListSerializer(
                data={"phenotypes": request.data["hpo_terms"]}
            )

            if serializer_list.is_valid():
                phenotypes_data = serializer_list.validated_data.get("phenotypes")

                if not phenotypes_data:
                    return Response(
                        {"error": "Empty phenotype. Please provide valid data."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                # Add each phenotype from the input list
                for phenotype in phenotypes_data:
                    # Format data to be accepted by LGDPhenotypeSerializer
                    phenotype_input = phenotype.get("phenotype")
                    phenotype_input["publication"] = phenotype.get("publication")[
                        "pmid"
                    ]

                    serializer_class = LGDPhenotypeSerializer(
                        data=phenotype_input, context={"lgd": lgd}
                    )

                    if serializer_class.is_valid():
                        serializer_class.save()
                        success_flag = 1
                        response = Response(
                            {
                                "message": "Phenotype added to the G2P entry successfully."
                            },
                            status=status.HTTP_201_CREATED,
                        )
                    else:
                        response = Response(
                            {"error": serializer_class.errors},
                            status=status.HTTP_400_BAD_REQUEST,
                        )

                # Update the date of the last update in the record table
                if success_flag:
                    lgd.date_review = get_date_now()
                    lgd.save()

            else:
                response = Response(
                    {"error": serializer_list.errors},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # Add extra functionality to the endpoint
        # Also adds phenotype summary - phenotypes and phenotype summary are edited on the website at the same time
        if "summaries" in request.data:
            success_flag = 0  # flag if at least one phenotype is updated successfully
            serializer_summary_list = LGDPhenotypeSummaryListSerializer(
                data={"summaries": request.data["summaries"]}
            )

            if serializer_summary_list.is_valid():
                phenotype_summary_data = serializer_summary_list.validated_data.get(
                    "summaries"
                )

                if not phenotype_summary_data:
                    return Response(
                        {
                            "error": "Empty phenotype summary. Please provide valid data."
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                # Add each phenotype summary from the input list
                for phenotype_summary in phenotype_summary_data:
                    serializer_class = LGDPhenotypeSummarySerializer(
                        data=phenotype_summary, context={"lgd": lgd}
                    )

                    if serializer_class.is_valid():
                        serializer_class.save()
                        success_flag = 1
                        response = Response(
                            {
                                "message": "Phenotype summary added to the G2P entry successfully."
                            },
                            status=status.HTTP_201_CREATED,
                        )
                    else:
                        response = Response(
                            {"error": serializer_class.errors},
                            status=status.HTTP_400_BAD_REQUEST,
                        )

                # Update the date of the last update in the record table
                if success_flag:
                    lgd.date_review = get_date_now()
                    lgd.save()

            else:
                response = Response(
                    {"error": serializer_summary_list.errors},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        return response

    @transaction.atomic
    def patch(self, request, stable_id):
        """
        Delete a phenotype from a LGD record.
        The deletion does not remove the entry from the database, instead
        it sets the flag 'is_deleted' to 1.
        """
        accession = request.data.get("accession")
        user = self.request.user  # TODO check if user has permission

        lgd_obj = get_object_or_404(
            LocusGenotypeDisease, stable_id__stable_id=stable_id, is_deleted=0
        )

        # Fetch phenotype from Ontology Term
        try:
            phenotype_obj = OntologyTerm.objects.get(accession=accession)
        except OntologyTerm.DoesNotExist:
            raise Http404(f"Cannot find phenotype for accession '{accession}'")

        # Fetch LGD-phenotype list
        # Each phenotype can be linked to several publications
        try:
            LGDPhenotype.objects.filter(
                lgd=lgd_obj, phenotype=phenotype_obj, is_deleted=0
            ).update(is_deleted=1)
        except:
            return Response(
                {
                    "error": f"Could not delete phenotype '{accession}' for ID '{stable_id}'"
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        else:
            # The phenotype was deleted successfully - update the date of last update in the record table
            lgd_obj.date_review = get_date_now()
            lgd_obj.save()
            return Response(
                {
                    "message": f"Phenotype '{accession}' successfully deleted for ID '{stable_id}'"
                },
                status=status.HTTP_200_OK,
            )


@extend_schema(exclude=True)
class LGDEditPhenotypeSummary(CustomPermissionAPIView):
    http_method_names = ["post", "patch", "options"]

    # Define specific permissions
    method_permissions = {
        "post": [permissions.IsAuthenticated],
        "patch": [permissions.IsAuthenticated, IsSuperUser],
    }

    def get_serializer_class(self, action):
        """
        Returns the appropriate serializer class based on the action.
        To add data use LGDPhenotypeSummaryListSerializer: it accepts a list of phenotype summaries.
        To delete data use LGDPhenotypeSummarySerializer: it accepts one phenotype summary.
        """
        action = action.lower()

        if action == "post":
            return LGDPhenotypeSummaryListSerializer
        elif action == "patch":
            return LGDPhenotypeSummarySerializer
        else:
            return None

    @transaction.atomic
    def post(self, request, stable_id):
        """
        The post method adds a list of phenotype summaries to an existing G2P record (LGD).
        A summary can be linked to one or more publications.

        We want to whole process to be done in one db transaction.

        Args:
            request (list): list of phenotype summaries, each summaries has to following format
                summary (string): phenotype summary text (mandatory)
                publication (list): list of pmids (mandatory)

            Example:
                [{
                    "summary": "This is a summary",
                    "publication": [1, 12345]
                }]
        """
        user = self.request.user
        success_flag = 0  # flag if at least one phenotype is updated successfully

        lgd = get_object_or_404(
            LocusGenotypeDisease, stable_id__stable_id=stable_id, is_deleted=0
        )

        serializer_summary_list = LGDPhenotypeSummaryListSerializer(
            data={"summaries": request.data}
        )

        if serializer_summary_list.is_valid():
            phenotype_summary_data = serializer_summary_list.validated_data.get(
                "summaries"
            )

            if not phenotype_summary_data:
                return Response(
                    {"error": "Empty phenotype summary. Please provide valid data."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Add each phenotype summary from the input list
            # LGDPhenotypeSummarySerializer accepts a summary of phenotypes associated with pmids
            for phenotype_summary in phenotype_summary_data:
                serializer_class = LGDPhenotypeSummarySerializer(
                    data=phenotype_summary, context={"lgd": lgd}
                )

                if serializer_class.is_valid():
                    serializer_class.save()
                    success_flag = 1
                    response = Response(
                        {
                            "message": "Phenotype summary added to the G2P entry successfully."
                        },
                        status=status.HTTP_201_CREATED,
                    )
                else:
                    response = Response(
                        {"error": serializer_class.errors},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

            # Update the date of the last update in the record table
            if success_flag:
                lgd.date_review = get_date_now()
                lgd.save()

        else:
            response = Response(
                {"error": serializer_summary_list.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return response

    @transaction.atomic
    def patch(self, request, stable_id):
        """
        This method deletes the LGD-phenotype summary.
        The deletion does not remove the entry from the database, instead
        it sets the flag 'is_deleted' to 1.
        """
        summary = request.data.get("summary")

        # Get G2P entries to be deleted
        lgd_obj = get_object_or_404(
            LocusGenotypeDisease, stable_id__stable_id=stable_id, is_deleted=0
        )

        # Fetch LGD-phenotype summary list
        # Different rows mean the lgd-phenotype summary is associated with multiple publications
        # We have to delete all rows
        try:
            LGDPhenotypeSummary.objects.filter(
                lgd=lgd_obj, summary=summary, is_deleted=0
            ).update(is_deleted=1)
        except:
            return Response(
                {"error": f"Could not delete phenotype summary for ID '{stable_id}'"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        else:
            # The phenotype was deleted successfully - update the date of last update in the record table
            lgd_obj.date_review = get_date_now()
            lgd_obj.save()
            return Response(
                {
                    "message": f"Phenotype summary successfully deleted for ID '{stable_id}'"
                },
                status=status.HTTP_200_OK,
            )


### Add phenotype ###
@extend_schema(exclude=True)
class AddPhenotype(BaseAdd):
    """
    Add new phenotype.
    The create method is in the PhenotypeSerializer.

    Called by: endpoint add/phenotype/
    """

    serializer_class = PhenotypeOntologyTermSerializer
    permission_classes = [permissions.IsAuthenticated]
