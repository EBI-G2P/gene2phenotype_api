from django.test import TestCase
from django.urls import reverse

class PublicationTests(TestCase):
    """
        Test the publication endpoint: PublicationDetail
    """
    fixtures = [
        "gene2phenotype_app/fixtures/publication.json",
        "gene2phenotype_app/fixtures/attribs.json",
        "gene2phenotype_app/fixtures/source.json"
    ]

    def test_get_publication(self):
        """
            Test the response of the publication endpoint
        """
        self.url_publication = reverse("publication_details", kwargs={"pmids": "3897232,1234"})
        response = self.client.get(self.url_publication)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 2)

        expected_data = [
            {
                "pmid": 3897232,
                "title": "Acetyl coenzyme A: alpha-glucosaminide N-acetyltransferase. Evidence for a transmembrane acetylation mechanism.",
                "authors": "Bame KJ, Rome LH.",
                "year": 1985,
                "source": "G2P"
            },
            {
                "pmid": 1234,
                "title": "Change in the kinetics of sulphacetamide tissue distribution in Walker tumor-bearing rats.",
                "authors": "Nadeau D, Marchand C.",
                "year": 1975,
                "source": "EuropePMC"
            }
        ]
        self.assertEqual(list(response.data["results"]), expected_data)

    def test_invalid(self):
        """
            Test the response of the publication endpoint
            when one of the publications is invalid
        """
        self.url_publication = reverse("publication_details", kwargs={"pmids": "1234,0"})
        response = self.client.get(self.url_publication)

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data["detail"], "Invalid PMID(s): 0")
