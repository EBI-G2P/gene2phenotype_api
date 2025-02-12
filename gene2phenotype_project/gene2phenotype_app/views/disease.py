from rest_framework import permissions, status
from rest_framework.response import Response
from django.db.models import Q
from django.shortcuts import get_object_or_404

from gene2phenotype_app.serializers import (GeneDiseaseSerializer,
                                            DiseaseDetailSerializer,
                                            CreateDiseaseSerializer)

from gene2phenotype_app.models import (AttribType, Locus, OntologyTerm,
                                       DiseaseOntologyTerm, Disease,
                                       LocusAttrib, GeneDisease, LocusGenotypeDisease)

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


### Add data
"""
    Add new disease.
    This view is called by the endpoint that directly adds a disease (add/disease/).
    The create method is in the CreateDiseaseSerializer.
"""
class AddDisease(BaseAdd):
    serializer_class = CreateDiseaseSerializer
    permission_classes = [IsSuperUser]

### Update data
class UpdateDisease(BaseAdd):
    http_method_names = ['post', 'options']
    permission_classes = [IsSuperUser]

    def post(self, request):
        diseases = request.data  # list of diseases {'id': ..., 'name': ...}

        if not isinstance(diseases, list):
            return Response({"error": "Request should be a list"}, status=status.HTTP_400_BAD_REQUEST)

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
                errors.append({
                    "id": disease_id,
                    "name": new_name,
                    "existing_id": check_disease[0].id,
                    "error": f"A disease with the name '{new_name}' already exists."
                })
                continue

            # Update and save
            disease.name = new_name
            disease.save()
            updated_diseases.append({"id": disease_id, "name": new_name})

        response_data = {}
        if updated_diseases:
            response_data["updated"] = updated_diseases

        if errors:
            response_data["errors"] = errors

        return Response(response_data, status=status.HTTP_200_OK if updated_diseases else status.HTTP_400_BAD_REQUEST)

class LGDUpdateDisease(BaseAdd):
    http_method_names = ['post', 'options']
    permission_classes = [IsSuperUser]

    def post(self, request):
        data_to_update = request.data

        if not isinstance(data_to_update, list):
            return Response({"error": "Request should be a list"}, status=status.HTTP_400_BAD_REQUEST)

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
            response_data["Errors"] = errors

        return Response(response_data, status=status.HTTP_200_OK if updated_records else status.HTTP_400_BAD_REQUEST)