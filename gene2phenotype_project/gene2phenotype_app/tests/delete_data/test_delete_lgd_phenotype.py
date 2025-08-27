from django.test import TestCase
from django.urls import reverse
from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken
from gene2phenotype_app.models import User, LGDPhenotype


class LGDDeletePhenotype(TestCase):
    """
    Test endpoint to delete phenotypes from a record (LGD)
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
        "gene2phenotype_app/fixtures/source.json",
    ]

    def setUp(self):
        self.url_delete = reverse("lgd_phenotype", kwargs={"stable_id": "G2P00002"})

    def test_invalid_delete(self):
        """
        Test deleting an invalid phenotype from the record (LGD).
        Cannot delete a phenotype that does not exist in G2P.
        """
        # Login
        user = User.objects.get(email="john@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        # Authenticate by setting cookie on the test client
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        response = self.client.patch(
            self.url_delete,
            {"accession": "HP:0033128"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 404)

        response_data = response.json()
        self.assertEqual(
            response_data["error"], "Cannot find phenotype for accession 'HP:0033128'"
        )

    def test_delete_unlinked_phenotype(self):
        """
        Test deleting a phenotype that is not linked to the record (LGD).
        """
        # Login
        user = User.objects.get(email="john@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        # Authenticate by setting cookie on the test client
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        response = self.client.patch(
            self.url_delete,
            {"accession": "HP:0000118"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 404)

        response_data = response.json()
        self.assertEqual(
            response_data["error"],
            "Could not find phenotype 'HP:0000118' for ID 'G2P00002'",
        )

    def test_delete_non_superuser(self):
        """
        Test deleting the phenotype for non super user.
        Only super users can delete phenotypes.
        """
        # Login
        user = User.objects.get(email="mary@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        # Authenticate by setting cookie on the test client
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        response = self.client.patch(
            self.url_delete,
            {"accession": "HP:0003549"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)

        response_data = response.json()
        self.assertEqual(
            response_data["error"], "You do not have permission to perform this action."
        )

    def test_delete_no_permission(self):
        """
        Test deleting the phenotype for user without permission to edit the record.
        """
        # Login
        user = User.objects.get(email="sofia@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        # Authenticate by setting cookie on the test client
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        response = self.client.patch(
            self.url_delete,
            {"accession": "HP:0003549"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)

        response_data = response.json()
        self.assertEqual(
            response_data["error"], "No permission to update record 'G2P00002'"
        )

    def test_lgd_phenotype_delete(self):
        """
        Test deleting the phenotype from the record (LGD)
        """
        # Login
        user = User.objects.get(email="john@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        # Authenticate by setting cookie on the test client
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        # Check LGD-phenotypes before deletion
        lgd_phenotypes = LGDPhenotype.objects.filter(
            lgd__stable_id__stable_id="G2P00002", is_deleted=0
        )
        self.assertEqual(len(lgd_phenotypes), 3)

        response = self.client.patch(
            self.url_delete,
            {"accession": "HP:0003549"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)

        # Check deleted LGD-phenotype
        lgd_deleted_phenotypes = LGDPhenotype.objects.filter(
            lgd__stable_id__stable_id="G2P00002", is_deleted=1
        )
        self.assertEqual(len(lgd_deleted_phenotypes), 1)

        # Check remaining LGD-phenotypes
        lgd_phenotypes = LGDPhenotype.objects.filter(
            lgd__stable_id__stable_id="G2P00002", is_deleted=0
        )
        self.assertEqual(len(lgd_phenotypes), 2)

        # Test the LGDPhenotype history table
        history_records = LGDPhenotype.history.all()
        self.assertEqual(len(history_records), 1)
        self.assertEqual(history_records[0].is_deleted, 1)
