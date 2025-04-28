from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.decorators import api_view
from django.db.models import Q
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.http import Http404

from gene2phenotype_app.serializers import (
    GeneDiseaseSerializer,
    DiseaseDetailSerializer,
    CreateDiseaseSerializer,
    DiseaseOntologyTermSerializer,
    DiseaseOntologyTermListSerializer
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
    DiseaseExternal
)

from ..utils import clean_omim_disease
from .base import BaseView, BaseAdd, IsSuperUser

class GeneDiseaseView(BaseView):
    """
        Retrieves all diseases associated with a specific gene.

        Args:
            (str) gene_name: gene symbol or the synonym symbol

        Returns:
            Response object includes:
                    (list) results: disease data
                                    - original_disease_name
                                    - disease_name
                                    - identifier
                                    - source name
                    (int) count: number of diseases associated with the gene
    """

    serializer_class = GeneDiseaseSerializer

    def get_queryset(self):
        name = self.kwargs['name']
        gene_obj = Locus.objects.filter(name=name)
        queryset = GeneDisease.objects.filter(gene=gene_obj.first())

        if not queryset.exists():
            # Try to find gene in locus_attrib (gene synonyms)
            attrib_type = AttribType.objects.filter(code='gene_synonym')
            queryset = LocusAttrib.objects.filter(value=name, attrib_type=attrib_type.first().id, is_deleted=0)

            if not queryset.exists():
                self.handle_no_permission('Gene', name)

            gene_obj = Locus.objects.filter(id=queryset.first().locus.id)
            queryset = GeneDisease.objects.filter(gene=gene_obj.first())

            if not queryset.exists():
                self.handle_no_permission('Gene-Disease association', name)

        return queryset

    def get(self, request, name, *args, **kwargs):
        queryset = self.get_queryset()
        results = []
        for gene_disease_obj in queryset:
            # Return the original disease name and the clean version (without subtype)
            # In the future, we will import diseases from other sources (Mondo, GenCC)
            new_disease_name = clean_omim_disease(gene_disease_obj.disease)
            results.append({
                            'original_disease_name': gene_disease_obj.disease,
                            'disease_name': new_disease_name,
                            'identifier': gene_disease_obj.identifier,
                            'source': gene_disease_obj.source.name
                           })

        return Response({'results': results, 'count': len(results)})

class DiseaseDetail(BaseView):
    """
        Display information for a specific disease.

        Args:
            (str) disease id: disease name or ontology ID (Mondo, OMIM)

        Returns:
            Disease object
    """

    serializer_class = DiseaseDetailSerializer

    def get_queryset(self):
        id = self.kwargs['id']

        # Fetch disease by MONDO ID or by OMIM ID (only digits)
        if id.startswith('MONDO') or id.isdigit():
            ontology_term = OntologyTerm.objects.filter(accession=id)

            if not ontology_term.exists():
                self.handle_no_permission('Disease', id)

            disease_ontology = DiseaseOntologyTerm.objects.filter(ontology_term_id=ontology_term.first().id)

            if not disease_ontology.exists():
                self.handle_no_permission('Disease', id)

            queryset = Disease.objects.filter(id=disease_ontology.first().disease_id)

        else:
            # Fetch disease by name or by synonym
            queryset = Disease.objects.filter(name=id) | Disease.objects.filter(Q(diseasesynonym__synonym=id))

        if not queryset.exists():
            self.handle_no_permission('Disease', id)

        return queryset

    def list(self, request, *args, **kwargs):
        disease_obj = self.get_queryset().first()
        serializer = DiseaseDetailSerializer(disease_obj)
        return Response(serializer.data)

class DiseaseSummary(DiseaseDetail):
    """
        Display a summary of the latest G2P entries associated with disease.

        Args:
            (str) disease id: disease name or ontology ID (Mondo)

        Returns:
            Response object includes:
                    (string) disease: disease data
                    (list) records_summary: summary of records linked to disease
    """

    def list(self, request, *args, **kwargs):
        disease = kwargs.get('id')
        disease_obj = self.get_queryset().first()
        serializer = DiseaseDetailSerializer(disease_obj)
        summmary = serializer.records_summary(disease_obj.id, self.request.user)
        response_data = {
            'disease': disease,
            'records_summary': summmary,
        }

        return Response(response_data)

@api_view(['GET'])
def ExternalDisease(request, ext_ids):
    """
        Returns the disease for a list of external disease IDs.
        External sources can be OMIM or Mondo.

        Args:
            (str) external disease ids: the list if disease IDs of the external source (OMIM/Mondo)

        Returns:
            Response object includes:
                (list) results: contains publication data for each publication
                                disease: the disease name as represented in the source
                                identifier: disease ID
                                source: source name
                (int) count: number of IDs

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
                        "source": gene_disease.first().source.name
                    }
                )
            else:
                external_disease = DiseaseExternal.objects.filter(identifier=disease_id)
                if external_disease.exists():
                    data.append(
                    {
                        "disease": external_disease.first().disease,
                        "identifier": external_disease.first().identifier,
                        "source": external_disease.first().source.name
                    }
                )
                else:
                    invalid_ids.append(disease_id)

        else:
            invalid_ids.append(disease_id)

    if invalid_ids:
        disease_list = ", ".join(invalid_ids)
        response = Response({"error": f"Invalid ID(s): {disease_list}"}, status=status.HTTP_404_NOT_FOUND)

    else:
        response = Response({"results": data, "count": len(data)})

    return response

### Add data
class AddDisease(BaseAdd):
    """
        Add new disease.
        This view is called by the endpoint that directly adds a disease (add/disease/).
        The create method is in the CreateDiseaseSerializer.
    """
    serializer_class = CreateDiseaseSerializer
    permission_classes = [IsSuperUser]

### Update data
class UpdateDisease(BaseAdd):
    http_method_names = ['post', 'options']
    permission_classes = [IsSuperUser]

    def post(self, request):
        diseases = request.data  # list of diseases {'id': ..., 'name': ...}

        if not isinstance(diseases, list):
            return Response(
                {"error": "Request should be a list"},
                status=status.HTTP_400_BAD_REQUEST
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
                errors.append({
                    "id": disease_id,
                    "name": new_name,
                    "existing_id": check_disease[0].id,
                    "error": f"A disease with the name '{new_name}' already exists."
                })
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

        return Response(response_data, status=status.HTTP_200_OK if updated_diseases else status.HTTP_400_BAD_REQUEST)

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
                (dict) request: dictionary with the following keys
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
            disease_ontologies = disease_ont_list.validated_data.get("disease_ontologies")

            # Check if list of consequences is empty
            if not disease_ontologies:
                return Response(
                    {"error": "Empty disease cross references. Please provide valid data."},
                     status=status.HTTP_400_BAD_REQUEST
                )

            # Add each ontology to the disease from the input list
            for ontology in disease_ontologies:
                # The data is created in DiseaseOntologyTermSerializer
                # Input the expected data format
                if "source" in ontology["ontology_term"]:
                    ontology["ontology_term"]["source"] = ontology["ontology_term"]["source"]["name"]

                serializer_class = DiseaseOntologyTermSerializer(
                    data=ontology["ontology_term"],
                    context={"disease": disease_obj}
                )

                if serializer_class.is_valid():
                    serializer_class.save()
                    response = Response(
                        {"message": "Disease cross reference added to the G2P entry successfully."},
                        status=status.HTTP_201_CREATED
                    )
                else:
                    response = Response(
                        {"error": serializer_class.errors},
                        status=status.HTTP_400_BAD_REQUEST
                    )

        else:
            response = Response(
                {"error": disease_ont_list.errors},
                status=status.HTTP_400_BAD_REQUEST
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
                    status=status.HTTP_400_BAD_REQUEST
            )

        accession = request.data.get('accession')

        # Fetch phenotype from Ontology Term
        try:
            disease_ont_obj = DiseaseOntologyTerm.objects.get(disease=disease_obj.id, ontology_term__accession=accession)
        except DiseaseOntologyTerm.DoesNotExist:
            raise Http404(f"Cannot find '{accession}' for disease '{name}'")
        else:
            try:
                disease_ont_obj.delete()
            except:
                return Response(
                    {"error": f"Could not delete '{accession}' deleted successfully from disease '{name}'"},
                        status=status.HTTP_400_BAD_REQUEST
                )
            else:
                response = Response(
                    {"message": f"'{accession}' deleted successfully from disease '{name}'"},
                    status=status.HTTP_200_OK
                )

        return response

class LGDUpdateDisease(BaseAdd):
    http_method_names = ['post', 'options']
    permission_classes = [IsSuperUser]

    def post(self, request):
        data_to_update = request.data

        if not isinstance(data_to_update, list):
            return Response(
                {"error": "Request should be a list"},
                status=status.HTTP_400_BAD_REQUEST
            )

        updated_records = []
        errors = []

        for disease_to_update in data_to_update:
            current_disease_id = disease_to_update.get("disease_id")
            new_disease_id = disease_to_update.get("new_disease_id")

            if not current_disease_id or not new_disease_id:
                errors.append({"error": "Both 'disease_id' and 'new_disease_id' are required."})
                continue

            # Get records that use the disease id
            lgd_list = LocusGenotypeDisease.objects.filter(disease_id=current_disease_id, is_deleted=0)

            for lgd_obj in lgd_list:
                # Check if there is another LGD record linked to the new disease id
                try:
                    existing_lgd_obj = LocusGenotypeDisease.objects.get(
                        locus_id = lgd_obj.locus_id,
                        disease_id = new_disease_id,
                        genotype_id = lgd_obj.genotype_id,
                        mechanism_id = lgd_obj.mechanism_id
                    )
                    errors.append({"disease_id": current_disease_id, "error": f"Found a different record with same locus, genotype, disease and mechanism: '{existing_lgd_obj.stable_id.stable_id}'"})
                except:
                    # Update record with new disease id
                    lgd_obj.disease_id = new_disease_id
                    lgd_obj.save()
                    updated_records.append({"g2p_id": lgd_obj.stable_id.stable_id, "lgd_id": lgd_obj.id})

        response_data = {}
        if updated_records:
            response_data["Updated records"] = updated_records

        if errors:
            response_data["error"] = errors

        return Response(response_data, status=status.HTTP_200_OK if updated_records else status.HTTP_400_BAD_REQUEST)
    

class UpdateOntologyTerms(BaseAdd):
    """
    Method to update the term and/or description of Ontology Terms in bulk.
    POST: updates the ontology terms
    DELETE: deletes the ontology terms
    """

    http_method_names = ["post", "delete", "options"]
    permission_classes = [IsSuperUser]

    def post(self, request):
        ontologies = request.data  # dictionary of ontologies to update {accession: {"term": ..., "description": ...}}

        if not isinstance(ontologies, dict):
            return Response(
                {"error": "Request should be a dictionary"},
                status=status.HTTP_400_BAD_REQUEST
            )

        updated_ontologies = []
        errors = []

        for ontology_accession, ontology_data in ontologies.items():
            ontology_term = ontology_data.get("term")
            ontology_description = ontology_data.get("description")

            if not ontology_term:
                errors.append({"error": f"Missing ontology term for '{ontology_accession}"})
                continue

            # Fetch ontology term or return 404 if not found
            ontology_obj = get_object_or_404(OntologyTerm, accession=ontology_accession)
            # Else update disease name and save
            ontology_obj.term = ontology_term
            if ontology_description:
                ontology_obj.description = ontology_description
            ontology_obj.save()
            updated_ontologies.append({"accession": ontology_accession, "term": ontology_term})

        response_data = {}
        if updated_ontologies:
            response_data["updated"] = updated_ontologies

        if errors:
            response_data["error"] = errors

        return Response(response_data, status=status.HTTP_200_OK if updated_ontologies else status.HTTP_400_BAD_REQUEST)

    def delete(self, request):
        ontologies = request.data  # list of ontologies to delete

        if not isinstance(ontologies, list):
            return Response(
                {"error": "Request should be a list"},
                status=status.HTTP_400_BAD_REQUEST
            )

        deleted_ontologies = []
        errors = []

        for ontology_accession in ontologies:
            to_delete = 1
            # Fetch ontology term or return 404 if not found
            ontology_obj = get_object_or_404(OntologyTerm, accession=ontology_accession)
            
            # Check if ontology is linked to any disease
            # If so, unlink the two
            disease_ont_queryset = DiseaseOntologyTerm.objects.filter(ontology_term__accession=ontology_accession)
            if disease_ont_queryset.exists():
                for disease_ont_obj in disease_ont_queryset:
                    try:
                        disease_ont_obj.delete()
                    except:
                        errors.append({"error": f"Could not delete '{ontology_accession}' from disease '{disease_ont_obj.disease.name}'"})
                    else:
                        to_delete = 0

            if to_delete:
                ontology_obj.delete()
                deleted_ontologies.append(ontology_accession)
            else:
                errors.append({"error": f"Could not delete '{ontology_accession}'"})

        response_data = {}
        if deleted_ontologies:
            response_data["deleted"] = deleted_ontologies

        if errors:
            response_data["error"] = errors

        return Response(response_data, status=status.HTTP_200_OK if deleted_ontologies else status.HTTP_400_BAD_REQUEST)