from django.test import TestCase
from django.urls import reverse
from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken

from gene2phenotype_app.models import User


class LocusGenotypeDiseaseDetailEndpoint(TestCase):
    """
    Test endpoint that returns the locus genotype disease record
    """

    fixtures = [
        "gene2phenotype_app/fixtures/attribs.json",
        "gene2phenotype_app/fixtures/cv_molecular_mechanism.json",
        "gene2phenotype_app/fixtures/disease.json",
        "gene2phenotype_app/fixtures/g2p_stable_id.json",
        "gene2phenotype_app/fixtures/cv_molecular_mechanism.json",
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
        "gene2phenotype_app/fixtures/lgd_comment.json",
        "gene2phenotype_app/fixtures/lgd_phenotype.json",
        "gene2phenotype_app/fixtures/lgd_publication_comment.json",
    ]

    def test_lgd_detail(self):
        """
        Test the locus genotype disease display
        """
        url_list_lgd = reverse("lgd", kwargs={"stable_id": "G2P00001"})

        response = self.client.get(url_list_lgd)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["stable_id"], "G2P00001")
        self.assertEqual(response.data["genotype"], "biallelic_autosomal")
        self.assertEqual(response.data["confidence"], "definitive")
        self.assertEqual(response.data["variant_consequence"], [])
        (self.assertEqual(list(response.data["variant_type"]), []),)
        (self.assertEqual(list(response.data["variant_description"]), []),)
        (self.assertEqual(list(response.data["phenotype_summary"]), []),)
        (self.assertEqual(response.data["cross_cutting_modifier"], []),)
        self.assertEqual(response.data["last_updated"], "2017-04-24")
        self.assertEqual(response.data["date_created"], None)

        expected_data_comments = [
            {
                "id": 2,
                "date": "2024-09-24",
                "is_public": 1,
                "text": "JLNS is due to altered gene product sequence",
            }
        ]
        self.assertEqual(response.data["comments"], expected_data_comments)

        expected_data_publication = [
            {
                "publication": {
                    "pmid": 3897232,
                    "title": "Acetyl coenzyme A: alpha-glucosaminide N-acetyltransferase. Evidence for a transmembrane acetylation mechanism.",
                    "authors": "Bame KJ, Rome LH.",
                    "year": "1985",
                },
                "number_of_families": None,
                "consanguinity": None,
                "affected_individuals": None,
                "ancestry": None,
                "comments": [],
            }
        ]
        self.assertEqual(response.data["publications"], expected_data_publication)

        expected_data_disease = {
            "name": "CEP290-related JOUBERT SYNDROME TYPE 5",
            "ontology_terms": [
                {
                    "accession": "610188",
                    "term": "JOUBERT SYNDROME 5",
                    "description": None,
                    "source": "OMIM",
                }
            ],
            "synonyms": [],
        }
        self.assertEqual(response.data["disease"], expected_data_disease)

        expected_data_mechanism = {
            "mechanism": "loss of function",
            "mechanism_support": "evidence",
            "synopsis": [{"synopsis": "assembly-mediated GOF", "support": "inferred"}],
            "evidence": {
                3897232: {
                    "functional_studies": {"Function": ["Biochemical"]},
                    "descriptions": [],
                }
            },
        }
        self.assertEqual(response.data["molecular_mechanism"], expected_data_mechanism)

        expected_data_panels = [
            {"name": "DD", "description": "Developmental disorders"},
            {"name": "Eye", "description": "Eye disorders"},
        ]
        self.assertEqual(response.data["panels"], expected_data_panels)

        expected_data_phenotypes = [
            {
                "accession": "HP:0033127",
                "publications": [3897232],
                "term": "Abnormality of the musculoskeletal system",
            }
        ]
        self.assertEqual(list(response.data["phenotypes"]), expected_data_phenotypes)

    def test_lgd_detail_authenticated(self):
        """
        Test the locus genotype disease display for authenticated users.
        Check if publication comments are available.
        """
        url_list_lgd = reverse("lgd", kwargs={"stable_id": "G2P00001"})

        # Login
        user = User.objects.get(email="user5@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        # Authenticate by setting cookie on the test client
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        response = self.client.get(url_list_lgd)
        self.assertEqual(response.status_code, 200)

        expected_data_publication = [
            {
                "publication": {
                    "pmid": 3897232,
                    "title": "Acetyl coenzyme A: alpha-glucosaminide N-acetyltransferase. Evidence for a transmembrane acetylation mechanism.",
                    "authors": "Bame KJ, Rome LH.",
                    "year": "1985",
                },
                "number_of_families": None,
                "consanguinity": None,
                "affected_individuals": None,
                "ancestry": None,
                "comments": [
                    {
                        "comment": "See supplementary table 1. Homozygous.",
                        "user": "test_user1",
                        "date": "2025-02-19",
                    }
                ],
            }
        ]
        self.assertEqual(response.data["publications"], expected_data_publication)

        expected_data_mechanism = {
            "mechanism": "loss of function",
            "mechanism_support": "evidence",
            "synopsis": [{"synopsis": "assembly-mediated GOF", "support": "inferred"}],
            "evidence": {
                3897232: {
                    "functional_studies": {"Function": ["Biochemical"]},
                    "descriptions": ["This is the evidence found in PMID:3897232"],
                }
            },
        }
        self.assertEqual(response.data["molecular_mechanism"], expected_data_mechanism)
