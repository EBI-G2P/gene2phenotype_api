from rest_framework import permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import api_view
from django.db import transaction
from django.shortcuts import get_object_or_404

from gene2phenotype_app.serializers import (PublicationSerializer, LGDPublicationSerializer,
                                            LGDPublicationListSerializer, LGDPhenotypeSerializer,
                                            LGDVariantTypeSerializer, LGDVariantTypeDescriptionSerializer,
                                            LocusGenotypeDiseaseSerializer)

from gene2phenotype_app.models import (Publication, LocusGenotypeDisease, LGDPublication,
                                       LGDPhenotype, LGDPhenotypeSummary, LGDVariantType,
                                       LGDVariantTypeDescription, MolecularMechanismEvidence)

from .base import BaseAdd, BaseUpdate

from ..utils import get_publication, get_authors


"""
    Retrieve publication data for a list of PMIDs.
    If PMID is found in G2P then return details from G2P.
    If PMID not found in G2P then returns info from EuropePMC.

    Args:
            (HttpRequest) request: HTTP request
            (str) pmids: A comma-separated string of PMIDs

    Returns:
            Response object includes:
                (list) results: contains publication data for each publication
                                    - pmid
                                    - title
                                    - authors
                                    - year
                                    - source (possible values: 'G2P', 'EuropePMC')
                (int) count: number of PMIDs
    
    Raises:
            Invalid PMID
"""
@api_view(['GET'])
def PublicationDetail(request, pmids):
    id_list = pmids.split(',')
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
                data.append({
                    'pmid': int(publication.pmid),
                    'title': publication.title,
                    'authors': publication.authors,
                    'year': int(publication.year),
                    'source': 'G2P'
                })
            except Publication.DoesNotExist:
                # Query EuropePMC
                response = get_publication(pmid)
                if response['hitCount'] == 0:
                    invalid_pmids.append(pmid_str)
                else:
                    authors = get_authors(response)
                    year = None
                    publication_info = response['result']
                    title = publication_info['title']
                    if 'pubYear' in publication_info:
                        year = publication_info['pubYear']

                    data.append({
                        'pmid': int(pmid),
                        'title': title,
                        'authors': authors,
                        'year': int(year),
                        'source': 'EuropePMC'
                    })

    # if any of the PMIDs is invalid raise error and display all invalid IDs
    if invalid_pmids:
        pmid_list = ", ".join(invalid_pmids)
        response = Response({'detail': f"Invalid PMID(s): {pmid_list}"}, status=status.HTTP_404_NOT_FOUND)

    else:
        response = Response({'results': data, 'count': len(data)})

    return response


### Add publication ###
class AddPublication(BaseAdd):
    """
        Add new publication.
        The create method is in the PublicationSerializer.
    """
    serializer_class = PublicationSerializer
    permission_classes = [permissions.IsAuthenticated]

### LGD-publication ###
# Add or delete data
class LGDEditPublications(BaseUpdate):
    """
        Add or delete lgd-publication.

        Add data (action: POST)
            Add a list of publications to an existing G2P record (LGD).
            When adding a publication it can also add:
                - comment
                - family info as reported in the publication
        
        Delete data (action: UPDATE)
            Delete a publication associated with the LGD.
            The deletion does not remove the entry from the database, instead
            it sets the flag 'is_deleted' to 1.
    """
    http_method_names = ['post', 'update', 'options']
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self, action):
        """
            Returns the appropriate serializer class based on the action.
            To add data use LGDPublicationListSerializer: it accepts a list of publications.
            To delete data use LGDPublicationSerializer: it accepts one publication.
        """
        action = action.lower()

        if action == "post":
            return LGDPublicationListSerializer
        elif action == "update":
            return LGDPublicationSerializer
        else:
            return None

    @transaction.atomic
    def post(self, request, stable_id):
        """
            The post method creates an association between the current LGD record and a list of publications.
            We want to whole process to be done in one db transaction.

            This method allows to add extra data to the LGD record.
            When a publication is linked to a LGD record, other types of data can be associated to the record
            and the publication:
                - phenotypes
                - variant types
                - variant descriptions
                - molecular mechanism evidence

            Args:
                (dict) request data

                Example for a record already linked to pmid '41':
                { "publications":[
                        {
                            "publication": { "pmid": "1234" },
                            "comment": { "comment": "this is a comment", "is_public": 1 },
                            "families": { "families": 2, "consanguinity": "unknown", "ancestries": "african", "affected_individuals": 1 },
                            "phenotypes": [{
                                        "pmid": "41",
                                        "summary": "",
                                        "hpo_terms": [{ "term": "Orofacial dyskinesia",
                                                        "accession": "HP:0002310",
                                                        "description": "" }]
                                    }],
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
                "mechanism_synopsis": {
                    "name": "",
                    "support": ""
                },
                "mechanism_evidence": [{
                            "pmid": "1234",
                            "description": "This is new evidence for the existing mechanism evidence.",
                            "evidence_types": [ { "primary_type": "Function",
                                                    "secondary_type": [ "Biochemical" ]}
                            ]}]
            }
        """
        user = self.request.user

        lgd = get_object_or_404(LocusGenotypeDisease, stable_id__stable_id=stable_id, is_deleted=0)

        # LGDPublicationListSerializer accepts a list of publications
        serializer_list = LGDPublicationListSerializer(data=request.data)

        if serializer_list.is_valid():
            publications_data = serializer_list.validated_data.get('publications') # the pmids are mandatory
            phenotypes_data = serializer_list.validated_data.get('phenotypes', []) # optional
            variant_types_data = serializer_list.validated_data.get('variant_types', []) # optional
            variant_descriptions_data = serializer_list.validated_data.get('variant_descriptions', []) # optional
            mechanism_data = serializer_list.validated_data.get('molecular_mechanism', None) # optional
            mechanism_synopsis_data = serializer_list.validated_data.get('mechanism_synopsis', None) # optional
            mechanism_evidence_data = serializer_list.validated_data.get('mechanism_evidence', None) # optional

            for publication in publications_data:
                serializer_class = LGDPublicationSerializer(
                    data=publication,
                    context={"lgd": lgd, "user": user}
                )

                # Insert new publication
                if serializer_class.is_valid():
                    serializer_class.save()
                else:
                    response = Response({"errors": serializer_class.errors}, status=status.HTTP_400_BAD_REQUEST)

            # Add extra data linked to the publication - phenotypes
            # Expected structure:
            #   { "phenotypes": [{ "accession": "HP:0003974", "publication": 1 }] }
            for phenotype in phenotypes_data:
                hpo_terms = phenotype['hpo_terms']
                for hpo in hpo_terms:
                    phenotype_data = {
                        "accession": hpo["accession"],
                        "publication": phenotype["pmid"]
                    }
                    try:
                        lgd_phenotype_serializer = LGDPhenotypeSerializer(
                            data = phenotype_data,
                            context = {'lgd': lgd}
                        )
                        # Validate the input data
                        if lgd_phenotype_serializer.is_valid():
                            # save() is going to call create()
                            lgd_phenotype_serializer.save()
                        else:
                            response = Response({"errors": lgd_phenotype_serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
                    except:
                        accession = phenotype_data["accession"]
                        return Response(
                            {"errors": f"Could not insert phenotype '{accession}' for ID '{stable_id}'"},
                            status=status.HTTP_400_BAD_REQUEST
                        )

            # Add extra data linked to the publication - variant types
            for variant_type in variant_types_data:
                LGDVariantTypeSerializer(context={'lgd': lgd, 'user': user}).create(variant_type)

            # Add extra data linked to the publication - variant descriptions (HGVS)
            for variant_type_desc in variant_descriptions_data:
                LGDVariantTypeDescriptionSerializer(context={'lgd': lgd}).create(variant_type_desc)

            # Only mechanism "undetermined" can be updated
            # If mechanism has to be updated, call method update_mechanism() and send new mechanism value
            # plus the synopsis and the new evidence (if applicable)
            # update_mechanism() updates the 'date_review' of the LGD record
            if mechanism_data:
                lgd_serializer = LocusGenotypeDiseaseSerializer()
                mechanism_obj = lgd.molecular_mechanism

                # Check if it's possible to update the mechanism
                if(mechanism_obj.mechanism.value != "undetermined" or
                    mechanism_obj.mechanism_support.value != "inferred"):
                    self.handle_no_update('molecular mechanism', stable_id)

                # Build mechanism data
                mechanism_data_input = { 
                    "molecular_mechanism": mechanism_data
                }
                # Attach the synopsis to be updated (if applicable)
                if mechanism_synopsis_data:
                    mechanism_data_input["mechanism_synopsis"] = mechanism_synopsis_data
                # Attach the evidence to be updated (if applicable)
                if mechanism_evidence_data:
                    mechanism_data_input["mechanism_evidence"] = mechanism_evidence_data

                try:
                    lgd_serializer.update_mechanism(lgd, mechanism_data_input)
                except Exception as e:
                    return self.handle_update_exception(e, "Error while updating molecular mechanism")

            # If only the mechanism evidence is going to be updated, call method update_mechanism_evidence()
            # update_mechanism_evidence() updates the 'date_review' of the LGD record
            # TODO: but before adding evidence we have to check/update the mechanism support to "evidence"
            elif mechanism_evidence_data:
                lgd_serializer = LocusGenotypeDiseaseSerializer()
                try:
                    lgd_serializer.update_mechanism_evidence(lgd, mechanism_evidence_data)
                except Exception as e:
                    return self.handle_update_exception(e, "Error while updating molecular mechanism evidence")

            response = Response({'message': 'Publication added to the G2P entry successfully.'}, status=status.HTTP_201_CREATED)

        else:
            response = Response({"errors": serializer_list.errors}, status=status.HTTP_400_BAD_REQUEST)

        return response

    @transaction.atomic
    def update(self, request, stable_id):
        """
            This method deletes the LGD-publication.

            Args:
                { "pmid": 1234 }
        """
        pmid = request.data.get("pmid", None)
        user = request.user # TODO check if user has permission

        lgd_obj = get_object_or_404(LocusGenotypeDisease, stable_id__stable_id=stable_id, is_deleted=0)
        publication_obj = get_object_or_404(Publication, pmid=pmid)

        try:
            lgd_publication_obj = LGDPublication.objects.get(lgd=lgd_obj, publication=publication_obj, is_deleted=0)
        except LGDPublication.DoesNotExist:
            return Response(
                {"errors": f"Could not find publication '{pmid}' for ID '{stable_id}'"},
                status=status.HTTP_404_NOT_FOUND)

        # Before deleting this publication check if LGD record is linked to other publications
        queryset_all = LGDPublication.objects.filter(lgd=lgd_publication_obj.lgd, is_deleted=0)

        # TODO: if we are going to delete the last publication then delete LGD record
        if(queryset_all.exists() and len(queryset_all) == 1):
            return Response(
                {"errors": f"Could not delete PMID '{pmid}' for ID '{stable_id}'"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Remove the publication from the LGD
        lgd_publication_obj.is_deleted = 1

        try:
            lgd_publication_obj.save()
        except:
            return Response(
                {"errors": f"Could not delete PMID '{pmid}' for ID '{stable_id}'"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Delete publication from other tables
        # lgd_phenotype - different phenotypes can be linked to the same publication
        try:
            LGDPhenotype.objects.filter(
                lgd=lgd_publication_obj.lgd,
                publication=lgd_publication_obj.publication,
                is_deleted=0).update(is_deleted=1)
        except:
            return Response(
                {"errors": f"Could not delete PMID '{pmid}' for ID '{stable_id}'"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # lgd_phenotype_summary - the phenotype summary is directly associated with the LGD record
        # A LGD record should only have one phenotype summary but to make sure we delete everything correctly
        # we'll run the filter to catch all objects
        try:
            LGDPhenotypeSummary.objects.filter(
                lgd=lgd_publication_obj.lgd,
                publication=lgd_publication_obj.publication,
                is_deleted=0).update(is_deleted=1)
        except:
            return Response(
                {"errors": f"Could not delete PMID '{pmid}' for ID '{stable_id}'"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # lgd_variant_type - different variant types can be linked to the same publication
        try:
            LGDVariantType.objects.filter(
                lgd=lgd_publication_obj.lgd,
                publication=lgd_publication_obj.publication,
                is_deleted=0).update(is_deleted=1)
        except:
            return Response(
                {"errors": f"Could not delete PMID '{pmid}' for ID '{stable_id}'"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # lgd_variant_type_description - different descriptions can be linked to the same publication
        try:
            LGDVariantTypeDescription.objects.filter(
                lgd=lgd_publication_obj.lgd,
                publication=lgd_publication_obj.publication,
                is_deleted=0).update(is_deleted=1)
        except:
            return Response(
                {"errors": f"Could not delete PMID '{pmid}' for ID '{stable_id}'"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # molecular_mechanism_evidence - only the molecular mechanism evidence is linked to a publication
        lgd_mechanism_obj = lgd_publication_obj.lgd.molecular_mechanism

        # If the mechanism support is evidence then get the list of MolecularMechanismEvidence
        # Different types of evidence can be linked to the same publication
        if(lgd_mechanism_obj and lgd_mechanism_obj.mechanism_support.value == "evidence"):
            MolecularMechanismEvidence.objects.filter(
                molecular_mechanism=lgd_mechanism_obj,
                publication=lgd_publication_obj.publication,
                is_deleted=0).update(is_deleted=1)

            # Check if MolecularMechanism has evidence linked to other publications
            lgd_check_evidence_set = MolecularMechanismEvidence.objects.filter(
                molecular_mechanism=lgd_mechanism_obj,
                is_deleted=0)

            # # There are no other evidence for this lgd-mechanism
            # # In this case, delete the mechanism
            # if(not lgd_check_evidence_set.exists()):
            #     lgd_mechanism_obj.is_deleted=1 # TODO if there is no mechanism then delete LGD record
            #     lgd_mechanism_obj.save()

        return Response(
                {"message": f"Publication '{pmid}' successfully deleted for ID '{stable_id}'"},
                 status=status.HTTP_200_OK)

