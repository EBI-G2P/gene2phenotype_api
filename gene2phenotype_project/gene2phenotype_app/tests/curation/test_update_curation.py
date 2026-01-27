from django.test import TestCase
from django.urls import reverse
from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken
from gene2phenotype_app.models import User, CurationData


class LGDUpdateCurationEndpoint(TestCase):
    """
    Test endpoint to update curation
    """

    fixtures = [
        "gene2phenotype_app/fixtures/g2p_stable_id.json",
        "gene2phenotype_app/fixtures/user_panels.json",
        "gene2phenotype_app/fixtures/curation_data.json",
        "gene2phenotype_app/fixtures/locus.json",
        "gene2phenotype_app/fixtures/sequence.json",
        "gene2phenotype_app/fixtures/source.json",
        "gene2phenotype_app/fixtures/attribs.json",
    ]

    def setUp(self):
        self.url_update_curation = reverse(
            "update_curation", kwargs={"stable_id": "G2P00004"}
        )
        self.url_update_curation_2 = reverse(
            "update_curation", kwargs={"stable_id": "G2P00010"}
        )
        self.url_update_invalid_curation = reverse(
            "update_curation", kwargs={"stable_id": "G2P00123"}
        )

    def login_user(self):
        self.user = User.objects.get(email="user5@test.ac.uk")
        refresh = RefreshToken.for_user(self.user)
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = str(
            refresh.access_token
        )

    def test_update_curation_success(self):
        """
        Test successful call to update curation endpoint
        """
        self.login_user()

        # Define the complex data structure
        curation_to_update = {
            "json_data": {
                "allelic_requirement": "biallelic_autosomal",
                "confidence": "limited",
                "cross_cutting_modifier": ["potential secondary finding"],
                "disease": {
                    "cross_references": [
                        {
                            "disease_name": "bardet-biedl syndrome",
                            "identifier": "615991",
                            "original_disease_name": "BARDET-BIEDL SYNDROME 14",
                            "source": "OMIM",
                        }
                    ],
                    "disease_name": "CEP290-related bardet-biedl syndrome",
                },
                "locus": "CEP290",
                "mechanism_evidence": [
                    {
                        "description": "updated test comment",
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
                "phenotypes": [
                    {
                        "hpo_terms": [
                            {
                                "accession": "HP:0012372",
                                "term": "Abnormal eye morphology",
                            }
                        ],
                        "pmid": "1",
                        "summary": "updated test comment",
                    }
                ],
                "private_comment": "updated test comment",
                "public_comment": "updated test comment",
                "publications": [
                    {
                        "affectedIndividuals": 1,
                        "ancestries": "updated test",
                        "authors": "Makar AB, McMartin KE, Palese M, Tephly TR.",
                        "comment": "updated test comment",
                        "consanguineous": "no",
                        "families": 1,
                        "pmid": "1",
                        "source": "G2P",
                        "title": "Formate assay in body fluids: application in methanol poisoning.",
                        "year": 1975,
                    }
                ],
                "session_name": "test session",
                "variant_consequences": [
                    {
                        "support": "inferred",
                        "variant_consequence": "altered_gene_product_level",
                    }
                ],
                "variant_descriptions": [
                    {"description": "updated test description", "publication": "1"}
                ],
                "variant_types": [
                    {
                        "comment": "updated test comment",
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

        response = self.client.put(
            self.url_update_curation,
            curation_to_update,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)

        response_data = response.json()
        self.assertEqual(
            response_data["message"],
            "Data updated successfully for session name 'test session'",
        )

        # Check curation_data table
        curation_entries = CurationData.objects.filter(session_name="test session")
        self.assertEqual(len(curation_entries), 1)

        # Test history table
        history_records = CurationData.history.filter(stable_id__stable_id="G2P00004")
        self.assertEqual(len(history_records), 1)

    def test_update_curation_no_permission(self):
        """
        Test call to update curation endpoint with super user who does not have permission to update the curation
        """
        # Define the complex data structure
        curation_to_update = {
            "json_data": {
                "allelic_requirement": "biallelic_autosomal",
                "confidence": "limited",
                "cross_cutting_modifier": ["potential secondary finding"],
                "disease": {
                    "cross_references": [
                        {
                            "disease_name": "bardet-biedl syndrome",
                            "identifier": "615991",
                            "original_disease_name": "BARDET-BIEDL SYNDROME 14",
                            "source": "OMIM",
                        }
                    ],
                    "disease_name": "CEP290-related bardet-biedl syndrome",
                },
                "locus": "CEP290",
                "mechanism_evidence": [
                    {
                        "description": "updated test comment",
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
                "phenotypes": [
                    {
                        "hpo_terms": [
                            {
                                "accession": "HP:0012372",
                                "term": "Abnormal eye morphology",
                            }
                        ],
                        "pmid": "1",
                        "summary": "updated test comment",
                    }
                ],
                "private_comment": "updated test comment",
                "public_comment": "updated test comment",
                "publications": [
                    {
                        "affectedIndividuals": 1,
                        "ancestries": "updated test",
                        "authors": "Makar AB, McMartin KE, Palese M, Tephly TR.",
                        "comment": "updated test comment",
                        "consanguineous": "no",
                        "families": 1,
                        "pmid": "1",
                        "source": "G2P",
                        "title": "Formate assay in body fluids: application in methanol poisoning.",
                        "year": 1975,
                    }
                ],
                "session_name": "test session",
                "variant_consequences": [
                    {
                        "support": "inferred",
                        "variant_consequence": "altered_gene_product_level",
                    }
                ],
                "variant_descriptions": [
                    {"description": "updated test description", "publication": "1"}
                ],
                "variant_types": [
                    {
                        "comment": "updated test comment",
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
        user = User.objects.get(email="john@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        # Authenticate by setting cookie on the test client
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        response = self.client.put(
            self.url_update_curation,
            curation_to_update,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 404)

        response_data = response.json()
        self.assertEqual(
            response_data["error"], "Could not find 'Entry' for ID 'G2P00004'"
        )

    def test_update_curation_invalid_request_body(self):
        """
        Test call to update curation endpoint with invalid request body
        """
        self.login_user()

        # Define the complex data structure
        curation_to_update = {
            "json_data": {
                "locus": "CEP290",
                "disease": "CEP290-related bardet-biedl syndrome",
            }
        }

        response = self.client.put(
            self.url_update_curation,
            curation_to_update,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

        response_data = response.json()
        self.assertIn(
            "JSON data does not follow the required format.", response_data["error"]
        )

    def test_update_curation_missing_json(self):
        """
        Test call to update curation endpoint with missing key 'json_data'
        """
        self.login_user()

        # Define the complex data structure
        curation_to_update = {
            "data": {
                "locus": "CEP290",
                "disease": "CEP290-related bardet-biedl syndrome",
            }
        }

        response = self.client.put(
            self.url_update_curation,
            curation_to_update,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

        response_data = response.json()
        self.assertEqual(
            response_data["error"], "Invalid data format: 'json_data' is missing"
        )

    def test_update_curation_empty_locus(self):
        """
        Test call to update curation endpoint with empty locus field
        """
        self.login_user()

        curation_to_update = {
            "json_data": {
                "allelic_requirement": "",
                "confidence": "",
                "cross_cutting_modifier": [],
                "disease": {"cross_references": [], "disease_name": ""},
                "locus": "",
                "mechanism_evidence": [],
                "mechanism_synopsis": [],
                "molecular_mechanism": {"name": "", "support": ""},
                "panels": [],
                "phenotypes": [],
                "private_comment": "",
                "public_comment": "",
                "publications": [],
                "session_name": "test session",
                "variant_consequences": [],
                "variant_descriptions": [],
                "variant_types": [],
            }
        }

        response = self.client.put(
            self.url_update_curation,
            curation_to_update,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

        response_data = response.json()
        self.assertEqual(response_data["error"], "To save a draft, the minimum requirement is a locus entry. Please save this draft with locus information")

    def test_update_curation_invalid_locus(self):
        """
        Test call to update curation endpoint with invalid locus field
        """
        self.login_user()

        curation_to_update = {
            "json_data": {
                "allelic_requirement": "",
                "confidence": "",
                "cross_cutting_modifier": [],
                "disease": {"cross_references": [], "disease_name": ""},
                "locus": "BAAT-21",
                "mechanism_evidence": [],
                "mechanism_synopsis": [],
                "molecular_mechanism": {"name": "", "support": ""},
                "panels": [],
                "phenotypes": [],
                "private_comment": "",
                "public_comment": "",
                "publications": [],
                "session_name": "test session",
                "variant_consequences": [],
                "variant_descriptions": [],
                "variant_types": [],
            }
        }

        response = self.client.put(
            self.url_update_curation,
            curation_to_update,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

        response_data = response.json()
        self.assertEqual(response_data["error"], "Invalid gene 'BAAT-21'")

    def test_update_invalid_curation(self):
        """
        Test to update invalid curation
        Cannot update a curation that does not exist
        """
        self.login_user()

        # Define the complex data structure
        curation_to_update = {
            "json_data": {
                "allelic_requirement": "",
                "confidence": "",
                "cross_cutting_modifier": [],
                "disease": {"cross_references": [], "disease_name": ""},
                "locus": "RHO",
                "mechanism_evidence": [],
                "mechanism_synopsis": [],
                "molecular_mechanism": {"name": "", "support": ""},
                "panels": [],
                "phenotypes": [],
                "private_comment": "",
                "public_comment": "",
                "publications": [],
                "session_name": "invalid test session",
                "variant_consequences": [],
                "variant_descriptions": [],
                "variant_types": [],
            }
        }

        response = self.client.put(
            self.url_update_invalid_curation,
            curation_to_update,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 404)

    def test_update_curation_duplicate(self):
        """
        Test to update curation that would create a duplicate entry
        G2P ID G2P00010 has session name 'test session SRY', this test
        tries to update the json content to be the same as session 'test session' (G2P00004)
        """
        self.login_user()

        curation_to_update = {
            "json_data": {
                "allelic_requirement": "",
                "confidence": "",
                "cross_cutting_modifier": [],
                "disease": {
                    "cross_references": [],
                    "disease_name": ""
                    },
                "locus": "CEP290",
                "mechanism_evidence": [],
                "mechanism_synopsis": [],
                "molecular_mechanism": {
                    "name": "",
                    "support": ""
                    },
                "panels": [],
                "phenotypes": [],
                "private_comment": "",
                "public_comment": "",
                "publications": [],
                "session_name": "test session SRY",
                "variant_consequences": [],
                "variant_descriptions": [],
                "variant_types": []
            }
        }

        response = self.client.put(
            self.url_update_curation_2,
            curation_to_update,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

        response_data = response.json()
        self.assertEqual(response_data["error"], "Data already under curation. Please check session 'test session'")
