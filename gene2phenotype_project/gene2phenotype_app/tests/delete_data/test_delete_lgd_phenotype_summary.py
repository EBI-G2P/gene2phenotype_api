from django.test import TestCase
from django.urls import reverse
from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken
from gene2phenotype_app.models import (User, LGDPhenotypeSummary, LocusGenotypeDisease)


class LGDDeletePhenotypeSummary(TestCase):
    """
    Test endpoint to delete phenotype summary from a record (LGD)
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
        "gene2phenotype_app/fixtures/lgd_phenotype.json",
        "gene2phenotype_app/fixtures/lgd_phenotype_summary.json",
        "gene2phenotype_app/fixtures/source.json",
    ]

    def setUp(self):
        self.url_delete = reverse("lgd_phenotype_summary", kwargs={"stable_id": "G2P00002"})
        self.summary_to_delete = {"summary": "Abnormality of connective tissue and of the musculoskeletal system"}

    def test_invalid_delete(self):
        """
        Test deleting an invalid phenotype summary from the record (LGD).
        The provided summary is not linked to the record.
        """
        # Login
        user = User.objects.get(email="john@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        response = self.client.patch(
            self.url_delete,
            {"summary": "summary"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

        response_data = response.json()
        self.assertEqual(
            response_data["error"], "Phenotype summary is not associated with 'G2P00002'"
        )

    def test_invalid_input(self):
        """
        Test deleting a phenotype summary when providing empty summary.
        """
        # Login
        user = User.objects.get(email="john@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        response = self.client.patch(
            self.url_delete,
            {"summary": ""},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

        response_data = response.json()
        self.assertEqual(
            response_data["error"],
            "Please provide valid phenotype summary.",
        )

    def test_delete_no_permission(self):
        """
        Test deleting the phenotype summary for non super user.
        Only super users can delete phenotype summaries.
        """
        # Login
        user = User.objects.get(email="mary@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        response = self.client.patch(
            self.url_delete,
            self.summary_to_delete,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)

        response_data = response.json()
        self.assertEqual(
            response_data["error"], "You do not have permission to perform this action."
        )

    def test_delete_no_permission_2(self):
        """
        Test deleting the phenotype summary for user without permission to edit the record.
        """
        # Login
        user = User.objects.get(email="sofia@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        response = self.client.patch(
            self.url_delete,
            self.summary_to_delete,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)

        response_data = response.json()
        self.assertEqual(
            response_data["error"], "No permission to update record 'G2P00002'"
        )

    def test_lgd_phenotype_summary_delete(self):
        """
        Test successfully deleting the phenotype summary from the record (LGD)
        """
        # Login
        user = User.objects.get(email="john@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        # Check LGD-phenotype summary before deletion
        lgd_phenotype_summaries = LGDPhenotypeSummary.objects.filter(
            lgd__stable_id__stable_id="G2P00002", is_deleted=0
        )
        self.assertEqual(len(lgd_phenotype_summaries), 1)

        response = self.client.patch(
            self.url_delete,
            self.summary_to_delete,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)

        # Check deleted LGD-phenotype summary
        lgd_deleted_phenotypes = LGDPhenotypeSummary.objects.filter(
            lgd__stable_id__stable_id="G2P00002", is_deleted=1
        )
        self.assertEqual(len(lgd_deleted_phenotypes), 1)

        # Check remaining LGD-phenotype summaries
        lgd_phenotypes = LGDPhenotypeSummary.objects.filter(
            lgd__stable_id__stable_id="G2P00002", is_deleted=0
        )
        self.assertEqual(len(lgd_phenotypes), 0)

        # Test the LGDPhenotype history table
        history_records = LGDPhenotypeSummary.history.all()
        self.assertEqual(len(history_records), 1)
        self.assertEqual(history_records[0].is_deleted, 1)

        # Check the record date update triggered history
        lgd_history = LocusGenotypeDisease.history.all()
        self.assertEqual(len(lgd_history), 1)