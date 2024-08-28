from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.http import Http404, HttpResponse
from rest_framework.decorators import api_view
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.db.models import Q
import csv
import gzip
from datetime import datetime

from gene2phenotype_app.models import (Panel, User, LocusGenotypeDisease,
                                       LGDVariantType, LGDVariantGenccConsequence,
                                       LGDMolecularMechanism, LGDPhenotype,
                                       LGDPublication, LGDCrossCuttingModifier,
                                       LGDPanel)

from gene2phenotype_app.serializers import PanelDetailSerializer, LGDPanelSerializer, UserSerializer

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

### Edit data ###
class LGDEditPanel(APIView):
    """
        Method to add or delete LGD-panel association.
    """
    http_method_names = ['post', 'update', 'options']
    serializer_class = LGDPanelSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    @transaction.atomic
    def post(self, request, stable_id):
        """
            The post method links the current LGD record to the panel.
            We want to whole process to be done in one db transaction.
        """
        user = self.request.user

        if not user.is_authenticated:
            return Response({"message": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)

        panel_name_input = request.data.get("name", None)

        if panel_name_input is None:
            return Response({"message": f"Please enter a panel name"}, status=status.HTTP_400_BAD_REQUEST)

        # Check if panel name is valid
        panel_obj = get_object_or_404(Panel, name=panel_name_input)

        # Check if user can update panel
        user_obj = get_object_or_404(User, email=user)
        serializer = UserSerializer(user_obj, context={"user" : user})
        user_panel_list_lower = [panel.lower() for panel in serializer.panels_names(user_obj)]

        if panel_name_input.lower() not in user_panel_list_lower:
            return Response({"message": f"No permission to update panel {panel_name_input}"}, status=status.HTTP_403_FORBIDDEN)

        lgd = get_object_or_404(LocusGenotypeDisease, stable_id__stable_id=stable_id, is_deleted=0)

        serializer_class = LGDPanelSerializer(data={"name": panel_name_input}, context={"lgd": lgd})

        if serializer_class.is_valid():
            serializer_class.save()
            response = Response({"message": "Panel added to the G2P entry successfully."}, status=status.HTTP_200_OK)
        else:
            response = Response({"errors": serializer_class.errors}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return response

    @transaction.atomic
    def update(self, request, stable_id):
        """
            This method deletes the LGD-panel
        """
        panel = request.data.get("name", None)
        user = request.user # TODO check if user has permission to edit the panel and the record

        # Get G2P entry to be updated
        lgd_obj = get_object_or_404(LocusGenotypeDisease, stable_id__stable_id=stable_id, is_deleted=0)
        panel_obj = get_object_or_404(Panel, name=panel)

        queryset_all_panels = LGDPanel.objects.filter(lgd=lgd_obj, is_deleted=0)

        if(len(queryset_all_panels) == 1):
            raise Http404(f"Cannot delete panel for ID '{stable_id}'")

        try:
            LGDPanel.objects.filter(lgd=lgd_obj, panel=panel_obj, is_deleted=0).update(is_deleted=1)
        except:
            return Response(
                {"errors": f"Could not delete panel '{panel}' for ID '{stable_id}'"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            return Response(
                {"message": f"Panel '{panel}' successfully deleted for ID '{stable_id}'"},
                 status=status.HTTP_200_OK)

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
    filename = f"G2P_{name}_{date_now}.csv.gz"

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
    lgd_mechanism_data = {} # key = lgd_id; {value = molecular mechanism value, support = mechanism support ('inferred' or 'evidence')}
    queryset_lgd_mechanism = LGDMolecularMechanism.objects.filter(
        is_deleted=0).select_related('lgd__id','mechanism__value', 'mechanism_support__value'
        ).prefetch_related('lgd_molecular_mechanism_evidence').values(
            'lgd__id',
            'mechanism__value',
            'mechanism_support__value',
            'lgdmolecularmechanismevidence__evidence__subtype',
            'lgdmolecularmechanismevidence__evidence__value',
            'lgdmolecularmechanismevidence__publication__pmid')

    evidence_data = {}

    # First collect the evidence data for each lgd_id
    for data in queryset_lgd_mechanism:
        if data['mechanism_support__value'] == "evidence":
            mechanism_value = data['mechanism__value']
            subtype = data['lgdmolecularmechanismevidence__evidence__subtype']
            value = data['lgdmolecularmechanismevidence__evidence__value']
            pmid = data['lgdmolecularmechanismevidence__publication__pmid']

            if data['lgd__id'] not in evidence_data:
                evidence_data[data['lgd__id']] = {
                    mechanism_value: [{"subtype": subtype, "value": value, "pmid" :pmid}]
                }
            else:
                # this should be the most common scenario
                if mechanism_value in evidence_data[data['lgd__id']]:
                    evidence_data[data['lgd__id']][mechanism_value].append({"subtype": subtype, "value": value, "pmid":pmid})
                else:
                    # if lgd_id has multiple mechanisms
                    evidence_data[data['lgd__id']].update({
                        mechanism_value: [{subtype: 1, value: 1, pmid :pmid}]
                    })

    # Prepare final dict of mechanisms + evidence (if applicable)
    for data in queryset_lgd_mechanism:
        if data['lgd__id'] not in lgd_mechanism_data:
            # check if there is evidence
            if data['lgd__id'] in evidence_data:
                evidence = evidence_data[data['lgd__id']][data['mechanism__value']]
                lgd_mechanism_data[data['lgd__id']] = [{
                    "value": data['mechanism__value'],
                    "support": data['mechanism_support__value'],
                    "evidence": evidence
                }]

            else:
                lgd_mechanism_data[data['lgd__id']] = [{
                    "value": data['mechanism__value'],
                    "support": data['mechanism_support__value']
                }]

        else:
            # check if there is evidence
            if data['lgd__id'] in evidence_data:
                evidence = evidence_data[data['lgd__id']][data['mechanism__value']]
                lgd_mechanism_data[data['lgd__id']].append({
                    "value": data['mechanism__value'],
                    "support": data['mechanism_support__value'],
                    "evidence": evidence
                })

            else:
                lgd_mechanism_data[data['lgd__id']].append({
                    "value": data['mechanism__value'],
                    "support": data['mechanism_support__value']
                })

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

        # Prepare to write to output file
        with gzip.open(filename, "wt") as fh:
            writer = csv.writer(fh, delimiter=',')

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
                "molecular mechanism evidence",
                "phenotypes",
                "publications",
                "cross cutting modifier",
                "date of last review"
            ])

            # Prepare final data
            for lgd in queryset_list:
                lgd_id = lgd.id
                variant_types = ""
                variant_consequences = ""
                molecular_mechanism = ""
                molecular_mechanism_evidence = ""
                phenotypes = ""
                publications = ""
                ccm = ""

                # extra data for disease and locus
                disease_ids = ""
                locus_ids = ""
                locus_previous = ""

                if lgd_id in extra_data_dict:
                    if 'disease_ids' in extra_data_dict[lgd_id]:
                        disease_ids = '; '.join(extra_data_dict[lgd_id]['disease_ids'])
                    if 'locus_ids' in extra_data_dict[lgd_id]:
                        locus_ids = '; '.join(extra_data_dict[lgd_id]['locus_ids'])
                    if 'locus_previous_symbols' in extra_data_dict[lgd_id]:
                        locus_previous = '; '.join(extra_data_dict[lgd_id]['locus_previous_symbols'])

                # Get preloaded variant types for this g2p entry
                if lgd_id in lgd_variantype_data:
                    variant_types = '; '.join(lgd_variantype_data[lgd_id])

                # Get preloaded variant consequenes for this g2p entry
                if lgd_id in lgd_varianconsequence_data:
                    variant_consequences = '; '.join(lgd_varianconsequence_data[lgd_id])

                # Get preloaded molecular mechanism for this g2p entry
                if lgd_id in lgd_mechanism_data:
                    final_mechanisms = set()
                    mechanism_evidence = set()
                    for mechanism_data in lgd_mechanism_data[lgd_id]:
                        final_mechanisms.add(f"{mechanism_data["value"]} ({mechanism_data["support"]})")

                        if "evidence" in mechanism_data:
                            for element in mechanism_data["evidence"]:
                                mechanism_evidence.add(f"{element["subtype"]}:{element["value"]}:{element["pmid"]}")
                    molecular_mechanism = "; ".join(final_mechanisms)
                    molecular_mechanism_evidence = "; ".join(mechanism_evidence)

                # Get preloaded phenotypes for this g2p entry
                if lgd_id in lgd_phenotype_data:
                    phenotypes = '; '.join(lgd_phenotype_data[lgd_id])

                # Get preloaded publications for this g2p entry
                if lgd_id in lgd_publication_data:
                    publications = '; '.join(lgd_publication_data[lgd_id])

                # Get preloaded cross cutting modifier for this g2p entry
                if lgd_id in lgd_ccm_data:
                    ccm = '; '.join(lgd_ccm_data[lgd_id])

                # Write data to output file
                writer.writerow([
                    lgd.stable_id.stable_id,
                    lgd.locus.name,
                    locus_ids,
                    locus_previous,
                    lgd.disease.name,
                    disease_ids,
                    lgd.genotype.value,
                    lgd.confidence.value,
                    variant_consequences,
                    variant_types,
                    molecular_mechanism,
                    molecular_mechanism_evidence,
                    phenotypes,
                    publications,
                    ccm,
                    lgd.date_review
                ])
    else:
        # If user is not authenticated then it can only download visible panels
        # Return no matching panel
        raise Http404(f"No matching panel found for: {name}")

    response = HttpResponse(
        open(filename, 'rb'),
        content_type="text/gzip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )

    return response