from rest_framework import status, permissions
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema

from gene2phenotype_app.models import LGDReviewCase
from gene2phenotype_app.serializers import (
    LGDReviewCaseSerializer,
    LGDReviewCaseCreateSerializer,
    LGDReviewCaseUpdateSerializer,
)

from .base import BaseAPIView


@extend_schema(exclude=True)
class ReviewQueueListCreate(BaseAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = LGDReviewCaseSerializer
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self, request):
        queryset = LGDReviewCase.objects.filter(is_deleted=0).select_related(
            "lgd", "lgd__stable_id", "created_by", "assigned_to"
        )
        status_value = request.query_params.get("status")
        stable_id = request.query_params.get("stable_id")
        assigned_to_me = request.query_params.get("assigned_to_me")

        if status_value:
            queryset = queryset.filter(status=status_value)
        if stable_id:
            queryset = queryset.filter(lgd__stable_id__stable_id=stable_id)
        if assigned_to_me and assigned_to_me.lower() == "true":
            queryset = queryset.filter(assigned_to__email=request.user.email)

        return queryset.order_by("-date_last_update")

    def get(self, request):
        queryset = self.get_queryset(request)
        serializer = self.serializer_class(queryset, many=True)
        return Response({"results": serializer.data, "count": len(serializer.data)})

    def post(self, request):
        serializer = LGDReviewCaseCreateSerializer(
            data=request.data, context={"user": request.user}
        )
        serializer.is_valid(raise_exception=True)
        review_case = serializer.save()

        return Response(
            LGDReviewCaseSerializer(review_case).data, status=status.HTTP_201_CREATED
        )


@extend_schema(exclude=True)
class ReviewQueueDetail(BaseAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = LGDReviewCaseSerializer
    http_method_names = ["get", "patch", "head", "options"]

    def get_object(self, case_id):
        return get_object_or_404(LGDReviewCase, id=case_id, is_deleted=0)

    def get(self, request, case_id):
        review_case = self.get_object(case_id)
        serializer = self.serializer_class(review_case)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request, case_id):
        review_case = self.get_object(case_id)
        serializer = LGDReviewCaseUpdateSerializer(
            review_case, data=request.data, partial=True, context={"user": request.user}
        )
        serializer.is_valid(raise_exception=True)
        review_case = serializer.save()
        return Response(
            LGDReviewCaseSerializer(review_case).data, status=status.HTTP_200_OK
        )
