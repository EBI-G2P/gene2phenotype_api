from rest_framework import generics
from rest_framework.response import Response
from django.http import Http404, HttpResponse
from rest_framework.decorators import api_view
from django.db.models import Q
import csv
from datetime import datetime

from gene2phenotype_app.models import (Panel, User, LocusGenotypeDisease,
                                       LGDVariantType, LGDVariantGenccConsequence,
                                       LGDMolecularMechanism, LGDPhenotype,
                                       LGDPublication, LGDCrossCuttingModifier)

from gene2phenotype_app.serializers import PanelDetailSerializer

from .base import BaseView


class PanelList(generics.ListAPIView):
    """
        Display all panels info.
        The information includes some stats: 
            - total number of records linked to panel
            - total number of genes linked to panel
            - total number of records by confidence

        Returns:
            Response object includes:
                            (list) results: list of panels info
                            (int) count: number of panels
    """

    queryset = Panel.objects.all()
    serializer_class = PanelDetailSerializer

    def list(self, request, *args, **kwargs):
        user = self.request.user
        queryset = self.get_queryset()
        serializer = PanelDetailSerializer()
        panel_list = []

        for panel in queryset:
            panel_info = {}
            if panel.is_visible == 1 or (user.is_authenticated and panel.is_visible == 0):
                stats = serializer.calculate_stats(panel)
                panel_info['name'] = panel.name
                panel_info['description'] = panel.description
                panel_info['stats'] = stats
                panel_list.append(panel_info)

        return Response({'results':panel_list, 'count':len(panel_list)})

class PanelDetail(BaseView):
    """
        Display the panel info.

        Args:
            (str) panel: the panel short name

        Returns:
            Response object includes:
                            (string) panel name
                            (string) panel description: long name
                            (list) curators: list of curators with permission to edit the panel
                            (string) last_updated
                            (dict) stats
    """

    def get(self, request, name, *args, **kwargs):
        user = self.request.user
        queryset = Panel.objects.filter(name=name)

        flag = 0
        for panel in queryset:
            if panel.is_visible == 1 or (user.is_authenticated and panel.is_visible == 0):
                flag = 1

        if flag == 1:
            serializer = PanelDetailSerializer()
            curators = serializer.get_curators(queryset.first())
            last_update = serializer.get_last_updated(queryset.first())
            stats = serializer.calculate_stats(queryset.first())
            response_data = {
                'name': queryset.first().name,
                'description': queryset.first().description,
                'curators': curators,
                'last_updated': last_update,
                'stats': stats,
            }
            return Response(response_data)

        else:
            self.handle_no_permission('Panel', name)

class PanelRecordsSummary(BaseView):
    """
        Display a summary of the latest G2P entries associated with panel.

        Args:
            (str) panel: the panel short name

        Returns:
            Response object includes:
                            (string) panel name
                            (list) records_summary: summary of entries linked to panel
    """

    def get(self, request, name, *args, **kwargs):
        user = self.request.user
        queryset = Panel.objects.filter(name=name)

        flag = 0
        for panel in queryset:
            if panel.is_visible == 1 or (user.is_authenticated and panel.is_visible == 0):
                flag = 1

        if flag == 1:
            serializer = PanelDetailSerializer()
            summary = serializer.records_summary(queryset.first())
            response_data = {
                'panel_name': queryset.first().name,
                'records_summary': summary,
            }
            return Response(response_data)

        else:
            self.handle_no_permission('Panel', name)


@api_view(['GET'])
def PanelDownload(request, name):
    """
        Method to download the panel data.
        Authenticated users can download data for all panels.

        Args:
                (HttpRequest) request: HTTP request
                (str) name: the data of the panel to download

        Returns:
                csv file

        Raises:
                Invalid panel
    """

    user_email = request.user

    # Get user
    try:
        user_obj = User.objects.get(email=user_email)
    except User.DoesNotExist:
        user_obj = None

    # Check if panel is valid
    try:
        panel = Panel.objects.get(name=name)
    except Panel.DoesNotExist:
        raise Http404(f"No matching panel found for: {name}")

    # Get date to attach to filename
    date_now = datetime.today().strftime('%Y-%m-%d')
    filename = f"G2P_{name}_{date_now}.csv"

    response = HttpResponse(
        content_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )

    # Preload data attached to the g2p entries
    # Preload variant types
    lgd_variantype_data = {} # key = lgd_id; value = variant type term
    queryset_lgd_variantype = LGDVariantType.objects.filter(
        is_deleted=0).select_related('lgd__id','variant_type_ot__term').values('lgd__id', 'variant_type_ot__term')

    for data in queryset_lgd_variantype:
        if data['lgd__id'] not in lgd_variantype_data:
            lgd_variantype_data[data['lgd__id']] = [data['variant_type_ot__term']]
        else:
            lgd_variantype_data[data['lgd__id']].append(data['variant_type_ot__term'])

    # Preload variant GenCC consequence
    lgd_varianconsequence_data = {} # key = lgd_id; value = variant consequence term
    queryset_lgd_var_cons = LGDVariantGenccConsequence.objects.filter(
        is_deleted=0).select_related('lgd__id','variant_consequence__term').values('lgd__id', 'variant_consequence__term')
    
    for data in queryset_lgd_var_cons:
        if data['lgd__id'] not in lgd_varianconsequence_data:
            lgd_varianconsequence_data[data['lgd__id']] = [data['variant_consequence__term']]
        else:
            lgd_varianconsequence_data[data['lgd__id']].append(data['variant_consequence__term'])

    # Preload molecular mechanism
    lgd_mechanism_data = {} # key = lgd_id; value = molecular mechanism value
    queryset_lgd_mechanism = LGDMolecularMechanism.objects.filter(
        is_deleted=0).select_related('lgd__id','mechanism__value').values('lgd__id', 'mechanism__value')
    
    for data in queryset_lgd_mechanism:
        if data['lgd__id'] not in lgd_mechanism_data:
            lgd_mechanism_data[data['lgd__id']] = [data['mechanism__value']]
        else:
            lgd_mechanism_data[data['lgd__id']].append(data['mechanism__value'])

    # Preload phenotypes
    lgd_phenotype_data = {} # key = lgd_id; value = phenotype accession
    queryset_lgd_phenotype = LGDPhenotype.objects.filter(
        is_deleted=0).select_related('lgd__id','phenotype__accession').values('lgd__id', 'phenotype__accession')

    for data in queryset_lgd_phenotype:
        if data['lgd__id'] not in lgd_phenotype_data:
            lgd_phenotype_data[data['lgd__id']] = [data['phenotype__accession']]
        else:
            lgd_phenotype_data[data['lgd__id']].append(data['phenotype__accession'])

    # Preload publications
    lgd_publication_data = {} # key = lgd_id; value = pmid
    queryset_lgd_publication = LGDPublication.objects.filter(
        is_deleted=0).select_related('lgd__id','publication__pmid').values('lgd__id', 'publication__pmid')

    for data in queryset_lgd_publication:
        if data['lgd__id'] not in lgd_publication_data:
            lgd_publication_data[data['lgd__id']] = [str(data['publication__pmid'])]
        else:
            lgd_publication_data[data['lgd__id']].append(str(data['publication__pmid']))

    # Preload cross cutting modifier
    lgd_ccm_data = {} # key = lgd_id; value = pmid
    queryset_lgd_ccm = LGDCrossCuttingModifier.objects.filter(
        is_deleted=0).select_related('lgd__id','ccm__value').values('lgd__id', 'ccm__value')

    for data in queryset_lgd_ccm:
        if data['lgd__id'] not in lgd_ccm_data:
            lgd_ccm_data[data['lgd__id']] = [data['ccm__value']]
        else:
            lgd_ccm_data[data['lgd__id']].append(data['ccm__value'])

    # Prepare to write to output file
    writer = csv.writer(response)
    # Write file header
    writer.writerow([
            "g2p id",
            "gene symbol",
            "gene ids",
            "gene previous symbols",
            "disease name",
            "disease ids",
            "allelic requirement",
            "confidence",
            "variant consequence",
            "variant type",
            "molecular mechanism",
            "phenotypes",
            "publications",
            "cross cutting modifier",
            "date of last review"
    ])

    # Authenticated users can download all panels
    # Non authenticated users can only download visible panels
    if panel.is_visible == 1 or (user_obj and user_obj.is_authenticated and panel.is_visible == 0):
        # Download reviewed entries
        queryset_list = LocusGenotypeDisease.objects.filter(
            is_deleted = 0,
            is_reviewed = 1,
            lgdpanel__panel = panel
        ).distinct().select_related('stable_id', 'locus', 'disease', 'genotype', 'confidence'
                                    ).prefetch_related('disease', 'locus')

        # Non authenticated users cannot download entries with the following confidence values:
        # 'disputed' and 'refuted'
        if not user_obj:
            queryset_list = queryset_list.filter(~Q(confidence__value='refuted') & ~Q(confidence__value='disputed'))

        # Get extra info for the disease and the locus:
        #  disease - ids from external dbs (omim, mondo)
        #  locus - previous gene symbols (from ensembl) and external ids (hgnc, ensembl)
        queryset_list_extra = list(queryset_list.values(
            'stable_id',
            'disease__diseaseontologyterm__ontology_term__accession',
            'locus__locusattrib__value',
            'locus__locusidentifier__identifier'
            ))

        extra_data_dict = {}
        for data in queryset_list_extra:
            g2p_id = data['stable_id']
            if g2p_id not in extra_data_dict:
                extra_data_dict[g2p_id] = {}

                if data['disease__diseaseontologyterm__ontology_term__accession'] is not None:
                    extra_data_dict[g2p_id]['disease_ids'] = [data['disease__diseaseontologyterm__ontology_term__accession']]

                if data['locus__locusattrib__value'] is not None:
                    extra_data_dict[g2p_id]['locus_previous_symbols'] = [data['locus__locusattrib__value']]

                if data['locus__locusidentifier__identifier'] is not None:
                    extra_data_dict[g2p_id]['locus_ids'] = [data['locus__locusidentifier__identifier']]

            else:
                if (data['disease__diseaseontologyterm__ontology_term__accession'] is not None
                    and data['disease__diseaseontologyterm__ontology_term__accession'] not in extra_data_dict[g2p_id]['disease_ids']):
                    extra_data_dict[g2p_id]['disease_ids'].append(data['disease__diseaseontologyterm__ontology_term__accession'])

                if (data['locus__locusattrib__value'] is not None
                    and data['locus__locusattrib__value'] not in extra_data_dict[g2p_id]['locus_previous_symbols']):
                    extra_data_dict[g2p_id]['locus_previous_symbols'].append(data['locus__locusattrib__value'])

                if (data['locus__locusidentifier__identifier'] is not None
                    and data['locus__locusidentifier__identifier'] not in extra_data_dict[g2p_id]['locus_ids']):
                    extra_data_dict[g2p_id]['locus_ids'].append(data['locus__locusidentifier__identifier'])

        # Prepare final data
        for lgd in queryset_list:
            lgd_id = lgd.id
            variant_types = ""
            variant_consequences = ""
            molecular_mechanism = ""
            phenotypes = ""
            publications = ""
            ccm = ""

            # extra data for disease and locus
            disease_ids = ""
            locus_ids = ""
            locus_previous = ""

            if lgd_id in extra_data_dict:
                if 'disease_ids' in extra_data_dict[lgd_id]:
                    disease_ids = ', '.join(extra_data_dict[lgd_id]['disease_ids'])
                if 'locus_ids' in extra_data_dict[lgd_id]:
                    locus_ids = ', '.join(extra_data_dict[lgd_id]['locus_ids'])
                if 'locus_previous_symbols' in extra_data_dict[lgd_id]:
                    locus_previous = ', '.join(extra_data_dict[lgd_id]['locus_previous_symbols'])

            # Get preloaded variant types for this g2p entry
            if lgd_id in lgd_variantype_data:
                variant_types = ', '.join(lgd_variantype_data[lgd_id])

            # Get preloaded variant consequenes for this g2p entry
            if lgd_id in lgd_varianconsequence_data:
                variant_consequences = ', '.join(lgd_varianconsequence_data[lgd_id])

            # Get preloaded molecular mechanism for this g2p entry
            if lgd_id in lgd_mechanism_data:
                molecular_mechanism = ', '.join(lgd_mechanism_data[lgd_id])

            # Get preloaded phenotypes for this g2p entry
            if lgd_id in lgd_phenotype_data:
                phenotypes = ', '.join(lgd_phenotype_data[lgd_id])
            
            # Get preloaded publications for this g2p entry
            if lgd_id in lgd_publication_data:
                publications = ', '.join(lgd_publication_data[lgd_id])

            # Get preloaded cross cutting modifier for this g2p entry
            if lgd_id in lgd_ccm_data:
                ccm = ', '.join(lgd_ccm_data[lgd_id])

            # Write data to output file
            writer.writerow([
                lgd.stable_id.stable_id,
                lgd.locus.name,
                locus_ids, # locus ids (hgnc, ensembl)
                locus_previous, # gene previous symbols
                lgd.disease.name,
                disease_ids, # omim and mondo ids
                lgd.genotype.value,
                lgd.confidence.value,
                variant_consequences,
                variant_types,
                molecular_mechanism,
                phenotypes,
                publications,
                ccm,
                lgd.date_review
            ])

    else:
        # If user is not authenticated then it can only download visible panels
        # Return no matching panel
        raise Http404(f"No matching panel found for: {name}")

    return response