from django.test import TestCase
from django.urls import reverse
from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken
from gene2phenotype_app.models import (
    User,
    LGDPanel,
    LocusGenotypeDisease,
)


class CreatePanelEndpoint(TestCase):
    """
    Test endpoint to create panels
    """

    fixtures = [
        "gene2phenotype_app/fixtures/attribs.json",
        "gene2phenotype_app/fixtures/g2p_stable_id.json",
        "gene2phenotype_app/fixtures/cv_molecular_mechanism.json",
        "gene2phenotype_app/fixtures/disease.json",
        "gene2phenotype_app/fixtures/lgd_panel.json",
        "gene2phenotype_app/fixtures/locus_genotype_disease.json",
        "gene2phenotype_app/fixtures/locus.json",
        "gene2phenotype_app/fixtures/publication.json",
        "gene2phenotype_app/fixtures/sequence.json",
        "gene2phenotype_app/fixtures/user_panels.json",
        "gene2phenotype_app/fixtures/ontology_term.json",
        "gene2phenotype_app/fixtures/source.json",
        "gene2phenotype_app/fixtures/lgd_publication.json",
    ]

    def setUp(self):
        self.url_add_panel = reverse("panel_create")

        self.panel_to_add = {
            "name": "DD",
            "description": "Developmental disorders",
            "is_visible": True
        }

        self.private_panel_to_add = {
            "name": "Ear",
            "description": "Ear disorders",
            "is_visible": False
        }

        self.new_panel_to_add = {
            "name": "Mitochondrial",
            "description": "Mitochondrial disorders",
            "is_visible": True
        }

    def test_add_duplicate_panel(self):
        """
        Test the endpoint to add panel that already exists
        """
        # Login
        user = User.objects.get(email="user5@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        # Authenticate by setting cookie on the test client
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        # Add DD panel which already exists and it's public
        response = self.client.post(
            self.url_add_panel,
            self.panel_to_add,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

        response_data = response.json()
        self.assertEqual(response_data["error"], ["The panel 'DD' already exists."])

        # Add Ear panel which already exists and it's private
        response_private = self.client.post(
            self.url_add_panel,
            self.private_panel_to_add,
            content_type="application/json",
        )
        self.assertEqual(response_private.status_code, 400)

        response_data = response_private.json()
        self.assertEqual(response_data["error"], ["The panel 'Ear' already exists."])

    def test_create_panel(self):
        """
        Test the endpoint to add new panel successfully
        """
        # Login
        user = User.objects.get(email="user5@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        # Authenticate by setting cookie on the test client
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        # Add new Mitochondrial panel
        response = self.client.post(
            self.url_add_panel,
            self.new_panel_to_add,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)

        expected_response = {
            "name": "Mitochondrial",
            "description": "Mitochondrial disorders",
            "is_visible": True
        }

        response_data = response.json()
        self.assertEqual(response_data, expected_response)


class LGDAddPanelEndpoint(TestCase):
    """
    Test endpoint to add panel to a LGD record
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
    ]

    def setUp(self):
        self.url_add_panel = reverse("lgd_panel", kwargs={"stable_id": "G2P00005"})

        self.url_add_panel_invalid_record = reverse("lgd_panel", kwargs={"stable_id": "G2P00123"})

        self.panel_to_add = {
            "name": "DD"
        }

        self.panel_to_add_existing = {
            "name": "Ear"
        }

        # test activity logs after insertion
        self.url_base_activity_logs = reverse("activity_logs")

    def test_add_panel_unauthorised_access(self):
        """
        Test the endpoint to add panel for non authenticated user
        """

        response = self.client.post(
            self.url_add_panel,
            self.panel_to_add,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 401)

    def test_add_panel_no_permission(self):
        """
        Test the endpoint to add panel for user without permission to edit record
        """
        # Login
        user = User.objects.get(email="john@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        # Authenticate by setting cookie on the test client
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        response = self.client.post(
            self.url_add_panel,
            self.panel_to_add,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)

        response_data = response.json()
        self.assertEqual(response_data["error"], "No permission to update panel DD")

    def test_add_empty_panel(self):
        """
        Test the endpoint to add empty panel to a record
        """
        empty_panel_to_add = {"name": ""}

        # Login
        user = User.objects.get(email="user1@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        # Authenticate by setting cookie on the test client
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        response = self.client.post(
            self.url_add_panel,
            empty_panel_to_add,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

        response_data = response.json()
        self.assertEqual(
            response_data["error"], "Please enter a panel name"
        )

    def test_add_invalid_panel(self):
        """
        Test the endpoint to add invalid panel
        Cannot add a panel that does not exist
        """
        invalid_panel_to_add = {"name": "Dummy"}

        # Login
        user = User.objects.get(email="user1@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        # Authenticate by setting cookie on the test client
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        response = self.client.post(
            self.url_add_panel,
            invalid_panel_to_add,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 404)

        response_data = response.json()
        self.assertEqual(response_data["error"], "No Panel matches the given query.")

    def test_add_existing_lgd_panel(self):
        """
        Test the endpoint to add panel to an g2p record that already has the panel
        """
        # Login
        user = User.objects.get(email="user1@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        # Authenticate by setting cookie on the test client
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        response = self.client.post(
            self.url_add_panel,
            self.panel_to_add_existing,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

        response_data = response.json()
        self.assertEqual(response_data["error"], "G2P entry G2P00005 is already linked to panel Ear")

    def test_add_panel_invalid_record(self):
        """
        Test the endpoint to add panel to an invalid lgd record
        Cannot add a panel to a record that does not exist
        """

        # Login
        user = User.objects.get(email="user1@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        # Authenticate by setting cookie on the test client
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        response = self.client.post(
            self.url_add_panel_invalid_record,
            self.panel_to_add,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 404)

        response_data = response.json()
        self.assertEqual(response_data["error"], "No LocusGenotypeDisease matches the given query.")

    def test_add_panel_success(self):
        """
        Test the endpoint to add panel to a record
        """
        # Login
        user = User.objects.get(email="user1@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        # Authenticate by setting cookie on the test client
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        response = self.client.post(
            self.url_add_panel,
            self.panel_to_add,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)

        response_data = response.json()
        self.assertEqual(
            response_data["message"], "Panel added to the G2P entry successfully."
        )

        # Check lgd_panel table
        lgd_panels = LGDPanel.objects.filter(
            lgd__stable_id__stable_id="G2P00005", is_deleted=0
        )
        self.assertEqual(len(lgd_panels), 2)

        # Test history tables
        history_records = LGDPanel.history.filter(lgd__stable_id__stable_id="G2P00005")
        self.assertEqual(len(history_records), 1)
        history_records_lgd = LocusGenotypeDisease.history.all()
        self.assertEqual(len(history_records_lgd), 0)

        # Query the activity logs
        url_activity_logs = f"{self.url_base_activity_logs}?stable_id=G2P00005"
        response_logs = self.client.get(url_activity_logs)
        self.assertEqual(response_logs.status_code, 200)
        response_logs_data = response_logs.json()
        self.assertEqual(response_logs_data["results"][0]["change_type"], "created")
        self.assertEqual(response_logs_data["count"], 1)
