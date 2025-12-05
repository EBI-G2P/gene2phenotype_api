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
    serializer_class = CreateGenCCSubmissionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request: Request) -> Response:
        """
        Create one or more GenCC submissions.

        Args:
            request (Request): The incoming request containing a list of GenCC submission objects.

        Returns:
            Response: Empty body with HTTP 201 status if creation succeeds.
        """
        serializer = CreateGenCCSubmissionSerializer(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(status=status.HTTP_201_CREATED)


@extend_schema(exclude=True)
class GenCCSubmissionView(APIView):
    def get(self, request: Request) -> Response:
        """
        Retrieve G2P IDs that have not yet been submitted to GenCC.

        Returns:
            Response: A JSON list of id strings.
        """
        unused_ids = GenCCSubmissionSerializer.fetch_list_of_unsubmitted_stable_id()
        serializer = G2PStableIDSerializer(unused_ids, many=True)
        stable_ids = [entry["stable_id"] for entry in serializer.data]
        return Response(stable_ids, status=status.HTTP_200_OK)


@extend_schema(exclude=True)
class GenCCDeletedRecords(APIView):
    def get(self, request: Request) -> Response:
        """
        Gets the records that have been submitted to GenCC but are now deleted in G2P.

        Returns:
            Response: Response object containing
             - ids: dict with stable_id as key and submission_id as value
             - count: number of IDs
        """
        deleted_ids = GenCCSubmissionSerializer.fetch_list_of_deleted_stable_id()
        return Response(
            {"ids": deleted_ids, "count": len(deleted_ids)},
            status=status.HTTP_200_OK,
        )


@extend_schema(exclude=True)
class StableIDsWithLaterReviewDateView(APIView):
    def get(self, request: Request) -> Response:
        """
        Fetches records that have been updated in G2P since the last GenCC submission.
        It returns the GenCC ID used for the G2P submission and the G2P ID.

        Returns:
            Response: Response object containing
             - ids: dict with stable_id as key and submission_id as value
             - count: number of IDs
        """
        stable_ids = GenCCSubmissionSerializer.fetch_stable_ids_with_later_review_date()
        return Response(
            {"ids": stable_ids, "count": len(list(stable_ids))},
            status=status.HTTP_200_OK,
        )
