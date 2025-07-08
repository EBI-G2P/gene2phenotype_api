from django.test import TestCase
from django.urls import reverse
from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken
from gene2phenotype_app.models import User, LGDPublication


class LGDDeletePublication(TestCase):
    """
    Test endpoint to delete a publication from a record (LGD)
    """

    fixtures = [
        "gene2phenotype_app/fixtures/attribs.json",
        "gene2phenotype_app/fixtures/cv_molecular_mechanism.json",
        "gene2phenotype_app/fixtures/disease.json",
        "gene2phenotype_app/fixtures/g2p_stable_id.json",
        "gene2phenotype_app/fixtures/g2p_stable_id.json",
        "gene2phenotype_app/fixtures/cv_molecular_mechanism.json",
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
        "gene2phenotype_app/fixtures/lgd_comment.json",
        "gene2phenotype_app/fixtures/lgd_phenotype.json",
        "gene2phenotype_app/fixtures/lgd_phenotype_summary.json",
        "gene2phenotype_app/fixtures/lgd_variant_type.json",
        "gene2phenotype_app/fixtures/lgd_variant_type_comment.json",
        "gene2phenotype_app/fixtures/lgd_variant_type_description.json",
        "gene2phenotype_app/fixtures/lgd_variant_consequence.json",
    ]

    def setUp(self):
        self.url_delete = reverse("lgd_publication", kwargs={"stable_id": "G2P00002"})

    def test_delete_no_permission(self):
        """
        Test deleting the publication for non superuser
        """
        to_delete = {"pmid": 15214012}

        # Login
        user = User.objects.get(email="user3@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        # Authenticate by setting cookie on the test client
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        response = self.client.patch(
            self.url_delete, to_delete, content_type="application/json"
        )
        self.assertEqual(response.status_code, 403)

    def test_forbidden_delete(self):
        """
        Test deleting the publication for record with only one publication
        """
        url_no_delete = reverse("lgd_publication", kwargs={"stable_id": "G2P00001"})
        to_delete = {"pmid": 3897232}

        # Login
        user = User.objects.get(email="john@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        # Authenticate by setting cookie on the test client
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        response = self.client.patch(
            url_no_delete, to_delete, content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)

        response_data = response.json()
        self.assertEqual(
            response_data["error"],
            "Could not delete PMID '3897232' for ID 'G2P00001'",
        )

    def test_invalid_delete(self):
        """
        Test deleting an invalid publication from the record (LGD)
        """
        to_delete = {"pmid": 1}

        # Login
        user = User.objects.get(email="john@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        # Authenticate by setting cookie on the test client
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        response = self.client.patch(
            self.url_delete, to_delete, content_type="application/json"
        )
        self.assertEqual(response.status_code, 404)

        response_data = response.json()
        self.assertEqual(
            response_data["detail"], "No Publication matches the given query."
        )

    def test_invalid_delete_2(self):
        """
        Test deleting a publication that is not linked to record (LGD)
        """
        to_delete = {"pmid": 3897232}

        # Login
        user = User.objects.get(email="john@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        # Authenticate by setting cookie on the test client
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        response = self.client.patch(
            self.url_delete, to_delete, content_type="application/json"
        )
        self.assertEqual(response.status_code, 404)

        response_data = response.json()
        self.assertEqual(
            response_data["error"],
            "Could not find publication '3897232' for ID 'G2P00002'",
        )

    def test_lgd_publication_delete(self):
        """
        Test deleting the publication from the record (LGD)
        """
        to_delete = {"pmid": 15214012}

        # Login
        user = User.objects.get(email="john@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        # Authenticate by setting cookie on the test client
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        response = self.client.patch(
            self.url_delete, to_delete, content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)

        # Check deleted record-publication
        lgd_publications = LGDPublication.objects.filter(
            lgd__stable_id__stable_id="G2P00002",
            is_deleted=1,
            publication__pmid=15214012,
        )
        self.assertEqual(len(lgd_publications), 1)
