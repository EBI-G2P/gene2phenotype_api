from django.test import TestCase
from django.urls import reverse
from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken
from gene2phenotype_app.models import (
    User,
    LGDPhenotype,
    LGDPhenotypeSummary,
)


class LGDEditPhenotypeEndpoint(TestCase):
    """
    Test endpoint to add phenotypes to a LGD record
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
        "gene2phenotype_app/fixtures/lgd_phenotype_summary.json",
    ]

    def setUp(self):
        self.url_add_phenotype = reverse(
            "lgd_phenotype", kwargs={"stable_id": "G2P00002"}
        )
        self.phenotype_to_add = {
            "hpo_terms": [
                {"accession": "HP:0000118", "publication": 15214012},
                {"accession": "HP:6000692", "publication": 15214012},
            ]
        }
        self.phenotype_with_summary_to_add = {
            "hpo_terms": [{"accession": "HP:0000118", "publication": 12451214}],
            "summaries": [{"summary": "This is a summary", "publication": [12451214]}],
        }
        self.phenotype_to_add_2 = {"hpo_terms": []}
        # test activity logs after insertion
        self.url_base_activity_logs = reverse("activity_logs")

    def test_add_unauthorised_access(self):
        """
        Test the endpoint to add phenotypes for non authenticated user
        """
        response = self.client.post(
            self.url_add_phenotype,
            self.phenotype_to_add,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 401)

    def test_add_no_permission(self):
        """
        Test the endpoint to add phenotypes for user without permission to edit record
        """
        # Login
        user = User.objects.get(email="sofia@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        # Authenticate by setting cookie on the test client
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        response = self.client.post(
            self.url_add_phenotype,
            self.phenotype_to_add,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)

        response_data = response.json()
        self.assertEqual(
            response_data["error"], "No permission to update record 'G2P00002'"
        )

    def test_add_lgd_phenotypes(self):
        """
        Test the endpoint to add phenotypes to a record
        """
        # Login
        user = User.objects.get(email="john@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        # Authenticate by setting cookie on the test client
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        response = self.client.post(
            self.url_add_phenotype,
            self.phenotype_to_add,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)

        response_data = response.json()
        self.assertEqual(
            response_data["message"], "Phenotype added to the G2P entry successfully."
        )

        # Check inserted data
        lgd_phenotypes = LGDPhenotype.objects.filter(
            lgd__stable_id__stable_id="G2P00002", is_deleted=0
        )
        self.assertEqual(len(lgd_phenotypes), 5)

        # Query the activity logs
        url_activity_logs = f"{self.url_base_activity_logs}?stable_id=G2P00002"
        response_logs = self.client.get(url_activity_logs)
        self.assertEqual(response_logs.status_code, 200)
        response_logs_data = response_logs.json()
        self.assertEqual(response_logs_data["results"][0]["change_type"], "created")
        self.assertEqual(response_logs_data["count"], 2)

    def test_add_lgd_phenotypes_with_summary(self):
        """
        Test the endpoint to add phenotypes and phenotype summary to a record
        """
        # Login
        user = User.objects.get(email="john@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        # Authenticate by setting cookie on the test client
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        response = self.client.post(
            self.url_add_phenotype,
            self.phenotype_with_summary_to_add,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)

        response_data = response.json()
        self.assertEqual(
            response_data["message"],
            "Phenotype summary added to the G2P entry successfully.",
        )

        # Check inserted data
        lgd_phenotypes = LGDPhenotype.objects.filter(
            lgd__stable_id__stable_id="G2P00002", is_deleted=0
        )
        self.assertEqual(len(lgd_phenotypes), 4)

        lgd_phenotype_summary = LGDPhenotypeSummary.objects.filter(
            lgd__stable_id__stable_id="G2P00002", is_deleted=0
        )
        self.assertEqual(len(lgd_phenotype_summary), 2)

        # Check history tables
        history_records_pheno = LGDPhenotype.history.all()
        self.assertEqual(len(history_records_pheno), 1)
        history_records_pheno_summary = LGDPhenotypeSummary.history.all()
        self.assertEqual(len(history_records_pheno_summary), 1)

    def test_add_empty_phenotype(self):
        """
        Test the endpoint to add empty phenotype to a record
        """
        # Login
        user = User.objects.get(email="john@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        # Authenticate by setting cookie on the test client
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        response = self.client.post(
            self.url_add_phenotype,
            self.phenotype_to_add_2,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

        response_data = response.json()
        self.assertEqual(
            response_data["error"], "Empty phenotype. Please provide valid data."
        )
