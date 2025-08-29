from django.conf import settings
from django.test import TestCase
from django.urls import reverse

from rest_framework_simplejwt.tokens import RefreshToken

from gene2phenotype_app.models import User


class SearchTests(TestCase):
    """
    Test the search endpoint: SearchView
    """

    fixtures = [
        "gene2phenotype_app/fixtures/locus.json",
        "gene2phenotype_app/fixtures/attribs.json",
        "gene2phenotype_app/fixtures/source.json",
        "gene2phenotype_app/fixtures/sequence.json",
        "gene2phenotype_app/fixtures/cv_molecular_mechanism.json",
        "gene2phenotype_app/fixtures/disease.json",
        "gene2phenotype_app/fixtures/g2p_stable_id.json",
        "gene2phenotype_app/fixtures/lgd_panel.json",
        "gene2phenotype_app/fixtures/locus_genotype_disease.json",
        "gene2phenotype_app/fixtures/publication.json",
        "gene2phenotype_app/fixtures/user_panels.json",
        "gene2phenotype_app/fixtures/ontology_term.json",
        "gene2phenotype_app/fixtures/lgd_publication.json",
        "gene2phenotype_app/fixtures/lgd_phenotype.json",
        "gene2phenotype_app/fixtures/curation_data.json",
    ]

    def setUp(self):
        self.base_url_search = reverse("search")
        self.expected_data = [
            {
                "stable_id": "G2P00001",
                "gene": "CEP290",
                "genotype": "biallelic_autosomal",
                "disease": "CEP290-related JOUBERT SYNDROME TYPE 5",
                "mechanism": "loss of function",
                "panel": ["DD", "Eye"],
                "confidence": "definitive",
            }
        ]

    def test_search_gene(self):
        """
        Test the response when searching by gene
        """
        url_search_gene = f"{self.base_url_search}?type=gene&query=CEP290"
        response = self.client.get(url_search_gene)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["next"], None)
        self.assertEqual(response.data["previous"], None)
        self.assertEqual(response.data["results"], self.expected_data)

    def test_search_disease(self):
        """
        Test the response when searching by disease type of search
        """
        url_search_disease = f"{self.base_url_search}?type=disease&query=CEP290-related JOUBERT SYNDROME TYPE 5"
        response = self.client.get(url_search_disease)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["next"], None)
        self.assertEqual(response.data["previous"], None)
        self.assertEqual(response.data["results"], self.expected_data)

    def test_search_disease_2(self):
        """
        Test the response when searching by disease and by panel
        """
        url_search_disease = f"{self.base_url_search}?type=disease&panel=DD&query=CEP290-related JOUBERT SYNDROME TYPE 5"
        response = self.client.get(url_search_disease)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["next"], None)
        self.assertEqual(response.data["previous"], None)
        self.assertEqual(response.data["results"], self.expected_data)

    def test_search_disease_not_found(self):
        """
        Test the response when searching by disease and by panel return 404
        """
        url_search_disease = f"{self.base_url_search}?type=disease&panel=DD&query=CEP290-related SYNDROME TYPE"
        response = self.client.get(url_search_disease)

        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            response.data["error"],
            "No matching Disease found for: CEP290-related SYNDROME TYPE",
        )

    def test_search_disease_generic(self):
        """
        Test the response when searching a disease
        """
        url_search_disease = (
            f"{self.base_url_search}?query=CEP290-related JOUBERT SYNDROME TYPE 5"
        )
        response = self.client.get(url_search_disease)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["next"], None)
        self.assertEqual(response.data["previous"], None)
        self.assertEqual(response.data["results"], self.expected_data)

    def test_search_by_phenotype(self):
        """
        Test the response when searching by phenotype and by panel
        """
        url_search_disease = (
            f"{self.base_url_search}?type=phenotype&panel=DD&query=HP:0033127"
        )
        response = self.client.get(url_search_disease)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["next"], None)
        self.assertEqual(response.data["previous"], None)
        self.assertEqual(response.data["results"], self.expected_data)

    def test_search_by_phenotype_2(self):
        """
        Test the response when searching by phenotype
        """
        url_search_disease = f"{self.base_url_search}?type=phenotype&query=HP:0033127"
        response = self.client.get(url_search_disease)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 2)
        self.assertEqual(response.data["next"], None)
        self.assertEqual(response.data["previous"], None)

    def test_search_by_phenotype_not_found(self):
        """
        Test the response when searching by phenotype without results
        """
        url_search_disease = f"{self.base_url_search}?type=phenotype&query=HP:0033126"
        response = self.client.get(url_search_disease)

        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            response.data["error"], "No matching Phenotype found for: HP:0033126"
        )

    def test_search_g2p_id(self):
        """
        Test the response when searching by G2P stable ID
        """
        url_search_id = f"{self.base_url_search}?type=stable_id&query=G2P00001"
        response = self.client.get(url_search_id)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["next"], None)
        self.assertEqual(response.data["previous"], None)
        self.assertEqual(response.data["results"], self.expected_data)

    def test_search_g2p_id_2(self):
        """
        Test the response when searching by G2P stable ID and by panel
        """
        url_search_id = f"{self.base_url_search}?type=stable_id&panel=DD&query=G2P00001"
        response = self.client.get(url_search_id)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["next"], None)
        self.assertEqual(response.data["previous"], None)
        self.assertEqual(response.data["results"], self.expected_data)

    def test_search_g2p_id_not_found(self):
        """
        Test the response when searching by G2P stable ID that has been deleted
        """
        url_search_id = f"{self.base_url_search}?type=stable_id&query=G2P00003"
        response = self.client.get(url_search_id)

        self.assertEqual(response.status_code, 410)
        self.assertEqual(
            response.data["message"], "G2P00003 is no longer available."
        )

    def test_search_g2p_id_merged(self):
        """
        Test the response when searching by G2P stable ID that has been merged
        """
        url_search_id = f"{self.base_url_search}?type=stable_id&query=G2P00007"
        response = self.client.get(url_search_id)

        self.assertEqual(response.status_code, 410)
        self.assertEqual(
            response.data["message"],
            "G2P00007 is no longer available. It has been merged into G2P00001",
        )
        self.assertEqual(response.data["stable_id"], "G2P00001")

    def test_generic_search_merged(self):
        """
        Test the response when searching by a record that has been merged
        """
        url_search_id = f"{self.base_url_search}?query=G2P00007"
        response = self.client.get(url_search_id)

        self.assertEqual(response.status_code, 410)
        self.assertEqual(
            response.data["message"],
            "G2P00007 is no longer available. It has been merged into G2P00001",
        )
        self.assertEqual(response.data["stable_id"], "G2P00001")

    def test_search_draft(self):
        """
        Test the response when searching a draft
        """
        # Login
        user = User.objects.get(email="user5@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        # Authenticate by setting cookie on the test client
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        url_search_id = f"{self.base_url_search}?type=draft&query=CEP290"
        response = self.client.get(url_search_id)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)

    def test_search_draft_not_found(self):
        """
        Test the response when searching a draft without results
        """
        # Login
        user = User.objects.get(email="user5@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        # Authenticate by setting cookie on the test client
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        url_search_id = f"{self.base_url_search}?type=draft&query=CDH1"
        response = self.client.get(url_search_id)

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data["error"], "No matching draft found for: CDH1")

    def test_search_all(self):
        """
        Test the response when searching without specific type
        """
        url_search = f"{self.base_url_search}?query=CEP290"
        response = self.client.get(url_search)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["next"], None)
        self.assertEqual(response.data["previous"], None)
        self.assertEqual(response.data["results"], self.expected_data)

    def test_search_not_found(self):
        """
        Test the response when not found
        """
        url_search_gene = f"{self.base_url_search}?type=gene&query=TUBB4A"
        response = self.client.get(url_search_gene)

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data["error"], "No matching Gene found for: TUBB4A")

    def test_search_not_found_2(self):
        """
        Test the response when not found because the record is deleted
        """
        url_search_gene = f"{self.base_url_search}?type=gene&query=STRA6"
        response = self.client.get(url_search_gene)

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data["error"], "No matching Gene found for: STRA6")

    def test_search_not_found_3(self):
        """
        Test the response when not found because the record is private
        """
        url_search_gene = f"{self.base_url_search}?query=BAAT"
        response = self.client.get(url_search_gene)

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data["error"], "No matching results found for: BAAT")

    def test_search_not_found_4(self):
        """
        Test the response when gene not found because the record is private
        """
        url_search_gene = f"{self.base_url_search}?type=gene&query=BAAT"
        response = self.client.get(url_search_gene)

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data["error"], "No matching Gene found for: BAAT")

    def test_search_without_query(self):
        """
        Test the endpoint when querying without a query text
        """
        url_search_gene = f"{self.base_url_search}?type=gene"
        response = self.client.get(url_search_gene)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 0)

    def test_generic_search_by_panel(self):
        """
        Test the response when searching by panel
        """
        url_search_disease = f"{self.base_url_search}?query=CEP290&panel=DD"
        response = self.client.get(url_search_disease)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["next"], None)
        self.assertEqual(response.data["previous"], None)
        self.assertEqual(response.data["results"], self.expected_data)

    def test_generic_search_by_panel_2(self):
        """
        Test the response when searching by panel without results
        """
        url_search_disease = f"{self.base_url_search}?query=GS2&panel=DD"
        response = self.client.get(url_search_disease)

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data["error"], "No matching results found for: GS2")

    def test_generic_search_by_panel_3(self):
        """
        Test the response when searching by panel
        """
        url_search_disease = f"{self.base_url_search}?type=gene&query=CEP290&panel=DD"
        response = self.client.get(url_search_disease)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["next"], None)
        self.assertEqual(response.data["previous"], None)
        self.assertEqual(response.data["results"], self.expected_data)

    def test_invalid_search_type(self):
        """
        Test the endpoint with an invalid search type
        """
        url_search_disease = f"{self.base_url_search}?type=g2p&query=CEP290"
        response = self.client.get(url_search_disease)

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data["error"], "Search type is not valid")

    def test_search_authenticated_user(self):
        """
        Test the response for authenticated users
        """
        # Login
        user = User.objects.get(email="user5@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        # Authenticate by setting cookie on the test client
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        url_search_id = f"{self.base_url_search}?query=G2P00006"
        response = self.client.get(url_search_id)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)

        expected_data = [
            {
                "stable_id": "G2P00006",
                "gene": "RAB27A",
                "genotype": "biallelic_autosomal",
                "disease": "RAB27A-related Griscelli syndrome biallelic",
                "mechanism": "loss of function",
                "panel": ["Ear", "Eye"],
                "confidence": "strong",
            }
        ]
        self.assertEqual(response.data["results"], expected_data)
