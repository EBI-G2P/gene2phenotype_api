from rest_framework import permissions
from rest_framework.response import Response
from django.db.models import Q

from gene2phenotype_app.serializers import (GeneDiseaseSerializer,
                                            DiseaseDetailSerializer,
                                            CreateDiseaseSerializer)

from gene2phenotype_app.models import (AttribType, Locus, OntologyTerm,
                                       DiseaseOntologyTerm, Disease,
                                       LocusAttrib, GeneDisease)

from ..utils import clean_omim_disease
from .base import BaseView, BaseAdd

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
    The create method is in the CreateDiseaseSerializer.
"""
class AddDisease(BaseAdd):
    serializer_class = CreateDiseaseSerializer
    permission_classes = [permissions.IsAuthenticated]
