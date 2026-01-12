import json, jsonschema
from rest_framework import generics, status, permissions
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from jsonschema import validate, exceptions
from django.conf import settings
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema

from gene2phenotype_app.serializers import CurationDataSerializer

from gene2phenotype_app.models import G2PStableID, CurationData, LocusGenotypeDisease

from .base import BaseView, BaseAdd, BaseUpdate, IsNotJuniorCurator


### Curation data
@extend_schema(exclude=True)
class AddCurationData(BaseAdd):
    serializer_class = CurationDataSerializer
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        """
        Handle POST requests.

        Returns:
            A Response object with appropriate status and message.
        """
        user = self.request.user

        json_file_path = settings.BASE_DIR.joinpath(
            "gene2phenotype_app", "utils", "curation_schema.json"
        )
        try:
            with open(json_file_path, "r") as file:
                schema = json.load(file)
        except FileNotFoundError:
            return Response(
                {"error": "Schema file not found"}, status=status.HTTP_404_NOT_FOUND
            )

        # json format accepts null values but in python these values are represented as 'None'
        # dumps() converts 'None' to 'null' before json validation
        input_data = json.dumps(request.data)
        input_json_data = json.loads(input_data)

        if "json_data" not in input_json_data:
            return Response(
                {"error": "Invalid data format: 'json_data' is missing"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate the JSON data against the schema
        try:
            validate(instance=input_json_data["json_data"], schema=schema)
        except jsonschema.exceptions.ValidationError as e:
            return Response(
                {
                    "error": "JSON data does not follow the required format. Required format is"
                    + str(e)
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = self.serializer_class(data=request.data, context={"user": user})

        # If data is invalid, return error message from the serializer
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        return Response(
            {
                "message": f"Data saved successfully for session name '{instance.session_name}'",
                "result": f"{instance.stable_id.stable_id}",
            },
            status=status.HTTP_200_OK,
        )


@extend_schema(exclude=True)
class ListCurationEntries(BaseView):
    serializer_class = CurationDataSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        Retrieve the queryset of CurationData objects for the specific user.

        Returns:
            Queryset of CurationData objects.
        """
        user = self.request.user

        queryset = CurationData.objects.filter(user__email=user, user__is_active=1)

        return queryset

    def list(self, request, *args, **kwargs):
        """
        List the CurationData objects.

        Returns:
            Response containing the list of CurationData objects with specified fields.
        """
        queryset = self.get_queryset()
        list_data = []
        for data in queryset:
            entry = {
                "locus": data.json_data["locus"],
                "session_name": data.session_name,
                "stable_id": data.stable_id.stable_id,
                "created_on": data.date_created.strftime("%Y-%m-%d %H:%M"),
                "last_update": data.date_last_update.strftime("%Y-%m-%d %H:%M"),
            }

            list_data.append(entry)

        return Response({"results": list_data, "count": len(list_data)})


@extend_schema(exclude=True)
class CurationDataDetail(BaseView):
    serializer_class = CurationDataSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        stable_id = self.kwargs["stable_id"]
        user = self.request.user

        g2p_stable_id = get_object_or_404(G2PStableID, stable_id=stable_id)
        # Get the entry if the user matches
        queryset = CurationData.objects.filter(
            stable_id=g2p_stable_id, user__email=user
        )

        if not queryset.exists():
            self.handle_no_permission("Entry", stable_id)
        else:
            return queryset

    def list(self, request, *args, **kwargs):
        """
        Returns a specific curation entry.

        Args:
            stable_id (string)

        Returns:
                Response containing the CurationData object
                    - session_name
                    - stable_id
                    - created_on
                    - last_updated_on
                    - data (json data under curation)
        """
        curation_data_obj = self.get_queryset().first()

        response_data = {
            "session_name": curation_data_obj.session_name,
            "stable_id": curation_data_obj.stable_id.stable_id,
            "created_on": curation_data_obj.date_created,
            "last_updated_on": curation_data_obj.date_last_update,
            "data": curation_data_obj.json_data,
        }
        return Response(response_data)


@extend_schema(exclude=True)
class UpdateCurationData(BaseUpdate):
    http_method_names = ["put", "options"]
    serializer_class = CurationDataSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        stable_id = self.kwargs["stable_id"]
        user = self.request.user

        g2p_stable_id = get_object_or_404(G2PStableID, stable_id=stable_id)
        # Get the entry for this user
        queryset = CurationData.objects.filter(
            stable_id=g2p_stable_id, user__email=user
        )

        if not queryset.exists():
            self.handle_no_permission("Entry", stable_id)
        else:
            return queryset

    def update(self, request, *args, **kwargs):
        """
        Update the JSON data for the specific G2P ID.
        It replaces the existing json with the new data.

        Args:
            stable_id (string)
        """
        user = self.request.user

        # Get curation entry to be updated
        curation_obj = self.get_queryset().first()

        json_file_path = settings.BASE_DIR.joinpath(
            "gene2phenotype_app", "utils", "curation_schema.json"
        )
        try:
            with open(json_file_path, "r") as file:
                schema = json.load(file)
        except FileNotFoundError:
            return Response(
                {"error": "Schema file not found"}, status=status.HTTP_404_NOT_FOUND
            )

        # json format accepts null values but in python these values are represented as 'None'
        # dumps() converts 'None' to 'null' before json validation
        input_data = json.dumps(request.data)
        input_json_data = json.loads(input_data)

        if "json_data" not in input_json_data:
            return Response(
                {"error": "Invalid data format: 'json_data' is missing"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate the JSON data against the schema
        try:
            validate(instance=input_json_data["json_data"], schema=schema)
        except jsonschema.exceptions.ValidationError as e:
            return Response(
                {
                    "error": "JSON data does not follow the required format. Required format is"
                    + str(e)
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Update data - it replaces the data
        serializer = CurationDataSerializer(
            curation_obj,
            data=request.data,
            context={"user": user, "session_name": curation_obj.session_name},
        )

        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        return Response(
            {
                "message": f"Data updated successfully for session name '{instance.session_name}'"
            },
            status=status.HTTP_200_OK,
        )


@extend_schema(exclude=True)
class PublishRecord(APIView):
    http_method_names = ["post", "head"]
    serializer_class = CurationDataSerializer
    permission_classes = [permissions.IsAuthenticated, IsNotJuniorCurator]

    def post(self, request, stable_id):
        """
        Publish the curation record.
        If data is published succesfully, it deletes entry from curation list and
        updates the G2P ID status to live.

        Args:
            stable_id (string)

        Returns:
                Response message
        """
        user = self.request.user

        try:
            # Get curation record
            curation_obj = CurationData.objects.get(
                stable_id__stable_id=stable_id, user__email=user
            )

            # Check if there is enough data to publish the record
            locus_obj = self.serializer_class().validate_to_publish(curation_obj)

            # Publish record
            try:
                lgd_obj, check = self.serializer_class(context={"user": user}).publish(
                    curation_obj
                )
                # Delete entry from 'curation_data'
                curation_obj.delete()

                if check:
                    return Response(
                        {
                            "message": f"Record '{lgd_obj.stable_id.stable_id}' published successfully. Info: there is a monoallelic record with the same locus, disease and mechanism"
                        },
                        status=status.HTTP_201_CREATED,
                    )

                return Response(
                    {
                        "message": f"Record '{lgd_obj.stable_id.stable_id}' published successfully"
                    },
                    status=status.HTTP_201_CREATED,
                )

            except LocusGenotypeDisease.DoesNotExist:
                Response(
                    {"error": f"Failed to publish record ID '{stable_id}'"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        except CurationData.DoesNotExist:
            return Response(
                {"error": f"Curation data not found for ID '{stable_id}'"},
                status=status.HTTP_404_NOT_FOUND,
            )


@extend_schema(exclude=True)
class DeleteCurationData(generics.DestroyAPIView):
    http_method_names = ["delete", "head"]
    serializer_class = CurationDataSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        stable_id = self.kwargs["stable_id"]
        user = self.request.user

        g2p_stable_id = get_object_or_404(G2PStableID, stable_id=stable_id)
        # Get the entry for this user
        queryset = CurationData.objects.filter(
            stable_id=g2p_stable_id, user__email=user
        )

        if not queryset.exists():
            return None
        else:
            return queryset

    def perform_destroy(self, instance, stable_id):
        """
        Overwrite method perform_destroy()
        This method deletes the G2P ID (set 'is_deleted' to 1) and calls the delete() method
        to remove the record from the curation table.
        """
        # Delete the G2P ID linked to this instance
        # to delete we set the flag 'is_deleted' to 1
        g2p_obj = instance.first().stable_id
        g2p_obj.is_deleted = 1
        g2p_obj.save()

        # Delete data
        instance.delete()

    def destroy(self, request, *args, **kwargs):
        """
        Deletes a curation record.
        Removes entry from curation table, it also deletes the G2P ID (set 'is_deleted' to 1).

        Args:
            stable_id (string): G2P ID associated with entry to be deleted

        Returns:
            Response message
        """
        # Get curation entry to be deleted
        curation_obj = self.get_queryset()
        stable_id = self.kwargs["stable_id"]

        if not curation_obj or len(curation_obj) == 0:
            return Response(
                {"error": f"Cannot find ID {stable_id}"},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            # delete record + G2P ID
            self.perform_destroy(curation_obj, stable_id)
        except Exception as e:
            return Response(
                {"error": f"Cannot delete data for ID {stable_id}: {str(e)}"},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(
            {"message": f"Data deleted successfully for ID {stable_id}"},
            status=status.HTTP_200_OK,
        )
