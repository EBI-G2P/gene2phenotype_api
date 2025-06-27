from django.test import TestCase
from django.urls import reverse
from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken
from gene2phenotype_app.models import (
    User,
    G2PStableID,
    LocusGenotypeDisease,
    LGDVariantType,
    LGDVariantTypeComment,
    LGDPublication,
)


class LGDEditPublicationsEndpoint(TestCase):
    """
    Test endpoint to merge records
    """

    fixtures = [
        "gene2phenotype_app/fixtures/attribs.json",
        "gene2phenotype_app/fixtures/cv_molecular_mechanism.json",
        "gene2phenotype_app/fixtures/disease.json",
        "gene2phenotype_app/fixtures/g2p_stable_id.json",
        "gene2phenotype_app/fixtures/lgd_mechanism_evidence.json",
        "gene2phenotype_app/fixtures/lgd_mechanism_synopsis.json",
        "gene2phenotype_app/fixtures/lgd_panel.json",
        "gene2phenotype_app/fixtures/locus_genotype_disease.json",
        "gene2phenotype_app/fixtures/locus.json",
        "gene2phenotype_app/fixtures/publication.json",
        "gene2phenotype_app/fixtures/sequence.json",
        "gene2phenotype_app/fixtures/user_panels.json",
        "gene2phenotype_app/fixtures/ontology_term.json",
        "gene2phenotype_app/fixtures/source.json",
        "gene2phenotype_app/fixtures/lgd_publication.json",
        "gene2phenotype_app/fixtures/lgd_phenotype.json",
        "gene2phenotype_app/fixtures/lgd_variant_consequence.json",
        "gene2phenotype_app/fixtures/lgd_variant_type.json",
        "gene2phenotype_app/fixtures/lgd_variant_type_comment.json",
    ]

    def test_merge_invalid_ids(self):
        """
        Test merging invalid G2P IDs
        """
        url_merge = reverse("merge_records")

        records_to_merge = [{"g2p_ids": ["G2P11111"], "final_g2p_id": "G2P11113"}]

        # Login
        user = User.objects.get(email="user5@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        # Authenticate by setting cookie on the test client
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        response = self.client.post(
            url_merge, records_to_merge, content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)

        response_data = response.json()
        expected_error = [
            {"error": "Invalid G2P record G2P11113"},
            {"error": "Invalid G2P record G2P11111"},
        ]
        self.assertEqual(response_data["error"], expected_error)

    def test_no_permission(self):
        """
        Test merging records without permission
        """
        url_merge = reverse("merge_records")

        records_to_merge = [{"g2p_ids": ["G2P00001"], "final_g2p_id": "G2P00002"}]

        # Login
        user = User.objects.get(email="user1@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        # Authenticate by setting cookie on the test client
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        response = self.client.post(
            url_merge, records_to_merge, content_type="application/json"
        )
        self.assertEqual(response.status_code, 403)

    def test_invalid_input_format(self):
        """
        Test merging records with an invalid input format
        """
        url_merge = reverse("merge_records")

        records_to_merge = {"g2p_ids": ["G2P11111"], "final_g2p_id": "G2P11113"}

        # Login
        user = User.objects.get(email="user5@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        # Authenticate by setting cookie on the test client
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        response = self.client.post(
            url_merge, records_to_merge, content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)

        response_data = response.json()
        self.assertEqual(
            response_data["error"],
            "Request should be a list containing the records to merge",
        )

    def test_merge_different_genes(self):
        """
        Test merging records with different genes
        """
        url_merge = reverse("merge_records")

        records_to_merge = [{"g2p_ids": ["G2P00001"], "final_g2p_id": "G2P00002"}]

        # Login
        user = User.objects.get(email="user5@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        # Authenticate by setting cookie on the test client
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        response = self.client.post(
            url_merge, records_to_merge, content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)

        response_data = response.json()
        expected_error = [
            {"error": "Cannot merge records G2P00002 and G2P00001 with different genes"}
        ]
        self.assertEqual(response_data["error"], expected_error)

    def test_merge_records(self):
        """
        Test merging two records
        """
        url_merge = reverse("merge_records")

        records_to_merge = [{"g2p_ids": ["G2P00002"], "final_g2p_id": "G2P00006"}]

        # Login
        user = User.objects.get(email="user5@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        # Authenticate by setting cookie on the test client
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        response = self.client.post(
            url_merge, records_to_merge, content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)

        response_data = response.json()
        self.assertEqual(
            response_data["merged_records"], [["G2P00002 merged into G2P00006"]]
        )

        # Test merged records
        deleted_stable_id_obj = G2PStableID.objects.get(stable_id="G2P00002")
        self.assertEqual(deleted_stable_id_obj.is_live, False)
        self.assertEqual(deleted_stable_id_obj.is_deleted, 1)
        self.assertEqual(deleted_stable_id_obj.comment, "Merged into G2P00006")
        stable_id_obj = G2PStableID.objects.get(stable_id="G2P00006")
        self.assertEqual(stable_id_obj.is_live, True)
        lgd_obj = LocusGenotypeDisease.objects.get(
            stable_id=stable_id_obj.id, is_deleted=0
        )
        # Check if all variant types were merged correctly
        lgd_variant_type_list = LGDVariantType.objects.filter(lgd=lgd_obj.id)
        self.assertEqual(len(lgd_variant_type_list), 3)
        for variant_type in lgd_variant_type_list:
            if (
                variant_type.publication.id == 1
                and variant_type.variant_type_ot.term == "intron_variant"
            ):
                variant_type_comment_list = LGDVariantTypeComment.objects.filter(
                    lgd_variant_type=variant_type.id
                )
                self.assertEqual(
                    variant_type_comment_list[0].comment,
                    "Recurrent c.340C>T; other variant",
                )
        # Count the number of publications
        lgd_publication_list = LGDPublication.objects.filter(lgd=lgd_obj.id)
        self.assertEqual(len(lgd_publication_list), 4)
