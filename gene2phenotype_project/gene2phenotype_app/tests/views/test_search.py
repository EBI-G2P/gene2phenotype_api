from django.test import TestCase
from django.urls import reverse

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
        "gene2phenotype_app/fixtures/lgd_publication.json"
    ]

    def test_search_gene(self):
        """
            Test the response when searching by gene
        """
        base_url_search = reverse("search")
        url_search_gene = f"{base_url_search}?type=gene&query=CEP290"
        response = self.client.get(url_search_gene)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["next"], None)
        self.assertEqual(response.data["previous"], None)

        expected_data = [
            {
                "id": "G2P00001",
                "gene": "CEP290",
                "genotype": "biallelic_autosomal",
                "disease": "CEP290-related JOUBERT SYNDROME TYPE 5",
                "mechanism": "loss of function",
                "panel": ["DD", "Eye"],
                "confidence": "definitive"
            }
        ]
        self.assertEqual(response.data["results"], expected_data)

    def test_search_disease(self):
        """
            Test the response when searching by disease
        """
        base_url_search = reverse("search")
        url_search_disease = f"{base_url_search}?type=disease&query=CEP290-related JOUBERT SYNDROME TYPE 5"
        response = self.client.get(url_search_disease)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["next"], None)
        self.assertEqual(response.data["previous"], None)

        expected_data = [
            {
                "id": "G2P00001",
                "gene": "CEP290",
                "genotype": "biallelic_autosomal",
                "disease": "CEP290-related JOUBERT SYNDROME TYPE 5",
                "mechanism": "loss of function",
                "panel": ["DD", "Eye"],
                "confidence": "definitive"
            }
        ]
        self.assertEqual(response.data["results"], expected_data)

    def test_search_g2p_id(self):
        """
            Test the response when searching by G2P stable ID
        """
        base_url_search = reverse("search")
        url_search_id = f"{base_url_search}?type=g2p_id&query=G2P00001"
        response = self.client.get(url_search_id)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["next"], None)
        self.assertEqual(response.data["previous"], None)

        expected_data = [
            {
                "id": "G2P00001",
                "gene": "CEP290",
                "genotype": "biallelic_autosomal",
                "disease": "CEP290-related JOUBERT SYNDROME TYPE 5",
                "mechanism": "loss of function",
                "panel": ["DD", "Eye"],
                "confidence": "definitive"
            }
        ]
        self.assertEqual(response.data["results"], expected_data)

    def test_search_all(self):
        """
            Test the response when searching without specific type
        """
        base_url_search = reverse("search")
        url_search = f"{base_url_search}?query=CEP290"
        response = self.client.get(url_search)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["next"], None)
        self.assertEqual(response.data["previous"], None)

        expected_data = [
            {
                "id": "G2P00001",
                "gene": "CEP290",
                "genotype": "biallelic_autosomal",
                "disease": "CEP290-related JOUBERT SYNDROME TYPE 5",
                "mechanism": "loss of function",
                "panel": ["DD", "Eye"],
                "confidence": "definitive"
            }
        ]
        self.assertEqual(response.data["results"], expected_data)

    def test_search_not_found(self):
        """
            Test the response when not found
        """
        base_url_search = reverse("search")
        url_search_gene = f"{base_url_search}?type=gene&query=TUBB4A"
        response = self.client.get(url_search_gene)

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data["error"], "No matching Gene found for: TUBB4A")