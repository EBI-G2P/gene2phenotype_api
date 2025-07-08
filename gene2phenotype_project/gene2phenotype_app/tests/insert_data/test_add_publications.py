from django.test import TestCase
from django.urls import reverse
from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken
from gene2phenotype_app.models import (
    User,
    LGDPublication,
    LGDMolecularMechanismEvidence,
    LGDMolecularMechanismSynopsis,
    LGDPhenotype,
    LGDVariantType,
    LGDVariantTypeDescription,
)


class LGDEditPublicationsEndpoint(TestCase):
    """
    Test endpoint to add publications (+ associated data) to a LGD record
    """

    fixtures = [
        "gene2phenotype_app/fixtures/attribs.json",
        "gene2phenotype_app/fixtures/cv_molecular_mechanism.json",
        "gene2phenotype_app/fixtures/disease.json",
        "gene2phenotype_app/fixtures/g2p_stable_id.json",
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
    ]

    def setUp(self):
        self.url_add_publication = reverse(
            "lgd_publication", kwargs={"stable_id": "G2P00001"}
        )

    def test_lgd_detail(self):
        """
        Test the locus genotype disease display
        """
        # Define the complex data structure
        publication_to_add = {
            "publications": [
                {
                    "publication": {"pmid": 15214012},
                    "comment": {"comment": "", "is_public": 1},
                    "families": {
                        "families": 0,
                        "consanguinity": "unknown",
                        "ancestries": None,
                        "affected_individuals": 0,
                    },
                }
            ],
            "phenotypes": [
                {
                    "pmid": "15214012",
                    "summary": "",
                    "hpo_terms": [
                        {
                            "term": "Abnormality of connective tissue",
                            "accession": "HP:0003549",
                            "description": "",
                        }
                    ],
                }
            ],
            "variant_types": [
                {
                    "comment": "",
                    "de_novo": False,
                    "inherited": False,
                    "nmd_escape": False,
                    "primary_type": "protein_changing",
                    "secondary_type": "inframe_insertion",
                    "supporting_papers": ["15214012"],
                    "unknown_inheritance": True,
                }
            ],
            "variant_descriptions": [
                {"description": "HGVS:c.9Pro", "publication": "15214012"}
            ],
            "mechanism_synopsis": [{"name": "", "support": ""}],
            "mechanism_evidence": [
                {
                    "pmid": "15214012",
                    "description": "This is new evidence for the existing mechanism evidence.",
                    "evidence_types": [
                        {"primary_type": "Function", "secondary_type": ["Biochemical"]}
                    ],
                }
            ],
        }

        # Login
        user = User.objects.get(email="user5@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        # Authenticate by setting cookie on the test client
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        response = self.client.post(
            self.url_add_publication,
            publication_to_add,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)

        response_data = response.json()
        self.assertEqual(
            response_data["message"], "Publication added to the G2P entry successfully."
        )

        # Check inserted data
        lgd_publications = LGDPublication.objects.filter(
            lgd__stable_id__stable_id="G2P00001", is_deleted=0
        )
        self.assertEqual(len(lgd_publications), 2)

        lgd_mechanism_evidence = LGDMolecularMechanismEvidence.objects.filter(
            lgd__stable_id__stable_id="G2P00001", is_deleted=0
        )
        self.assertEqual(len(lgd_mechanism_evidence), 2)

        lgd_mechanism_synopsis = LGDMolecularMechanismSynopsis.objects.filter(
            lgd__stable_id__stable_id="G2P00001", is_deleted=0
        )
        self.assertEqual(len(lgd_mechanism_synopsis), 1)

        lgd_phenotypes = LGDPhenotype.objects.filter(
            lgd__stable_id__stable_id="G2P00001", is_deleted=0
        )
        self.assertEqual(len(lgd_phenotypes), 1)

        lgd_variant_types = LGDVariantType.objects.filter(
            lgd__stable_id__stable_id="G2P00001", is_deleted=0
        )
        self.assertEqual(len(lgd_variant_types), 1)

        lgd_variant_descriptions = LGDVariantTypeDescription.objects.filter(
            lgd__stable_id__stable_id="G2P00001", is_deleted=0
        )
        self.assertEqual(len(lgd_variant_descriptions), 1)
