from django.test import TestCase
from django.urls import reverse
from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken
from gene2phenotype_app.models import (
    User,
    LGDCrossCuttingModifier,
    LocusGenotypeDisease,
)


class LGDEditCCMEndpoint(TestCase):
    """
    Test endpoint to delete cross cutting modifier from a record (LGD)
    """

    fixtures = [
        "gene2phenotype_app/fixtures/attribs.json",
        "gene2phenotype_app/fixtures/cv_molecular_mechanism.json",
        "gene2phenotype_app/fixtures/disease.json",
        "gene2phenotype_app/fixtures/g2p_stable_id.json",
        "gene2phenotype_app/fixtures/lgd_panel.json",
        "gene2phenotype_app/fixtures/locus_genotype_disease.json",
        "gene2phenotype_app/fixtures/locus.json",
        "gene2phenotype_app/fixtures/publication.json",
        "gene2phenotype_app/fixtures/sequence.json",
        "gene2phenotype_app/fixtures/user_panels.json",
        "gene2phenotype_app/fixtures/ontology_term.json",
        "gene2phenotype_app/fixtures/source.json",
        "gene2phenotype_app/fixtures/lgd_publication.json",
        "gene2phenotype_app/fixtures/lgd_cross_cutting_modifier.json",
    ]

    def setUp(self):
        self.url_delete = reverse(
            "lgd_cross_cutting_modifier", kwargs={"stable_id": "G2P00002"}
        )

    def test_invalid_delete(self):
        """
        Test deleting an invalid cross cutting modifier from the record (LGD).
        Cannot delete a term that does not exist in G2P.
        """
        # Login
        user = User.objects.get(email="john@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        # Authenticate by setting cookie on the test client
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        response = self.client.patch(
            self.url_delete,
            {"term": "typically de novos"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 404)

        response_data = response.json()
        self.assertEqual(
            response_data["error"],
            "Invalid cross cutting modifier 'typically de novos'",
        )

    def test_invalid_delete_2(self):
        """
        Test deleting an invalid cross cutting modifier from the record (LGD).
        Cannot delete a term if it is not linked to the record.
        """
        # Login
        user = User.objects.get(email="john@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        # Authenticate by setting cookie on the test client
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        response = self.client.patch(
            self.url_delete,
            {"term": "typically mosaic"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

        response_data = response.json()
        self.assertEqual(
            response_data["error"],
            "Could not find cross cutting modifier 'typically mosaic' for ID 'G2P00002'",
        )

    def test_delete_no_permission(self):
        """
        Test deleting the cross cutting modifier for non super user.
        Only super users can delete cross cutting modifiers.
        """
        # Login
        user = User.objects.get(email="mary@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        # Authenticate by setting cookie on the test client
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        response = self.client.patch(
            self.url_delete,
            {"term": "typically de novo"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)

        response_data = response.json()
        self.assertEqual(
            response_data["error"], "You do not have permission to perform this action."
        )

    def test_delete_no_permission_2(self):
        """
        Test deleting the cross cutting modifier for user without permission to edit the record.
        """
        # Login
        user = User.objects.get(email="sofia@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        # Authenticate by setting cookie on the test client
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        response = self.client.patch(
            self.url_delete,
            {"term": "typically de novo"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)

        response_data = response.json()
        self.assertEqual(
            response_data["error"], "No permission to update record 'G2P00002'"
        )

    def test_delete_empty_input(self):
        """
        Test deleting the cross cutting modifier for empty input.
        """
        # Login
        user = User.objects.get(email="john@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        # Authenticate by setting cookie on the test client
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        response = self.client.patch(
            self.url_delete,
            {},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

        response_data = response.json()
        self.assertEqual(
            response_data["error"],
            "Empty cross cutting modifier. Please provide the 'term'.",
        )

    def test_lgd_ccm_delete(self):
        """
        Test deleting the cross cutting modifier from the record (LGD)
        """
        # Login
        user = User.objects.get(email="john@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        # Authenticate by setting cookie on the test client
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        # Check LGD-cross cutting modifiers before deletion
        lgd_ccm_list = LGDCrossCuttingModifier.objects.filter(
            lgd__stable_id__stable_id="G2P00002", is_deleted=0
        )
        self.assertEqual(len(lgd_ccm_list), 2)

        response = self.client.patch(
            self.url_delete,
            {"term": "typically de novo"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)

        # Check deleted LGD-cross cutting modifiers
        lgd_deleted_ccms = LGDCrossCuttingModifier.objects.filter(
            lgd__stable_id__stable_id="G2P00002", is_deleted=1
        )
        self.assertEqual(len(lgd_deleted_ccms), 1)

        # Check remaining LGD-cross cutting modifiers
        lgd_ccms = LGDCrossCuttingModifier.objects.filter(
            lgd__stable_id__stable_id="G2P00002", is_deleted=0
        )
        self.assertEqual(len(lgd_ccms), 1)

        # Test the history tables
        history_records = LGDCrossCuttingModifier.history.all()
        self.assertEqual(len(history_records), 1)
        self.assertEqual(history_records[0].is_deleted, 1)
        history_records_lgd = LocusGenotypeDisease.history.all()
        self.assertEqual(len(history_records_lgd), 1)
