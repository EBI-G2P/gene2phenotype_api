from django.test import TestCase
from django.urls import reverse
from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken
from gene2phenotype_app.models import (
    User,
    LocusGenotypeDisease,
    LGDPublication,
    LGDPublicationComment,
)


class LGDAddCurationEndpoint(TestCase):
    """
    Test endpoint to publish a record
    """

    fixtures = [
        "gene2phenotype_app/fixtures/g2p_stable_id.json",
        "gene2phenotype_app/fixtures/user_panels.json",
        "gene2phenotype_app/fixtures/auth_groups.json",
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

    def login_user(self):
        self.user = User.objects.get(email="user5@test.ac.uk")
        refresh = RefreshToken.for_user(self.user)
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = str(
            refresh.access_token
        )

    def login_junior_user(self):
        self.user = User.objects.get(email="elisa@test.ac.uk")
        refresh = RefreshToken.for_user(self.user)
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = str(
            refresh.access_token
        )

    def test_publish_incorrect_genotype(self):
        """
        Test the curation endpoint when the genotype is incorrect for the gene.
        First, call the endpoint to add the curation data - it is possible to save the data
        even when the genotype is incorrect.
        And finally try to publish the data - it is not possible to publish the data.
        """
        self.login_user()
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

    def test_publish_invalid_disease(self):
        """
        Test the curation endpoint when the disease name is invalid.
        First, call the endpoint to add the curation data - it is possible to save the data
        even when the disease is invalid.
        And finally try to publish the data - it is not possible to publish the data.
        """
        self.login_user()
        # Define the input data structure
        data_to_add = {
            "json_data": {
                "allelic_requirement": "monoallelic_Y_hemizygous",
                "confidence": "refuted",
                "cross_cutting_modifier": [],
                "disease": {
                    "cross_references": [
                        {
                            "disease_name": "46,xx sex reversal",
                            "identifier": "MONDO:0100250",
                            "original_disease_name": "46,xx sex reversal",
                            "source": "Mondo",
                        }
                    ],
                    "disease_name": "SRY-related SRY-related 46,xx sex reversal",
                },
                "locus": "SRY",
                "mechanism_evidence": [],
                "mechanism_synopsis": [
                    {"name": "assembly-mediated GOF", "support": "inferred"}
                ],
                "molecular_mechanism": {
                    "name": "gain of function",
                    "support": "inferred",
                },
                "panels": ["Developmental disorders"],
                "phenotypes": [],
                "private_comment": "This is a private comment",
                "public_comment": "This a public comment",
                "publications": [
                    {
                        "affectedIndividuals": 2,
                        "ancestries": "test",
                        "authors": "Makar AB, McMartin KE, Palese M, Tephly TR.",
                        "comment": "test comment",
                        "consanguineous": "no",
                        "families": 2,
                        "pmid": "1",
                        "source": "G2P",
                        "title": "Formate assay in body fluids: application in methanol poisoning.",
                        "year": 1975,
                    }
                ],
                "session_name": "test invalid disease",
                "variant_consequences": [
                    {
                        "support": "inferred",
                        "variant_consequence": "decreased_gene_product_level",
                    }
                ],
                "variant_descriptions": [
                    {"description": "test variant description", "publication": "1"}
                ],
                "variant_types": [
                    {
                        "comment": "Important variant",
                        "de_novo": True,
                        "inherited": True,
                        "nmd_escape": True,
                        "primary_type": "protein_changing",
                        "secondary_type": "missense_variant",
                        "supporting_papers": ["1"],
                        "unknown_inheritance": False,
                    }
                ],
            }
        }

        response = self.client.post(
            self.url_add_curation, data_to_add, content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)

        response_data = response.json()
        self.assertEqual(
            response_data["message"],
            "Data saved successfully for session name 'test invalid disease'",
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
            "Invalid disease name 'SRY-related SRY-related 46,xx sex reversal'",
        )

    def test_publish_insufficient_publications(self):
        """
        Test the curation endpoint when the number of publications
        is not enough for the confidence value.
        """
        self.login_user()
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

    def test_publish_missing_data(self):
        """
        Test the curation endpoint without providing mandatory data.
        """
        self.login_user()
        # Define the input data structure
        data_to_add = {
            "json_data": {
                "allelic_requirement": "",
                "confidence": "definitive",
                "cross_cutting_modifier": ["potential secondary finding"],
                "disease": {
                    "cross_references": [],
                    "disease_name": "",
                },
                "locus": "SRY",
                "mechanism_evidence": [],
                "mechanism_synopsis": [],
                "molecular_mechanism": {
                    "name": "",
                    "support": "",
                },
                "panels": [],
                "phenotypes": [],
                "private_comment": "",
                "public_comment": "",
                "publications": [],
                "session_name": "Test mandatory data",
                "variant_consequences": [],
                "variant_descriptions": [],
                "variant_types": [],
            }
        }

        # Save the curation draft
        response = self.client.post(
            self.url_add_curation, data_to_add, content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)

        response_data = response.json()
        self.assertEqual(
            response_data["message"],
            "Data saved successfully for session name 'Test mandatory data'",
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
            "The following mandatory fields are missing: disease, publication, panel, allelic_requirement, molecular_mechanism, variant_consequences",
        )

    def test_publish_success(self):
        """
        Test successful call to publish a record
        """
        self.login_user()
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
            "Record 'G2P00010' published successfully",
        )

        # Check inserted data
        lgd_obj = LocusGenotypeDisease.objects.get(
            locus__name="SRY",
            disease__name="SRY-related 46,xx sex reversal",
            genotype__value="monoallelic_Y_hemizygous",
            is_deleted=0,
        )

        lgd_publications = LGDPublication.objects.filter(lgd=lgd_obj, is_deleted=0)
        self.assertEqual(len(lgd_publications), 1)

        lgd_publication_comments = LGDPublicationComment.objects.filter(
            lgd_publication=lgd_publications[0], is_deleted=0
        )
        self.assertEqual(len(lgd_publication_comments), 1)

    def test_publish_similar_record(self):
        """
        Test trying to publish a record that is too similar to already published record
        """
        self.login_user()
        # Define the input data structure
        data_to_add = {
            "json_data": {
                "allelic_requirement": "biallelic_autosomal",
                "confidence": "limited",
                "cross_cutting_modifier": ["potential secondary finding"],
                "disease": {
                    "cross_references": [],
                    "disease_name": "CEP290-related JOUBERT SYNDROME TYPE 5",
                },
                "locus": "CEP290",
                "mechanism_evidence": [],
                "mechanism_synopsis": [],
                "molecular_mechanism": {
                    "name": "undetermined",
                    "support": "inferred",
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
                "session_name": "Test C",
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

        # Save the curation draft
        response = self.client.post(
            self.url_add_curation, data_to_add, content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)

        response_data = response.json()
        self.assertEqual(
            response_data["message"],
            "Data saved successfully for session name 'Test C'",
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
            "Found similar record(s) with same locus, genotype and disease. Please check G2P ID(s) 'G2P00001'",
        )

    def test_publish_duplicate_record(self):
        """
        Test trying to publish a record that is already published
        """
        self.login_user()
        # Define the input data structure
        data_to_add = {
            "json_data": {
                "allelic_requirement": "biallelic_autosomal",
                "confidence": "limited",
                "cross_cutting_modifier": ["potential secondary finding"],
                "disease": {
                    "cross_references": [],
                    "disease_name": "CEP290-related JOUBERT SYNDROME TYPE 5",
                },
                "locus": "CEP290",
                "mechanism_evidence": [],
                "mechanism_synopsis": [],
                "molecular_mechanism": {
                    "name": "loss of function",
                    "support": "inferred",
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
                "session_name": "Test D",
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

        # Save the curation draft
        response = self.client.post(
            self.url_add_curation, data_to_add, content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)

        response_data = response.json()
        self.assertEqual(
            response_data["message"],
            "Data saved successfully for session name 'Test D'",
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
            "Found another record with same locus, genotype, disease and molecular mechanism. Please check G2P ID 'G2P00001'",
        )

    def test_publish_duplicate_record(self):
        """
        Test publishing a record for a 'junior curator' user
        """
        self.login_junior_user()
        # Define the input data structure
        data_to_add = {
            "json_data": {
                "allelic_requirement": "biallelic_autosomal",
                "confidence": "limited",
                "cross_cutting_modifier": ["potential secondary finding"],
                "disease": {
                    "cross_references": [],
                    "disease_name": "CEP290-related JOUBERT SYNDROME test",
                },
                "locus": "CEP290",
                "mechanism_evidence": [],
                "mechanism_synopsis": [],
                "molecular_mechanism": {
                    "name": "loss of function",
                    "support": "inferred",
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
                "session_name": "Test E",
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

        # Save the curation draft
        response = self.client.post(
            self.url_add_curation, data_to_add, content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)

        response_data = response.json()
        self.assertEqual(
            response_data["message"],
            "Data saved successfully for session name 'Test E'",
        )

        # Prepare the URL to publish the record
        url_publish = reverse(
            "publish_record", kwargs={"stable_id": response_data["result"]}
        )

        # Call the endpoint to publish
        response_publish = self.client.post(
            url_publish, content_type="application/json"
        )
        self.assertEqual(response_publish.status_code, 403)

        response_data_publish = response_publish.json()
        self.assertEqual(
            response_data_publish["detail"],
            "You do not have permission to perform this action.",
        )
