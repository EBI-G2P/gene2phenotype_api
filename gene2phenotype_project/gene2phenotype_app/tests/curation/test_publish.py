from django.test import TestCase
from django.urls import reverse
from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken
from gene2phenotype_app.models import (
    User,
    LocusGenotypeDisease,
    LGDComment,
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
        "gene2phenotype_app/fixtures/disease_external.json",
        "gene2phenotype_app/fixtures/gene_disease.json",
    ]

    def setUp(self):
        self.url_add_curation = reverse("add_curation_data")

    def login_user(self):
        self.user = User.objects.get(email="user5@test.ac.uk")
        refresh = RefreshToken.for_user(self.user)
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = str(
            refresh.access_token
        )

    def login_as(self, email):
        self.user = User.objects.get(email=email)
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

    def get_publishable_curation_payload(
        self,
        session_name="Test B",
        panels=None,
        disease_name="SRY-related 46,xx sex reversal",
    ):
        return {
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
                    "disease_name": disease_name,
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
                "panels": panels or ["Developmental disorders"],
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
                "session_name": session_name,
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
                        "primary_type": "protein_changing",
                        "secondary_type": "missense_variant",
                        "supporting_papers": ["1"],
                        "unknown_inheritance": False,
                    }
                ],
            }
        }

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
        data_to_add = self.get_publishable_curation_payload()

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
            "Record 'G2P00017' published successfully",
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

        lgd_comments = LGDComment.objects.filter(lgd=lgd_obj, is_deleted=0)
        self.assertEqual(len(lgd_comments), 2)
        self.assertFalse(
            lgd_comments.filter(comment__contains="reviewed by").exists()
        )

    def test_publish_junior_curator_record_adds_review_comment(self):
        """
        Test publishing a junior curator draft as a senior curator adds the
        private review comment.
        """
        self.login_junior_user()
        data_to_add = self.get_publishable_curation_payload(
            session_name="Test junior review publish",
            disease_name="SRY-related 46,xx sex reversal junior review",
        )

        response = self.client.post(
            self.url_add_curation, data_to_add, content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)

        response_data = response.json()
        self.assertEqual(
            response_data["message"],
            "Data saved successfully for session name 'Test junior review publish'",
        )

        self.login_user()
        url_publish = reverse(
            "publish_record", kwargs={"stable_id": response_data["result"]}
        )

        response_publish = self.client.post(
            url_publish, content_type="application/json"
        )
        self.assertEqual(response_publish.status_code, 201)
        response_data_publish = response_publish.json()
        self.assertEqual(
            response_data_publish["message"],
            "Record 'G2P00017' published successfully",
        )

        lgd_obj = LocusGenotypeDisease.objects.get(
            locus__name="SRY",
            disease__name="SRY-related 46,xx sex reversal junior review",
            genotype__value="monoallelic_Y_hemizygous",
            is_deleted=0,
        )

        lgd_comments = LGDComment.objects.filter(lgd=lgd_obj, is_deleted=0)
        self.assertEqual(len(lgd_comments), 3)

        review_comment = LGDComment.objects.get(
            lgd=lgd_obj,
            is_deleted=0,
            is_public=0,
            comment=(
                "Record created by Elisa Stevens and reviewed by Test User5."
            ),
        )
        self.assertEqual(review_comment.user.email, "user5@test.ac.uk")

    def test_publish_unauthorised_access(self):
        """
        Test publishing a record without authentication
        """
        url_publish = reverse("publish_record", kwargs={"stable_id": "G2P00010"})

        response_publish = self.client.post(
            url_publish, content_type="application/json"
        )
        self.assertEqual(response_publish.status_code, 401)

    def test_publish_success_when_user_owns_entry_without_panel_access(self):
        """
        Test publishing succeeds for the owner even when the draft panel
        is not in the user's panel assignments.
        """
        self.login_user()

        data_to_add = self.get_publishable_curation_payload(
            session_name="Test owner no panel",
            disease_name="SRY-related 46,xx sex reversal owner no panel",
        )

        response = self.client.post(
            self.url_add_curation, data_to_add, content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)

        stable_id = response.json()["result"]
        from gene2phenotype_app.models import CurationData

        curation_obj = CurationData.objects.get(stable_id__stable_id=stable_id)
        curation_obj.json_data["panels"] = ["Cancer disorders"]
        curation_obj.save(update_fields=["json_data"])

        url_publish = reverse("publish_record", kwargs={"stable_id": stable_id})

        response_publish = self.client.post(
            url_publish, content_type="application/json"
        )
        self.assertEqual(response_publish.status_code, 201)

    def test_publish_success_when_junior_owned_entry_panel_matches(self):
        """
        Test publishing succeeds for a non-junior user when the draft is owned
        by a junior curator and the user has access to the draft panel.
        """
        self.login_junior_user()

        data_to_add = self.get_publishable_curation_payload(
            session_name="Test junior match",
            panels=["Developmental disorders"],
            disease_name="SRY-related 46,xx sex reversal junior match",
        )

        response = self.client.post(
            self.url_add_curation, data_to_add, content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)

        stable_id = response.json()["result"]

        self.login_user()
        url_publish = reverse("publish_record", kwargs={"stable_id": stable_id})

        response_publish = self.client.post(
            url_publish, content_type="application/json"
        )
        self.assertEqual(response_publish.status_code, 201)

    def test_publish_not_found_when_junior_owned_entry_panel_does_not_match(self):
        """
        Test publishing is rejected when the draft is owned by a junior curator
        but the user has no access to the draft panel.
        """
        self.login_junior_user()

        data_to_add = self.get_publishable_curation_payload(
            session_name="Test junior no match",
            disease_name="SRY-related 46,xx sex reversal junior no match",
        )

        response = self.client.post(
            self.url_add_curation, data_to_add, content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)

        stable_id = response.json()["result"]
        from gene2phenotype_app.models import CurationData

        curation_obj = CurationData.objects.get(stable_id__stable_id=stable_id)
        curation_obj.json_data["panels"] = ["Cancer disorders"]
        curation_obj.save(update_fields=["json_data"])

        self.login_user()
        url_publish = reverse("publish_record", kwargs={"stable_id": stable_id})

        response_publish = self.client.post(
            url_publish, content_type="application/json"
        )
        self.assertEqual(response_publish.status_code, 404)

        response_data_publish = response_publish.json()
        self.assertEqual(
            response_data_publish["error"],
            f"Could not find 'Entry' for ID '{stable_id}'",
        )

    def test_publish_not_found_when_other_user_owns_non_junior_entry(self):
        """
        Test publishing is rejected when the draft is owned by another user
        who is not a junior curator.
        """
        self.login_as("john@test.ac.uk")

        url_publish = reverse("publish_record", kwargs={"stable_id": "G2P00004"})

        response_publish = self.client.post(
            url_publish, content_type="application/json"
        )
        self.assertEqual(response_publish.status_code, 404)

        response_data_publish = response_publish.json()
        self.assertEqual(
            response_data_publish["error"],
            "Could not find 'Entry' for ID 'G2P00004'",
        )

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

    def test_publish_old_record(self):
        """
        Test trying to publish a record that is the same as a deleted record
        """
        self.login_user()
        # Define the input data structure
        data_to_add = {
            "json_data": {
                "allelic_requirement": "biallelic_autosomal",
                "confidence": "limited",
                "cross_cutting_modifier": [],
                "disease": {
                    "cross_references": [],
                    "disease_name": "STRA6-related Griscelli Type 2",
                },
                "locus": "STRA6",
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
                "session_name": "Test publish old record",
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
            "Data saved successfully for session name 'Test publish old record'",
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
            "The locus, genotype, disease and molecular mechanism match an old record: 'G2P00003'",
        )

    def test_publish_record_junior_user(self):
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

    def test_publish_automatic_record(self):
        """
        Test trying to publish a record that was created automatically
        """
        self.login_user()

        # Prepare the URL to publish the record
        url_publish = reverse("publish_record", kwargs={"stable_id": "G2P00010"})

        # Call the endpoint to publish
        response_publish = self.client.post(
            url_publish, content_type="application/json"
        )
        self.assertEqual(response_publish.status_code, 400)

        response_data_publish = response_publish.json()
        self.assertEqual(
            response_data_publish["error"],
            "Cannot publish record 'G2P00010': status is 'automatic'. Please update the record before publishing.",
        )
