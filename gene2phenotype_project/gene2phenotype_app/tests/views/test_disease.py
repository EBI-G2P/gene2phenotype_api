from django.test import TestCase
from django.urls import reverse

class DiseaseEndpointTests(TestCase):
    """
        Test the disease endpoint: DiseaseDetail
    """
    fixtures = [
        "gene2phenotype_app/fixtures/disease.json",
        "gene2phenotype_app/fixtures/attribs.json",
        "gene2phenotype_app/fixtures/source.json",
        "gene2phenotype_app/fixtures/ontology_term.json"
    ]

    def test_get_disease(self):
        """
            Test the response of the disease detail endpoint
        """
        self.url_disease = reverse("disease_details", kwargs={"id": "Congenital ichthyosis type 1"})

        response = self.client.get(self.url_disease)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], "Congenital ichthyosis type 1")
        self.assertEqual(response.data["last_updated"], None)
        self.assertEqual(response.data["synonyms"], [])

        expected_data = [{
            "accession": "MONDO:0009441",
            "term": "MONDO:0009441",
            "description": "Any autosomal recessive congenital ichthyosis in which the cause of the disease is a mutation in the TGM1 gene.",
            "source": "Mondo"
        }]
        self.assertEqual(list(response.data["ontology_terms"]), expected_data)

    def test_not_found(self):
        """
            Test the response of the disease detail endpoint
            when disease is not found
        """
        self.url_disease = reverse("disease_details", kwargs={"id": "CACNA1F-related Aland Island"})

        response = self.client.get(self.url_disease)

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data["message"], "No matching Disease found for: CACNA1F-related Aland Island")

class DiseaseSummaryTests(TestCase):
    """
        Test the disease endpoint: DiseaseSummary
    """
    fixtures = [
        "gene2phenotype_app/fixtures/disease.json",
        "gene2phenotype_app/fixtures/attribs.json",
        "gene2phenotype_app/fixtures/cv_molecular_mechanism.json",
        "gene2phenotype_app/fixtures/g2p_stable_id.json",
        "gene2phenotype_app/fixtures/lgd_panel.json",
        "gene2phenotype_app/fixtures/user_panels.json",
        "gene2phenotype_app/fixtures/locus_genotype_disease.json",
        "gene2phenotype_app/fixtures/locus.json",
        "gene2phenotype_app/fixtures/sequence.json",
        "gene2phenotype_app/fixtures/ontology_term.json",
        "gene2phenotype_app/fixtures/source.json"
    ]

    def test_get_disease(self):
        """
            Test the response of the disease summary endpoint
        """
        self.url_disease = reverse("disease_summary", kwargs={"id": "CEP290-related JOUBERT SYNDROME TYPE 5"})

        response = self.client.get(self.url_disease)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["disease"], "CEP290-related JOUBERT SYNDROME TYPE 5")

        expected_data = [
            {
                "locus": "CEP290",
                "genotype": "biallelic_autosomal",
                "confidence": "definitive",
                "panels": ["DD", "Eye"],
                "variant_consequence": [None],
                "variant_type": [],
                "molecular_mechanism": "loss of function",
                "stable_id": "G2P00001"
            }
        ]
        self.assertEqual(list(response.data["records_summary"]), expected_data)
