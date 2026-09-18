from django.conf import settings
from django.test import TestCase
from django.urls import reverse
from rest_framework_simplejwt.tokens import RefreshToken

from gene2phenotype_app.models import (
    LGDVariantTypeComment,
    LocusGenotypeDisease,
    User,
)


class LGDEditVariantTypeCommentEndpoint(TestCase):
    """
    Test endpoint to delete variant type comments from a record (LGD)
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
        "gene2phenotype_app/fixtures/lgd_variant_type.json",
        "gene2phenotype_app/fixtures/lgd_variant_type_publication.json",
        "gene2phenotype_app/fixtures/lgd_variant_type_comment.json",
    ]

    def setUp(self):
        self.url_delete = reverse(
            "lgd_variant_type_comment",
            kwargs={"stable_id": "G2P00002", "comment_id": 1},
        )

    def _authenticate(self, email):
        user = User.objects.get(email=email)
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

    def test_invalid_delete(self):
        """
        Cannot delete a variant type comment that does not exist.
        """
        self._authenticate("john@test.ac.uk")

        url = reverse(
            "lgd_variant_type_comment",
            kwargs={"stable_id": "G2P00002", "comment_id": 1000},
        )
        response = self.client.patch(url, {}, content_type="application/json")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            response.json()["error"],
            "Cannot find variant type comment for record 'G2P00002'",
        )

    def test_delete_non_superuser(self):
        """
        Only super users can delete variant type comments.
        """
        self._authenticate("mary@test.ac.uk")

        response = self.client.patch(
            self.url_delete, {}, content_type="application/json"
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.json()["error"],
            "You do not have permission to perform this action.",
        )

    def test_delete_no_permission(self):
        """
        Super users still need panel permission to edit the record.
        """
        self._authenticate("sofia@test.ac.uk")

        response = self.client.patch(
            self.url_delete, {}, content_type="application/json"
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.json()["error"], "No permission to update record 'G2P00002'"
        )

    def test_lgd_variant_type_comment_delete(self):
        """
        Test successfully deleting the variant type comment from the record (LGD)
        """
        self._authenticate("john@test.ac.uk")

        lgd_variant_type_comments = LGDVariantTypeComment.objects.filter(
            lgd_variant_type__lgd__stable_id__stable_id="G2P00002", is_deleted=0
        )
        self.assertEqual(len(lgd_variant_type_comments), 1)

        response = self.client.patch(
            self.url_delete, {}, content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)

        lgd_deleted_variant_type_comments = LGDVariantTypeComment.objects.filter(
            lgd_variant_type__lgd__stable_id__stable_id="G2P00002", is_deleted=1
        )
        self.assertEqual(len(lgd_deleted_variant_type_comments), 1)

        history_records = LGDVariantTypeComment.history.all()
        self.assertEqual(len(history_records), 1)
        self.assertEqual(history_records[0].is_deleted, 1)

        history_records_lgd = LocusGenotypeDisease.history.all()
        self.assertEqual(len(history_records_lgd), 0)
