from django.test import TestCase
from django.urls import reverse
from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken
from gene2phenotype_app.models import User, CurationData

class LGDAddCurationEndpoint(TestCase):
    """
        Test endpoint to add curation
    """
    fixtures = ["gene2phenotype_app/fixtures/user_panels.json"]

    def setUp(self):
        self.url_add_curation = reverse("add_curation_data")

    def test_add_curation_success(self):
        """
            Test successful call to add curation endpoint
        """
        # Define the complex data structure
        curation_to_add = {
            "json_data": {
                "allelic_requirement": "biallelic_autosomal",
                "confidence": "limited",
                "cross_cutting_modifier": [
                    "potential secondary finding"
                ],
                "disease": {
                    "cross_references": [
                        {
                            "disease_name": "bardet-biedl syndrome",
                            "identifier": "615991",
                            "original_disease_name": "BARDET-BIEDL SYNDROME 14",
                            "source": "OMIM"
                        }
                    ],
                    "disease_name": "CEP290-related bardet-biedl syndrome"
                },
                "locus": "CEP290",
                "mechanism_evidence": [
                    {
                        "description": "test comment",
                        "evidence_types": [
                            {
                                "primary_type": "Rescue",
                                "secondary_type": [
                                    "Patient Cells"
                                ]
                            }
                        ],
                        "pmid": "1"
                    }
                ],
                "mechanism_synopsis": {
                    "name": "destabilising LOF",
                    "support": "inferred"
                },
                "molecular_mechanism": {
                    "name": "loss of function",
                    "support": "evidence"
                },
                "panels": [
                    "Developmental disorders"
                ],
                "phenotypes": [
                    {
                        "hpo_terms": [
                            {
                                "accession": "HP:0012372",
                                "term": "Abnormal eye morphology"
                            }
                        ],
                        "pmid": "1",
                        "summary": "test comment"
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
                        "year": 1975
                    }
                ],
                "session_name": "unit test session",
                "variant_consequences": [
                    {
                        "support": "inferred",
                        "variant_consequence": "altered_gene_product_level"
                    }
                ],
                "variant_descriptions": [
                    {
                        "description": "test description",
                        "publication": "1"
                    }
                ],
                "variant_types": [
                    {
                        "comment": "test comment",
                        "de_novo": True,
                        "inherited": True,
                        "nmd_escape": False,
                        "primary_type": "protein_changing",
                        "secondary_type": "missense_variant",
                        "supporting_papers": [
                            "1"
                        ],
                        "unknown_inheritance": False
                    }
                ]
            }
        }

        # Login
        user = User.objects.get(email="user5@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        # Authenticate by setting cookie on the test client
        self.client.cookies[settings.SIMPLE_JWT['AUTH_COOKIE']] = access_token

        response = self.client.post(self.url_add_curation, curation_to_add, content_type="application/json")
        self.assertEqual(response.status_code, 200)

        response_data = response.json()
        self.assertEqual(response_data["message"], "Data saved successfully for session name 'unit test session'")

        curation_entries = CurationData.objects.filter(session_name="unit test session")
        self.assertEqual(len(curation_entries), 1)
