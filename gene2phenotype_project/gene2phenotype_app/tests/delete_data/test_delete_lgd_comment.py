from django.test import TestCase
from django.urls import reverse
from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken
from gene2phenotype_app.models import User, LGDComment


class LGDDeleteComment(TestCase):
    """
    Test endpoint to delete a comment from a record (LGD)
    """

    fixtures = [
        "gene2phenotype_app/fixtures/attribs.json",
        "gene2phenotype_app/fixtures/cv_molecular_mechanism.json",
        "gene2phenotype_app/fixtures/disease.json",
        "gene2phenotype_app/fixtures/g2p_stable_id.json",
        "gene2phenotype_app/fixtures/g2p_stable_id.json",
        "gene2phenotype_app/fixtures/cv_molecular_mechanism.json",
        "gene2phenotype_app/fixtures/lgd_panel.json",
        "gene2phenotype_app/fixtures/locus_genotype_disease.json",
        "gene2phenotype_app/fixtures/locus.json",
        "gene2phenotype_app/fixtures/publication.json",
        "gene2phenotype_app/fixtures/sequence.json",
        "gene2phenotype_app/fixtures/user_panels.json",
        "gene2phenotype_app/fixtures/ontology_term.json",
        "gene2phenotype_app/fixtures/source.json",
        "gene2phenotype_app/fixtures/lgd_publication.json",
        "gene2phenotype_app/fixtures/lgd_comment.json",
    ]

    def setUp(self):
        self.url_delete = reverse("lgd_comment", kwargs={"stable_id": "G2P00002"})
        self.comment_to_delete = {
            "comment": "All mutations are located in the aminoterminal part of the gene, before the first epidermal growth factor-like domain."
        }
        self.comment_to_delete_2 = {"comment": "All mutations are invalid"}

    def test_delete_no_permission(self):
        """
        Test deleting the comment for non superuser
        TODO: in the future any user will be able to delete comments
        """
        # Login
        user = User.objects.get(email="user3@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        # Authenticate by setting cookie on the test client
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        response = self.client.patch(
            self.url_delete, self.comment_to_delete, content_type="application/json"
        )
        self.assertEqual(response.status_code, 403)

        response_data = response.json()
        self.assertEqual(
            response_data["error"],
            "You do not have permission to perform this action.",
        )

    # def test_invalid_delete(self):
    #     """
    #     Test deleting an invalid comment from the record (LGD)
    #     """
    #     # Login
    #     user = User.objects.get(email="john@test.ac.uk")
    #     refresh = RefreshToken.for_user(user)
    #     access_token = str(refresh.access_token)

    #     # Authenticate by setting cookie on the test client
    #     self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

    #     response = self.client.patch(
    #         self.url_delete, self.comment_to_delete_2, content_type="application/json"
    #     )
    #     self.assertEqual(response.status_code, 404)

    #     response_data = response.json()
    #     self.assertEqual(
    #         response_data["detail"], "Cannot delete comment for ID 'G2P00002'"
    #     )

    def test_lgd_comment_delete(self):
        """
        Test deleting the comment from the record (LGD)
        """
        # Login
        user = User.objects.get(email="john@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        # Authenticate by setting cookie on the test client
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        response = self.client.patch(
            self.url_delete, self.comment_to_delete, content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)

        # Check deleted record-publication
        lgd_comments = LGDComment.objects.filter(
            lgd__stable_id__stable_id="G2P00002", is_deleted=1
        )
        self.assertEqual(len(lgd_comments), 1)
