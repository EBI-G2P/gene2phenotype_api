from django.test import TestCase
from django.urls import reverse
from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken
from gene2phenotype_app.models import (
    User,
    LGDPublication,
    LGDPhenotype,
    LGDPhenotypeSummary,
    LGDVariantType,
    LGDVariantTypeComment,
    LGDVariantTypeDescription,
    LGDMolecularMechanismEvidence,
    LocusGenotypeDisease,
)


class LGDDeletePublication(TestCase):
    """
    Test endpoint to delete a publication from a record (LGD)
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
        self.url_try_delete = reverse(
            "lgd_publication", kwargs={"stable_id": "G2P00001"}
        )

    def test_delete_non_superuser(self):
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

    def test_delete_no_permission(self):
        """
        Test deleting the publication for user without permission to edit panel
        """
        to_delete = {"pmid": 15214012}

        # Login with super user
        user = User.objects.get(email="sofia@test.ac.uk")
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
        user = User.objects.get(email="user5@test.ac.uk")
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

    def test_delete_unlinked_publication(self):
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

    def test_invalid_input(self):
        """
        Test deleting a publication with empty pmid
        """
        to_delete = {"pmid": ""}

        # Login
        user = User.objects.get(email="john@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        response = self.client.patch(
            self.url_delete, to_delete, content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)

        response_data = response.json()
        self.assertEqual(
            response_data["error"],
            "Please provide valid pmid.",
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

        lgd_phenotypes = LGDPhenotype.objects.filter(
            lgd__stable_id__stable_id="G2P00002",
            publication__pmid=15214012,
            is_deleted=1,
        )
        self.assertEqual(len(lgd_phenotypes), 3)

        lgd_phenotype_summary = LGDPhenotypeSummary.objects.filter(
            lgd__stable_id__stable_id="G2P00002",
            publication__pmid=15214012,
            is_deleted=1,
        )
        self.assertEqual(len(lgd_phenotype_summary), 1)

        lgd_variant_type = LGDVariantType.objects.filter(
            lgd__stable_id__stable_id="G2P00002",
            publication__pmid=15214012,
            is_deleted=1,
        )
        self.assertEqual(len(lgd_variant_type), 2)

        lgd_variant_description = LGDVariantTypeDescription.objects.filter(
            lgd__stable_id__stable_id="G2P00002",
            publication__pmid=15214012,
            is_deleted=1,
        )
        self.assertEqual(len(lgd_variant_description), 2)

        lgd_mechanism_evidence = LGDMolecularMechanismEvidence.objects.filter(
            lgd__stable_id__stable_id="G2P00002",
            publication__pmid=15214012,
            is_deleted=1,
        )
        self.assertEqual(len(lgd_mechanism_evidence), 1)

        # Check the history table
        history_records = LGDPublication.history.all()
        self.assertEqual(len(history_records), 1)
        self.assertEqual(history_records[0].is_deleted, 1)
        history_records_phenotype = LGDPhenotype.history.all()
        self.assertEqual(len(history_records_phenotype), 3)
        history_records_pheno_sum = LGDPhenotypeSummary.history.all()
        self.assertEqual(len(history_records_pheno_sum), 1)
        history_records_var_type = LGDVariantType.history.all()
        self.assertEqual(len(history_records_var_type), 2)
        history_records_var_type_comment = LGDVariantTypeComment.history.all()
        self.assertEqual(len(history_records_var_type_comment), 1)
        history_records_var_type_desc = LGDVariantTypeDescription.history.all()
        self.assertEqual(len(history_records_var_type_desc), 2)
        history_records_mechanism_evidence = LGDMolecularMechanismEvidence.history.all()
        self.assertEqual(len(history_records_mechanism_evidence), 1)
        history_records_lgd = LocusGenotypeDisease.history.all()
        self.assertEqual(len(history_records_lgd), 0)
