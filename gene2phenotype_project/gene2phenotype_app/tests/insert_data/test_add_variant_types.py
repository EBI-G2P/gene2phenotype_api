from django.test import TestCase
from django.urls import reverse
from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken
from gene2phenotype_app.models import (
    User,
    LGDVariantType,
    LocusGenotypeDisease,
)


class LGDEditVariantTypesTests(TestCase):
    """
    Test endpoint to add variant types to a LGD record
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
        "gene2phenotype_app/fixtures/lgd_variant_type.json",
    ]

    def setUp(self):
        self.url_add_variant = reverse(
            "lgd_variant_type", kwargs={"stable_id": "G2P00002"}
        )
        self.variant_to_add = {
            "variant_types": [
                {
                    "comment": "this is a comment",
                    "de_novo": False,
                    "inherited": True,
                    "nmd_escape": False,
                    "primary_type": "protein_changing",
                    "secondary_type": "stop_gained",
                    "supporting_papers": ["12451214"],
                    "unknown_inheritance": True,
                }
            ]
        }
        self.empty_variant_to_add = {"variant_types": []}
        # test activity logs after insertion
        self.url_base_activity_logs = reverse("activity_logs")

    def test_add_unauthorised_access(self):
        """
        Test the endpoint to add variant types for non authenticated user
        """
        response = self.client.post(
            self.url_add_variant,
            self.variant_to_add,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 401)

    def test_add_no_permission(self):
        """
        Test the endpoint to add variant types for user without permission to edit record
        """
        # Login
        user = User.objects.get(email="sofia@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        # Authenticate by setting cookie on the test client
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        response = self.client.post(
            self.url_add_variant,
            self.variant_to_add,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)

        response_data = response.json()
        self.assertEqual(
            response_data["error"], "No permission to update record 'G2P00002'"
        )

    def test_add_lgd_variant_types(self):
        """
        Test the endpoint to add variant types to a record
        """
        # Login
        user = User.objects.get(email="john@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        # Authenticate by setting cookie on the test client
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        response = self.client.post(
            self.url_add_variant,
            self.variant_to_add,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)

        response_data = response.json()
        self.assertEqual(
            response_data["message"],
            "Variant type added to the G2P entry successfully.",
        )

        # Check inserted data
        lgd_variants = LGDVariantType.objects.filter(
            lgd__stable_id__stable_id="G2P00002", is_deleted=0
        )
        self.assertEqual(len(lgd_variants), 3)

        # Check history tables
        history_records = LGDVariantType.history.all()
        self.assertEqual(len(history_records), 1)
        history_records_lgd = LocusGenotypeDisease.history.all()
        self.assertEqual(len(history_records_lgd), 1)

        # Query the activity logs
        url_activity_logs = f"{self.url_base_activity_logs}?stable_id=G2P00002"
        response_logs = self.client.get(url_activity_logs)
        self.assertEqual(response_logs.status_code, 200)
        response_logs_data = response_logs.json()
        self.assertEqual(response_logs_data["results"][0]["change_type"], "created")

    def test_add_empty_variant_type(self):
        """
        Test the endpoint to add empty variant types to a record
        """
        # Login
        user = User.objects.get(email="john@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        # Authenticate by setting cookie on the test client
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        response = self.client.post(
            self.url_add_variant,
            self.empty_variant_to_add,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

        response_data = response.json()
        self.assertEqual(
            response_data["error"],
            "Empty variant type. Please provide valid data.",
        )
