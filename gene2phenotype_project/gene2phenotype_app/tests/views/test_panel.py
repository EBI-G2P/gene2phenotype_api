import csv
from io import StringIO
from django.test import TestCase
from django.conf import settings
from django.urls import reverse
import datetime
from gene2phenotype_app.models import User
from rest_framework_simplejwt.tokens import RefreshToken


class PanelListEndpointTests(TestCase):
    """
    Test the panel endpoint: PanelList
    """

    fixtures = [
        "gene2phenotype_app/fixtures/user_panels.json",
        "gene2phenotype_app/fixtures/attribs.json",
    ]

    def setUp(self):
        self.url_panels = reverse("list_panels")

    def test_get_panel_list(self):
        """
        Test for non-authenticated users.
        Non-visible panels are not included in the response.
        """
        response = self.client.get(self.url_panels)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data.get("count"), 3)

    def test_login_get_panel_list(self):
        """
        Test for authenticated users.
        All panels are included in the response.
        """
        user = User.objects.get(email="user5@test.ac.uk")
        # Create token for the user
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        # Authenticate by setting cookie on the test client
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        response = self.client.get(self.url_panels)
        self.assertEqual(response.status_code, 200)

        self.assertEqual(response.data.get("count"), 4)


class PanelDetailsEndpointTests(TestCase):
    """
    Test the panel endpoint: PanelDetail
    """

    fixtures = [
        "gene2phenotype_app/fixtures/user_panels.json",
        "gene2phenotype_app/fixtures/attribs.json",
        "gene2phenotype_app/fixtures/g2p_stable_id.json",
        "gene2phenotype_app/fixtures/locus.json",
        "gene2phenotype_app/fixtures/sequence.json",
        "gene2phenotype_app/fixtures/disease.json",
        "gene2phenotype_app/fixtures/ontology_term.json",
        "gene2phenotype_app/fixtures/source.json",
        "gene2phenotype_app/fixtures/locus_genotype_disease.json",
        "gene2phenotype_app/fixtures/lgd_panel.json",
        "gene2phenotype_app/fixtures/cv_molecular_mechanism.json",
    ]

    def test_get_panel_details(self):
        """
        Get the details for a visible panel.
        """
        url_panel_dd = reverse("panel_details", kwargs={"name": "DD"})
        response = self.client.get(url_panel_dd)
        self.assertEqual(response.status_code, 200)

        expected_data = {
            "name": "DD",
            "description": "Developmental disorders",
            "last_updated": datetime.date(2017, 4, 24),
            "stats": {
                "total_records": 1,
                "total_genes": 1,
                "by_confidence": {"definitive": 1},
            },
        }
        self.assertEqual(response.data, expected_data)

    def test_panel_no_permission(self):
        """
        Returns code 401 for non-authenticated users when accessing a non-visible panel.
        """
        url_panel_ear = reverse("panel_details", kwargs={"name": "Ear"})
        response = self.client.get(url_panel_ear)
        self.assertEqual(response.status_code, 401)

    def test_invalid_panel(self):
        """
        Returns code 404 when accessing an invalid panel.
        """
        url_panel_ear = reverse("panel_details", kwargs={"name": "Ears"})
        response = self.client.get(url_panel_ear)
        self.assertEqual(response.status_code, 404)


class PanelSummaryEndpointTests(TestCase):
    """
    Test the panel endpoint: PanelRecordsSummary
    """

    fixtures = [
        "gene2phenotype_app/fixtures/user_panels.json",
        "gene2phenotype_app/fixtures/attribs.json",
        "gene2phenotype_app/fixtures/g2p_stable_id.json",
        "gene2phenotype_app/fixtures/locus.json",
        "gene2phenotype_app/fixtures/sequence.json",
        "gene2phenotype_app/fixtures/disease.json",
        "gene2phenotype_app/fixtures/ontology_term.json",
        "gene2phenotype_app/fixtures/source.json",
        "gene2phenotype_app/fixtures/locus_genotype_disease.json",
        "gene2phenotype_app/fixtures/lgd_panel.json",
        "gene2phenotype_app/fixtures/cv_molecular_mechanism.json",
    ]

    def setUp(self):
        self.url_panels = reverse("panel_summary", kwargs={"name": "DD"})

    def test_get_panel_summary(self):
        """
        Get the summary for a visible panel.
        """
        response = self.client.get(self.url_panels)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data.get("records_summary")), 1)


class PanelDownloadEndpointTests(TestCase):
    """
    Test the panel download endpoint: PanelDownload
    """

    fixtures = [
        "gene2phenotype_app/fixtures/user_panels.json",
        "gene2phenotype_app/fixtures/attribs.json",
        "gene2phenotype_app/fixtures/g2p_stable_id.json",
        "gene2phenotype_app/fixtures/locus.json",
        "gene2phenotype_app/fixtures/sequence.json",
        "gene2phenotype_app/fixtures/disease.json",
        "gene2phenotype_app/fixtures/ontology_term.json",
        "gene2phenotype_app/fixtures/source.json",
        "gene2phenotype_app/fixtures/locus_genotype_disease.json",
        "gene2phenotype_app/fixtures/lgd_panel.json",
        "gene2phenotype_app/fixtures/cv_molecular_mechanism.json",
    ]

    def test_download_visible_panel(self):
        """
        Download a visible panel.
        """
        url_panel = reverse("panel_download", kwargs={"name": "DD"})
        response = self.client.get(url_panel)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")

        # Check the content
        content_disposition = response.get("Content-Disposition")
        self.assertTrue(content_disposition.startswith("attachment"))
        self.assertIn("filename=", content_disposition)

        content = response.content.decode("utf-8")
        csv_reader = csv.reader(StringIO(content))
        rows = list(csv_reader)

        # Check content of file
        self.assertEqual(len(rows), 2)
        self.assertIn("g2p id", rows[0])

        expected_data = [
            "G2P00001",
            "CEP290",
            "",
            "29021",
            "BBS14; CT87; KIAA0373",
            "CEP290-related JOUBERT SYNDROME TYPE 5",
            "610188",
            "",
            "biallelic_autosomal",
            "",
            "definitive",
            "",
            "",
            "loss of function",
            "evidence",
            "",
            "",
            "",
            "DD; Eye",
            "",
            "2017-04-24 16:33:40+00:00",
        ]

        self.assertEqual(rows[1], expected_data)

    def test_download_all_visible_panel(self):
        """
        Download a all visible panel (non authenticated user)
        """
        url_panel = reverse("panel_download", kwargs={"name": "all"})
        response = self.client.get(url_panel)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")

        # Check the content
        content_disposition = response.get("Content-Disposition")
        self.assertTrue(content_disposition.startswith("attachment"))
        self.assertIn("filename=", content_disposition)

        content = response.content.decode("utf-8")
        csv_reader = csv.reader(StringIO(content))
        rows = list(csv_reader)

        # Check content of file
        self.assertEqual(len(rows), 4)
        self.assertIn("g2p id", rows[0])

        expected_data = [
            "G2P00002",
            "RAB27A",
            "",
            "9766",
            "GS2; RAB27",
            "RAB27A-related Griscelli syndrome",
            "",
            "",
            "biallelic_autosomal",
            "",
            "definitive",
            "",
            "",
            "loss of function",
            "evidence",
            "",
            "",
            "",
            "Cardiac",
            "",
            "2018-07-05 16:33:03+00:00",
        ]

        self.assertEqual(rows[2], expected_data)