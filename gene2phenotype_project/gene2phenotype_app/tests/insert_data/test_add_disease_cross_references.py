from django.test import TestCase
from django.urls import reverse
from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken
from gene2phenotype_app.models import (
    User,
    DiseaseOntologyTerm,
)


class LGDAddDiseaseCrossReferences(TestCase):
    """
    Test endpoint to add diseases cross references
    """

    fixtures = [
        "gene2phenotype_app/fixtures/attribs.json",
        "gene2phenotype_app/fixtures/cv_molecular_mechanism.json",
        "gene2phenotype_app/fixtures/disease.json",
        "gene2phenotype_app/fixtures/g2p_stable_id.json",
        "gene2phenotype_app/fixtures/lgd_panel.json",
        "gene2phenotype_app/fixtures/locus_genotype_disease.json",
        "gene2phenotype_app/fixtures/locus.json",
        "gene2phenotype_app/fixtures/publication.json",
        "gene2phenotype_app/fixtures/sequence.json",
        "gene2phenotype_app/fixtures/user_panels.json",
        "gene2phenotype_app/fixtures/ontology_term.json",
        "gene2phenotype_app/fixtures/source.json",
    ]

    def setUp(self):
        self.url_add_disease_references = reverse(
            "update_disease_references", kwargs={"id": 1}
        )
        self.ontology_to_add = {
            "disease_ontologies": [
                {
                    "accession": "601110",
                    "term": "CONGENITAL DISORDER OF GLYCOSYLATION, TYPE Id",
                    "description": "CONGENITAL DISORDER OF GLYCOSYLATION, TYPE Id",
                    "source": "OMIM",
                },
                {
                    "accession": "MONDO:0012123",
                    "term": "congenital disorder of glycosylation type 1E",
                    "description": "The CDG (Congenital Disorders of Glycosylation) syndromes are a group of autosomal recessive disorders affecting glycoprotein synthesis. CDG syndrome type Ie is characterized by psychomotor delay, seizures, hypotonia, facial dysmorphism and microcephaly. Ocular anomalies are also very common.",
                    "source": "Mondo",
                },
            ]
        }

    def test_add_unauthorised_access(self):
        """
        Test the endpoint to add disease cross references for non authenticated user
        """
        response = self.client.post(
            self.url_add_disease_references,
            self.ontology_to_add,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 401)

    def test_add_disease_cross_references(self):
        """
        Test the endpoint to add disease cross references
        """
        # Login
        user = User.objects.get(email="john@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        # Authenticate by setting cookie on the test client
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        response = self.client.post(
            self.url_add_disease_references,
            self.ontology_to_add,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)

        response_data = response.json()
        self.assertEqual(
            response_data["message"],
            "Disease cross reference added to the G2P entry successfully.",
        )

        # Check inserted data
        disease_ontologies = DiseaseOntologyTerm.objects.filter(disease__id=1)
        self.assertEqual(len(disease_ontologies), 3)

        # Check history tables
        history_records = DiseaseOntologyTerm.history.all()
        self.assertEqual(len(history_records), 2)
