from django.conf import settings
from django.test import TestCase
from django.urls import reverse
from rest_framework_simplejwt.tokens import RefreshToken

from gene2phenotype_app.models import LGDVariantTypeComment, LocusGenotypeDisease, User


class LGDEditVariantTypeCommentEndpoint(TestCase):
    """
    Test endpoint to delete variant type comments from a record (LGD).
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
        "gene2phenotype_app/fixtures/lgd_variant_type_comment.json",
    ]

    def setUp(self):
        self.url_delete = reverse(
            "lgd_variant_type_comment", kwargs={"stable_id": "G2P00002"}
        )
        self.url_lgd_detail = reverse("lgd", kwargs={"stable_id": "G2P00002"})
        self.original_date_review = LocusGenotypeDisease.objects.get(
            stable_id__stable_id="G2P00002"
        ).date_review

    def authenticate(self, email):
        user = User.objects.get(email=email)
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

    def test_delete_unauthorised_access(self):
        response = self.client.patch(
            self.url_delete,
            {"comment_id": 1},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 401)

    def test_delete_non_superuser(self):
        self.authenticate("mary@test.ac.uk")

        response = self.client.patch(
            self.url_delete,
            {"comment_id": 1},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.json()["error"],
            "You do not have permission to perform this action.",
        )

    def test_delete_no_permission(self):
        self.authenticate("sofia@test.ac.uk")

        response = self.client.patch(
            self.url_delete,
            {"comment_id": 1},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.json()["error"], "No permission to update record 'G2P00002'"
        )

    def test_delete_missing_comment_id(self):
        self.authenticate("john@test.ac.uk")

        response = self.client.patch(
            self.url_delete,
            {},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()["error"],
            "Missing input key 'comment_id'",
        )

    def test_delete_missing_comment(self):
        self.authenticate("john@test.ac.uk")

        response = self.client.patch(
            self.url_delete,
            {"comment_id": 999},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            response.json()["error"],
            "Cannot find variant type comment for record 'G2P00002'",
        )

    def test_delete_already_soft_deleted_comment(self):
        self.authenticate("john@test.ac.uk")

        variant_type_comment = LGDVariantTypeComment.objects.get(id=1, is_deleted=0)
        variant_type_comment.is_deleted = 1
        variant_type_comment.save()

        response = self.client.patch(
            self.url_delete,
            {"comment_id": variant_type_comment.id},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            response.json()["error"],
            "Cannot find variant type comment for record 'G2P00002'",
        )

    def test_delete_variant_type_comment(self):
        self.authenticate("john@test.ac.uk")

        variant_type_comment = LGDVariantTypeComment.objects.get(id=1, is_deleted=0)

        response = self.client.patch(
            self.url_delete,
            {"comment_id": variant_type_comment.id},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["message"],
            "Variant type comment successfully deleted for record 'G2P00002'",
        )

        variant_type_comment.refresh_from_db()
        self.assertEqual(variant_type_comment.is_deleted, 1)

        history_records = LGDVariantTypeComment.history.all()
        self.assertEqual(len(history_records), 1)
        self.assertEqual(history_records[0].is_deleted, 1)

        lgd_obj = LocusGenotypeDisease.objects.get(stable_id__stable_id="G2P00002")
        self.assertNotEqual(lgd_obj.date_review, self.original_date_review)

    def test_deleted_comment_hidden_from_authenticated_lgd_detail(self):
        self.authenticate("john@test.ac.uk")

        variant_type_comment = LGDVariantTypeComment.objects.get(id=1, is_deleted=0)

        delete_response = self.client.patch(
            self.url_delete,
            {"comment_id": variant_type_comment.id},
            content_type="application/json",
        )
        self.assertEqual(delete_response.status_code, 200)

        detail_response = self.client.get(self.url_lgd_detail)
        self.assertEqual(detail_response.status_code, 200)

        inframe_insertion = next(
            variant
            for variant in detail_response.data["variant_type"]
            if variant["term"] == "inframe_insertion"
        )
        self.assertEqual(inframe_insertion["comments"], [])
