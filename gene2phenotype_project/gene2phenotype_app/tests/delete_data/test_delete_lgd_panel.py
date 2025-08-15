from django.test import TestCase
from django.urls import reverse
from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken
from gene2phenotype_app.models import (
    User,
    LGDPanel
)


class LGDDeletePanelEndpoint(TestCase):
    """
    Test endpoint to delete panel from a LGD record
    """

    fixtures = [
        "gene2phenotype_app/fixtures/attribs.json",
        "gene2phenotype_app/fixtures/cv_molecular_mechanism.json",
        "gene2phenotype_app/fixtures/disease.json",
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
    ]

    def setUp(self):
        self.url_delete_panel = reverse("lgd_panel", kwargs={"stable_id": "G2P00006"})

        self.url_delete_panel_invalid_record = reverse("lgd_panel", kwargs={"stable_id": "G2P00123"})

        self.url_delete_single_panel = reverse("lgd_panel", kwargs={"stable_id": "G2P00005"})

        self.panel_to_delete = {
            "name": "Ear"
        }

    def test_delete_panel_unauthorised_access(self):
        """
        Test the endpoint to delete panel for non authenticated user
        """

        response = self.client.patch(
            self.url_delete_panel,
            self.panel_to_delete,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 401)

    def test_delete_panel_no_permission(self):
        """
        Test the endpoint to delete panel for user without permission to edit record
        """
        # Login
        user = User.objects.get(email="john@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        # Authenticate by setting cookie on the test client
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        response = self.client.patch(
            self.url_delete_panel,
            self.panel_to_delete,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)

        response_data = response.json()
        self.assertEqual(response_data["error"], "No permission to update panel Ear")

    def test_delete_panel_no_superuser(self):
        """
        Test the endpoint to delete panel for user who is not superuser
        """
        # Login
        user = User.objects.get(email="user1@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        # Authenticate by setting cookie on the test client
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        response = self.client.patch(
            self.url_delete_panel,
            self.panel_to_delete,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)

        response_data = response.json()
        self.assertEqual(response_data["error"], "You do not have permission to perform this action.")

    def test_delete_empty_panel(self):
        """
        Test the endpoint to delete empty panel
        """
        empty_panel_to_delete = {"name": ""}

        # Login
        user = User.objects.get(email="user5@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        # Authenticate by setting cookie on the test client
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        response = self.client.patch(
            self.url_delete_panel,
            empty_panel_to_delete,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

        response_data = response.json()
        self.assertEqual(
            response_data["error"], "Please enter a panel name"
        )

    def test_delete_invalid_panel(self):
        """
        Test the endpoint to delete invalid panel
        Cannot delete a panel that does not exist
        """
        invalid_panel_to_delete = {"name": "Dummy"}

        # Login
        user = User.objects.get(email="user5@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        # Authenticate by setting cookie on the test client
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        response = self.client.patch(
            self.url_delete_panel,
            invalid_panel_to_delete,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 404)
    
    def test_delete_single_panel(self):
        """
        Test the endpoint to delete panel from a record that has only 1 panel
        Cannot delete a panel from a record that has only 1 panel
        """

        # Login
        user = User.objects.get(email="user5@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        # Authenticate by setting cookie on the test client
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        response = self.client.patch(
            self.url_delete_single_panel,
            self.panel_to_delete,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

        response_data = response.json()
        self.assertEqual(
            response_data["error"], "Can not delete panel 'Ear' for ID 'G2P00005'"
        )

    def test_delete_panel_not_linked_to_record(self):
        """
        Test the endpoint to delete panel not linked to the record
        Cannot delete a panel not linked to the record
        """

        panel_not_linked_to_record = {"name": "DD"}

        # Login
        user = User.objects.get(email="user5@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        # Authenticate by setting cookie on the test client
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        response = self.client.patch(
            self.url_delete_panel,
            panel_not_linked_to_record,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

        response_data = response.json()
        self.assertEqual(
            response_data["error"], "Panel 'DD' does not exist for ID 'G2P00006'"
        )

    def test_delete_panel_invalid_record(self):
        """
        Test the endpoint to delete panel from an invalid lgd record
        Cannot delete a panel from a record that does not exist
        """

        # Login
        user = User.objects.get(email="user5@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        # Authenticate by setting cookie on the test client
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        response = self.client.patch(
            self.url_delete_panel_invalid_record,
            self.panel_to_delete,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 404)

    def test_delete_panel_success(self):
        """
        Test the endpoint to delete panel from a record
        """
        # Login
        user = User.objects.get(email="user5@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        # Authenticate by setting cookie on the test client
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        response = self.client.patch(
            self.url_delete_panel,
            self.panel_to_delete,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)

        response_data = response.json()
        self.assertEqual(
            response_data["message"], "Panel 'Ear' successfully deleted for ID 'G2P00006'"
        )

        # Check lgd_panel table
        lgd_panels = LGDPanel.objects.filter(
            lgd__stable_id__stable_id="G2P00006", is_deleted=1
        )
        self.assertEqual(len(lgd_panels), 1)

        # Test history table              
        history_records = LGDPanel.history.filter(lgd__stable_id__stable_id="G2P00006")
        self.assertEqual(len(history_records), 1)
