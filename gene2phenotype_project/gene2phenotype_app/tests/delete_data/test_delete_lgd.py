from django.test import TestCase
from django.urls import reverse
from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken
from gene2phenotype_app.models import (
    User,
    G2PStableID,
    LocusGenotypeDisease,
    LGDPanel
)

class LGDDeleteLGDEndpoint(TestCase):
    """
        Test endpoint to delete a record (LGD)
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
        self.url_delete_lgd = reverse("lgd_delete", kwargs={"stable_id": "G2P00002"})

    def test_lgd_delete_no_permission(self):
        """
            Test deleting the record (LGD) with user with no permission to edit the LGD panel
        """

        # Login
        user = User.objects.get(email="user5@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        # Authenticate by setting cookie on the test client
        self.client.cookies[settings.SIMPLE_JWT['AUTH_COOKIE']] = access_token

        response = self.client.generic("UPDATE", self.url_delete_lgd, content_type="application/json")
        self.assertEqual(response.status_code, 403)

    def test_lgd_delete_no_superuser(self):
        """
            Test deleting the record (LGD) without super user
        """

        # Login
        user = User.objects.get(email="user3@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        # Authenticate by setting cookie on the test client
        self.client.cookies[settings.SIMPLE_JWT['AUTH_COOKIE']] = access_token

        response = self.client.generic("UPDATE", self.url_delete_lgd, content_type="application/json")
        self.assertEqual(response.status_code, 403)

    def test_lgd_delete(self):
        """
            Test deleting the record (LGD) with correct user
        """

        # Login
        user = User.objects.get(email="john@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        # Authenticate by setting cookie on the test client
        self.client.cookies[settings.SIMPLE_JWT['AUTH_COOKIE']] = access_token

        response = self.client.generic("UPDATE", self.url_delete_lgd, content_type="application/json")
        self.assertEqual(response.status_code, 200)

        # Check deleted record
        g2p_stable_id_obj = G2PStableID.objects.get(stable_id="G2P00002")
        self.assertEqual(g2p_stable_id_obj.is_live, False)
        self.assertEqual(g2p_stable_id_obj.is_deleted, 1)
        lgd_obj = LocusGenotypeDisease.objects.get(stable_id=g2p_stable_id_obj.id)
        self.assertEqual(lgd_obj.is_deleted, 1)
        lgd_panel_obj = LGDPanel.objects.get(lgd=lgd_obj.id)
        self.assertEqual(lgd_panel_obj.is_deleted, 1)
