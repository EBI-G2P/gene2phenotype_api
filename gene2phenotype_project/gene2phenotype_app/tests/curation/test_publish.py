from django.test import TestCase
from django.urls import reverse
from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken
from gene2phenotype_app.models import User, CurationData


class LGDAddCurationEndpoint(TestCase):
    """
    Test endpoint to publish a record
    """

    fixtures = [
        "gene2phenotype_app/fixtures/g2p_stable_id.json",
        "gene2phenotype_app/fixtures/user_panels.json",
        "gene2phenotype_app/fixtures/curation_data.json",
        "gene2phenotype_app/fixtures/sequence.json",
        "gene2phenotype_app/fixtures/locus.json",
        "gene2phenotype_app/fixtures/source.json",
        "gene2phenotype_app/fixtures/attribs.json",
        "gene2phenotype_app/fixtures/cv_molecular_mechanism.json",
        "gene2phenotype_app/fixtures/ontology_term.json",
        "gene2phenotype_app/fixtures/locus_genotype_disease.json",
        "gene2phenotype_app/fixtures/disease.json",
    ]

    def setUp(self):
        self.url_add_curation = reverse("add_curation_data")

    def test_publish_incorrect_genotype(self):
        """
        Test the curation endpoint when the genotype is incorrect for the gene.
        First, call the endpoint to add the curation data - it is possible to save the data
        even when the genotype is incorrect.
        And finally try to publish the data - it is not possible to publish the data.
        """
        # Define the input data structure
        data_to_add = {
            "json_data": {
                "allelic_requirement": "biallelic_autosomal",
                "confidence": "disputed",
                "cross_cutting_modifier": ["potential secondary finding"],
                "disease": {
                    "cross_references": [
                        {
                            "disease_name": "46,xx sex reversal",
                            "identifier": "MONDO:0100250",
                            "original_disease_name": "46,xx sex reversal",
                            "source": "Mondo",
                        }
                    ],
                    "disease_name": "SRY-related 46,xx sex reversal",
                },
                "locus": "SRY",
                "mechanism_evidence": [
                    {
                        "description": "test comment",
                        "evidence_types": [
                            {
                                "primary_type": "Rescue",
                                "secondary_type": ["Patient Cells"],
                            }
                        ],
                        "pmid": "1",
                    }
                ],
                "mechanism_synopsis": [
                    {"name": "destabilising LOF", "support": "inferred"}
                ],
                "molecular_mechanism": {
                    "name": "loss of function",
                    "support": "evidence",
                },
                "panels": ["Developmental disorders"],
                "phenotypes": [],
                "private_comment": "test comment",
                "public_comment": "test comment public",
                "publications": [
                    {
                        "affectedIndividuals": 1,
                        "ancestries": "test",
                        "authors": "Makar AB, McMartin KE, Palese M, Tephly TR.",
                        "comment": "test comment",
                        "consanguineous": "no",
                        "families": 1,
                        "pmid": "1",
                        "source": "G2P",
                        "title": "Formate assay in body fluids: application in methanol poisoning.",
                        "year": 1975,
                    }
                ],
                "session_name": "test genotype",
                "variant_consequences": [
                    {
                        "support": "inferred",
                        "variant_consequence": "decreased_gene_product_level",
                    }
                ],
                "variant_descriptions": [
                    {"description": "test description", "publication": "1"}
                ],
                "variant_types": [
                    {
                        "comment": "test comment",
                        "de_novo": True,
                        "inherited": True,
                        "nmd_escape": False,
                        "primary_type": "protein_changing",
                        "secondary_type": "missense_variant",
                        "supporting_papers": ["1"],
                        "unknown_inheritance": False,
                    }
                ],
            }
        }

        # Login
        user = User.objects.get(email="user5@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        # Authenticate by setting cookie on the test client
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        response = self.client.post(
            self.url_add_curation, data_to_add, content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)

        response_data = response.json()
        self.assertEqual(
            response_data["message"],
            "Data saved successfully for session name 'test genotype'",
        )

        # Prepare the URL to publish the record
        url_publish = reverse(
            "publish_record", kwargs={"stable_id": response_data["result"]}
        )

        # Call the endpoint to publish
        response_publish = self.client.post(
            url_publish, content_type="application/json"
        )
        self.assertEqual(response_publish.status_code, 400)

        response_data_publish = response_publish.json()
        self.assertEqual(
            response_data_publish["error"],
            "Invalid genotype 'biallelic_autosomal' for locus 'SRY'",
        )

    def test_publish_insufficient_publications(self):
        """
        Test the curation endpoint when the number of publications
        is not enough for the confidence value.
        """
        # Define the input data structure
        data_to_add = {
            "json_data": {
                "allelic_requirement": "monoallelic_Y_hemizygous",
                "confidence": "definitive",
                "cross_cutting_modifier": ["potential secondary finding"],
                "disease": {
                    "cross_references": [
                        {
                            "disease_name": "46,xx sex reversal",
                            "identifier": "MONDO:0100250",
                            "original_disease_name": "46,xx sex reversal",
                            "source": "Mondo",
                        }
                    ],
                    "disease_name": "SRY-related 46,xx sex reversal",
                },
                "locus": "SRY",
                "mechanism_evidence": [
                    {
                        "description": "test comment",
                        "evidence_types": [
                            {
                                "primary_type": "Rescue",
                                "secondary_type": ["Patient Cells"],
                            }
                        ],
                        "pmid": "1",
                    }
                ],
                "mechanism_synopsis": [
                    {"name": "destabilising LOF", "support": "inferred"}
                ],
                "molecular_mechanism": {
                    "name": "loss of function",
                    "support": "evidence",
                },
                "panels": ["Developmental disorders"],
                "phenotypes": [],
                "private_comment": "test comment",
                "public_comment": "test comment public",
                "publications": [
                    {
                        "affectedIndividuals": 1,
                        "ancestries": "test",
                        "authors": "Makar AB, McMartin KE, Palese M, Tephly TR.",
                        "comment": "test comment",
                        "consanguineous": "no",
                        "families": 1,
                        "pmid": "1",
                        "source": "G2P",
                        "title": "Formate assay in body fluids: application in methanol poisoning.",
                        "year": 1975,
                    }
                ],
                "session_name": "Test A",
                "variant_consequences": [
                    {
                        "support": "inferred",
                        "variant_consequence": "altered_gene_product_level",
                    }
                ],
                "variant_descriptions": [
                    {"description": "test description", "publication": "1"}
                ],
                "variant_types": [
                    {
                        "comment": "test comment",
                        "de_novo": True,
                        "inherited": True,
                        "nmd_escape": False,
                        "primary_type": "protein_changing",
                        "secondary_type": "missense_variant",
                        "supporting_papers": ["1"],
                        "unknown_inheritance": False,
                    }
                ],
            }
        }

        # Login
        user = User.objects.get(email="user5@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        # Authenticate by setting cookie on the test client
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        # Save the curation draft
        response = self.client.post(
            self.url_add_curation, data_to_add, content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)

        response_data = response.json()
        self.assertEqual(
            response_data["message"],
            "Data saved successfully for session name 'Test A'",
        )

        # Prepare the URL to publish the record
        url_publish = reverse(
            "publish_record", kwargs={"stable_id": response_data["result"]}
        )

        # Call the endpoint to publish
        response_publish = self.client.post(
            url_publish, content_type="application/json"
        )
        self.assertEqual(response_publish.status_code, 400)

        response_data_publish = response_publish.json()
        self.assertEqual(
            response_data_publish["error"],
            "Confidence 'definitive' requires more than one publication as evidence",
        )

    def test_publish_success(self):
        """
        Test successful call to publish a record
        """
        # Define the input data structure
        data_to_add = {
            "json_data": {
                "allelic_requirement": "monoallelic_Y_hemizygous",
                "confidence": "limited",
                "cross_cutting_modifier": ["potential secondary finding"],
                "disease": {
                    "cross_references": [
                        {
                            "disease_name": "46,xx sex reversal",
                            "identifier": "MONDO:0100250",
                            "original_disease_name": "46,xx sex reversal",
                            "source": "Mondo",
                        }
                    ],
                    "disease_name": "SRY-related 46,xx sex reversal",
                },
                "locus": "SRY",
                "mechanism_evidence": [
                    {
                        "description": "test comment",
                        "evidence_types": [
                            {
                                "primary_type": "Rescue",
                                "secondary_type": ["Patient Cells"],
                            }
                        ],
                        "pmid": "1",
                    }
                ],
                "mechanism_synopsis": [
                    {"name": "destabilising LOF", "support": "inferred"}
                ],
                "molecular_mechanism": {
                    "name": "loss of function",
                    "support": "evidence",
                },
                "panels": ["Developmental disorders"],
                "phenotypes": [],
                "private_comment": "test comment",
                "public_comment": "test comment public",
                "publications": [
                    {
                        "affectedIndividuals": 1,
                        "ancestries": "test",
                        "authors": "Makar AB, McMartin KE, Palese M, Tephly TR.",
                        "comment": "test comment",
                        "consanguineous": "no",
                        "families": 1,
                        "pmid": "1",
                        "source": "G2P",
                        "title": "Formate assay in body fluids: application in methanol poisoning.",
                        "year": 1975,
                    }
                ],
                "session_name": "Test B",
                "variant_consequences": [
                    {
                        "support": "inferred",
                        "variant_consequence": "decreased_gene_product_level",
                    }
                ],
                "variant_descriptions": [
                    {"description": "test description", "publication": "1"}
                ],
                "variant_types": [
                    {
                        "comment": "test comment",
                        "de_novo": True,
                        "inherited": True,
                        "nmd_escape": False,
                        "primary_type": "protein_changing",
                        "secondary_type": "missense_variant",
                        "supporting_papers": ["1"],
                        "unknown_inheritance": False,
                    }
                ],
            }
        }

        # Login
        user = User.objects.get(email="user5@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        # Authenticate by setting cookie on the test client
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        # Save the curation draft
        response = self.client.post(
            self.url_add_curation, data_to_add, content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)

        response_data = response.json()
        self.assertEqual(
            response_data["message"],
            "Data saved successfully for session name 'Test B'",
        )

        # Prepare the URL to publish the record
        url_publish = reverse(
            "publish_record", kwargs={"stable_id": response_data["result"]}
        )

        # Call the endpoint to publish
        response_publish = self.client.post(
            url_publish, content_type="application/json"
        )
        self.assertEqual(response_publish.status_code, 201)

        response_data_publish = response_publish.json()
        self.assertEqual(
            response_data_publish["message"],
            "Record 'G2P00007' published successfully",
        )
