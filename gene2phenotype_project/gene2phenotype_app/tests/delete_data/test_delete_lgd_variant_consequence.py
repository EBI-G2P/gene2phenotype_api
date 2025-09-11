from django.test import TestCase
from django.urls import reverse
from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken
from gene2phenotype_app.models import (
    User,
    LGDVariantGenccConsequence,
    LocusGenotypeDisease,
)


class LGDEditVariantConsequenceEndpoint(TestCase):
    """
    Test endpoint to delete variant consequence from a record (LGD)
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
        "gene2phenotype_app/fixtures/lgd_variant_consequence.json",
    ]

    def setUp(self):
        self.url_delete = reverse(
            "lgd_var_consequence", kwargs={"stable_id": "G2P00002"}
        )
        self.consequence_to_delete = {"variant_consequence": "absent gene product"}

    def test_invalid_delete(self):
        """
        Test deleting an invalid variant consequence from the record (LGD).
        Cannot delete a term that does not exist in G2P.
        """
        # Login
        user = User.objects.get(email="john@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        response = self.client.patch(
            self.url_delete,
            {"variant_consequence": "absent gene products"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 404)

        response_data = response.json()
        self.assertEqual(
            response_data["error"],
            "Invalid variant consequence 'absent gene products'",
        )

    def test_delete_unlinked_variant_consequence(self):
        """
        Test deleting an invalid variant consequence from the record (LGD).
        Cannot delete a consequence if it is not linked to the record.
        """
        # Login
        user = User.objects.get(email="john@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        response = self.client.patch(
            self.url_delete,
            {"variant_consequence": "altered gene product structure"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 404)

        response_data = response.json()
        self.assertEqual(
            response_data["error"],
            "Could not find variant consequence 'altered gene product structure' for ID 'G2P00002'",
        )

    def test_delete_non_superuser(self):
        """
        Test deleting the variant consequence for non super user.
        Only super users can delete variant consequences.
        """
        # Login
        user = User.objects.get(email="mary@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        response = self.client.patch(
            self.url_delete,
            self.consequence_to_delete,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)

        response_data = response.json()
        self.assertEqual(
            response_data["error"], "You do not have permission to perform this action."
        )

    def test_delete_no_permission(self):
        """
        Test deleting the variant consequence for user without permission to edit the record.
        """
        # Login
        user = User.objects.get(email="sofia@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        response = self.client.patch(
            self.url_delete,
            self.consequence_to_delete,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)

        response_data = response.json()
        self.assertEqual(
            response_data["error"], "No permission to update record 'G2P00002'"
        )

    def test_delete_empty_input(self):
        """
        Test deleting the variant consequence for empty input.
        """
        # Login
        user = User.objects.get(email="john@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
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
            "Empty variant consequence. Please provide the 'variant_consequence'.",
        )

    def test_lgd_variant_consequence_delete(self):
        """
        Test deleting the variant consequence from the record (LGD)
        """
        # Login
        user = User.objects.get(email="john@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        # Check LGD-variant consequence before deletion
        lgd_consequence_list = LGDVariantGenccConsequence.objects.filter(
            lgd__stable_id__stable_id="G2P00002", is_deleted=0
        )
        self.assertEqual(len(lgd_consequence_list), 1)

        response = self.client.patch(
            self.url_delete,
            self.consequence_to_delete,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)

        # Check deleted LGD-variant consequence
        lgd_deleted_consequence = LGDVariantGenccConsequence.objects.filter(
            lgd__stable_id__stable_id="G2P00002", is_deleted=1
        )
        self.assertEqual(len(lgd_deleted_consequence), 1)

        # Test the history tables
        history_records = LGDVariantGenccConsequence.history.all()
        self.assertEqual(len(history_records), 1)
        self.assertEqual(history_records[0].is_deleted, 1)
        history_records_lgd = LocusGenotypeDisease.history.all()
        self.assertEqual(len(history_records_lgd), 0)
