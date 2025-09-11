from django.test import TestCase
from django.urls import reverse
from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken
from gene2phenotype_app.models import (
    User,
    LGDVariantType,
    LocusGenotypeDisease,
)


class LGDEditVariantTypesEndpoint(TestCase):
    """
    Test endpoint to delete variant types from a record (LGD)
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
        "gene2phenotype_app/fixtures/lgd_variant_type.json",
    ]

    def setUp(self):
        self.url_delete = reverse(
            "lgd_variant_type", kwargs={"stable_id": "G2P00002"}
        )

    def test_invalid_delete(self):
        """
        Test deleting an invalid variant type from the record (LGD).
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
            {"secondary_type": "stopp_gained"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 404)

        response_data = response.json()
        self.assertEqual(
            response_data["error"],
            "Invalid variant type 'stopp_gained'",
        )

    def test_delete_unlinked_variant_type(self):
        """
        Test deleting an invalid variant type from the record (LGD).
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
            {"secondary_type": "stop_gained"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 404)

        response_data = response.json()
        self.assertEqual(
            response_data["error"],
            "Could not find variant type 'stop_gained' for ID 'G2P00002'",
        )

    def test_delete_non_superuser(self):
        """
        Test deleting the variant type for non super user.
        Only super users can delete variant types.
        """
        # Login
        user = User.objects.get(email="mary@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        # Authenticate by setting cookie on the test client
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        response = self.client.patch(
            self.url_delete,
            {"secondary_type": "intron_variant"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)

        response_data = response.json()
        self.assertEqual(
            response_data["error"], "You do not have permission to perform this action."
        )

    def test_delete_no_permission(self):
        """
        Test deleting the variant type for user without permission to edit the record.
        """
        # Login
        user = User.objects.get(email="sofia@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        # Authenticate by setting cookie on the test client
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        response = self.client.patch(
            self.url_delete,
            {"secondary_type": "intron_variant"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)

        response_data = response.json()
        self.assertEqual(
            response_data["error"], "No permission to update record 'G2P00002'"
        )

    def test_delete_empty_input(self):
        """
        Test deleting the variant type for empty input.
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
            "Empty variant type. Please provide the 'secondary_type'.",
        )

    def test_lgd_variant_type_delete(self):
        """
        Test deleting the variant type from the record (LGD)
        """
        # Login
        user = User.objects.get(email="john@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        # Authenticate by setting cookie on the test client
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        # Check LGD-variant types before deletion
        lgd_variant_type_list = LGDVariantType.objects.filter(
            lgd__stable_id__stable_id="G2P00002", is_deleted=0
        )
        self.assertEqual(len(lgd_variant_type_list), 2)

        response = self.client.patch(
            self.url_delete,
            {"secondary_type": "intron_variant"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)

        # Check deleted LGD-variant types
        lgd_deleted_variants = LGDVariantType.objects.filter(
            lgd__stable_id__stable_id="G2P00002", is_deleted=1
        )
        self.assertEqual(len(lgd_deleted_variants), 1)

        # Check remaining LGD-variant types
        lgd_variants = LGDVariantType.objects.filter(
            lgd__stable_id__stable_id="G2P00002", is_deleted=0
        )
        self.assertEqual(len(lgd_variants), 1)

        # Test the history tables
        history_records = LGDVariantType.history.all()
        self.assertEqual(len(history_records), 1)
        self.assertEqual(history_records[0].is_deleted, 1)
        history_records_lgd = LocusGenotypeDisease.history.all()
        self.assertEqual(len(history_records_lgd), 0)
