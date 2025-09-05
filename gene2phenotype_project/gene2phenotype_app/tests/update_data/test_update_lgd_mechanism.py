from django.test import TestCase
from django.urls import reverse
from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken
from gene2phenotype_app.models import (
    User,
    LocusGenotypeDisease,
    LGDMolecularMechanismSynopsis,
)


class LGDUpdateLGDMechanism(TestCase):
    """
    Test endpoint to update the record mechanism
    """

    fixtures = [
        "gene2phenotype_app/fixtures/attribs.json",
        "gene2phenotype_app/fixtures/cv_molecular_mechanism.json",
        "gene2phenotype_app/fixtures/disease.json",
        "gene2phenotype_app/fixtures/g2p_stable_id.json",
        "gene2phenotype_app/fixtures/lgd_mechanism_evidence.json",
        "gene2phenotype_app/fixtures/lgd_mechanism_synopsis.json",
        "gene2phenotype_app/fixtures/lgd_panel.json",
        "gene2phenotype_app/fixtures/lgd_publication.json",
        "gene2phenotype_app/fixtures/locus_genotype_disease.json",
        "gene2phenotype_app/fixtures/locus.json",
        "gene2phenotype_app/fixtures/publication.json",
        "gene2phenotype_app/fixtures/sequence.json",
        "gene2phenotype_app/fixtures/user_panels.json",
        "gene2phenotype_app/fixtures/ontology_term.json",
        "gene2phenotype_app/fixtures/source.json",
    ]

    def setUp(self):
        self.url_lgd_mechanism = reverse(
            "lgd_update_mechanism", kwargs={"stable_id": "G2P00001"}
        )
        self.url_lgd_mechanism_2 = reverse(
            "lgd_update_mechanism", kwargs={"stable_id": "G2P00002"}
        )
        self.mechanism_data = {
            "molecular_mechanism": {"name": "gain of function", "support": "evidence"},
            "mechanism_synopsis": [
                {"name": "destabilising LOF", "support": "evidence"}
            ],
            "mechanism_evidence": [
                {
                    "pmid": "25099252",
                    "description": "text",
                    "evidence_types": [
                        {"primary_type": "Rescue", "secondary_type": ["Patient Cells"]}
                    ],
                }
            ],
        }
        self.mechanism_data_synopsis = {
            "mechanism_synopsis": [{"name": "destabilising LOF", "support": "evidence"}]
        }
        # test activity logs after the updates
        self.url_base_activity_logs = reverse("activity_logs")

        # Setup login
        user = User.objects.get(email="user5@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        self.access_token = str(refresh.access_token)

    def test_invalid_update(self):
        """
        Test updating mechanism with empty input data
        """
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = self.access_token

        response = self.client.patch(
            self.url_lgd_mechanism, {}, content_type="application/json"
        )
        self.assertEqual(response.status_code, 404)

        response_data = response.json()
        self.assertEqual(response_data["detail"], "Mechanism data is missing")

    def test_unauthorised_access(self):
        """
        Test updating record mechanism without being authenticated
        """
        response = self.client.patch(
            self.url_lgd_mechanism, self.mechanism_data, content_type="application/json"
        )
        self.assertEqual(response.status_code, 401)

    def test_no_permission(self):
        """
        Test trying to update the mechanism for user without permission to edit record
        """
        # Login
        user = User.objects.get(email="sofia@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        response = self.client.patch(
            self.url_lgd_mechanism_2,
            self.mechanism_data,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)

        response_data = response.json()
        self.assertEqual(
            response_data["error"], "No permission to update record 'G2P00002'"
        )

    def test_valid_update(self):
        """
        Test successfully updating the record mechanism
        """
        # Authenticate by setting cookie on the test client
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = self.access_token

        response = self.client.patch(
            self.url_lgd_mechanism,
            self.mechanism_data_synopsis,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)

        response_data = response.json()
        self.assertEqual(
            response_data["message"],
            "Molecular mechanism updated successfully for 'G2P00001'",
        )

        history_records = LGDMolecularMechanismSynopsis.history.all()
        self.assertEqual(len(history_records), 1)
        lgd_history = LocusGenotypeDisease.history.all()
        self.assertEqual(len(lgd_history), 1)

        # Query the activity logs
        url_activity_logs = f"{self.url_base_activity_logs}?stable_id=G2P00001"
        response_logs = self.client.get(url_activity_logs)
        self.assertEqual(response_logs.status_code, 200)
        response_logs_data = response_logs.json()
        self.assertEqual(response_logs_data[0]["change_type"], "created")

    def test_no_permission_update(self):
        """
        Test trying to update the record mechanism when it cannot be updated
        """
        # Authenticate by setting cookie on the test client
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = self.access_token

        response = self.client.patch(
            self.url_lgd_mechanism, self.mechanism_data, content_type="application/json"
        )
        self.assertEqual(response.status_code, 403)

        response_data = response.json()
        self.assertEqual(
            response_data["error"],
            "Cannot update 'molecular mechanism' for ID 'G2P00001'",
        )
