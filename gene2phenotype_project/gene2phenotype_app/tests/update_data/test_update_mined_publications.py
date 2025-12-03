from django.test import TestCase
from django.urls import reverse
from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken
from gene2phenotype_app.models import User, LGDMinedPublication


class LGDDeletePanelEndpoint(TestCase):
    """
    Test endpoint to update mined publications for a LGD record
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
        "gene2phenotype_app/fixtures/mined_publication.json",
        "gene2phenotype_app/fixtures/lgd_mined_publication.json",
    ]

    def setUp(self):
        self.url_update = reverse(
            "lgd_mined_publication", kwargs={"stable_id": "G2P00001"}
        )

        self.url_update_invalid_record = reverse(
            "lgd_mined_publication", kwargs={"stable_id": "G2P00123"}
        )

        self.input_data = {
            "mined_publications": [
                {"pmid": 7866404, "status": "rejected", "comment": "Test comment 1"},
            ]
        }

    def test_update_unauthorised_access(self):
        """
        Test the endpoint to update mined publications for non authenticated user
        """

        response = self.client.put(
            self.url_update,
            self.input_data,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 401)

    def test_update_no_permission(self):
        """
        Test the endpoint to update mined publications for user without permission to edit record
        """
        # Login
        user = User.objects.get(email="john@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        # Authenticate by setting cookie on the test client
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        response = self.client.put(
            self.url_update,
            self.input_data,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)

        response_data = response.json()
        self.assertEqual(response_data["error"], "No permission to edit 'G2P00001'")

    def test_update_empty_input(self):
        """
        Test the endpoint to update mined publications with empty input
        """
        empty_input_data = {"mined_publications": []}

        # Login
        user = User.objects.get(email="user5@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        # Authenticate by setting cookie on the test client
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        response = self.client.put(
            self.url_update,
            empty_input_data,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

        response_data = response.json()
        self.assertEqual(
            response_data["error"],
            "Provided mined publications list is empty. Please provide valid data.",
        )

    def test_update_null_pmid(self):
        """
        Test the endpoint to update mined publications with null pmid
        """
        invalid_input_data = {
            "mined_publications": [
                {"pmid": None, "status": "rejected", "comment": "Test comment 1"}
            ]
        }

        # Login
        user = User.objects.get(email="user5@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        # Authenticate by setting cookie on the test client
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        response = self.client.put(
            self.url_update,
            invalid_input_data,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_update_invalid_pmid(self):
        """
        Test the endpoint to update mined publications with invalid pmid
        """
        invalid_input_data = {
            "mined_publications": [
                {"pmid": 1, "status": "rejected", "comment": "Test comment 1"}
            ]
        }

        # Login
        user = User.objects.get(email="user5@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        # Authenticate by setting cookie on the test client
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        response = self.client.put(
            self.url_update,
            invalid_input_data,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

        response_data = response.json()
        self.assertEqual(
            response_data["error"],
            "Provided mined publication '1' does not exist. Please provide valid data.",
        )

    def test_update_empty_status(self):
        """
        Test the endpoint to update mined publications with empty status
        """
        invalid_input_data = {
            "mined_publications": [
                {"pmid": 7866404, "status": "", "comment": "Test comment 1"}
            ]
        }

        # Login
        user = User.objects.get(email="user5@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        # Authenticate by setting cookie on the test client
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        response = self.client.put(
            self.url_update,
            invalid_input_data,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_update_invalid_status(self):
        """
        Test the endpoint to update mined publications with invalid status
        """
        invalid_input_data = {
            "mined_publications": [
                {"pmid": 7866404, "status": "dummy", "comment": "Test comment 1"}
            ]
        }

        # Login
        user = User.objects.get(email="user5@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        # Authenticate by setting cookie on the test client
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        response = self.client.put(
            self.url_update,
            invalid_input_data,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        response_data = response.json()
        self.assertEqual(
            response_data["error"],
            "Invalid status. Valid statuses are: mined, curated, rejected",
        )

    def test_update_same_status(self):
        """
        Test the endpoint to update mined publications with same status
        """
        invalid_input_data = {
            "mined_publications": [{"pmid": 7866404, "status": "mined", "comment": ""}]
        }

        # Login
        user = User.objects.get(email="user5@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        # Authenticate by setting cookie on the test client
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        response = self.client.put(
            self.url_update,
            invalid_input_data,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

        response_data = response.json()
        self.assertEqual(
            response_data["error"],
            "For mined publication '7866404', status is already 'mined'. Please provide valid data.",
        )

    def test_update_empty_comment_for_rejected_status(self):
        """
        Test the endpoint to update mined publications with rejected status but empty comment
        """
        invalid_input_data = {
            "mined_publications": [
                {"pmid": 7866404, "status": "rejected", "comment": ""}
            ]
        }

        # Login
        user = User.objects.get(email="user5@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        # Authenticate by setting cookie on the test client
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        response = self.client.put(
            self.url_update,
            invalid_input_data,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

        response_data = response.json()
        self.assertEqual(
            response_data["error"],
            "For mined publication '7866404', comment can not be empty or null for status 'rejected'. Please provide valid data.",
        )

    def test_update_mined_publication_not_linked_to_record(self):
        """
        Test the endpoint to update mined publications not linked to record
        """
        invalid_input_data = {
            "mined_publications": [
                {"pmid": 32302040, "status": "rejected", "comment": "Test comment 1"}
            ]
        }

        # Login
        user = User.objects.get(email="user5@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        # Authenticate by setting cookie on the test client
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        response = self.client.put(
            self.url_update,
            invalid_input_data,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

        response_data = response.json()
        self.assertEqual(
            response_data["error"],
            "Provided mined publication '32302040' is not linked to the record 'G2P00001'. Please provide valid data.",
        )

    def test_update_invalid_record(self):
        """
        Test the endpoint to update mined publications for an invalid lgd record
        Cannot update mined publications for a record that does not exist
        """

        # Login
        user = User.objects.get(email="user5@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        # Authenticate by setting cookie on the test client
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        response = self.client.put(
            self.url_update_invalid_record,
            self.input_data,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 404)

    def test_update_with_rejected_status_success(self):
        """
        Test the endpoint to update mined publications with 'rejected' status for a record
        """
        # Login
        user = User.objects.get(email="user5@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        # Authenticate by setting cookie on the test client
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        response = self.client.put(
            self.url_update,
            self.input_data,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)

        response_data = response.json()
        self.assertEqual(
            response_data["message"],
            "Mined publications updated successfully.",
        )

        # Check lgd_mined_publication table
        lgd_panels = LGDMinedPublication.objects.filter(
            lgd__stable_id__stable_id="G2P00001", status="rejected"
        )
        self.assertEqual(len(lgd_panels), 1)

        # Test history tables
        history_records = LGDMinedPublication.history.filter(
            lgd__stable_id__stable_id="G2P00001"
        )
        self.assertEqual(len(history_records), 1)

    def test_update_with_curated_status_success(self):
        """
        Test the endpoint to update mined publications with 'curated' status for a record
        """
        input_data = {
            "mined_publications": [
                {"pmid": 7866404, "status": "curated", "comment": ""},
            ]
        }

        # Login
        user = User.objects.get(email="user5@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        # Authenticate by setting cookie on the test client
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        response = self.client.put(
            self.url_update,
            input_data,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)

        response_data = response.json()
        self.assertEqual(
            response_data["message"],
            "Mined publications updated successfully.",
        )

        # Check lgd_mined_publication table
        lgd_panels = LGDMinedPublication.objects.filter(
            lgd__stable_id__stable_id="G2P00001", status="curated"
        )
        self.assertEqual(len(lgd_panels), 1)

        # Test history tables
        history_records = LGDMinedPublication.history.filter(
            lgd__stable_id__stable_id="G2P00001"
        )
        self.assertEqual(len(history_records), 1)
