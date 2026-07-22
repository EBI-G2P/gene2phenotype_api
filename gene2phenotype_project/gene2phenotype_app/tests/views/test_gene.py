from django.test import TestCase
from django.urls import reverse

from gene2phenotype_app.models import LGDVariantGenccConsequence


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
        self.assertCountEqual(response.data["synonyms"], expected_data_synonyms)


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
        "gene2phenotype_app/fixtures/lgd_variant_type_publication.json",
        "gene2phenotype_app/fixtures/lgd_variant_consequence.json",
    ]

    def setUp(self):
        self.url_gene_summary = reverse("locus_gene_summary", kwargs={"name": "CEP290"})
        self.url_gene_summary_2 = reverse(
            "locus_gene_summary", kwargs={"name": "RAB27A"}
        )

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
                "variant_consequence": [],
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

        record = next(
            item
            for item in response.data["records_summary"]
            if item["stable_id"] == "G2P00002"
        )

        self.assertEqual(record["disease"], "RAB27A-related Griscelli syndrome")
        self.assertEqual(record["genotype"], "biallelic_autosomal")
        self.assertEqual(record["confidence"], "definitive")
        self.assertEqual(record["molecular_mechanism"], "loss of function")
        self.assertEqual(record["last_updated"], "2018-07-05")
        self.assertCountEqual(record["panels"], ["Cardiac"])
        self.assertCountEqual(
            record["variant_consequence"], ["absent gene product"]
        )
        self.assertCountEqual(
            record["variant_type"], ["inframe_insertion", "intron_variant"]
        )

    def test_get_summary_with_only_deleted_variant_consequence(self):
        """
        Records with only deleted variant consequences should still be returned.
        """
        LGDVariantGenccConsequence.objects.filter(lgd_id=2).update(is_deleted=1)

        response = self.client.get(self.url_gene_summary_2)

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
        self.url_gene_function_subunit = reverse(
            "locus_gene_function", kwargs={"name": "RAB27A"}
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
        self.assertEqual(response.data["subunit_structure"], {})

    def test_get_function_with_subunit(self):
        """
        Test the response of the gene function endpoint when there is subunit structure information available
        """
        response = self.client.get(self.url_gene_function_subunit)

        self.assertEqual(response.status_code, 200)

        expected_data_function = {
            "protein_function": "The small GTPases Rab are key regulators of intracellular membrane trafficking, from the formation of transport vesicles to their fusion with membranes. Rabs cycle between an inactive GDP-bound form and an active GTP-bound form that is able to recruit to membranes different sets of downstream effectors directly responsible for vesicle formation, movement, tethering and fusion (PubMed:30771381). RAB27A regulates homeostasis of late endocytic pathway, including endosomal positioning, maturation and secretion (PubMed:30771381). Plays a role in cytotoxic granule exocytosis in lymphocytes. Required for both granule maturation and granule docking and priming at the immunologic synapse (PubMed:18812475)",
            "uniprot_accession": "P51159",
        }
        expected_subunit_structure = {
            "quaternary_structure": "Does not interact with the BLOC-3 complex (heterodimer of HPS1 and HPS4) (PubMed:20048159).",
            "uniprot_accession": "P51159",
        }

        self.assertEqual(response.data["function"], expected_data_function)
        self.assertEqual(response.data["subunit_structure"], expected_subunit_structure)


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
        self.assertCountEqual(response.data["results"], expected_data_function)

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
        self.assertCountEqual(response.data["results"], expected_data_function)

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
