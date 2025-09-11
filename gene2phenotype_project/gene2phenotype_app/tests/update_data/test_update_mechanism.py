from django.test import TestCase
from django.urls import reverse
from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken
from gene2phenotype_app.models import (
    User,
    LGDMolecularMechanismSynopsis,
    LocusGenotypeDisease,
    LGDMolecularMechanismEvidence,
)


class LGDUpdateMechanismEndpoint(TestCase):
    """
    Test endpoint to update mechanism for a LGD record
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
        # Record has mechanism 'undetermined'
        self.url_lgd_update_mechanism = reverse(
            "lgd_update_mechanism", kwargs={"stable_id": "G2P00009"}
        )

        # Record has mechanism 'loss of function' and source 'inferred'
        self.url_lgd_update_mechanism_2 = reverse(
            "lgd_update_mechanism", kwargs={"stable_id": "G2P00008"}
        )

        # Record has mechanism 'loss of function' and source 'evidence'
        self.url_lgd_update_mechanism_3 = reverse(
            "lgd_update_mechanism", kwargs={"stable_id": "G2P00001"}
        )

        self.url_lgd_update_mechanism_invalid_record = reverse(
            "lgd_update_mechanism", kwargs={"stable_id": "G2P00123"}
        )

        self.input_data = {
            "molecular_mechanism": {"name": "loss of function", "support": "evidence"},
            "mechanism_synopsis": [
                {"name": "interaction-disrupting LOF", "support": "inferred"}
            ],
            "mechanism_evidence": [
                {
                    "pmid": "1882842",
                    "description": "text",
                    "evidence_types": [
                        {
                            "primary_type": "Rescue",
                            "secondary_type": ["Patient Cells"],
                        }
                    ],
                }
            ],
        }

    def test_update_unauthorised_access(self):
        """
        Test the endpoint to update mechanism for non authenticated user
        """

        response = self.client.patch(
            self.url_lgd_update_mechanism,
            self.input_data,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 401)

    def test_update_no_permission(self):
        """
        Test the endpoint to update mechanism for user without permission to edit record
        """
        # Login
        user = User.objects.get(email="john@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        # Authenticate by setting cookie on the test client
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        response = self.client.patch(
            self.url_lgd_update_mechanism,
            self.input_data,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)

        response_data = response.json()
        self.assertEqual(
            response_data["error"], "No permission to update record 'G2P00009'"
        )

    def test_update_empty_input(self):
        """
        Test the endpoint to update mechanism with empty input data
        """
        empty_input_data = {}

        # Login
        user = User.objects.get(email="user5@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        # Authenticate by setting cookie on the test client
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        response = self.client.patch(
            self.url_lgd_update_mechanism,
            empty_input_data,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 404)

        response_data = response.json()
        self.assertEqual(response_data["detail"], "Mechanism data is missing")

    def test_update_not_undetermined(self):
        """
        Test the endpoint to update mechanism for a record that does not have 'undetermined' mechanism
        API only allows to update mechanisms with value 'undetermined' or support 'inferred'
        """
        invalid_input_data = {
            "molecular_mechanism": {"name": "loss of function", "support": "inferred"}
        }

        # Login
        user = User.objects.get(email="user5@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        # Authenticate by setting cookie on the test client
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        response = self.client.patch(
            self.url_lgd_update_mechanism_3,
            invalid_input_data,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)
        response_data = response.json()
        self.assertEqual(
            response_data["error"],
            "Cannot update 'molecular mechanism' for ID 'G2P00001'",
        )

    def test_update_no_evidence(self):
        """
        Test the endpoint to update mechanism for a record with support 'evidence' but no evidence provided
        If the mechanism support is "evidence" then the evidence has to be provided
        """
        invalid_input_data = {
            "molecular_mechanism": {"name": "", "support": "evidence"},
        }

        # Login
        user = User.objects.get(email="user5@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        # Authenticate by setting cookie on the test client
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        response = self.client.patch(
            self.url_lgd_update_mechanism_2,
            invalid_input_data,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 404)
        response_data = response.json()
        self.assertEqual(
            response_data["detail"],
            "Mechanism evidence is missing",
        )

    def test_update_empty_evidence(self):
        """
        Test the endpoint to update mechanism for a record with support 'evidence' but empty evidence array provided
        If the mechanism support is "evidence" then the evidence has to be provided
        """
        invalid_input_data = {
            "molecular_mechanism": {"name": "", "support": "evidence"},
            "mechanism_evidence": [],
        }

        # Login
        user = User.objects.get(email="user5@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        # Authenticate by setting cookie on the test client
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        response = self.client.patch(
            self.url_lgd_update_mechanism_2,
            invalid_input_data,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 404)
        response_data = response.json()
        self.assertEqual(
            response_data["detail"],
            "Mechanism evidence is missing",
        )

    def test_update_evidence_invalid_pmid(self):
        """
        Test the endpoint to update mechanism for a record with support 'evidence' but evidence has invalid pmid
        """
        invalid_input_data = {
            "molecular_mechanism": {"name": "", "support": "evidence"},
            "mechanism_evidence": [
                {
                    "pmid": "123456",
                    "description": "This is new evidence for the existing mechanism evidence.",
                    "evidence_types": [
                        {"primary_type": "Function", "secondary_type": ["Biochemical"]}
                    ],
                }
            ],
        }

        # Login
        user = User.objects.get(email="user5@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        # Authenticate by setting cookie on the test client
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        response = self.client.patch(
            self.url_lgd_update_mechanism_2,
            invalid_input_data,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        response_data = response.json()
        self.assertEqual(
            response_data["error"],
            "pmid '123456' not found in G2P",
        )

    def test_update_evidence_empty_primary_subtype(self):
        """
        Test the endpoint to update mechanism for a record with support 'evidence' but evidence has empty evidence primary subtype
        """
        invalid_input_data = {
            "molecular_mechanism": {"name": "", "support": "evidence"},
            "mechanism_evidence": [
                {
                    "pmid": "3897232",
                    "description": "This is new evidence for the existing mechanism evidence.",
                    "evidence_types": [
                        {"primary_type": "", "secondary_type": ["Biochemical"]}
                    ],
                }
            ],
        }

        # Login
        user = User.objects.get(email="user5@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        # Authenticate by setting cookie on the test client
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        response = self.client.patch(
            self.url_lgd_update_mechanism_2,
            invalid_input_data,
            content_type="application/json",
        )
        # Check why
        self.assertEqual(response.status_code, 400)
        response_data = response.json()
        self.assertEqual(
            response_data["error"],
            "Empty evidence subtype",
        )

    def test_update_evidence_invalid_secondary_subtype(self):
        """
        Test the endpoint to update mechanism for a record with support 'evidence' but evidence has invalid evidence secondary subtype
        """
        invalid_input_data = {
            "molecular_mechanism": {"name": "", "support": "evidence"},
            "mechanism_evidence": [
                {
                    "pmid": "3897232",
                    "description": "This is new evidence for the existing mechanism evidence.",
                    "evidence_types": [
                        {"primary_type": "Function", "secondary_type": ["dummy"]}
                    ],
                }
            ],
        }

        # Login
        user = User.objects.get(email="user5@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        # Authenticate by setting cookie on the test client
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        response = self.client.patch(
            self.url_lgd_update_mechanism_2,
            invalid_input_data,
            content_type="application/json",
        )
        # Check why
        self.assertEqual(response.status_code, 400)
        response_data = response.json()
        self.assertEqual(
            response_data["error"],
            "Invalid mechanism evidence 'dummy'",
        )

    def test_update_invalid_record(self):
        """
        Test the endpoint to update mechanism for an invalid lgd record
        Cannot update mechanism for a record that does not exist
        """

        # Login
        user = User.objects.get(email="user5@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        # Authenticate by setting cookie on the test client
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        response = self.client.patch(
            self.url_lgd_update_mechanism_invalid_record,
            self.input_data,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 404)

    def test_update_invalid_mechanism(self):
        """
        Test the endpoint to update invalid mechanism
        """
        invalid_input_data = {
            "molecular_mechanism": {"name": "dummy", "support": "inferred"}
        }

        # Login
        user = User.objects.get(email="user5@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        # Authenticate by setting cookie on the test client
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        response = self.client.patch(
            self.url_lgd_update_mechanism,
            invalid_input_data,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

        response_data = response.json()
        self.assertEqual(response_data["error"], "Invalid mechanism value 'dummy'")

    def test_update_invalid_mechanism_support(self):
        """
        Test the endpoint to update mechanism with invalid support
        """
        invalid_input_data = {"molecular_mechanism": {"name": "", "support": "dummy"}}

        # Login
        user = User.objects.get(email="user5@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        # Authenticate by setting cookie on the test client
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        response = self.client.patch(
            self.url_lgd_update_mechanism_2,
            invalid_input_data,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

        response_data = response.json()
        self.assertEqual(response_data["error"], "Invalid mechanism support 'dummy'")

    def test_update_invalid_mechanism_synopsis(self):
        """
        Test the endpoint to update invalid mechanism synopsis
        """
        invalid_input_data = {
            "mechanism_synopsis": [{"name": "dummy", "support": "inferred"}]
        }

        # Login
        user = User.objects.get(email="user5@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        # Authenticate by setting cookie on the test client
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        response = self.client.patch(
            self.url_lgd_update_mechanism_3,
            invalid_input_data,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

        response_data = response.json()
        self.assertEqual(
            response_data["error"], "Invalid mechanism synopsis value 'dummy'"
        )

    def test_update_invalid_mechanism_synopsis_support(self):
        """
        Test the endpoint to update mechanism synopsis with invalid support
        """
        invalid_input_data = {
            "mechanism_synopsis": [{"name": "loss of activity LOF", "support": "dummy"}]
        }

        # Login
        user = User.objects.get(email="user5@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        # Authenticate by setting cookie on the test client
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        response = self.client.patch(
            self.url_lgd_update_mechanism_3,
            invalid_input_data,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

        response_data = response.json()
        self.assertEqual(
            response_data["error"], "Invalid mechanism synopsis support 'dummy'"
        )

    def test_update_incompatible_mechanism_synopsis(self):
        """
        Test the endpoint to update mechanism synopsis which is not compatible with the mechansim
        """
        invalid_input_data = {
            "mechanism_synopsis": [
                {"name": "assembly-mediated GOF", "support": "inferred"}
            ]
        }

        # Login
        user = User.objects.get(email="user5@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        # Authenticate by setting cookie on the test client
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        response = self.client.patch(
            self.url_lgd_update_mechanism_3,
            invalid_input_data,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

        response_data = response.json()
        self.assertEqual(
            response_data["error"],
            "The categorisation 'assembly-mediated GOF' is not compatible with the mechanism 'loss of function'. Please choose a categorisation relevant to the selected mechanism.",
        )

    def test_update_mechanism_all_data_success(self):
        """
        Test the endpoint to update mechanism with all data
        """
        # Login
        user = User.objects.get(email="user5@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        # Authenticate by setting cookie on the test client
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        response = self.client.patch(
            self.url_lgd_update_mechanism,
            self.input_data,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)

        response_data = response.json()
        self.assertEqual(
            response_data["message"],
            "Molecular mechanism updated successfully for 'G2P00009'",
        )

        # Check locus_genotype_disease table
        locus_genotype_disease = LocusGenotypeDisease.objects.filter(
            stable_id__stable_id="G2P00009",
            mechanism_support__type="support",
            mechanism_support__value="evidence",
            is_deleted=0,
        )
        self.assertEqual(len(locus_genotype_disease), 1)

        # Check lgd_mechanism_evidence table
        lgd_mechanism_evidence = LGDMolecularMechanismEvidence.objects.filter(
            lgd__stable_id__stable_id="G2P00009", is_deleted=0
        )
        self.assertEqual(len(lgd_mechanism_evidence), 1)

        # Check lgd_mechanism_synopsis table
        lgd_mechanism_synopsis = LGDMolecularMechanismSynopsis.objects.filter(
            lgd__stable_id__stable_id="G2P00009", is_deleted=0
        )
        self.assertEqual(len(lgd_mechanism_synopsis), 1)

        # Test lgd_mechanism_evidence history table
        history_records = LGDMolecularMechanismEvidence.history.filter(
            lgd__stable_id__stable_id="G2P00009"
        )
        self.assertEqual(len(history_records), 1)

        # Test lgd_mechanism_synopsis history table
        history_records = LGDMolecularMechanismSynopsis.history.filter(
            lgd__stable_id__stable_id="G2P00009"
        )
        self.assertEqual(len(history_records), 1)

        # Test locus_genotype_disease history table
        history_records = LocusGenotypeDisease.history.filter(
            stable_id__stable_id="G2P00009"
        )
        # LGD date_review should be updated only once
        self.assertEqual(len(history_records), 1)

    def test_update_mechanism_evidence_success(self):
        """
        Test the endpoint to update mechanism evidence
        """
        input_data = {
            "molecular_mechanism": {"name": "", "support": "evidence"},
            "mechanism_evidence": [
                {
                    "pmid": "1882842",
                    "description": "text",
                    "evidence_types": [
                        {
                            "primary_type": "Rescue",
                            "secondary_type": ["Patient Cells"],
                        }
                    ],
                }
            ],
        }

        # Login
        user = User.objects.get(email="user5@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        # Authenticate by setting cookie on the test client
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        response = self.client.patch(
            self.url_lgd_update_mechanism_2,
            input_data,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)

        response_data = response.json()
        self.assertEqual(
            response_data["message"],
            "Molecular mechanism updated successfully for 'G2P00008'",
        )

        # Check locus_genotype_disease table
        locus_genotype_disease = LocusGenotypeDisease.objects.filter(
            stable_id__stable_id="G2P00008",
            mechanism_support__type="support",
            mechanism_support__value="evidence",
            is_deleted=0,
        )
        self.assertEqual(len(locus_genotype_disease), 1)

        # Check lgd_mechanism_evidence table
        lgd_mechanism_evidence = LGDMolecularMechanismEvidence.objects.filter(
            lgd__stable_id__stable_id="G2P00008", is_deleted=0
        )
        self.assertEqual(len(lgd_mechanism_evidence), 1)

        # Test lgd_mechanism_evidence history table
        history_records = LGDMolecularMechanismEvidence.history.filter(
            lgd__stable_id__stable_id="G2P00008"
        )
        self.assertEqual(len(history_records), 1)

        # Test locus_genotype_disease history table
        history_records = LocusGenotypeDisease.history.filter(
            stable_id__stable_id="G2P00008"
        )
        # LGD date_review is updated only once
        self.assertEqual(len(history_records), 1)

    def test_update_mechanism_synopsis_success(self):
        """
        Test the endpoint to update mechanism synopsis
        """
        input_data = {
            "mechanism_synopsis": [
                {"name": "interaction-disrupting LOF", "support": "inferred"}
            ]
        }

        # Login
        user = User.objects.get(email="user5@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        # Authenticate by setting cookie on the test client
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        response = self.client.patch(
            self.url_lgd_update_mechanism_3,
            input_data,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)

        response_data = response.json()
        self.assertEqual(
            response_data["message"],
            "Molecular mechanism updated successfully for 'G2P00001'",
        )

        # Check lgd_mechanism_synopsis table
        lgd_mechanism_synopsis = LGDMolecularMechanismSynopsis.objects.filter(
            lgd__stable_id__stable_id="G2P00001", is_deleted=0
        )
        self.assertEqual(len(lgd_mechanism_synopsis), 2)

        # Test lgd_mechanism_synopsis history table
        history_records = LGDMolecularMechanismSynopsis.history.filter(
            lgd__stable_id__stable_id="G2P00001"
        )
        self.assertEqual(len(history_records), 1)

        # Test locus_genotype_disease history table
        history_records = LocusGenotypeDisease.history.filter(
            stable_id__stable_id="G2P00001"
        )
        # LGD date_review is updated 1 time
        self.assertEqual(len(history_records), 1)
