from django.test import TestCase
from django.urls import reverse
from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken
from gene2phenotype_app.models import (
    User,
    LocusGenotypeDisease,
)


class LGDDiseaseUpdatesEndpoint(TestCase):
    """
    Test endpoint to update the record disease ID
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
    ]

    def setUp(self):
        self.url_update = reverse("lgd_disease_updates")
        self.incorrect_diseases_to_update = [
            {"disease_id": 1000, "new_disease_id": 2000}
        ]
        self.diseases_to_update = [{"disease_id": 11, "new_disease_id": 10}]
        self.diseases_to_update_2 = [{"disease_id": 10, "new_disease_id": 11}]
        self.specific_lgd_diseases_duplicate = [{"disease_id": 10, "new_disease_id": 11, "stable_id": "G2P00002"}]
        self.specific_lgd_diseases_to_update = [{"disease_id": 2, "new_disease_id": 13, "stable_id": "G2P00001"}]
        self.specific_lgd_diseases_invalid = [{"disease_id": 1, "new_disease_id": 13, "stable_id": "G2P00001"}]

    def test_update_invalid_ids(self):
        """
        Test updating invalid disease IDs
        """
        # Login
        user = User.objects.get(email="user5@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        response = self.client.post(
            self.url_update,
            self.incorrect_diseases_to_update,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_no_permission(self):
        """
        Test updating records without permission
        """
        # Login
        user = User.objects.get(email="user1@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        response = self.client.post(
            self.url_update,
            self.incorrect_diseases_to_update,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)

    def test_invalid_input_format(self):
        """
        Test updating records with an invalid input format
        """
        # Login
        user = User.objects.get(email="user5@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        response = self.client.post(
            self.url_update, [{}], content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)

        response_data = response.json()
        self.assertEqual(
            response_data["error"],
            [{"error": "Both 'disease_id' and 'new_disease_id' are required."}],
        )

    def test_update_record_disease(self):
        """
        Try to update records disease IDs
        """
        # Login
        user = User.objects.get(email="user5@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        # First update
        response_duplicate = self.client.post(
            self.url_update, self.diseases_to_update, content_type="application/json"
        )
        self.assertEqual(response_duplicate.status_code, 400)

        response_data = response_duplicate.json()
        self.assertEqual(
            response_data["error"],
            [
                {
                    "disease_id": 11,
                    "error": "Found a different record with same locus, genotype, disease and mechanism: 'G2P00002'",
                }
            ],
        )

        # Second update
        response = self.client.post(
            self.url_update, self.diseases_to_update_2, content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)

        response_data = response.json()
        # Record G2P00008 was associated with disease id 10, the endpoint updated it to disease id 11
        expected_response_updates = [{"g2p_id": "G2P00008", "lgd_id": 7}]
        # The other record associated with disease id 10 cannot be updated
        expected_response_data_error = [
            {
                "disease_id": 10,
                "error": "Found a different record with same locus, genotype, disease and mechanism: 'G2P00006'",
            }
        ]
        self.assertEqual(response_data["Updated records"], expected_response_updates)
        self.assertEqual(response_data["error"], expected_response_data_error)

        # Test updated records
        lgd_obj = LocusGenotypeDisease.objects.get(
            stable_id__stable_id="G2P00008", is_deleted=0
        )
        self.assertEqual(lgd_obj.disease.id, 11)

        lgd_obj_history = LocusGenotypeDisease.history.filter(
            stable_id__stable_id="G2P00008"
        )
        self.assertEqual(lgd_obj_history[0].disease.id, 11)

    def test_update_specific_record_disease_duplicate(self):
        """
        Try to update records disease IDs
        """
        # Login
        user = User.objects.get(email="user5@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        # First update
        response = self.client.post(
            self.url_update, self.specific_lgd_diseases_duplicate, content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)

        response_data = response.json()
        self.assertEqual(
            response_data["error"],
            [
                {
                    "disease_id": 10,
                    "error": "Found a different record with same locus, genotype, disease and mechanism: 'G2P00006'",
                }
            ],
        )

    def test_update_specific_record_disease(self):
        """
        Try to update records disease IDs
        """
        # Login
        user = User.objects.get(email="user5@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        response = self.client.post(
            self.url_update, self.specific_lgd_diseases_to_update, content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)

        response_data = response.json()
        self.assertEqual(response_data["Updated records"],[{'g2p_id': 'G2P00001', 'lgd_id': 1}])

    def test_update_specific_record_disease_invalid(self):
        """
        Try to update records disease IDs for invalid values
        """
        # Login
        user = User.objects.get(email="user5@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        response = self.client.post(
            self.url_update, self.specific_lgd_diseases_invalid, content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)

        response_data = response.json()
        self.assertEqual(response_data["error"], [{'error': 'No records associated with disease id 1'}])
