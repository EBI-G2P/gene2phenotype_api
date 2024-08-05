import json, jsonschema
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
        user = self.request.user

        json_file_path = settings.BASE_DIR.joinpath("gene2phenotype_app", "utils", "curation_schema.json")
        try:
            with open(json_file_path, 'r') as file:
                schema = json.load(file)
        except FileNotFoundError:
            return Response({"message": "Schema file not found"}, status=status.HTTP_404_NOT_FOUND)

        # json format accepts null values but in python these values are represented as 'None'
        # dumps() converts 'None' to 'null' before json validation
        input_data = json.dumps(request.data)
        input_json_data = json.loads(input_data)

        # Validate the JSON data against the schema
        try:
            validate(instance=input_json_data["json_data"], schema=schema)
        except jsonschema.exceptions.ValidationError as e:
            return Response({"message": "JSON data does not follow the required format. Required format is" + str(e)}, status=status.HTTP_400_BAD_REQUEST)

        serializer = self.serializer_class(data=request.data, context={'user': user})

        if serializer.is_valid():
            instance = serializer.save()
            return Response({"message": f"Data saved successfully for session name '{instance.session_name}'"}, status=status.HTTP_200_OK)
        else:
            return Response({"errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

class ListCurationEntries(BaseView):
    """
        List all the curation entries being curated by the user.
        It is only available for authenticated users.

        Returns:
                list of entries under 'curation'
                number of entries under 'count'
    """

    serializer_class = CurationDataSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
            Retrieve the queryset of CurationData objects.

            Returns:
                Queryset of CurationData objects.
        """
        user = self.request.user

        queryset = CurationData.objects.filter(user__email=user, user__is_active=1)

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
        Returns all data for a specific curation entry.
        It is only available for authenticated users.

        Args:
            (string) stable_id

        Returns:
                Response containing the CurationData object
                    - session_name
                    - stable_id
                    - created_on
                    - last_updated_on
                    - data (json data under curation)
    """

    serializer_class = CurationDataSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        stable_id = self.kwargs['stable_id']
        user = self.request.user

        g2p_stable_id = get_object_or_404(G2PStableID, stable_id=stable_id)
        # Get the entry if the user matches
        queryset = CurationData.objects.filter(stable_id=g2p_stable_id, user__email=user)

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
        Update the JSON data for the specific G2P ID.
        It replaces the existing json with the new data.

        Args:
            (string) stable_id
            (json) new data to save

        Returns:
                Response message
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
        user = self.request.user
 
        # Get curation entry to be updated
        curation_obj = self.get_queryset().first()

        json_file_path = settings.BASE_DIR.joinpath("gene2phenotype_app", "utils", "curation_schema.json")
        try:
            with open(json_file_path, 'r') as file:
                schema = json.load(file)
        except FileNotFoundError:
            return Response({"message": "Schema file not found"}, status=status.HTTP_404_NOT_FOUND)

        # json format accepts null values but in python these values are represented as 'None'
        # dumps() converts 'None' to 'null' before json validation
        input_data = json.dumps(request.data)
        input_json_data = json.loads(input_data)

        # Validate the JSON data against the schema
        try:
            validate(instance=input_json_data["json_data"], schema=schema)
        except jsonschema.exceptions.ValidationError as e:
            return Response({"message": "JSON data does not follow the required format. Required format is" + str(e)}, status=status.HTTP_400_BAD_REQUEST)

        # Update data - it replaces the data
        serializer = CurationDataSerializer(
            curation_obj,
            data=request.data,
            context={'user': user,'session_name': curation_obj.session_name}
        )

        if serializer.is_valid():
            instance = serializer.save()
            return Response({"message": f"Data updated successfully for session name '{instance.session_name}'"}, status=status.HTTP_200_OK)

        else:
            return Response({"message": "Failed to update data", "details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

class PublishRecord(APIView):
    """
        Publish the data.
        If data is published succesfully, it deletes entry from curation data list and
        updates the G2P ID status to live.

        Args:
            (string) stable_id

        Returns:
                Response message
    """

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
