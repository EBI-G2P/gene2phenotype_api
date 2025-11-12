from django.test import TestCase
from django.urls import reverse


class GeneEndpointTests(TestCase):
    """
    Test the gene endpoint: LocusGene
    """

    fixtures = [
        "gene2phenotype_app/fixtures/locus.json",
        "gene2phenotype_app/fixtures/attribs.json",
        "gene2phenotype_app/fixtures/source.json",
        "gene2phenotype_app/fixtures/sequence.json",
    ]

    def setUp(self):
        self.url_gene = reverse("locus_gene", kwargs={"name": "CEP290"})

    def test_get_gene(self):
        """
        Test the response of the gene endpoint
        """
        response = self.client.get(self.url_gene)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["gene_symbol"], "CEP290")
        self.assertEqual(response.data["sequence"], "12")
        self.assertEqual(response.data["start"], 88049016)
        self.assertEqual(response.data["end"], 88142099)

        expected_data_ids = {"HGNC": "HGNC:29021", "Ensembl": "ENSG00000198707"}
        self.assertEqual(response.data["ids"], expected_data_ids)

        expected_data_synonyms = ["BBS14", "CT87"]
        self.assertEqual(list(response.data["synonyms"]), expected_data_synonyms)


class GeneSummaryEndpointTests(TestCase):
    """
    Test the gene summary endpoint: LocusGeneSummary
    """

    fixtures = [
        "gene2phenotype_app/fixtures/attribs.json",
        "gene2phenotype_app/fixtures/cv_molecular_mechanism.json",
        "gene2phenotype_app/fixtures/disease.json",
        "gene2phenotype_app/fixtures/g2p_stable_id.json",
        "gene2phenotype_app/fixtures/lgd_mechanism_evidence.json",
        "gene2phenotype_app/fixtures/lgd_mechanism_synopsis.json",
        "gene2phenotype_app/fixtures/lgd_panel.json",
        "gene2phenotype_app/fixtures/locus_genotype_disease.json",
        "gene2phenotype_app/fixtures/locus.json",
        "gene2phenotype_app/fixtures/publication.json",
        "gene2phenotype_app/fixtures/sequence.json",
        "gene2phenotype_app/fixtures/user_panels.json",
        "gene2phenotype_app/fixtures/ontology_term.json",
        "gene2phenotype_app/fixtures/source.json",
        "gene2phenotype_app/fixtures/lgd_publication.json",
        "gene2phenotype_app/fixtures/lgd_variant_type.json",
        "gene2phenotype_app/fixtures/lgd_variant_consequence.json",
    ]

    def setUp(self):
        self.url_gene_summary = reverse("locus_gene_summary", kwargs={"name": "CEP290"})
        self.url_gene_summary_2 = reverse("locus_gene_summary", kwargs={"name": "RAB27A"})

    def test_get_summary(self):
        """
        Test the response of the gene summary endpoint
        """
        response = self.client.get(self.url_gene_summary)

        self.assertEqual(response.status_code, 200)

        expected_data = [
            {
                "disease": "CEP290-related JOUBERT SYNDROME TYPE 5",
                "genotype": "biallelic_autosomal",
                "confidence": "definitive",
                "panels": ["DD", "Eye"],
                "variant_consequence": [None],
                "variant_type": [],
                "molecular_mechanism": "loss of function",
                "last_updated": "2017-04-24",
                "stable_id": "G2P00001",
            }
        ]
        self.assertEqual(list(response.data["records_summary"]), expected_data)

    def test_get_summary_complete(self):
        """
        Test the response of the gene summary endpoint when there are
        deleted variants in the record
        """
        response = self.client.get(self.url_gene_summary_2)

        self.assertEqual(response.status_code, 200)

        # The output is sorted by date of review
        expected_data = {
                "disease": "RAB27A-related Griscelli syndrome",
                "genotype": "biallelic_autosomal",
                "confidence": "definitive",
                "panels": ["Cardiac"],
                "variant_consequence": ["absent gene product"],
                "variant_type": ['inframe_insertion', 'intron_variant'],
                "molecular_mechanism": "loss of function",
                "last_updated": "2018-07-05",
                "stable_id": "G2P00002",
            }
        self.assertEqual(list(response.data["records_summary"])[1], expected_data)

class GeneFunctionEndpointTests(TestCase):
    """
    Test the gene function endpoint: GeneFunction
    """

    fixtures = [
        "gene2phenotype_app/fixtures/locus.json",
        "gene2phenotype_app/fixtures/attribs.json",
        "gene2phenotype_app/fixtures/source.json",
        "gene2phenotype_app/fixtures/sequence.json",
        "gene2phenotype_app/fixtures/uniprot_annotation.json",
        "gene2phenotype_app/fixtures/gene_stats.json",
    ]

    def setUp(self):
        self.url_gene_function = reverse(
            "locus_gene_function", kwargs={"name": "CEP290"}
        )

    def test_get_function(self):
        """
        Test the response of the gene function endpoint
        """
        response = self.client.get(self.url_gene_function)

        self.assertEqual(response.status_code, 200)

        expected_data_function = {
            "protein_function": "Involved in early and late steps in cilia formation. Its association with CCP110 is required for inhibition of primary cilia formation by CCP110 (PubMed:18694559).",
            "uniprot_accession": "O15078",
        }
        self.assertEqual(response.data["function"], expected_data_function)

        self.assertEqual(response.data["gene_stats"], {"gain_of_function_mp": 0.637})


class GeneDiseaseEndpointTests(TestCase):
    """
    Test the gene disease endpoint: GeneDiseaseView
    """

    fixtures = [
        "gene2phenotype_app/fixtures/locus.json",
        "gene2phenotype_app/fixtures/attribs.json",
        "gene2phenotype_app/fixtures/source.json",
        "gene2phenotype_app/fixtures/sequence.json",
        "gene2phenotype_app/fixtures/gene_disease.json",
    ]

    def setUp(self):
        self.url_gene = reverse("locus_gene_disease", kwargs={"name": "CEP290"})
        self.url_gene_synonym = reverse("locus_gene_disease", kwargs={"name": "BBS14"})
        self.url_invalid_gene = reverse("locus_gene_disease", kwargs={"name": "BBBS14"})
        self.url_not_found = reverse("locus_gene_disease", kwargs={"name": "GS2"})

    def test_get_gene(self):
        """
        Test the response of the gene disease endpoint
        """
        response = self.client.get(self.url_gene)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 4)

        expected_data_function = [
            {
                "original_disease_name": "JOUBERT SYNDROME 5",
                "disease_name": "joubert syndrome",
                "identifier": "610188",
                "source": "OMIM",
            },
            {
                "original_disease_name": "SENIOR-LOKEN SYNDROME 6",
                "disease_name": "senior-loken syndrome",
                "identifier": "610189",
                "source": "OMIM",
            },
            {
                "original_disease_name": "Joubert syndrome 5",
                "disease_name": "joubert syndrome",
                "identifier": "MONDO:0012432",
                "source": "Mondo",
            },
            {
                "original_disease_name": "Senior-Loken syndrome 6",
                "disease_name": "senior-loken syndrome",
                "identifier": "MONDO:0012433",
                "source": "Mondo",
            },
        ]
        self.assertEqual(response.data["results"], expected_data_function)

    def test_get_gene_synonym(self):
        """
        Test the response of the gene disease endpoint when searching the gene synonym.
        """
        response = self.client.get(self.url_gene_synonym)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 4)

        expected_data_function = [
            {
                "original_disease_name": "JOUBERT SYNDROME 5",
                "disease_name": "joubert syndrome",
                "identifier": "610188",
                "source": "OMIM",
            },
            {
                "original_disease_name": "SENIOR-LOKEN SYNDROME 6",
                "disease_name": "senior-loken syndrome",
                "identifier": "610189",
                "source": "OMIM",
            },
            {
                "original_disease_name": "Joubert syndrome 5",
                "disease_name": "joubert syndrome",
                "identifier": "MONDO:0012432",
                "source": "Mondo",
            },
            {
                "original_disease_name": "Senior-Loken syndrome 6",
                "disease_name": "senior-loken syndrome",
                "identifier": "MONDO:0012433",
                "source": "Mondo",
            },
        ]
        self.assertEqual(response.data["results"], expected_data_function)

    def test_get_invalid_gene(self):
        """
        Test the response of the gene disease endpoint when searching for an invalid gene.
        """
        response = self.client.get(self.url_invalid_gene)

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data["error"], "No matching Gene found for: BBBS14")

    def test_not_found(self):
        """
        Test the response of the gene disease endpoint when no association found.
        """
        response = self.client.get(self.url_not_found)

        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            response.data["error"],
            "No matching Gene-Disease association found for: GS2",
        )
