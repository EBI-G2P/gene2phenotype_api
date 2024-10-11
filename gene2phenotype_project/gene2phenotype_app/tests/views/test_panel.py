from django.test import TestCase
from django.urls import reverse
from knox.models import AuthToken
from gene2phenotype_app.models import User

class PanelListEndpointTests(TestCase):
    """
        Test the panel endpoint: PanelList
    """
    fixtures = ["gene2phenotype_app/fixtures/user_panels.json", "gene2phenotype_app/fixtures/attribs.json"]

    def setUp(self):
        self.url_panels = reverse('list_panels')

    def test_get_panel_list(self):
        """
            Test for non-autenticated users.
            Non-visible panels are not included in the response.
        """
        response = self.client.get(self.url_panels)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data.get("count"), 2)

    def test_login_get_panel_list(self):
        """
            Test for autenticated users.
            All panels are included in the response.
        """
        user = User.objects.get(email="user5@test.ac.uk")
        # Create token for the user
        token_id = AuthToken.objects.create(user)[1]
        # Authenticate using the token
        self.client.defaults['HTTP_AUTHORIZATION'] = 'Token ' + token_id

        response = self.client.get(self.url_panels)
        self.assertEqual(response.status_code, 200)

        self.assertEqual(response.data.get("count"), 3)

class PanelDetailsEndpointTests(TestCase):
    """
        Test the panel endpoint: PanelDetail
    """
    fixtures = ["gene2phenotype_app/fixtures/user_panels.json", "gene2phenotype_app/fixtures/attribs.json",
                "gene2phenotype_app/fixtures/g2p_stable_id.json", "gene2phenotype_app/fixtures/locus.json",
                "gene2phenotype_app/fixtures/sequence.json", "gene2phenotype_app/fixtures/disease.json",
                "gene2phenotype_app/fixtures/ontology_term.json", "gene2phenotype_app/fixtures/source.json",
                "gene2phenotype_app/fixtures/locus_genotype_disease.json", "gene2phenotype_app/fixtures/lgd_panel.json",
                "gene2phenotype_app/fixtures/molecular_mechanism.json", "gene2phenotype_app/fixtures/cv_molecular_mechanism.json"]

    def setUp(self):
        self.url_panels = reverse('panel_details', kwargs={'name': 'DD'})

    def test_get_panel_details(self):
        """
            Get the details for a visible panel.
        """
        response = self.client.get(self.url_panels)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data.get("description"), "Developmental disorders")

class PanelSummaryEndpointTests(TestCase):
    """
        Test the panel endpoint: PanelRecordsSummary
    """
    fixtures = ["gene2phenotype_app/fixtures/user_panels.json", "gene2phenotype_app/fixtures/attribs.json",
                "gene2phenotype_app/fixtures/g2p_stable_id.json", "gene2phenotype_app/fixtures/locus.json",
                "gene2phenotype_app/fixtures/sequence.json", "gene2phenotype_app/fixtures/disease.json",
                "gene2phenotype_app/fixtures/ontology_term.json", "gene2phenotype_app/fixtures/source.json",
                "gene2phenotype_app/fixtures/locus_genotype_disease.json", "gene2phenotype_app/fixtures/lgd_panel.json",
                "gene2phenotype_app/fixtures/molecular_mechanism.json", "gene2phenotype_app/fixtures/cv_molecular_mechanism.json"]

    def setUp(self):
        self.url_panels = reverse('panel_summary', kwargs={'name': 'DD'})

    def test_get_panel_summary(self):
        """
            Get the summary for a visible panel.
        """
        response = self.client.get(self.url_panels)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data.get("records_summary")), 1)
