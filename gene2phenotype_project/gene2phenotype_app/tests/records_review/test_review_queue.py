from datetime import timedelta

from django.conf import settings
from django.test import TestCase
from django.urls import reverse
from rest_framework_simplejwt.tokens import RefreshToken

from gene2phenotype_app.models import User


class ReviewQueueEndpointTests(TestCase):
    fixtures = [
        "gene2phenotype_app/fixtures/attribs.json",
        "gene2phenotype_app/fixtures/ontology_term.json",
        "gene2phenotype_app/fixtures/cv_molecular_mechanism.json",
        "gene2phenotype_app/fixtures/disease.json",
        "gene2phenotype_app/fixtures/g2p_stable_id.json",
        "gene2phenotype_app/fixtures/locus_genotype_disease.json",
        "gene2phenotype_app/fixtures/locus.json",
        "gene2phenotype_app/fixtures/sequence.json",
        "gene2phenotype_app/fixtures/source.json",
        "gene2phenotype_app/fixtures/user_panels.json",
    ]

    def setUp(self):
        self.url_review_queue = reverse("review_queue")
        self.url_review_queue_detail = reverse(
            "review_queue_detail", kwargs={"case_id": 1}
        )

    def _login(self, email):
        user = User.objects.get(email=email)
        refresh = RefreshToken.for_user(user)
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = str(
            refresh.access_token
        )
        return refresh

    def _assert_access_denied(self, status_code):
        for method, url in [
            ("get", self.url_review_queue),
            ("post", self.url_review_queue),
            ("get", self.url_review_queue_detail),
            ("patch", self.url_review_queue_detail),
        ]:
            with self.subTest(method=method, url=url):
                response = getattr(self.client, method)(url)
                self.assertEqual(response.status_code, status_code)
                if status_code == 401:
                    self.assertIn("error", response.json())
                    self.assertIn("WWW-Authenticate", response)
                else:
                    self.assertEqual(
                        response.json()["detail"],
                        "You do not have permission to perform this action.",
                    )

    def test_review_queue_requires_authentication(self):
        self._assert_access_denied(401)

    def test_review_queue_with_deleted_access_token_and_valid_refresh_token(self):
        refresh = self._login("user5@test.ac.uk")
        self.client.cookies[settings.SIMPLE_JWT["REFRESH_COOKIE"]] = str(refresh)
        del self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]]

        self._assert_access_denied(401)

    def test_review_queue_with_expired_access_token(self):
        refresh = self._login("user5@test.ac.uk")
        access_token = refresh.access_token
        access_token.set_exp(lifetime=timedelta(seconds=-1))
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = str(access_token)

        self._assert_access_denied(401)

    def test_review_queue_requires_superuser(self):
        self._login("user1@test.ac.uk")

        self._assert_access_denied(403)

    def test_create_and_update_review_case(self):
        self._login("user5@test.ac.uk")

        payload = {
            "stable_id": "G2P00001",
            "summary": "Record needs updates before next panel release.",
            "items": [
                {
                    "component": "mechanism",
                    "status": "open",
                    "comment": "Check mechanism evidence.",
                },
                {
                    "component": "disease",
                    "status": "open",
                    "comment": "Confirm disease name.",
                },
            ],
        }

        response_create = self.client.post(
            self.url_review_queue, payload, content_type="application/json"
        )
        self.assertEqual(response_create.status_code, 201)
        self.assertEqual(response_create.data["status"], "open")
        self.assertEqual(len(response_create.data["items"]), 2)

        response_list = self.client.get(self.url_review_queue)
        self.assertEqual(response_list.status_code, 200)
        self.assertEqual(response_list.data["count"], 1)

        case_id = response_create.data["id"]
        response_update = self.client.patch(
            reverse("review_queue_detail", kwargs={"case_id": case_id}),
            {"status": "under_review"},
            content_type="application/json",
        )
        self.assertEqual(response_update.status_code, 200)
        self.assertEqual(response_update.data["status"], "under_review")
