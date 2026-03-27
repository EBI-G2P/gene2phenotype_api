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

    def _login(self, email):
        user = User.objects.get(email=email)
        refresh = RefreshToken.for_user(user)
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = str(
            refresh.access_token
        )

    def test_review_queue_requires_authentication(self):
        response = self.client.get(self.url_review_queue)
        self.assertEqual(response.status_code, 403)

    def test_create_and_update_review_case(self):
        self._login("user5@test.ac.uk")

        payload = {
            "stable_id": "G2P00001",
            "summary": "Record needs updates before next panel release.",
            "items": [
                {
                    "component": "mechanism",
                    "details": {"note": "Review mechanism support."},
                    "status": "open",
                    "comment": "Check mechanism evidence.",
                },
                {
                    "component": "disease",
                    "details": {"note": "Disease name may need update."},
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
