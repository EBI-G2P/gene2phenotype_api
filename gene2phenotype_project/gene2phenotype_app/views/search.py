from rest_framework.response import Response
from django.db.models import Q
from rest_framework.pagination import PageNumberPagination

from gene2phenotype_app.serializers import LocusGenotypeDiseaseSerializer

from gene2phenotype_app.models import LGDPanel, LocusGenotypeDisease

from .base import BaseView


class SearchView(BaseView):
    """
        Search G2P entries by different types:
                                            - gene
                                            - disease
                                            - phenotype
                                            - G2P ID
        If no search type is specified then it performs a generic search.
        The search can be specific to one panel if using parameter 'panel'.
    """
    serializer_class = LocusGenotypeDiseaseSerializer
    pagination_class = PageNumberPagination

    def get_queryset(self):
        user = self.request.user
        search_type = self.request.query_params.get('type', None)
        search_query = self.request.query_params.get('query', None)
        search_panel = self.request.query_params.get('panel', None)

        if not search_query:
            return LocusGenotypeDisease.objects.none()

        base_locus = Q(locus__name=search_query, is_deleted=0)
        base_locus_2 = Q(locus__locusidentifier__isnull=False, locus__locusidentifier__identifier=search_query)
        base_locus_3 = Q(locus__locusattrib__isnull=False, locus__locusattrib__value=search_query, locus__locusattrib__is_deleted=0)
        base_disease = Q(disease__name__icontains=search_query, is_deleted=0)
        base_disease_2 = Q(disease__diseasesynonym__synonym__icontains=search_query, is_deleted=0)
        base_disease_3 = Q(disease__diseaseontologyterm__ontology_term__accession=search_query, is_deleted=0)
        base_phenotype = Q(lgdphenotype__phenotype__term__icontains=search_query, lgdphenotype__isnull=False, is_deleted=0)
        base_phenotype_2 = Q(lgdphenotype__phenotype__accession=search_query, lgdphenotype__isnull=False, is_deleted=0)
        base_g2p_id = Q(stable_id__stable_id=search_query, is_deleted=0)

        queryset = LocusGenotypeDisease.objects.none()

        # Generic search
        if not search_type:
            if search_panel:
                queryset = LocusGenotypeDisease.objects.filter(
                    base_locus & Q(lgdpanel__panel__name=search_panel) |
                    base_locus_2 & Q(lgdpanel__panel__name=search_panel) |
                    base_locus_3 & Q(lgdpanel__panel__name=search_panel) |
                    base_disease & Q(lgdpanel__panel__name=search_panel) |
                    base_disease_2 & Q(lgdpanel__panel__name=search_panel) |
                    base_disease_3 & Q(lgdpanel__panel__name=search_panel) |
                    base_phenotype & Q(lgdpanel__panel__name=search_panel) |
                    base_phenotype_2 & Q(lgdpanel__panel__name=search_panel) |
                    base_g2p_id & Q(lgdpanel__panel__name=search_panel)
                ).order_by('locus__name', 'stable_id__stable_id').distinct()
            else:
                queryset = LocusGenotypeDisease.objects.filter(
                    base_locus |
                    base_locus_2 |
                    base_locus_3 |
                    base_disease |
                    base_disease_2 |
                    base_disease_3 |
                    base_phenotype |
                    base_phenotype_2 |
                    base_g2p_id
                ).order_by('locus__name', 'stable_id__stable_id').distinct()

            if not queryset.exists():
                self.handle_no_permission('results', search_query)

        elif search_type == 'gene':
            if search_panel:
                queryset = LocusGenotypeDisease.objects.filter(
                    base_locus & Q(lgdpanel__panel__name=search_panel) |
                    base_locus_2 & Q(lgdpanel__panel__name=search_panel) |
                    base_locus_3 & Q(lgdpanel__panel__name=search_panel)
                ).order_by('locus__name', 'stable_id__stable_id').distinct()
            else:
                queryset = LocusGenotypeDisease.objects.filter(
                    base_locus |
                    base_locus_2 |
                    base_locus_3
                ).order_by('locus__name', 'stable_id__stable_id').distinct()

            if not queryset.exists():
                self.handle_no_permission('Gene', search_query)

        elif search_type == 'disease':
            if search_panel:
                queryset = LocusGenotypeDisease.objects.filter(
                    base_disease & Q(lgdpanel__panel__name=search_panel) |
                    base_disease_2 & Q(lgdpanel__panel__name=search_panel) |
                    base_disease_3 & Q(lgdpanel__panel__name=search_panel)
                ).order_by('locus__name', 'stable_id__stable_id').distinct()
            else:
                queryset = LocusGenotypeDisease.objects.filter(
                    base_disease |
                    base_disease_2 |
                    base_disease_3
                ).order_by('locus__name', 'stable_id__stable_id').distinct()

            if not queryset.exists():
                self.handle_no_permission('Disease', search_query)

        elif search_type == 'phenotype':
            if search_panel:
                queryset = LocusGenotypeDisease.objects.filter(
                    base_phenotype & Q(lgdpanel__panel__name=search_panel) |
                    base_phenotype_2 & Q(lgdpanel__panel__name=search_panel)
                ).order_by('locus__name', 'stable_id__stable_id').distinct()
            else:
                queryset = LocusGenotypeDisease.objects.filter(
                    base_phenotype |
                    base_phenotype_2
                ).order_by('locus__name', 'stable_id__stable_id').distinct()

            if not queryset.exists():
                self.handle_no_permission('Phenotype', search_query)

        elif search_type == 'g2p_id':
            if search_panel:
                queryset = LocusGenotypeDisease.objects.filter(
                    base_g2p_id & Q(lgdpanel__panel__name=search_panel)
                ).order_by('locus__name', 'stable_id__stable_id').distinct()
            else:
                queryset = LocusGenotypeDisease.objects.filter(
                    base_g2p_id
                ).order_by('locus__name', 'stable_id__stable_id').distinct()

            if not queryset.exists():
                self.handle_no_permission('g2p_id', search_query)

        else:
            self.handle_no_permission('Search type is not valid', None)

        new_queryset = []
        if queryset.exists():
            for lgd in queryset:
                # If the user is not logged in, only show visible panels
                if user.is_authenticated == False:
                    lgdpanel_select = LGDPanel.objects.filter(lgd=lgd, panel__is_visible=1, is_deleted=0)
                else:
                    lgdpanel_select = LGDPanel.objects.filter(lgd=lgd, is_deleted=0)

                lgd_panels = []
                for lp in lgdpanel_select:
                    lgd_panels.append(lp.panel.name)

                # Add new property to LGD object
                lgd.panels = lgd_panels
                if lgd_panels:
                    new_queryset.append(lgd)

        return new_queryset

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        list_output = []

        for lgd in queryset:
            data = { 'id':lgd.stable_id.stable_id,
                     'gene':lgd.locus.name,
                     'genotype':lgd.genotype.value,
                     'disease':lgd.disease.name,
                     'panel':lgd.panels
                   }
            list_output.append(data)
        paginated_output = self.paginate_queryset(list_output)

        if paginated_output is not None:
            return self.get_paginated_response(paginated_output)

        return Response({"results": list_output, "count": len(list_output)})
