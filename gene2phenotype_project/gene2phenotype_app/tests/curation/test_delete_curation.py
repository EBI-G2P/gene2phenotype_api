from django.test import TestCase
from django.urls import reverse
from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken
from gene2phenotype_app.models import User, CurationData, G2PStableID


class LGDDeleteCurationEndpoint(TestCase):
    """
    Test endpoint to delete curation
    """

    fixtures = [
        "gene2phenotype_app/fixtures/g2p_stable_id.json",
        "gene2phenotype_app/fixtures/user_panels.json",
        "gene2phenotype_app/fixtures/curation_data.json",
    ]

    def setUp(self):
        self.url_delete_curation = reverse(
            "delete_curation", kwargs={"stable_id": "G2P00004"}
        )
        self.url_delete_invalid_curation = reverse(
            "delete_curation", kwargs={"stable_id": "G2P00123"}
        )

    def test_delete_invalid_curation(self):
        """
        Test to delete invalid curation
        Cannot delete a curation that does not exist
        """
        # Login
        user = User.objects.get(email="user5@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        # Authenticate by setting cookie on the test client
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        response = self.client.delete(self.url_delete_invalid_curation)
        self.assertEqual(response.status_code, 404)

    def test_delete_curation_unauthorised_access(self):
        """
        Test call to delete curation endpoint without authentication
        """

        response = self.client.delete(self.url_delete_curation)
        self.assertEqual(response.status_code, 401)

    def test_delete_curation_no_permission(self):
        """
        Test call to delete curation endpoint with super user who does not have permission to delete the curation
        """
        # Login
        user = User.objects.get(email="john@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        # Authenticate by setting cookie on the test client
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        response = self.client.delete(self.url_delete_curation)
        self.assertEqual(response.status_code, 404)

        response_data = response.json()
        self.assertEqual(response_data["error"], "Cannot find ID G2P00004")

    def test_delete_curation_success(self):
        """
        Test successful call to delete curation endpoint
        """
        # Login
        user = User.objects.get(email="user5@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        # Authenticate by setting cookie on the test client
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        response = self.client.delete(self.url_delete_curation)
        self.assertEqual(response.status_code, 200)

        response_data = response.json()
        self.assertEqual(
            response_data["message"], "Data deleted successfully for ID G2P00004"
        )

        # Check curation_data table
        lgd_comments = CurationData.objects.filter(stable_id__stable_id="G2P00004")
        self.assertEqual(len(lgd_comments), 0)

        # Check g2p_stableid table
        g2p_stable_id_obj = G2PStableID.objects.get(stable_id="G2P00004")
        self.assertEqual(g2p_stable_id_obj.is_live, False)
        self.assertEqual(g2p_stable_id_obj.is_deleted, 1)

        # Test history table
        history_records = CurationData.history.filter(stable_id__stable_id="G2P00004")
        self.assertEqual(len(history_records), 1)
