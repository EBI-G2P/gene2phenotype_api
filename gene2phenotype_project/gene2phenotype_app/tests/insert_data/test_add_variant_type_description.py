from django.test import TestCase
from django.urls import reverse
from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken

from gene2phenotype_app.models import (
    User,
    LGDVariantTypeDescription,
    LocusGenotypeDisease,
)


class LGDEditVariantTypeDescriptionTests(TestCase):
    """
    Test endpoint to add variant type description to a LGD record
    """

    fixtures = [
        "gene2phenotype_app/fixtures/attribs.json",
        "gene2phenotype_app/fixtures/cv_molecular_mechanism.json",
        "gene2phenotype_app/fixtures/disease.json",
        "gene2phenotype_app/fixtures/g2p_stable_id.json",
        "gene2phenotype_app/fixtures/lgd_panel.json",
        "gene2phenotype_app/fixtures/locus_genotype_disease.json",
        "gene2phenotype_app/fixtures/locus.json",
        "gene2phenotype_app/fixtures/publication.json",
        "gene2phenotype_app/fixtures/sequence.json",
        "gene2phenotype_app/fixtures/user_panels.json",
        "gene2phenotype_app/fixtures/ontology_term.json",
        "gene2phenotype_app/fixtures/source.json",
        "gene2phenotype_app/fixtures/lgd_publication.json",
        "gene2phenotype_app/fixtures/lgd_variant_type_description.json",
    ]

    def setUp(self):
        self.url_add_variant = reverse(
            "lgd_variant_description", kwargs={"stable_id": "G2P00002"}
        )
        self.variant_to_add = {
            "variant_descriptions": [{
                "publications": [15214012, 12451214],
                "description": "NM_000546.6:c.794T>C (p.Leu265Pro)"
            },
            {
                "publications": [12451214],
                "description": "NM_000546.6:c.794T>G"
            }
            ]
        }
        self.empty_variant_to_add = {"variant_descriptions": []}
        self.invalid_variant_to_add = {
            "variant_descriptions": [
                {
                    "publications": [12451214],
                    "description": ""
                }
            ]
        }

    def test_add_unauthorised_access(self):
        """
        Test the endpoint to add variant type description for non authenticated user
        """
        response = self.client.post(
            self.url_add_variant,
            self.variant_to_add,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 401)

    def test_add_no_permission(self):
        """
        Test the endpoint to add variant type description for user without permission to edit record
        """
        # Login
        user = User.objects.get(email="sofia@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
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
        Test the endpoint to add variant type descriptions to a record
        """
        # Login
        user = User.objects.get(email="john@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
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
            "Variant description added to the G2P entry successfully.",
        )

        # Check inserted data
        lgd_variants = LGDVariantTypeDescription.objects.filter(
            lgd__stable_id__stable_id="G2P00002", is_deleted=0
        )
        self.assertEqual(len(lgd_variants), 5)

        # Check history tables
        history_records = LGDVariantTypeDescription.history.all()
        self.assertEqual(len(history_records), 3)
        history_records_lgd = LocusGenotypeDisease.history.all()
        self.assertEqual(len(history_records_lgd), 1)

    def test_add_empty_variant_description(self):
        """
        Test the endpoint to add empty variant type description to a record
        """
        # Login
        user = User.objects.get(email="john@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
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
            "Empty variant descriptions. Please provide valid data.",
        )

    def test_add_invalid_variant_description(self):
        """
        Test the endpoint to try to add an invalid variant description to a record
        """
        # Login
        user = User.objects.get(email="john@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        response = self.client.post(
            self.url_add_variant,
            self.invalid_variant_to_add,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
