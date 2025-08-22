from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import Http404
from django.urls import reverse
from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.permissions import BasePermission
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.views import APIView


class BaseView(generics.ListAPIView):
    """
    Generic methods to handle expection and permissions for classes
    using generics.ListAPIView.
    """

    def handle_no_permission(self, name_type, name):
        if name is None:
            raise Http404(f"{name_type}")
        else:
            raise Http404(f"No matching {name_type} found for: {name}")

    def handle_exception(self, exc):
        if isinstance(exc, Http404):
            return Response({"error": str(exc)}, status=status.HTTP_404_NOT_FOUND)

        return super().handle_exception(exc)

    def handle_merged_record(self, old_stable_id, new_stable_id):
        return Response(
            {
                "message": f"{old_stable_id} is no longer available. It has been merged into {new_stable_id}",
                "stable_id": new_stable_id,
            },
            status=status.HTTP_410_GONE,
        )


class BaseAPIView(APIView):
    """
    Generic methods to handle expection and permissions for classes
    using APIView.
    """

    def handle_no_permission(self, name_type, name):
        if name is None:
            raise Http404(f"{name_type}")
        else:
            raise Http404(f"No matching {name_type} found for: {name}")

    def handle_no_permission_authentication(self, name_type, name):
        if name is None:
            raise AuthenticationFailed("No permission")
        else:
            raise AuthenticationFailed(f"No permission to access {name_type} {name}")

    def handle_exception(self, exc):
        if isinstance(exc, Http404):
            return Response({"error": str(exc)}, status=status.HTTP_404_NOT_FOUND)

        return super().handle_exception(exc)

    def handle_merged_record(self, old_stable_id, new_stable_id):
        return Response(
            {
                "message": f"{old_stable_id} is no longer available. It has been merged into {new_stable_id}",
                "stable_id": new_stable_id,
            },
            status=status.HTTP_410_GONE,
        )


class BaseAdd(generics.CreateAPIView):
    """Generic method to add data"""

    http_method_names = ["post", "head"]

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data, status=status.HTTP_201_CREATED, headers=headers
        )


class BaseUpdate(generics.UpdateAPIView):
    """Generic methods to handle expection and permissions."""

    def handle_no_permission(self, data, stable_id):
        if data is None:
            raise Http404(f"{data}")
        else:
            raise Http404(f"Could not find '{data}' for ID '{stable_id}'")

    def handle_no_update(self, data, stable_id):
        if data is None:
            return Response(
                {"error": f"Cannot update '{data}'"},
                status=status.HTTP_403_FORBIDDEN,
            )
        else:
            return Response(
                {"error": f"Cannot update '{data}' for ID '{stable_id}'"},
                status=status.HTTP_403_FORBIDDEN,
            )

    def handle_update_exception(self, exception, context_message):
        if hasattr(exception, "detail") and "message" in exception.detail:
            error_message = exception.detail["message"]
            return Response(
                {"error": f"{context_message}: {error_message}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        else:
            error_message = context_message
            return Response(
                {"error": f"{context_message}"}, status=status.HTTP_400_BAD_REQUEST
            )

    def handle_missing_data(self, data_type):
        raise Http404(f"{data_type} is missing")


class CustomPermissionAPIView(APIView):
    """
    Base API view with reusable get_permissions logic.
    This view is used by endpoints that can update or delete data.
    Usually the method post() updates data while update() deletes data.
    """

    method_permissions = {
        "update": [
            permissions.IsAuthenticated()
        ],  # this will be defined further in the specific view
        "post": [permissions.IsAuthenticated()],
        "patch": [permissions.IsAuthenticated()],
    }

    def get_permissions(self):
        """
        Instantiates and returns the list of permissions for this view.
        post(): updates data - available to all authenticated users
        update(): deletes data - only available to authenticated super users
        patch(): deletes data - only available to authenticated super users
        """
        if (
            self.request.method.lower() == "update"
            or self.request.method.lower() == "patch"
        ):
            return [permissions.IsAuthenticated(), IsSuperUser()]
        return [permissions.IsAuthenticated()]


class IsSuperUser(BasePermission):
    """Allows access only to superusers."""

    def has_permission(self, request, view):
        if not (request.user and request.user.is_superuser):
            raise PermissionDenied(
                {"error": "You do not have permission to perform this action."}
            )
        return True
