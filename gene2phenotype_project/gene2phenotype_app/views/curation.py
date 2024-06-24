import json
from rest_framework import generics, status, permissions
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from jsonschema import validate, exceptions
from django.conf import settings
from rest_framework.views import APIView

from gene2phenotype_app.serializers import CurationDataSerializer

from gene2phenotype_app.models import G2PStableID, CurationData, LocusGenotypeDisease

from .base import BaseView, BaseAdd


### Curation data
class AddCurationData(BaseAdd):
    """
        Add a new curation entry.
        It is only available for authenticated users.
        We do not need to check for authenticated users because of the user management issues.
    """
    serializer_class = CurationDataSerializer
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        """
            Handle POST requests.

            Args:
                request: The HTTP request object.

            Returns:
                A Response object with appropriate status and message.
        """
        json_file_path = settings.BASE_DIR.joinpath("gene2phenotype_app", "utils", "curation_schema.json")
        try:
            with open(json_file_path, 'r') as file:
                schema = json.load(file)
        except FileNotFoundError:
            return Response({"message": "Schema file not found"}, status=status.HTTP_404_NOT_FOUND)

        # Validate the JSON data against the schema
        try:
            validate(instance=request.data, schema=schema)
        except exceptions.ValidationError as e:
            return Response({"message": "JSON data does not follow the required format, Required format is" + str(e)}, status=status.HTTP_400_BAD_REQUEST)

        serializer = self.serializer_class(data=request.data, context={'user': self.request.user})
        if serializer.is_valid():
            
            serializer.save()
            return Response({"message": "Data saved successfully"}, status=status.HTTP_200_OK)
        else:
            return Response({"errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

class ListCurationEntries(BaseView):
    """
        List all the curation entries being curated by the user.
        It is only available for authenticated users.
        Returns:
            - list of entries
            - number of entries
    """
    serializer_class = CurationDataSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
            Retrieve the queryset of CurationData objects.

            Returns:
                Queryset of CurationData objects.
            Future:

                user = self.request.user commenting this out for now we should user to filter the Curation objects we are getting for the future
        """
        queryset = CurationData.objects.all()

        return queryset

    def list(self, request, *args, **kwargs):
        """
            List the CurationData objects.

            Args:
                request: The HTTP request object.
                *args: Additional positional arguments.
                **kwargs: Additional keyword arguments.

            Returns:
                Response containing the list of CurationData objects with specified fields.
        """
        queryset = self.get_queryset()
        list_data = []
        for data in queryset:
            entry = {
                "locus":data.json_data["locus"],
                "session_name": data.session_name,
                "stable_id": data.stable_id.stable_id,
                "created_on": data.date_created.strftime("%Y-%m-%d %H:%M"),
                "last_update": data.date_last_update.strftime("%Y-%m-%d %H:%M")
            }

            list_data.append(entry)

        return Response({'results':list_data, 'count':len(list_data)})

class CurationDataDetail(BaseView):
    """
        Returns all the data for a specific curation entry.
        It is only available for authenticated users.
    """
    serializer_class = CurationDataSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        stable_id = self.kwargs['stable_id']
        user = self.request.user

        g2p_stable_id = get_object_or_404(G2PStableID, stable_id=stable_id)
        # Get the entry if the user matches
        queryset = CurationData.objects.filter(stable_id=g2p_stable_id, user=user)

        if not queryset.exists():
            self.handle_no_permission('Entry', stable_id)
        else:
            return queryset

    def list(self, request, *args, **kwargs):
        curation_data_obj = self.get_queryset().first()

        response_data = {
                'session_name': curation_data_obj.session_name,
                'stable_id': curation_data_obj.stable_id.stable_id,
                'created_on': curation_data_obj.date_created,
                'last_updated_on': curation_data_obj.date_last_update,
                'data': curation_data_obj.json_data,
            }
        return Response(response_data)

class UpdateCurationData(generics.UpdateAPIView):
    """
        Updates the JSON data for the specific G2P ID.
    """

    http_method_names = ['put', 'options']
    serializer_class = CurationDataSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        stable_id = self.kwargs['stable_id']
        user = self.request.user

        g2p_stable_id = get_object_or_404(G2PStableID, stable_id=stable_id)
        # Get the entry for this user
        queryset = CurationData.objects.filter(stable_id=g2p_stable_id, user__email=user)

        if not queryset.exists():
            self.handle_no_permission('Entry', stable_id)
        else:
            return queryset

    def update(self, request, *args, **kwargs):
        curation_obj = self.get_queryset().first()

        json_file_path = settings.BASE_DIR.joinpath("gene2phenotype_app", "utils", "curation_schema.json")
        try:
            with open(json_file_path, 'r') as file:
                schema = json.load(file)
        except FileNotFoundError:
            return Response({"message": "Schema file not found"}, status=status.HTTP_404_NOT_FOUND)
        # Validate the JSON data against the schema
        try:
            validate(instance=request.data, schema=schema)
        except exceptions.ValidationError as e:
            return Response({"message": "JSON data does not follow the required format, Required format is" + str(e)}, status=status.HTTP_400_BAD_REQUEST)

        serializer = CurationDataSerializer(curation_obj, data=request.data, context={'user': self.request.user})

        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Data updated successfully"})

        else:
            return Response({"message": "Failed to update data", "details": serializer.errors})

class PublishRecord(APIView):
    http_method_names = ['post', 'head']
    serializer_class = CurationDataSerializer
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, stable_id):
        user = self.request.user

        try:
            # Get curation record
            curation_obj = CurationData.objects.get(stable_id__stable_id=stable_id,
                                                    user__email=user)

            # Check if there is enough data to publish the record
            locus_obj = self.serializer_class().validate_to_publish(curation_obj)

            # Publish record
            try:
                lgd_obj = self.serializer_class(context={'user': user}).publish(curation_obj)
                # Delete entry from 'curation_data'
                curation_obj.delete()

                return Response({
                    "message": f"Record '{lgd_obj.stable_id.stable_id}' published successfully"
                    }, status=status.HTTP_201_CREATED)

            except LocusGenotypeDisease.DoesNotExist:
                Response({
                    "message": f"Failed to publish record ID '{stable_id}'"
                    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        except CurationData.DoesNotExist:
            return Response({
                "message": f"Curation data not found for ID '{stable_id}'"
                }, status=status.HTTP_404_NOT_FOUND)
