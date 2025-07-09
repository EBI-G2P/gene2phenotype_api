from django.test import TestCase
from django.urls import reverse
from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken
from gene2phenotype_app.models import (
    User,
    LGDComment,
)


class LGDEditCommentEndpoint(TestCase):
    """
    Test endpoint to add comments to a LGD record
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
        self.url_add_comment = reverse("lgd_comment", kwargs={"stable_id": "G2P00005"})
        self.url_add_comment_2 = reverse(
            "lgd_comment", kwargs={"stable_id": "G2P00001"}
        )
        self.comment_to_add = {
            "comments": [
                {
                    "comment": "Variants associated with gene-disease association of great relevance.",
                    "is_public": 1,
                },
                {"comment": "Need to review PMID:1882842", "is_public": 0},
            ]
        }
        self.comment_to_add_2 = {"comments": []}

    def test_add_no_permission(self):
        """
        Test the endpoint to add comments for non authenticated user
        """

        response = self.client.post(
            self.url_add_comment,
            self.comment_to_add,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 401)

    def test_add_no_permission_2(self):
        """
        Test the endpoint to add comments for user without permission to edit record
        """
        # Login
        user = User.objects.get(email="john@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        # Authenticate by setting cookie on the test client
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        response = self.client.post(
            self.url_add_comment_2,
            self.comment_to_add,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)

        response_data = response.json()
        self.assertEqual(response_data["error"], "No permission to edit G2P00001")

    def test_add_lgd_comments(self):
        """
        Test the endpoint to add comments to a record
        """
        # Login
        user = User.objects.get(email="user1@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        # Authenticate by setting cookie on the test client
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        response = self.client.post(
            self.url_add_comment,
            self.comment_to_add,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)

        response_data = response.json()
        self.assertEqual(
            response_data["message"], "Comments added to the G2P entry successfully."
        )

        # Check inserted data
        lgd_comments = LGDComment.objects.filter(
            lgd__stable_id__stable_id="G2P00005", is_deleted=0
        )
        self.assertEqual(len(lgd_comments), 2)

    def test_add_empty_comment(self):
        """
        Test the endpoint to add empty comment to a record
        """

        # Login
        user = User.objects.get(email="user1@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        # Authenticate by setting cookie on the test client
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        response = self.client.post(
            self.url_add_comment,
            self.comment_to_add_2,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

        response_data = response.json()
        self.assertEqual(
            response_data["error"], "Empty comment. Please provide valid data."
        )
