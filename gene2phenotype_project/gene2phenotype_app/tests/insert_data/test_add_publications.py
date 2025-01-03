from django.test import TestCase
from django.urls import reverse
from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken
from knox.models import AuthToken
from gene2phenotype_app.models import User, LGDPublication

class LGDEditPublicationsEndpoint(TestCase):
    """
        Test endpoint to add publications (+ associated data) to a LGD record
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
        self.url_add_publication = reverse("lgd_publication", kwargs={"stable_id": "G2P00001"})

    def test_lgd_detail(self):
        """
            Test the locus genotype disease display
        """
        # Define the complex data structure
        publication_to_add = {
            "publications":[{
                "publication": {"pmid": 15214012},
                "comment": {"comment": "", "is_public": 1},
                "families": {"families": 0, "consanguinity": "unknown", "ancestries": None, "affected_individuals": 0}
            }]
        }

        # Login
        user = User.objects.get(email="user5@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        # Authenticate by setting cookie on the test client
        self.client.cookies[settings.SIMPLE_JWT['AUTH_COOKIE']] = access_token

        response = self.client.post(self.url_add_publication, publication_to_add, content_type="application/json")
        self.assertEqual(response.status_code, 201)

        response_data = response.json()
        self.assertEqual(response_data["message"], "Publication added to the G2P entry successfully.")

        lgd_publications = LGDPublication.objects.filter(lgd__stable_id__stable_id="G2P00001")
        self.assertEqual(len(lgd_publications), 2)
