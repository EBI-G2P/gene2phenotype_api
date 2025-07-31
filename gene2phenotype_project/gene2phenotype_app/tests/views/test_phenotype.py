from django.test import TestCase
from django.urls import reverse


class PhenotypeTests(TestCase):
    """
    Test the phenotype endpoint: PhenotypeDetail
    """

    fixtures = [
        "gene2phenotype_app/fixtures/ontology_term.json",
        "gene2phenotype_app/fixtures/attribs.json",
        "gene2phenotype_app/fixtures/source.json",
    ]

    def test_get_phenotype(self):
        """
        Test the response of the phenotype endpoint
        """
        self.url_pheno = reverse(
            "phenotype_details", kwargs={"hpo_list": "HP:0009726,HP:0010786"}
        )
        response = self.client.get(self.url_pheno)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 2)

        expected_data = [
            {
                "accession": "HP:0009726",
                "term": "Renal neoplasm",
                "description": "The presence of a neoplasm of the kidney.",
            },
            {
                "accession": "HP:0010786",
                "term": "Urinary tract neoplasm",
                "description": "The presence of a neoplasm of the urinary system.",
            },
        ]
        self.assertEqual(list(response.data["results"]), expected_data)

    def test_invalid(self):
        """
        Test the response of the phenotype endpoint
        when one of the phenotypes is invalid.
        """
        self.url_pheno = reverse(
            "phenotype_details", kwargs={"hpo_list": "HP:0009726,HP:0"}
        )
        response = self.client.get(self.url_pheno)

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data["error"], "Invalid HPO term(s): HP:0")

    def test_invalid_2(self):
        """
        Test the response of the phenotype endpoint
        when one of the phenotypes has invalid format.
        """
        self.url_pheno = reverse(
            "phenotype_details", kwargs={"hpo_list": "HPO:0009726"}
        )
        response = self.client.get(self.url_pheno)

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data["error"], "Invalid HPO term(s): HPO:0009726")
