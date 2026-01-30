from django.test import TestCase
from django.urls import reverse
from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken
from gene2phenotype_app.models import User, CurationData


class LGDClaimCurationEndpoint(TestCase):
    """
    Test endpoint to claim curation
    """

    fixtures = [
        "gene2phenotype_app/fixtures/g2p_stable_id.json",
        "gene2phenotype_app/fixtures/user_panels.json",
        "gene2phenotype_app/fixtures/auth_groups.json",
        "gene2phenotype_app/fixtures/curation_data.json",
    ]

    def setUp(self):
        self.url_claim_curation_1 = reverse(
            "claim_curation", kwargs={"stable_id": "G2P00013"}
        )

        self.url_claim_curation_2 = reverse(
            "claim_curation", kwargs={"stable_id": "G2P00014"}
        )

        self.url_claim_invalid_curation = reverse(
            "claim_curation", kwargs={"stable_id": "G2P00123"}
        )

        self.url_claim_other_user_curation = reverse(
            "claim_curation", kwargs={"stable_id": "G2P00010"}
        )

        self.url_claim_same_user_curation = reverse(
            "claim_curation", kwargs={"stable_id": "G2P00001"}
        )

    def login_user(self):
        self.user = User.objects.get(email="user5@test.ac.uk")
        refresh = RefreshToken.for_user(self.user)
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = str(
            refresh.access_token
        )

    def test_claim_curation_success_junior_curator_group(self):
        """
        Test successful call to claim curation endpoint for curation which is claimed by junior curator group
        """
        self.login_user()

        response = self.client.patch(
            self.url_claim_curation_1,
            data=None,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)

        response_data = response.json()
        self.assertEqual(
            response_data["message"],
            "Curation draft with G2P Stable ID 'G2P00013' claimed successfully.",
        )

        # Check curation_data table
        curation_entries = CurationData.objects.filter(
            stable_id__stable_id="G2P00013", user__email="user5@test.ac.uk"
        )
        self.assertEqual(len(curation_entries), 1)

    def test_claim_curation_success_g2p_admin_group(self):
        """
        Test successful call to claim curation endpoint for curation which is claimed by g2p admin group
        """
        self.login_user()

        response = self.client.patch(
            self.url_claim_curation_2,
            data=None,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)

        response_data = response.json()
        self.assertEqual(
            response_data["message"],
            "Curation draft with G2P Stable ID 'G2P00014' claimed successfully.",
        )

        # Check curation_data table
        curation_entries = CurationData.objects.filter(
            stable_id__stable_id="G2P00014", user__email="user5@test.ac.uk"
        )
        self.assertEqual(len(curation_entries), 1)

    def test_claim_invalid_curation(self):
        """
        Test call to claim curation endpoint with invalid curation stable id
        """
        self.login_user()

        response = self.client.patch(
            self.url_claim_invalid_curation,
            data=None,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 404)

    def test_claim_curation_claimed_by_other_user(self):
        """
        Test call to claim curation endpoint for curation which is already claimed by another user
        """
        self.login_user()

        response = self.client.patch(
            self.url_claim_other_user_curation,
            data=None,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

        response_data = response.json()
        self.assertEqual(
            response_data["error"],
            "Curation draft with G2P Stable ID 'G2P00010' already claimed by another user.",
        )

    def test_claim_curation_claimed_by_same_user(self):
        """
        Test call to claim curation endpoint for curation which is already claimed by same user
        """
        self.login_user()

        response = self.client.patch(
            self.url_claim_same_user_curation,
            data=None,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

        response_data = response.json()
        self.assertEqual(
            response_data["error"],
            "Curation draft with G2P Stable ID 'G2P00001' already claimed by same user.",
        )
