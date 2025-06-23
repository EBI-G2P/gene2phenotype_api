from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import generics, permissions
from rest_framework import status
from drf_spectacular.utils import extend_schema
from rest_framework.request import Request

from gene2phenotype_app.serializers import (
    GenCCSubmissionSerializer,
    G2PStableIDSerializer,
    CreateGenCCSubmissionSerializer,
)


@extend_schema(exclude=True)
class GenCCSubmissionCreateView(generics.CreateAPIView):
    """Creates the GenCC submission record

    Args:
        generics (CreateAPIView): Create API view
    """

    serializer_class = CreateGenCCSubmissionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request: Request) -> Response:
        """Post method to create GenCC submission

        Args:
            request (Request): HttpRequest object

        Returns:
            Response: Response object confirming the bulk creation is completed
        """            
        serializer = CreateGenCCSubmissionSerializer(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

@extend_schema(exclude=True)
class GenCCSubmissionView(APIView):
    """Fetches unsubmitted stable ids"""

    def get(self, request: Request) -> Response:
        """Gets the unsubmitted stable ids

        Returns:
            Response: Response containing the status and the serializer.data
        """
        unused_ids = GenCCSubmissionSerializer.fetch_list_of_unsubmitted_stable_id()
        serializer = G2PStableIDSerializer(unused_ids, many=True)
        stable_ids = [entry["stable_id"] for entry in serializer.data]
        return Response(stable_ids, status=status.HTTP_200_OK)


@extend_schema(exclude=True)
class StableIDsWithLaterReviewDateView(APIView):
    """Fetches Stable IDs that has been updated since the last GenCC submission"""

    def get(self, request: Request) -> Response:
        """Gets the Stable IDs that were reviewed later

        Returns:
            Response: Response object containing the
             stable_ids as a list
             the count of stable_ids that fit this criteria
             status
        """
        stable_ids = GenCCSubmissionSerializer.fetch_stable_ids_with_later_review_date()
        return Response(
            {"ids": list(stable_ids), "count": len(list(stable_ids))},
            status=status.HTTP_200_OK,
        )


class RetrieveStableIDsWithSubmissionID(APIView):
    """Retrieve Stable ID with the Submission ID"""

    def get(self, request: Request, submission_id: str) -> Response:
        """Gets the stable id with the submission id

        Args:
            request (Request): HttpRequest
            submission_id (str): Submission id

        Returns:
            Response: Response object containing the
             stable_ids as a list
        """

        stable_id = GenCCSubmissionSerializer.get_stable_ids(submission_id)

        return Response(stable_id, status=status.HTTP_200_OK)
