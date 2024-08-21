from rest_framework import generics, status
from django.http import Http404
from rest_framework.response import Response
from django.db import transaction
from django.urls import get_resolver
from rest_framework.decorators import api_view
from gene2phenotype_app.models import User


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

class BaseUpdate(generics.UpdateAPIView):
    """
        Generic methods to handle expection and permissions.
    """
    def handle_no_permission(self, data, stable_id):
        if data is None:
            raise Http404(f"{data}")
        else:
            raise Http404(f"Could not find '{data}' for ID '{stable_id}'")


@api_view(['GET'])
def ListEndpoints(request):
    """
        Returns a list of available endpoints.
    """
    user = request.user

    # Get user obj
    try:
        user_obj = User.objects.get(email=user, is_active=1)
    except User.DoesNotExist:
        user_obj = None

    resolver = get_resolver()
    url_patterns = []
    # use a set to avoid duplicates
    list_urls = set()

    for key in resolver.reverse_dict.keys():
        url_patterns.extend(resolver.reverse_dict[key])

    for url_pattern in url_patterns:
        if isinstance(url_pattern, list):
            pattern = url_pattern[0][0]

            # Format the url to display the django format
            # Remove 'gene2phenotype/api/' from the urls
            pattern = pattern.replace("%(", "<").replace(")s", ">").replace("gene2phenotype/api/", "")

            # Authenticated users have access to all endpoints
            # Non-authenticated users can only search data
            if user_obj is not None and pattern != "":
                list_urls.add(pattern)
            elif user_obj is None and pattern != "" and "add" not in pattern and "curation" not in pattern:
                list_urls.add(pattern)

    return Response({"endpoints": sorted(list_urls)})