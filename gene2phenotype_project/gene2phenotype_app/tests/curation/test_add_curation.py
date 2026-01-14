from django.test import TestCase
from django.urls import reverse
from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken
from gene2phenotype_app.models import User, CurationData


class LGDAddCurationEndpoint(TestCase):
    """
    Test endpoint to add curation
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
        self.url_add_curation = reverse("add_curation_data")

    def login_user(self):
        self.user = User.objects.get(email="user5@test.ac.uk")
        refresh = RefreshToken.for_user(self.user)
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = str(
            refresh.access_token
        )

    def test_add_curation_success(self):
        """
        Test successful call to add curation endpoint
        """
        self.login_user()

        curation_to_add = {
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
                "phenotypes": [
                    {
                        "hpo_terms": [
                            {
                                "accession": "HP:0012372",
                                "term": "Abnormal eye morphology",
                            }
                        ],
                        "pmid": "1",
                        "summary": "test comment",
                    }
                ],
                "private_comment": "test comment",
                "public_comment": "test comment",
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
                "session_name": "unit test session",
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

        response = self.client.post(
            self.url_add_curation, curation_to_add, content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)

        response_data = response.json()
        self.assertEqual(
            response_data["message"],
            "Data saved successfully for session name 'unit test session'",
        )

        curation_entries = CurationData.objects.filter(session_name="unit test session")
        self.assertEqual(len(curation_entries), 1)

    def test_add_automatic_curation_success(self):
        """
        Test successful call to add an automatic curation draft
        """
        self.login_user()

        curation_to_add = {
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
                    "disease_name": "CEP290-related bardet-biedl syndrome test",
                },
                "locus": "CEP290",
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
                "phenotypes": [
                    {
                        "hpo_terms": [
                            {
                                "accession": "HP:0012372",
                                "term": "Abnormal eye morphology",
                            }
                        ],
                        "pmid": "1",
                        "summary": "test comment",
                    }
                ],
                "private_comment": "test comment",
                "public_comment": "test comment",
                "extra_comment": "",
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
                "session_name": "test automatic session",
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
            },
            "status": "automatic",
        }

        response = self.client.post(
            self.url_add_curation, curation_to_add, content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)

        response_data = response.json()
        self.assertEqual(
            response_data["message"],
            "Data saved successfully for session name 'test automatic session'",
        )

        curation_entries = CurationData.objects.filter(
            session_name="test automatic session"
        )
        self.assertEqual(len(curation_entries), 1)
        self.assertEqual(curation_entries[0].status, "automatic")

    def test_add_curation_existing_curation(self):
        """
        Test call to add curation endpoint with existing curation
        """
        self.login_user()

        curation_to_add = {
            "json_data": {
                "allelic_requirement": "",
                "confidence": "",
                "cross_cutting_modifier": [],
                "disease": {"cross_references": [], "disease_name": ""},
                "locus": "CEP290",
                "mechanism_evidence": [],
                "mechanism_synopsis": [],
                "molecular_mechanism": {"name": "", "support": ""},
                "panels": [],
                "phenotypes": [],
                "private_comment": "",
                "public_comment": "",
                "publications": [],
                "session_name": "unit test session",
                "variant_consequences": [],
                "variant_descriptions": [],
                "variant_types": [],
            }
        }

        response = self.client.post(
            self.url_add_curation, curation_to_add, content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)

        response_data = response.json()
        self.assertEqual(
            response_data["error"],
            "Data already under curation. Please check session 'test session'",
        )

    def test_add_curation_duplicate_session_name(self):
        """
        Test adding a curation draft with existing session name
        """
        self.login_user()

        curation_to_add = {
            "json_data": {
                "allelic_requirement": "",
                "confidence": "",
                "cross_cutting_modifier": [],
                "disease": {
                    "cross_references": [],
                    "disease_name": "SRY-related syndrome",
                },
                "locus": "SRY",
                "mechanism_evidence": [],
                "mechanism_synopsis": [],
                "molecular_mechanism": {"name": "", "support": ""},
                "panels": [],
                "phenotypes": [],
                "private_comment": "",
                "public_comment": "",
                "publications": [],
                "session_name": "test session SRY",
                "variant_consequences": [],
                "variant_descriptions": [],
                "variant_types": [],
            }
        }

        response = self.client.post(
            self.url_add_curation, curation_to_add, content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)

        response_data = response.json()
        self.assertEqual(
            response_data["error"],
            "Curation data with the session name 'test session SRY' already exists. Please change the session name and try again.",
        )

    def test_add_curation_unauthorised_panel(self):
        """
        Test call to add curation endpoint with unauthorised panel
        """
        self.login_user()

        curation_to_add = {
            "json_data": {
                "allelic_requirement": "",
                "confidence": "",
                "cross_cutting_modifier": [],
                "disease": {"cross_references": [], "disease_name": ""},
                "locus": "CEP290",
                "mechanism_evidence": [],
                "mechanism_synopsis": [],
                "molecular_mechanism": {"name": "", "support": ""},
                "panels": ["Demo"],
                "phenotypes": [],
                "private_comment": "",
                "public_comment": "",
                "publications": [],
                "session_name": "unit test session",
                "variant_consequences": [],
                "variant_descriptions": [],
                "variant_types": [],
            }
        }

        response = self.client.post(
            self.url_add_curation, curation_to_add, content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)

        response_data = response.json()
        self.assertEqual(
            response_data["error"],
            "You do not have permission to curate on these panels: 'Demo'",
        )

    def test_add_curation_invalid_request_body(self):
        """
        Test call to add curation endpoint with invalid request body
        """
        self.login_user()

        curation_to_add = {
            "json_data": {
                "locus": "CEP290",
                "disease": "CEP290-related bardet-biedl syndrome",
            }
        }

        response = self.client.post(
            self.url_add_curation, curation_to_add, content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)

        response_data = response.json()
        self.assertIn(
            "JSON data does not follow the required format.", response_data["error"]
        )

    def test_add_curation_empty_locus(self):
        """
        Test call to add curation endpoint with empty locus field
        """
        self.login_user()

        curation_to_add = {
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
                "session_name": "unit test session",
                "variant_consequences": [],
                "variant_descriptions": [],
                "variant_types": [],
            }
        }

        response = self.client.post(
            self.url_add_curation, curation_to_add, content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)

        response_data = response.json()
        self.assertEqual(
            response_data["error"],
            "To save a draft, the minimum requirement is a locus entry. Please save this draft with locus information",
        )

    def test_add_curation_old_locus(self):
        """
        Test call to add curation endpoint with an old gene symbol
        """
        self.login_user()

        curation_to_add = {
            "json_data": {
                "allelic_requirement": "",
                "confidence": "",
                "cross_cutting_modifier": [],
                "disease": {"cross_references": [], "disease_name": ""},
                "locus": "BETA-5",
                "mechanism_evidence": [],
                "mechanism_synopsis": [],
                "molecular_mechanism": {"name": "", "support": ""},
                "panels": [],
                "phenotypes": [],
                "private_comment": "",
                "public_comment": "",
                "publications": [],
                "session_name": "test old locus",
                "variant_consequences": [],
                "variant_descriptions": [],
                "variant_types": [],
            }
        }

        response = self.client.post(
            self.url_add_curation, curation_to_add, content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)

        curation_obj = CurationData.objects.get(session_name="test old locus")
        self.assertEqual("TUBB4A", curation_obj.gene_symbol)

    def test_add_curation_invalid_locus(self):
        """
        Test call to add curation endpoint with an invalid gene symbol
        """
        self.login_user()

        curation_to_add = {
            "json_data": {
                "allelic_requirement": "",
                "confidence": "",
                "cross_cutting_modifier": [],
                "disease": {"cross_references": [], "disease_name": ""},
                "locus": "BETA-INVALID",
                "mechanism_evidence": [],
                "mechanism_synopsis": [],
                "molecular_mechanism": {"name": "", "support": ""},
                "panels": [],
                "phenotypes": [],
                "private_comment": "",
                "public_comment": "",
                "publications": [],
                "session_name": "invalid locus session",
                "variant_consequences": [],
                "variant_descriptions": [],
                "variant_types": [],
            }
        }

        response = self.client.post(
            self.url_add_curation, curation_to_add, content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)

        response_data = response.json()
        self.assertEqual(
            response_data["error"],
            "Invalid gene 'BETA-INVALID'",
        )

    def test_add_curation_no_session_name(self):
        """
        Test adding a curation draft without a session name.
        """
        self.login_user()

        curation_to_add = {
            "json_data": {
                "allelic_requirement": "monoallelic_autosomal",
                "confidence": "strong",
                "cross_cutting_modifier": [],
                "disease": {
                    "cross_references": [],
                    "disease_name": "BAAT-related hypercholanemia familial",
                },
                "locus": "BAAT",
                "mechanism_evidence": [],
                "mechanism_synopsis": [],
                "molecular_mechanism": {"name": "", "support": ""},
                "panels": [],
                "phenotypes": [],
                "private_comment": "",
                "public_comment": "",
                "publications": [],
                "session_name": "",
                "variant_consequences": [],
                "variant_descriptions": [],
                "variant_types": [],
            }
        }

        response = self.client.post(
            self.url_add_curation, curation_to_add, content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)

        expected_response = {
            "message": "Data saved successfully for session name 'G2P00011'",
            "result": "G2P00011",
        }
        response_data = response.json()
        self.assertEqual(response_data, expected_response)
