from rest_framework import status, permissions
from rest_framework.response import Response
from django.db import IntegrityError
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema


from gene2phenotype_app.serializers import (
    UserSerializer,
    LocusGenotypeDiseaseSerializer,
    LGDMinedPublicationSerializer,
    LGDMinedPublicationListSerializer,
)

from gene2phenotype_app.models import (
    User,
    LGDMinedPublication,
    MinedPublication,
    LocusGenotypeDisease,
)

from .base import BaseUpdate


@extend_schema(exclude=True)
class LGDEditMinedPublication(BaseUpdate):
    http_method_names = ["put", "options"]
    serializer_class = LGDMinedPublicationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def update(self, request, stable_id):
        """
        This method updates the LGD mined publication.

        Mandatory fields to update mined publication:
                        - pmid
                        - status
                        - comment (Mandatory only for status 'rejected')

        Input example:
                {
                    "mined_publications": [
                        {
                            "pmid": 36718090,
                            "title": "SPTSSA variants alter sphingolipid synthesis and cause a complex hereditary spastic paraplegia.",
                            "status": "rejected",
                            "comment": "Not relevant to gene disease association"
                        },
                        {
                            "pmid": 39663403,
                            "title": "Profound hypotonia in an infant with δ-aminolevulinic acid dehydratase deficient porphyria.",
                            "status": "rejected",
                            "comment": "Not relevant to gene disease association"
                        }
                    ]
                }

        Raises:
            No permission to update mined publication
            Bad request errors
            Database integrity error
        """
        user = request.user

        # Check if G2P ID exists
        lgd = get_object_or_404(
            LocusGenotypeDisease, stable_id__stable_id=stable_id, is_deleted=0
        )

        # Check if user can edit this LGD entry
        lgd_serializer = LocusGenotypeDiseaseSerializer(lgd, context={"user": user})
        lgd_panels = lgd_serializer.get_panels(lgd)
        # Example of lgd_panels:
        # [{'name': 'DD', 'description': 'Developmental disorders'}, {'name': 'Eye', 'description': 'Eye disorders'}]
        user_obj = get_object_or_404(User, email=user, is_active=1)
        user_serializer = UserSerializer(user_obj, context={"user": user})

        if not user_serializer.check_panel_permission(lgd_panels):
            return Response(
                {"error": f"No permission to edit '{stable_id}'"},
                status=status.HTTP_403_FORBIDDEN,
            )

        # LGDMinedPublicationListSerializer accepts a list of mined publications
        serializer_list = LGDMinedPublicationListSerializer(data=request.data)

        if serializer_list.is_valid():
            lgd_mined_publications_list = serializer_list.validated_data.get(
                "mined_publications"
            )

            if not lgd_mined_publications_list:
                return Response(
                    {
                        "error": "Provided mined publications list is empty. Please provide valid data."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            errors = []
            # Update each mined publication from the input list
            for lgd_mined_publication in lgd_mined_publications_list:
                pmid = lgd_mined_publication.get("mined_publication").get("pmid")
                mined_publication_obj = None
                try:
                    mined_publication_obj = MinedPublication.objects.get(pmid=pmid)
                except MinedPublication.DoesNotExist:
                    return Response(
                        {
                            "error": f"Provided mined publication '{pmid}' does not exist. Please provide valid data."
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                lgd_mined_publication_obj = None
                try:
                    lgd_mined_publication_obj = LGDMinedPublication.objects.get(
                        lgd=lgd, mined_publication=mined_publication_obj
                    )
                except LGDMinedPublication.DoesNotExist:
                    return Response(
                        {
                            "error": f"Provided mined publication '{pmid}' is not linked to the record '{stable_id}'. Please provide valid data."
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                mined_publication_status = lgd_mined_publication.get("status")
                existing_mined_publication_status = lgd_mined_publication_obj.status
                if existing_mined_publication_status == mined_publication_status:
                    return Response(
                        {
                            "error": f"For mined publication '{pmid}', status is already '{mined_publication_status}'. Please provide valid data."
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                comment = lgd_mined_publication.get("comment")
                if mined_publication_status == "rejected" and (
                    not comment or comment == ""
                ):
                    return Response(
                        {
                            "error": f"For mined publication '{pmid}', comment can not be empty or null for status '{mined_publication_status}'. Please provide valid data."
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                serializer_class = LGDMinedPublicationSerializer(
                    instance=lgd_mined_publication_obj, data=lgd_mined_publication
                )

                if serializer_class.is_valid():
                    try:
                        serializer_class.save()
                    except IntegrityError as e:
                        return Response(
                            {"error": f"A database integrity error occurred: {str(e)}"},
                            status=status.HTTP_400_BAD_REQUEST,
                        )
                else:
                    errors.append(serializer_class.errors)

            if errors:
                return Response({"error": errors}, status=status.HTTP_400_BAD_REQUEST)

            response = Response(
                {"message": "Mined publications updated successfully."},
                status=status.HTTP_200_OK,
            )

        else:
            response = Response(
                {"error": serializer_list.errors}, status=status.HTTP_400_BAD_REQUEST
            )

        return response
