from django.conf import settings
from django.test import TestCase
from django.urls import reverse
from rest_framework_simplejwt.tokens import RefreshToken

from gene2phenotype_app.models import Attrib, LocusGenotypeDisease, User


class LGDUpdateGenotypeTests(TestCase):
    fixtures = [
        f"gene2phenotype_app/fixtures/{name}.json"
        for name in [
            "attribs", "cv_molecular_mechanism", "disease", "g2p_stable_id",
            "locus_genotype_disease", "locus", "sequence", "user_panels",
            "ontology_term", "source",
        ]
    ]

    def setUp(self):
        self.url = reverse("lgd_update_genotype", kwargs={"stable_id": "G2P00001"})
        self.lgd = LocusGenotypeDisease.objects.get(stable_id__stable_id="G2P00001")
        self.original_genotype_id = self.lgd.genotype_id
        self.genotype = Attrib.objects.get(
            type__code="genotype", value="monoallelic_autosomal"
        )
        self.user = User.objects.get(email="user5@test.ac.uk")
        self.authenticate(self.user)

    def authenticate(self, user):
        token = RefreshToken.for_user(user)
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = str(token.access_token)

    def patch(self, data, url=None):
        return self.client.patch(url or self.url, data, content_type="application/json")

    def assert_unchanged(self):
        self.lgd.refresh_from_db()
        self.assertEqual(self.lgd.genotype_id, self.original_genotype_id)

    def test_success_and_history(self):
        self.assertTrue(self.user.is_superuser)
        history_count = self.lgd.history.count()
        response = self.patch({"genotype": self.genotype.value})
        self.assertEqual(response.status_code, 200, response.content)
        self.lgd.refresh_from_db()
        self.assertEqual(self.lgd.genotype_id, self.genotype.pk)
        self.assertEqual(self.lgd.history.count(), history_count + 1)
        self.assertEqual(self.lgd.history.first().history_user_id, self.user.pk)

    def test_anonymous_denied(self):
        self.client.cookies.clear()
        response = self.patch({"genotype": self.genotype.value})
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json(), {"error": "Authentication credentials were not provided."})
        self.assert_unchanged()

    def test_regular_user_denied(self):
        user = User.objects.get(email="user1@test.ac.uk")
        self.assertFalse(user.is_superuser)
        self.authenticate(user)
        response = self.patch({"genotype": self.genotype.value})
        self.assertEqual(response.status_code, 403)
        other_response = self.client.post(
            reverse("lgd_disease_updates"), [], content_type="application/json"
        )
        self.assertEqual(response.json(), other_response.json())
        self.assert_unchanged()

    def test_invalid_or_missing_genotype(self):
        for data in [
            {}, {"genotype": None}, {"genotype": ""}, {"genotype": "   "},
            {"genotype": "unknown"}, {"genotype": "definitive"},
            {"genotype": []}, [],
        ]:
            with self.subTest(data=data):
                self.assertEqual(self.patch(data).status_code, 400)
                self.assert_unchanged()

    def test_unknown_or_deleted_record(self):
        url = reverse("lgd_update_genotype", kwargs={"stable_id": "G2P99999"})
        response = self.patch({"genotype": self.genotype.value}, url)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {"error": "No G2PStableID matches the given query."})
        self.lgd.is_deleted = 1
        self.lgd.save()
        response = self.patch({"genotype": self.genotype.value})
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {"error": "Could not find 'Entry' for ID 'G2P00001'"})
        self.assert_unchanged()

    def test_duplicate_record_rejected(self):
        duplicate = LocusGenotypeDisease.objects.exclude(pk=self.lgd.pk).first()
        duplicate.locus = self.lgd.locus
        duplicate.disease = self.lgd.disease
        duplicate.mechanism = self.lgd.mechanism
        duplicate.genotype = self.genotype
        duplicate.save()
        response = self.patch({"genotype": self.genotype.value})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json(),
            {"error": "Found a different record with same locus, genotype, disease "
             f"and mechanism: '{duplicate.stable_id.stable_id}'"},
        )
        self.assert_unchanged()

    def test_same_genotype_rejected(self):
        response = self.patch({"genotype": self.lgd.genotype.value})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json(),
            {"error": "G2P record 'G2P00001' already has genotype value "
             f"{self.lgd.genotype.value}"},
        )
        self.assert_unchanged()

    def test_field_validation_messages(self):
        for data, message in [
            ({}, "This field is required."),
            ({"genotype": None}, "This field may not be null."),
            ({"genotype": ""}, "This field may not be blank."),
        ]:
            with self.subTest(data=data):
                response = self.patch(data)
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.json(), {"error": {"genotype": [message]}})
                self.assert_unchanged()

    def test_invalid_vocabulary_message(self):
        for value in ["unknown", "definitive"]:
            with self.subTest(value=value):
                response = self.patch({"genotype": value})
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.json(), {"error": f"Invalid genotype value {value}"})
        self.assert_unchanged()

    def test_other_methods_not_allowed(self):
        for method in ["delete", "put", "post", "get"]:
            with self.subTest(method=method):
                response = getattr(self.client, method)(self.url)
                self.assertEqual(response.status_code, 405)
                self.assert_unchanged()

    def test_genotype_matches_gene_chromosome(self):
        cases = [
            ("12", "monoallelic_X_hemizygous", False),
            ("12", "monoallelic_X_heterozygous", False),
            ("12", "monoallelic_Y_hemizygous", False),
            ("12", "mitochondrial", False),
            ("12", "monoallelic_PAR", False),
            ("X", "monoallelic_autosomal", False),
            ("Y", "biallelic_autosomal", False),
            ("Y", "monoallelic_X_hemizygous", False),
            ("X", "monoallelic_Y_hemizygous", False),
            ("MT", "biallelic_PAR", False),
            ("12", "monoallelic_autosomal", True),
            ("X", "monoallelic_X_hemizygous", True),
            ("X", "monoallelic_X_heterozygous", True),
            ("Y", "monoallelic_Y_hemizygous", True),
            ("MT", "mitochondrial", True),
            ("X", "monoallelic_PAR", True),
            ("Y", "biallelic_PAR", True),
        ]
        sequence = self.lgd.locus.sequence
        for chromosome, genotype, valid in cases:
            with self.subTest(chromosome=chromosome, genotype=genotype):
                # Restore the original genotype before each independent update.
                LocusGenotypeDisease.objects.filter(pk=self.lgd.pk).update(
                    genotype_id=self.original_genotype_id
                )
                sequence.name = chromosome
                sequence.save()
                history_count = self.lgd.history.count()
                response = self.patch({"genotype": genotype})
                self.assertEqual(response.status_code, 200 if valid else 400)
                self.lgd.refresh_from_db()
                if valid:
                    self.assertEqual(self.lgd.genotype.value, genotype)
                else:
                    self.assertEqual(
                        response.json(),
                        {"error": f"Invalid genotype '{genotype}' for locus '{self.lgd.locus.name}'"},
                    )
                    self.assert_unchanged()
                    self.assertEqual(self.lgd.history.count(), history_count)
