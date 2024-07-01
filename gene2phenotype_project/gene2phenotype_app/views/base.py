from rest_framework import generics, status
from django.http import Http404
from rest_framework.response import Response
from django.db import transaction


class BaseView(generics.ListAPIView):
    """
        Generic methods to handle expection and permissions.
    """
    def handle_no_permission(self, name_type, name):
        if name is None:
            raise Http404(f"{name_type}")
        else:
            raise Http404(f"No matching {name_type} found for: {name}")

    def handle_exception(self, exc):
        if isinstance(exc, Http404):
            return Response({"message": str(exc)}, status=status.HTTP_404_NOT_FOUND)

        return super().handle_exception(exc)


class BaseAdd(generics.CreateAPIView):
    """
        Generic method to add data
    """
    http_method_names = ['post', 'head']

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
