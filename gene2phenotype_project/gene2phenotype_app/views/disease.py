from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.decorators import api_view
from django.db.models import Q
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.http import Http404
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiExample
import textwrap


from gene2phenotype_app.serializers import (
    GeneDiseaseSerializer,
    DiseaseDetailSerializer,
    CreateDiseaseSerializer,
    DiseaseOntologyTermSerializer,
    DiseaseOntologyTermListSerializer,
)

from gene2phenotype_app.models import (
    AttribType,
    Locus,
    OntologyTerm,
    DiseaseOntologyTerm,
    Disease,
    LocusAttrib,
    GeneDisease,
    LocusGenotypeDisease,
    DiseaseExternal,
)

from ..utils import clean_omim_disease
from .base import BaseAPIView, BaseAdd, IsSuperUser


@extend_schema(exclude=True)
class GeneDiseaseView(BaseAPIView):
    serializer_class = GeneDiseaseSerializer

    def get_queryset(self):
        name = self.kwargs["name"]
        gene_obj = Locus.objects.filter(name=name)
        queryset = GeneDisease.objects.filter(gene=gene_obj.first())

        if not queryset.exists():
            # Try to find gene in locus_attrib (gene synonyms)
            attrib_type = AttribType.objects.filter(code="gene_synonym")
            queryset = LocusAttrib.objects.filter(
                value=name, attrib_type=attrib_type.first().id, is_deleted=0
            )

            if not queryset.exists():
                self.handle_no_permission("Gene", name)

            gene_obj = Locus.objects.filter(id=queryset.first().locus.id)
            queryset = GeneDisease.objects.filter(gene=gene_obj.first())

            if not queryset.exists():
                self.handle_no_permission("Gene-Disease association", name)

        return queryset

    def get(self, request, name, *args, **kwargs):
        """
        Return gene-disease associations imported from Mondo and OMIM.

        Args:
            name (str): gene symbol or the synonym symbol

        Returns a list of objects where each object has
            results (list):
                    original_disease_name (str)
                    disease_name (str)
                    identifier (str)
                    source name (str)
            count (int): number of diseases associated with the gene
        """
        queryset = self.get_queryset()
        results = []
        for gene_disease_obj in queryset:
            # Return the original disease name and the clean version (without subtype)
            # In the future, we will import diseases from other sources (Mondo, GenCC)
            new_disease_name = clean_omim_disease(gene_disease_obj.disease)
            results.append(
                {
                    "original_disease_name": gene_disease_obj.disease,
                    "disease_name": new_disease_name,
                    "identifier": gene_disease_obj.identifier,
                    "source": gene_disease_obj.source.name,
                }
            )

        return Response({"results": results, "count": len(results)})


@extend_schema(exclude=True)
class DiseaseDetail(BaseAPIView):
    serializer_class = DiseaseDetailSerializer

    def get_queryset(self):
        id = self.kwargs["id"]

        # Fetch disease by MONDO ID or by OMIM ID (only digits)
        if id.startswith("MONDO") or id.isdigit():
            ontology_term = OntologyTerm.objects.filter(accession=id)

            if not ontology_term.exists():
                self.handle_no_permission("Disease", id)

            disease_ontology = DiseaseOntologyTerm.objects.filter(
                ontology_term_id=ontology_term.first().id
            )

            if not disease_ontology.exists():
                self.handle_no_permission("Disease", id)

            queryset = Disease.objects.filter(id=disease_ontology.first().disease_id)

        else:
            # Fetch disease by name or by synonym
            queryset = Disease.objects.filter(name=id) | Disease.objects.filter(
                Q(diseasesynonym__synonym=id)
            )

        if not queryset.exists():
            self.handle_no_permission("Disease", id)

        return queryset

    def get(self, request, *args, **kwargs):
        """
        Fetch the ontology terms and synonyms linked to a specific disease.
        The ontology terms are added manually by curators and the synonyms
        are old G2P disease names previously used.

        Args:
            id (str): disease name or ontology ID (example: MONDO:0006411)

        Returns a Disease object
        """
        disease_obj = self.get_queryset().first()
        serializer = DiseaseDetailSerializer(disease_obj)
        return Response(serializer.data)


@extend_schema(
    exclude=False,
    tags=["Fetch G2P summary records by disease"],
    description=textwrap.dedent("""
        Return a summary of the G2P records associated with the disease.
        
        The disease input can be a disease name or ontology ID (e.g. Mondo or OMIM).
        """),
    examples=[
        OpenApiExample(
            "MONDO:0008913",
            description="Fetch records linked to disease 'MONDO:0008913'",
            value={
                "disease": "MONDO:0008913",
                "records_summary": [
                    {
                        "locus": "PLD1",
                        "genotype": "biallelic_autosomal",
                        "confidence": "definitive",
                        "panels": ["DD"],
                        "variant_consequence": ["absent gene product"],
                        "variant_type": [
                            "splice_donor_variant",
                            "frameshift_variant",
                            "stop_gained",
                            "missense_variant",
                        ],
                        "molecular_mechanism": "loss of function",
                        "stable_id": "G2P03704",
                    }
                ],
            },
        )
    ],
    responses={
        200: OpenApiResponse(
            description="Disease summary response",
            response={
                "type": "object",
                "properties": {
                    "disease": {"type": "string"},
                    "records_summary": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "locus": {"type": "string"},
                                "genotype": {"type": "string"},
                                "confidence": {"type": "string"},
                                "panels": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                },
                                "variant_consequence": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                },
                                "variant_type": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                },
                                "molecular_mechanism": {"type": "string"},
                                "stable_id": {"type": "string"},
                            },
                        },
                    },
                },
            },
        )
    },
)
class DiseaseSummary(DiseaseDetail):
    def get(self, request, *args, **kwargs):
        """
        Fetch a summary of the G2P entries associated with the disease.

        Args:
            id (str): disease name or ontology ID (example: 251450)

        Returns a dictionary with the following format:
            disease (string): input disease
            records_summary (list): G2P records linked to the disease
        """
        disease = kwargs.get("id")
        disease_obj = self.get_queryset().first()
        serializer = DiseaseDetailSerializer(disease_obj)
        summmary = serializer.records_summary(disease_obj.id, self.request.user)
        response_data = {
            "disease": disease,
            "records_summary": summmary,
        }

        return Response(response_data)


@extend_schema(exclude=True)
@api_view(["GET"])
def ExternalDisease(request, ext_ids):
    """
    Returns the disease information for a list of external disease IDs.
    External sources can be OMIM or Mondo.

    Args:
        ext_ids (str): the list if disease IDs of the external source (OMIM/Mondo)

    Returns a dictionary with the following format:
        results (list): contains the disease name, identifier ID and the source name
        count (int): number of diseases in the response
    """
    disease_id_list = ext_ids.split(",")
    data = []
    invalid_ids = []

    for disease_id in disease_id_list:
        if disease_id.startswith("MONDO") or disease_id.isdigit():
            gene_disease = GeneDisease.objects.filter(identifier=disease_id)
            if gene_disease.exists():
                data.append(
                    {
                        "disease": gene_disease.first().disease,
                        "identifier": gene_disease.first().identifier,
                        "source": gene_disease.first().source.name,
                    }
                )
            else:
                external_disease = DiseaseExternal.objects.filter(identifier=disease_id)
                if external_disease.exists():
                    data.append(
                        {
                            "disease": external_disease.first().disease,
                            "identifier": external_disease.first().identifier,
                            "source": external_disease.first().source.name,
                        }
                    )
                else:
                    invalid_ids.append(disease_id)

        else:
            invalid_ids.append(disease_id)

    if invalid_ids:
        disease_list = ", ".join(invalid_ids)
        response = Response(
            {"error": f"Invalid ID(s): {disease_list}"},
            status=status.HTTP_404_NOT_FOUND,
        )

    else:
        response = Response({"results": data, "count": len(data)})

    return response


### Add data
@extend_schema(exclude=True)
class AddDisease(BaseAdd):
    """
    Add new disease.
    This view is called by the endpoint that directly adds a disease (add/disease/).
    The create method is in the CreateDiseaseSerializer.
    """
    serializer_class = CreateDiseaseSerializer
    permission_classes = [IsSuperUser]

    def create(self, request, *args, **kwargs):
        """
        Overwrite the method create() to format the response
        to include the disease id, otherwise only what's defined
        in the serializer is returned.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        disease_obj = serializer.save()
        return Response(
            {
                "id": disease_obj.id,
                "name": disease_obj.name,
            },
            status=status.HTTP_201_CREATED,
        )


### Update data
@extend_schema(exclude=True)
class UpdateDisease(BaseAdd):
    http_method_names = ["post", "options"]
    permission_classes = [IsSuperUser]

    def post(self, request):
        diseases = request.data  # list of diseases {'id': ..., 'name': ...}

        if not isinstance(diseases, list):
            return Response(
                {"error": "Request should be a list"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        updated_diseases = []
        errors = []

        for disease_data in diseases:
            disease_id = disease_data.get("id")
            new_name = disease_data.get("name")

            if not disease_id or not new_name:
                errors.append({"error": "Both 'id' and 'name' are required."})
                continue

            # Fetch disease or return 404 if not found
            disease = get_object_or_404(Disease, id=disease_id)

            # Ensure the new name is unique
            check_disease = Disease.objects.filter(name=new_name).exclude(id=disease_id)
            if check_disease:
                # If new disease name already exists then flag error
                errors.append(
                    {
                        "id": disease_id,
                        "name": new_name,
                        "existing_id": check_disease[0].id,
                        "error": f"A disease with the name '{new_name}' already exists.",
                    }
                )
            else:
                # Else update disease name and save
                disease.name = new_name
                disease.save()
                updated_diseases.append({"id": disease_id, "name": new_name})

        response_data = {}
        if updated_diseases:
            response_data["updated"] = updated_diseases

        if errors:
            response_data["error"] = errors

        return Response(
            response_data,
            status=status.HTTP_200_OK
            if updated_diseases
            else status.HTTP_400_BAD_REQUEST,
        )


@extend_schema(exclude=True)
class DiseaseUpdateReferences(BaseAdd):
    http_method_names = ["post", "delete", "options"]

    def get_serializer_class(self, action):
        """
        Returns the appropriate serializer class based on the action.
        To add data use DiseaseOntologyTermListSerializer: it accepts a list of disease IDs.
        To delete data use DiseaseOntologyTermSerializer: it accepts one disease ID.
        """
        action = action.lower()

        if action == "post":
            return DiseaseOntologyTermListSerializer
        elif action == "delete":
            return DiseaseOntologyTermSerializer
        else:
            return None

    def get_permissions(self):
        """
        Instantiates and returns the list of permissions for this view.
        post(): adds/updates data - available to all authenticated users
        delete(): deletes data - only available to authenticated super users
        """
        if self.request.method.lower() == "delete":
            return [permissions.IsAuthenticated(), IsSuperUser()]
        return [permissions.IsAuthenticated()]

    @transaction.atomic
    def post(self, request, name):
        """
        The post method creates an association between the disease and a list of cross references (external disease IDs).
        We want to whole process to be done in one db transaction.

        Args:
            request (dict): dictionary with the following keys
                            - accession (mandatory)
                            - term (mandatory)
                            - description (optional)
                            - source (mandatory)

            Example:
            {
                "disease_ontologies": [
                    {
                        "accession": "610445",
                        "term": "NIGHT BLINDNESS, CONGENITAL STATIONARY, AUTOSOMAL DOMINANT 1",
                        "description": "NIGHT BLINDNESS, CONGENITAL STATIONARY, RHODOPSIN-RELATED",
                        "source": "OMIM"
                    },
                    {
                        "accession": "MONDO:0012490",
                        "term": "cone-rod synaptic disorder, congenital nonprogressive",
                        "description": "cone-rod synaptic disorder, congenital nonprogressive",
                        "source": "Mondo"
                    }
                ]
            }
        """
        disease_obj = get_object_or_404(Disease, name=name)

        # DiseaseOntologyTermListSerializer accepts a list of disease ontologies
        disease_ont_list = DiseaseOntologyTermListSerializer(data=request.data)

        if disease_ont_list.is_valid():
            disease_ontologies = disease_ont_list.validated_data.get(
                "disease_ontologies"
            )

            # Check if list of consequences is empty
            if not disease_ontologies:
                return Response(
                    {
                        "error": "Empty disease cross references. Please provide valid data."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Add each ontology to the disease from the input list
            for ontology in disease_ontologies:
                # The data is created in DiseaseOntologyTermSerializer
                # Input the expected data format
                if "source" in ontology["ontology_term"]:
                    ontology["ontology_term"]["source"] = ontology["ontology_term"][
                        "source"
                    ]["name"]

                serializer_class = DiseaseOntologyTermSerializer(
                    data=ontology["ontology_term"], context={"disease": disease_obj}
                )

                if serializer_class.is_valid():
                    serializer_class.save()
                    response = Response(
                        {
                            "message": "Disease cross reference added to the G2P entry successfully."
                        },
                        status=status.HTTP_201_CREATED,
                    )
                else:
                    response = Response(
                        {"error": serializer_class.errors},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

        else:
            response = Response(
                {"error": disease_ont_list.errors}, status=status.HTTP_400_BAD_REQUEST
            )

        return response

    def delete(self, request, name):
        """
        This method deletes the disease cross reference

        Input data example:
            {
                "accession": "MONDO:0008693"
            }
        """
        disease_obj = get_object_or_404(Disease, name=name)

        if "accession" not in request.data:
            return Response(
                {"error": "'accession' is missing. Please provide valid data."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        accession = request.data.get("accession")

        # Fetch phenotype from Ontology Term
        try:
            disease_ont_obj = DiseaseOntologyTerm.objects.get(
                disease=disease_obj.id, ontology_term__accession=accession
            )
        except DiseaseOntologyTerm.DoesNotExist:
            raise Http404(f"Cannot find '{accession}' for disease '{name}'")
        else:
            try:
                disease_ont_obj.delete()
            except:
                return Response(
                    {
                        "error": f"Could not delete '{accession}' deleted successfully from disease '{name}'"
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            else:
                response = Response(
                    {
                        "message": f"'{accession}' deleted successfully from disease '{name}'"
                    },
                    status=status.HTTP_200_OK,
                )

        return response


@extend_schema(exclude=True)
class LGDUpdateDisease(BaseAdd):
    http_method_names = ["post", "options"]
    permission_classes = [IsSuperUser]

    def post(self, request):
        """
        Method to update the disease ID in the main table locus_genotype_disease.

        The update can be run in two modes:
            1) It updates each record linked to the disease ID
            Input example:
                    [{disease_id: 1, new_disease_id: 2}]

            2) It updates the disease ID for the specific record
            Input example:
                    [{disease_id: 1, new_disease_id: 2, stable_id: G2P00001}]
        """
        data_to_update = request.data

        if not isinstance(data_to_update, list):
            return Response(
                {"error": "Request should be a list"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        updated_records = []
        errors = []

        for disease_to_update in data_to_update:
            current_disease_id = disease_to_update.get("disease_id")
            new_disease_id = disease_to_update.get("new_disease_id")
            stable_id_to_update = disease_to_update.get("stable_id", None)

            if not current_disease_id or not new_disease_id:
                errors.append(
                    {"error": "Both 'disease_id' and 'new_disease_id' are required."}
                )
                continue

            # Get records that use the disease id
            if not stable_id_to_update:
                lgd_list = LocusGenotypeDisease.objects.filter(
                    disease_id=current_disease_id,
                    is_deleted=0
                )
            else:
                # This list contains only one record
                lgd_list = LocusGenotypeDisease.objects.filter(
                    stable_id__stable_id=stable_id_to_update,
                    disease_id=current_disease_id,
                    is_deleted=0
                )

            if not lgd_list:
                errors.append(
                    {"error": f"No records associated with disease id {current_disease_id}"}
                )
                continue

            for lgd_obj in lgd_list:
                # Check if there is another LGD record linked to the new disease id
                try:
                    existing_lgd_obj = LocusGenotypeDisease.objects.get(
                        locus_id=lgd_obj.locus_id,
                        disease_id=new_disease_id,
                        genotype_id=lgd_obj.genotype_id,
                        mechanism_id=lgd_obj.mechanism_id,
                    )
                    errors.append(
                        {
                            "disease_id": current_disease_id,
                            "error": f"Found a different record with same locus, genotype, disease and mechanism: '{existing_lgd_obj.stable_id.stable_id}'",
                        }
                    )
                except LocusGenotypeDisease.DoesNotExist:
                    # Update record with new disease id
                    lgd_obj.disease_id = new_disease_id
                    lgd_obj.save()
                    updated_records.append(
                        {"g2p_id": lgd_obj.stable_id.stable_id, "lgd_id": lgd_obj.id}
                    )

        response_data = {}
        if updated_records:
            response_data["Updated records"] = updated_records

        if errors:
            response_data["error"] = errors

        return Response(
            response_data,
            status=status.HTTP_200_OK
            if updated_records
            else status.HTTP_400_BAD_REQUEST,
        )


@extend_schema(exclude=True)
class UpdateDiseaseOntologyTerms(BaseAdd):
    http_method_names = ["post", "delete", "options"]
    permission_classes = [IsSuperUser]

    def post(self, request):
        """
        Method to update the term and/or the description of disease ontology terms in bulk.
        Valid ontology terms are from Mondo or OMIM.
        The input data is a dictionary.
        """
        ontologies = request.data  # dictionary of ontologies to update {accession: {"term": ..., "description": ...}}

        if not isinstance(ontologies, dict):
            return Response(
                {"error": "Expected format is a dictionary"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        updated_ontologies = []
        errors = []

        for ontology_accession, ontology_data in ontologies.items():
            ontology_term = ontology_data.get("term")
            ontology_description = ontology_data.get("description")

            if not ontology_term:
                errors.append(
                    {"error": f"Missing ontology term for '{ontology_accession}'"}
                )
                continue

            # Fetch ontology term or return 404 if not found
            ontology_obj = get_object_or_404(OntologyTerm, accession=ontology_accession)
            # Update the ontology object for the new term
            ontology_obj.term = ontology_term
            # If available, also update the description
            if ontology_description:
                ontology_obj.description = ontology_description
            # Save updates
            ontology_obj.save()
            # Add the updated ontology to the list to be returned in the endpoint message
            updated_ontologies.append(
                {"accession": ontology_accession, "term": ontology_term}
            )

        response_data = {}
        if updated_ontologies:
            response_data["updated"] = updated_ontologies

        if errors:
            response_data["error"] = errors

        return Response(
            response_data,
            status=status.HTTP_200_OK
            if updated_ontologies
            else status.HTTP_400_BAD_REQUEST,
        )

    def delete(self, request):
        """
        Method to delete the disease ontology terms in bulk.
        The input data is a list of accession IDs.
        """
        ontologies = request.data  # list of ontologies to delete

        if not isinstance(ontologies, list):
            return Response(
                {"error": "Expected format is a list"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        deleted_ontologies = []
        errors = []

        for ontology_accession in ontologies:
            to_delete = 1
            # Fetch ontology term or return 404 if not found
            ontology_obj = get_object_or_404(OntologyTerm, accession=ontology_accession)

            # Check if ontology is linked to any disease
            # If so, unlink the two
            disease_ont_queryset = DiseaseOntologyTerm.objects.filter(
                ontology_term__accession=ontology_accession
            )
            if disease_ont_queryset.exists():
                for disease_ont_obj in disease_ont_queryset:
                    try:
                        # Delete the DiseaseOntologyTerm obj
                        disease_ont_obj.delete()
                    except Exception as e:
                        errors.append(
                            {
                                "error": f"Could not delete '{ontology_accession}' from disease '{disease_ont_obj.disease.name}': {str(e)}"
                            }
                        )
                    else:
                        to_delete = 0

            if to_delete:
                # Only if the DiseaseOntologyTerm obj was deleted successfully, delete the Ontology obj
                ontology_obj.delete()
                # Add the deleted accession to the list to be returned by the endpoint
                deleted_ontologies.append(ontology_accession)
            else:
                errors.append({"error": f"Could not delete '{ontology_accession}'"})

        response_data = {}
        if deleted_ontologies:
            response_data["deleted"] = deleted_ontologies

        if errors:
            response_data["error"] = errors

        return Response(
            response_data,
            status=status.HTTP_200_OK
            if deleted_ontologies
            else status.HTTP_400_BAD_REQUEST,
        )
