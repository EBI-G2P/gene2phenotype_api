from rest_framework import permissions, status, serializers
from rest_framework.response import Response
from rest_framework.decorators import api_view
from django.db import transaction
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema


from gene2phenotype_app.serializers import (
    PublicationSerializer,
    LGDPublicationSerializer,
    LGDPublicationListSerializer,
    LGDPhenotypeSerializer,
    LGDVariantTypeSerializer,
    LGDVariantTypeDescriptionSerializer,
    LocusGenotypeDiseaseSerializer,
    LGDPhenotypeSummarySerializer,
    UserSerializer,
    LGDMinedPublicationSerializer,
)

from gene2phenotype_app.models import (
    Publication,
    LocusGenotypeDisease,
    LGDPublication,
    LGDPhenotype,
    LGDPhenotypeSummary,
    LGDVariantType,
    LGDVariantTypeDescription,
    LGDVariantTypeComment,
    LGDMolecularMechanismEvidence,
    User,
)

from .base import BaseAdd, BaseUpdate, IsSuperUser

from ..utils import get_publication, get_authors, clean_title, get_date_now


@extend_schema(exclude=True)
@api_view(["GET"])
def PublicationDetail(request, pmids):
    """
    Return the publication data for a list of PMIDs.
    If PMID is found in G2P then return details from G2P.
    If PMID not found in G2P then returns data from EuropePMC.

    Args:
        pmids (str): A comma-separated string of PMIDs

    Returns a dictionary with the following format:
        results (list): a list of the publication data for each PMID
        count (int): number of PMIDs in the response

    Raises: Invalid PMID
    """
    id_list = pmids.split(",")
    data = []
    invalid_pmids = []

    for pmid_str in id_list:
        try:
            pmid = int(pmid_str)

        except:
            invalid_pmids.append(pmid_str)

        else:
            # The PMID has the correct format
            try:
                publication = Publication.objects.get(pmid=pmid)
                data.append(
                    {
                        "pmid": int(publication.pmid),
                        "title": publication.title,
                        "authors": publication.authors,
                        "year": int(publication.year),
                        "source": "G2P",
                    }
                )
            except Publication.DoesNotExist:
                # Query EuropePMC
                response = get_publication(pmid)
                if response["hitCount"] == 0:
                    invalid_pmids.append(pmid_str)
                else:
                    authors = get_authors(response)
                    year = None
                    publication_info = response["result"]
                    title = clean_title(publication_info["title"])
                    if "pubYear" in publication_info:
                        year = publication_info["pubYear"]

                    data.append(
                        {
                            "pmid": int(pmid),
                            "title": title,
                            "authors": authors,
                            "year": int(year),
                            "source": "EuropePMC",
                        }
                    )

    # if any of the PMIDs is invalid raise error and display all invalid IDs
    if invalid_pmids:
        pmid_list = ", ".join(invalid_pmids)
        response = Response(
            {"error": f"Invalid PMID(s): {pmid_list}"}, status=status.HTTP_404_NOT_FOUND
        )

    else:
        response = Response({"results": data, "count": len(data)})

    return response


### Add publication ###
@extend_schema(exclude=True)
class AddPublication(BaseAdd):
    """
    Add new publication.
    The create method is in the PublicationSerializer.
    """

    serializer_class = PublicationSerializer
    permission_classes = [permissions.IsAuthenticated]


### LGD-publication ###
# Add or delete data
@extend_schema(exclude=True)
class LGDEditPublications(BaseUpdate):
    http_method_names = ["post", "patch", "options"]

    def get_permissions(self):
        """
        Instantiates and returns the list of permissions for this view.
        post(): updates data - available to all authenticated users
        patch(): deletes data - only available to authenticated super users
        """
        if self.request.method.lower() == "patch":
            return [permissions.IsAuthenticated(), IsSuperUser()]
        return [permissions.IsAuthenticated()]

    def get_serializer_class(self, action):
        """
        Returns the appropriate serializer class based on the action.
        To add data use LGDPublicationListSerializer: it accepts a list of publications.
        To delete data use LGDPublicationSerializer: it accepts one publication.
        """
        action = action.lower()

        if action == "post":
            return LGDPublicationListSerializer
        elif action == "patch":
            return LGDPublicationSerializer
        else:
            return None

    @transaction.atomic
    def post(self, request, stable_id):
        """
        The post method adds a list of publications to an existing G2P record (LGD).
        It also allows to add or updated data linked to the publication:
            - comment
            - family info as reported in the publication

        When a publication is linked to a LGD record, other types of data can be associated to the record
        and the publication:
            - phenotypes
            - variant types
            - variant descriptions
            - molecular mechanism value (if 'undetermined') + support
            - molecular mechanism synopsis/categorisation
            - molecular mechanism evidence

        Args:
                request data (dict)

            Example for a record already linked to pmid '41':
            { "publications":[
                    {
                        "publication": { "pmid": "1234" },
                        "comment": { "comment": "this is a comment", "is_public": 1 },
                        "families": { "families": 2, "consanguinity": "unknown", "ancestries": "african", "affected_individuals": 1 },
                    }],
            "phenotypes": [{
                                "pmid": "41",
                                "summary": "",
                                "hpo_terms": [{ "term": "Orofacial dyskinesia",
                                                "accession": "HP:0002310",
                                                "description": "" }]
                        }],
            "variant_types": [{
                        "comment": "",
                        "de_novo": false,
                        "inherited": false,
                        "nmd_escape": false,
                        "primary_type": "protein_changing",
                        "secondary_type": "inframe_insertion",
                        "supporting_papers": ["41"],
                        "unknown_inheritance": true
                    }],
            "variant_descriptions": [{
                        "description": "HGVS:c.9Pro",
                        "publication": "41"
                    }],
            "molecular_mechanism": {
                "name": "gain of function",
                "support": "evidence"
            },
            "mechanism_synopsis": [{
                "name": "",
                "support": ""
            }],
            "mechanism_evidence": [{
                        "pmid": "1234",
                        "description": "This is new evidence for the existing mechanism evidence.",
                        "evidence_types": [ { "primary_type": "Function",
                                                "secondary_type": [ "Biochemical" ]}
                        ]}]
        }
        """
        user = self.request.user

        lgd = get_object_or_404(
            LocusGenotypeDisease, stable_id__stable_id=stable_id, is_deleted=0
        )

        # LGDPublicationListSerializer accepts a list of publications
        serializer_list = LGDPublicationListSerializer(
            data=request.data, context={"lgd": lgd, "user": user}
        )

        if serializer_list.is_valid():
            publications_data = serializer_list.validated_data.get(
                "publications"
            )  # the pmids are mandatory
            phenotypes_data = serializer_list.validated_data.get(
                "phenotypes", []
            )  # optional
            variant_types_data = serializer_list.validated_data.get(
                "variant_types", []
            )  # optional
            variant_descriptions_data = serializer_list.validated_data.get(
                "variant_descriptions", []
            )  # optional
            mechanism_data = serializer_list.validated_data.get(
                "molecular_mechanism", None
            )  # optional
            mechanism_synopsis_data = serializer_list.validated_data.get(
                "mechanism_synopsis", []
            )  # optional
            mechanism_evidence_data = serializer_list.validated_data.get(
                "mechanism_evidence", None
            )  # optional

            for publication in publications_data:
                serializer_class = LGDPublicationSerializer(
                    data=publication, context={"lgd": lgd, "user": user}
                )

                # Insert new publication
                if serializer_class.is_valid():
                    serializer_class.save()
                else:
                    response = Response(
                        {"error": serializer_class.errors},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

            # Add extra data linked to the publication - phenotypes
            # Expected structure:
            #   { "phenotypes": [{ "accession": "HP:0003974", "publication": 1 }] }
            for phenotype in phenotypes_data:
                hpo_terms = phenotype["hpo_terms"]
                for hpo in hpo_terms:
                    phenotype_data = {
                        "accession": hpo["accession"],
                        "publication": phenotype["pmid"],
                    }
                    try:
                        lgd_phenotype_serializer = LGDPhenotypeSerializer(
                            data=phenotype_data, context={"lgd": lgd}
                        )
                        # Validate the input data
                        if lgd_phenotype_serializer.is_valid():
                            # save() is going to call create()
                            lgd_phenotype_serializer.save()
                        else:
                            response = Response(
                                {"error": lgd_phenotype_serializer.errors},
                                status=status.HTTP_400_BAD_REQUEST,
                            )
                    except Exception as e:
                        accession = phenotype_data["accession"]
                        return Response(
                            {
                                "error": f"Could not insert phenotype '{accession}' for ID '{stable_id}'"
                            },
                            status=status.HTTP_400_BAD_REQUEST,
                        )

                # Insert the phenotype summary
                if "summary" in phenotype and phenotype["summary"] != "":
                    try:
                        lgd_phenotype_summary_serializer = (
                            LGDPhenotypeSummarySerializer(
                                data={
                                    "summary": phenotype["summary"],
                                    "publication": [
                                        phenotype["pmid"]
                                    ],  # The serializer accepts a list
                                },
                                context={"lgd": lgd},
                            )
                        )
                        # Validate the input data
                        if lgd_phenotype_summary_serializer.is_valid(
                            raise_exception=True
                        ):
                            # save() is going to call create()
                            lgd_phenotype_summary_serializer.save()
                    except Exception as e:
                        return Response(
                            {
                                "error": f"Could not insert phenotype summary for PMID '{phenotype['pmid']}'"
                            },
                            status=status.HTTP_400_BAD_REQUEST,
                        )

            # Add extra data linked to the publication - variant types
            for variant_type in variant_types_data:
                LGDVariantTypeSerializer(context={"lgd": lgd, "user": user}).create(
                    variant_type
                )

            # Add extra data linked to the publication - variant descriptions (HGVS)
            for variant_type_desc in variant_descriptions_data:
                LGDVariantTypeDescriptionSerializer(context={"lgd": lgd}).create(
                    variant_type_desc
                )

            # Only mechanism "undetermined" can be updated - the check is done in the LocusGenotypeDiseaseSerializer
            # If mechanism has to be updated, call method update_mechanism() and send new mechanism value
            # plus the synopsis and the new evidence (if applicable)
            if mechanism_data or mechanism_synopsis_data:
                lgd_serializer = LocusGenotypeDiseaseSerializer()

                # Build mechanism data
                mechanism_data_input = {}

                # Check if mechanism value can be updated
                if (
                    mechanism_data
                    and lgd.mechanism.value != "undetermined"
                    and "name" in mechanism_data
                    and mechanism_data["name"] != ""
                ):
                    return self.handle_no_update("molecular mechanism", stable_id)

                # If the mechanism support = "evidence" then evidence data has to
                # be provided
                elif (
                    mechanism_data
                    and "support" in mechanism_data
                    and mechanism_data["support"] == "evidence"
                    and not mechanism_evidence_data
                ):
                    return self.handle_missing_data("Mechanism evidence")

                # Attach the mechanism to be updated
                elif mechanism_data:
                    mechanism_data_input["molecular_mechanism"] = mechanism_data

                # Attach the synopsis to be updated (if applicable)
                if mechanism_synopsis_data:
                    mechanism_data_input["mechanism_synopsis"] = mechanism_synopsis_data
                # Attach the evidence to be updated (if applicable)
                if mechanism_evidence_data:
                    mechanism_data_input["mechanism_evidence"] = mechanism_evidence_data

                try:
                    # update_mechanism() updates the 'date_review' of the LGD record
                    lgd_serializer.update_mechanism(lgd, mechanism_data_input)
                except serializers.ValidationError as e:
                    error_message = e.detail["error"]
                    return self.handle_update_exception(e, error_message)
                except Exception as e:
                    return self.handle_update_exception(
                        e, "Error while updating molecular mechanism"
                    )

            # If only the mechanism evidence is going to be updated, call method update_mechanism_evidence()
            # update_mechanism_evidence() updates the 'date_review' of the LGD record
            elif mechanism_evidence_data:
                lgd_serializer = LocusGenotypeDiseaseSerializer()
                try:
                    lgd_serializer.update_mechanism_evidence(
                        lgd, mechanism_evidence_data
                    )
                except serializers.ValidationError as e:
                    error_message = e.detail["error"]
                    return self.handle_update_exception(e, error_message)
                except Exception as e:
                    return self.handle_update_exception(
                        e, "Error while updating molecular mechanism evidence"
                    )

            # Update the status of linked mined publications to "curated"
            lgd_mined_publication_serializer = LGDMinedPublicationSerializer()
            try:
                lgd_mined_publication_serializer.update_status_to_curated(
                    lgd, publications_data
                )
            except Exception as e:
                return self.handle_update_exception(
                    e, "Error while updating mined publications"
                )

            # Update the date of the last update in the record table
            lgd.date_review = get_date_now()
            lgd.save_without_historical_record()

            response = Response(
                {"message": "Publication added to the G2P entry successfully."},
                status=status.HTTP_201_CREATED,
            )

        else:
            response = Response(
                {"error": serializer_list.errors}, status=status.HTTP_400_BAD_REQUEST
            )

        return response

    @transaction.atomic
    def patch(self, request, stable_id):
        """
        This method deletes the LGD-publication.
        The deletion does not remove the entry from the database, instead
        it sets the flag 'is_deleted' to 1.

        Args:
            { "pmid": 1234 }
        """
        pmid = request.data.get("pmid", None)
        user = request.user

        if not pmid or pmid == "" or not isinstance(pmid, int):
            return Response(
                {"error": "Please provide valid pmid."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        lgd_obj = get_object_or_404(
            LocusGenotypeDisease, stable_id__stable_id=stable_id, is_deleted=0
        )

        # Check if user has permission to update record
        user_obj = get_object_or_404(User, email=user, is_active=1)
        serializer_user = UserSerializer(user_obj, context={"user": user})
        user_panel_list = [panel for panel in serializer_user.panels_names(user_obj)]
        has_common = LocusGenotypeDiseaseSerializer(
            lgd_obj, context={"user": user}
        ).check_user_permission(lgd_obj, user_panel_list)
        if has_common is False:
            return Response(
                {"error": f"No permission to update record '{stable_id}'"},
                status=status.HTTP_403_FORBIDDEN,
            )

        publication_obj = get_object_or_404(Publication, pmid=pmid)

        try:
            lgd_publication_obj = LGDPublication.objects.get(
                lgd=lgd_obj, publication=publication_obj, is_deleted=0
            )
        except LGDPublication.DoesNotExist:
            return Response(
                {"error": f"Could not find publication '{pmid}' for ID '{stable_id}'"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Before deleting this publication check if LGD record is linked to other publications
        queryset_all = LGDPublication.objects.filter(lgd=lgd_obj, is_deleted=0)

        # TODO: if we are going to delete the last publication then delete LGD record
        if queryset_all.exists() and len(queryset_all) == 1:
            return Response(
                {"error": f"Could not delete PMID '{pmid}' for ID '{stable_id}'"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Remove the publication from the LGD
        lgd_publication_obj.is_deleted = 1

        try:
            lgd_publication_obj.save()
        except Exception as e:
            return Response(
                {"error": f"Could not delete PMID '{pmid}' for ID '{stable_id}': {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Delete publication from other tables
        # lgd_phenotype - different phenotypes can be linked to the same publication
        for phenotype in LGDPhenotype.objects.filter(
            lgd=lgd_obj, publication=lgd_publication_obj.publication, is_deleted=0
        ):
            phenotype.is_deleted = 1
            phenotype.save()

        # lgd_phenotype_summary - the phenotype summary is directly associated with the LGD record
        # A LGD record should only have one phenotype summary but to make sure we delete everything correctly
        # we'll run the filter to catch all objects
        for phenotype_summary in LGDPhenotypeSummary.objects.filter(
            lgd=lgd_obj, publication=lgd_publication_obj.publication, is_deleted=0
        ):
            phenotype_summary.is_deleted = 1
            phenotype_summary.save()

        # lgd_variant_type - different variant types can be linked to the same publication
        for lgd_variant_type in LGDVariantType.objects.filter(
            lgd=lgd_obj, publication=lgd_publication_obj.publication, is_deleted=0
        ):
            # Each variant type can be linked to a LGDVariantTypeComment
            # Delete these objects too
            for lgd_var_comment in LGDVariantTypeComment.objects.filter(
                lgd_variant_type=lgd_variant_type, is_deleted=0
            ):
                lgd_var_comment.is_deleted = 1
                lgd_var_comment.save()
            lgd_variant_type.is_deleted = 1
            lgd_variant_type.save()

        # lgd_variant_type_description - different descriptions can be linked to the same publication
        for lgd_variant_description in LGDVariantTypeDescription.objects.filter(
            lgd=lgd_obj, publication=lgd_publication_obj.publication, is_deleted=0
        ):
            lgd_variant_description.is_deleted = 1
            lgd_variant_description.save()

        # Delete the mechanism evidence associated with publication that is going to be deleted
        for lgd_mechanism_evidence in LGDMolecularMechanismEvidence.objects.filter(
            lgd=lgd_obj, publication=lgd_publication_obj.publication, is_deleted=0
        ):
            lgd_mechanism_evidence.is_deleted = 1
            lgd_mechanism_evidence.save()

        # Update the date of the last update of the record
        lgd_obj.date_review = get_date_now()
        lgd_obj.save_without_historical_record()

        return Response(
            {
                "message": f"Publication '{pmid}' successfully deleted for ID '{stable_id}'"
            },
            status=status.HTTP_200_OK,
        )
