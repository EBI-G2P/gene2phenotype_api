from django.test import TestCase
from django.urls import reverse

class LocusGenotypeDiseaseDetailEndpoint(TestCase):
    """
        Test endpoint that returns the locus genotype disease record
    """
    fixtures = ["gene2phenotype_app/fixtures/attribs.json", "gene2phenotype_app/fixtures/cv_molecular_mechanism.json",
                "gene2phenotype_app/fixtures/disease.json", "gene2phenotype_app/fixtures/g2p_stable_id.json",
                "gene2phenotype_app/fixtures/g2p_stable_id.json", "gene2phenotype_app/fixtures/cv_molecular_mechanism.json",
                "gene2phenotype_app/fixtures/lgd_mechanism_evidence.json", "gene2phenotype_app/fixtures/lgd_mechanism_synopsis.json",
                "gene2phenotype_app/fixtures/lgd_panel.json", "gene2phenotype_app/fixtures/locus_genotype_disease.json",
                "gene2phenotype_app/fixtures/locus.json", "gene2phenotype_app/fixtures/publication.json",
                "gene2phenotype_app/fixtures/sequence.json", "gene2phenotype_app/fixtures/user_panels.json",
                "gene2phenotype_app/fixtures/ontology_term.json", "gene2phenotype_app/fixtures/source.json",
                "gene2phenotype_app/fixtures/lgd_publication.json"
                ]

    def setUp(self):
        self.url_list_lgd = reverse("lgd", kwargs={"stable_id": "G2P00001"})
    
    def test_lgd_detail(self):
        """
            Test the locus genotype disease display
        """
        response = self.client.get(self.url_list_lgd)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["stable_id"], "G2P00001")
        self.assertEqual(response.data["genotype"], "biallelic_autosomal")
        self.assertEqual(response.data["confidence"], "definitive")
        self.assertEqual(response.data["variant_consequence"], [])
        self.assertEqual(response.data["last_updated"], "2017-04-24")

        expected_data_publication = [
            {"publication": {
                "pmid": 3897232,
                "title": "Acetyl coenzyme A: alpha-glucosaminide N-acetyltransferase. Evidence for a transmembrane acetylation mechanism.",
                "authors": "Bame KJ, Rome LH.", "year": "1985", "comments": [], "families": []}}
        ]
        self.assertEqual(response.data["publications"], expected_data_publication)

        expected_data_disease = {
            "name": "JOUBERT SYNDROME TYPE 5",
            "ontology_terms": [{"accession": "610188", "term": "JOUBERT SYNDROME 5", "description": None, "source": "OMIM"}],
            "synonyms": []
        }
        self.assertEqual(response.data["disease"], expected_data_disease)

        expected_data_mechanism = {
            "mechanism": "loss of function",
            "mechanism_support": "evidence",
            "synopsis": [{"synopsis": "assembly-mediated GOF", "support": "inferred"}],
            "evidence": {3897232: {"Function": ["Biochemical"]}} # TODO: check
        }
        self.assertEqual(response.data["molecular_mechanism"], expected_data_mechanism)

        expected_data_panels = [
            {"name": "DD", "description": "Developmental disorders"},
            {"name": "Eye", "description": "Eye disorders"}
        ]
        self.assertEqual(response.data["panels"], expected_data_panels)
