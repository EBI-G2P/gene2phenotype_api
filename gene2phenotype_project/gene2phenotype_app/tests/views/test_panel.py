import csv
from io import StringIO
from django.test import TestCase
from django.conf import settings
from django.urls import reverse
import datetime
from gene2phenotype_app.models import LGDVariantGenccConsequence, User
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
        self.assertEqual(response.data.get("count"), 4)

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

        self.assertEqual(response.data.get("count"), 5)


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
        self.assertEqual(response.data["error"], "No permission to access Panel Ear")

    def test_invalid_panel(self):
        """
        Returns code 404 when accessing an invalid panel.
        """
        url_panel_ear = reverse("panel_details", kwargs={"name": "Ears"})
        response = self.client.get(url_panel_ear)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data["error"], "No matching Panel found for: Ears")


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
        "gene2phenotype_app/fixtures/publication.json",
        "gene2phenotype_app/fixtures/ontology_term.json",
        "gene2phenotype_app/fixtures/source.json",
        "gene2phenotype_app/fixtures/locus_genotype_disease.json",
        "gene2phenotype_app/fixtures/lgd_panel.json",
        "gene2phenotype_app/fixtures/lgd_publication.json",
        "gene2phenotype_app/fixtures/lgd_variant_type.json",
        "gene2phenotype_app/fixtures/lgd_variant_type_publication.json",
        "gene2phenotype_app/fixtures/lgd_variant_consequence.json",
        "gene2phenotype_app/fixtures/cv_molecular_mechanism.json",
    ]

    def setUp(self):
        self.url_panel_dd = reverse("panel_summary", kwargs={"name": "DD"})
        self.url_panel_cardiac = reverse("panel_summary", kwargs={"name": "Cardiac"})

    def test_get_dd_panel_summary(self):
        """
        Get the summary for a visible panel.
        """
        response = self.client.get(self.url_panel_dd)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data.get("records_summary")), 1)

    def test_get_cardiac_panel_summary(self):
        """
        Get the summary for a visible panel.
        """
        response = self.client.get(self.url_panel_cardiac)
        self.assertEqual(response.status_code, 200)
        records_summary = response.data.get("records_summary")
        self.assertEqual(len(records_summary), 1)
        self.assertEqual(len(list(records_summary)[0]["variant_type"]), 2)
        self.assertEqual(len(list(records_summary)[0]["variant_consequence"]), 1)

    def test_get_panel_summary_with_only_deleted_variant_consequence(self):
        """
        Records with only deleted variant consequences should still be returned.
        """
        LGDVariantGenccConsequence.objects.filter(lgd_id=2).update(is_deleted=1)

        response = self.client.get(self.url_panel_cardiac)

        self.assertEqual(response.status_code, 200)

        record = next(
            item
            for item in response.data["records_summary"]
            if item["stable_id"] == "G2P00002"
        )
        self.assertEqual(record["variant_consequence"], [])
        self.assertCountEqual(
            record["variant_type"], ["inframe_insertion", "intron_variant"]
        )


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
        "gene2phenotype_app/fixtures/publication.json",
        "gene2phenotype_app/fixtures/mined_publication.json",
        "gene2phenotype_app/fixtures/lgd_panel.json",
        "gene2phenotype_app/fixtures/cv_molecular_mechanism.json",
        "gene2phenotype_app/fixtures/lgd_mechanism_evidence.json",
        "gene2phenotype_app/fixtures/lgd_mechanism_synopsis.json",
        "gene2phenotype_app/fixtures/lgd_publication.json",
        "gene2phenotype_app/fixtures/lgd_mined_publication.json",
        "gene2phenotype_app/fixtures/lgd_comment.json",
        "gene2phenotype_app/fixtures/lgd_phenotype.json",
        "gene2phenotype_app/fixtures/lgd_cross_cutting_modifier.json",
        "gene2phenotype_app/fixtures/lgd_variant_type.json",
        "gene2phenotype_app/fixtures/lgd_variant_type_publication.json",
        "gene2phenotype_app/fixtures/lgd_variant_consequence.json",
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
            "assembly-mediated GOF:inferred",
            "3897232 -> function: biochemical",
            "HP:0033127",
            "3897232",
            "7866404",
            "DD; Eye",
            "JLNS is due to altered gene product sequence",
            "2017-04-24 16:33:40+00:00",
            "",
        ]

        self.assertEqual(rows[1], expected_data)

    def test_download_all_visible_panel(self):
        """
        Download all visible panels (non authenticated user)
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
        self.assertEqual(len(rows), 6)
        self.assertIn("g2p id", rows[0])

        row = next(row for row in rows[1:] if row[0] == "G2P00002")

        self.assertEqual(row[0], "G2P00002")
        self.assertEqual(row[1], "RAB27A")
        self.assertEqual(row[2], "")
        self.assertEqual(row[3], "9766")
        self.assertEqual(row[5], "RAB27A-related Griscelli syndrome")
        self.assertEqual(row[6], "")
        self.assertEqual(row[7], "")
        self.assertEqual(row[8], "biallelic_autosomal")
        self.assertEqual(
            row[9], "typified by incomplete penetrance; typically de novo"
        )
        self.assertEqual(row[10], "definitive")
        self.assertEqual(row[11], "absent gene product")
        self.assertEqual(row[13], "loss of function")
        self.assertEqual(row[14], "evidence")
        self.assertEqual(row[16], "15214012 -> function: protein interaction")
        self.assertEqual(row[19], "32302040")
        self.assertEqual(row[20], "Cardiac")
        self.assertEqual(
            row[21],
            "All mutations are located in the aminoterminal part of the gene, before the first epidermal growth factor-like domain.",
        )
        self.assertEqual(row[22], "2018-07-05 16:33:03+00:00")
        self.assertEqual(row[23], "under review")
        self.assertCountEqual(row[4].split("; "), ["GS2", "RAB27"])
        self.assertCountEqual(
            row[12].split("; "), ["inframe_insertion", "intron_variant"]
        )
        self.assertCountEqual(
            row[15].split("; "),
            ["assembly-mediated GOF:inferred", "aggregation:inferred"],
        )
        self.assertCountEqual(
            row[17].split("; "), ["HP:0003549", "HP:0010786", "HP:0033127"]
        )
        self.assertCountEqual(row[18].split("; "), ["12451214", "15214012"])

    def test_download_all_visible_panel_with_summary(self):
        """
        Download all visible panels (non authenticated user)
        The download should include the summary for each record
        """
        url_panel = reverse("panel_download", kwargs={"name": "all"})
        response = self.client.get(url_panel + "?extra_columns=summary")

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
        self.assertEqual(len(rows), 6)
        self.assertIn("g2p id", rows[0])

        row = next(row for row in rows[1:] if row[0] == "G2P00002")
        expected_summary_prefix = (
            "RAB27A-related Griscelli syndrome has a confidence assertion of definitive based on 2 curated publications. "
            "This is a biallelic autosomal condition. This is typically de novo and this is typified by incomplete penetrance. "
            "Variant consequence is absent gene product (inferred). Molecular mechanism is loss of function (evidenced by protein "
            "interaction function). Recorded variant types include "
        )

        self.assertEqual(row[0], "G2P00002")
        self.assertEqual(row[1], "RAB27A")
        self.assertEqual(row[2], "")
        self.assertEqual(row[3], "9766")
        self.assertEqual(row[5], "RAB27A-related Griscelli syndrome")
        self.assertEqual(row[6], "")
        self.assertEqual(row[7], "")
        self.assertEqual(row[8], "biallelic_autosomal")
        self.assertEqual(
            row[9], "typified by incomplete penetrance; typically de novo"
        )
        self.assertEqual(row[10], "definitive")
        self.assertEqual(row[11], "absent gene product")
        self.assertEqual(row[13], "loss of function")
        self.assertEqual(row[14], "evidence")
        self.assertEqual(row[16], "15214012 -> function: protein interaction")
        self.assertEqual(row[19], "32302040")
        self.assertEqual(row[20], "Cardiac")
        self.assertEqual(
            row[21],
            "All mutations are located in the aminoterminal part of the gene, before the first epidermal growth factor-like domain.",
        )
        self.assertEqual(row[22], "2018-07-05 16:33:03+00:00")
        self.assertEqual(row[23], "under review")
        self.assertTrue(row[24].startswith(expected_summary_prefix))
        self.assertIn(
            row[24][len(expected_summary_prefix) :],
            {
                "inframe insertion and intron variant.",
                "intron variant and inframe insertion.",
            },
        )
        self.assertCountEqual(row[4].split("; "), ["GS2", "RAB27"])
        self.assertCountEqual(
            row[12].split("; "), ["inframe_insertion", "intron_variant"]
        )
        self.assertCountEqual(
            row[15].split("; "),
            ["assembly-mediated GOF:inferred", "aggregation:inferred"],
        )
        self.assertCountEqual(
            row[17].split("; "), ["HP:0003549", "HP:0010786", "HP:0033127"]
        )
        self.assertCountEqual(row[18].split("; "), ["12451214", "15214012"])
