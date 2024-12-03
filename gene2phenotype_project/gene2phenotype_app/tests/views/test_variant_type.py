from django.test import TestCase
from django.urls import reverse

class ListVariantTypesEndpoint(TestCase):
    """
        Test endpoint that returns the ontology terms for variant type
    """
    fixtures = ["gene2phenotype_app/fixtures/ontology_term.json", "gene2phenotype_app/fixtures/source.json",
                "gene2phenotype_app/fixtures/attribs.json"]

    def setUp(self):
        self.url_list_variant_types = reverse('list_variant_types')
    
    def test_variant_types(self):
        """
            Test the ontology types
        """
        response = self.client.get(self.url_list_variant_types)
        self.assertEqual(response.status_code, 200)
        # Counts the number of terms by variant type
        self.assertEqual(len(response.data["NMD_variants"]), 10)
        self.assertEqual(len(response.data["splice_variants"]), 3)
        self.assertEqual(len(response.data["protein_changing_variants"]), 7)
        self.assertEqual(len(response.data["regulatory_variants"]), 3)
        self.assertEqual(len(response.data["other_variants"]), 8)
