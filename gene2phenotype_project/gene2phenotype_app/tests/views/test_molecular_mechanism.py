from django.test import TestCase
from django.urls import reverse


class ListMolecularMechanismsEndpoint(TestCase):
    """
    Test endpoint that returns the mechanism values
    """

    fixtures = ["gene2phenotype_app/fixtures/cv_molecular_mechanism.json"]

    def setUp(self):
        self.url_list_mechanisms = reverse("list_mechanisms")

    def test_mechanism_list(self):
        """
        Test the cv_molecular_mechanism data
        """
        response = self.client.get(self.url_list_mechanisms)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 4)  # there are 4 types of mechanism data
        self.assertEqual(len(response.data["mechanism"]), 5)
        self.assertEqual(len(response.data["mechanism_synopsis"]), 10)
        self.assertEqual(len(response.data["support"]), 2)
        self.assertEqual(len(response.data["evidence"]), 4)
