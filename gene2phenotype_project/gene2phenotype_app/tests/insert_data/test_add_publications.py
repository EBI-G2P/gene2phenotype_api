from django.test import TestCase
from django.urls import reverse
from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken
from gene2phenotype_app.models import (
    User,
    LGDPublication,
    LGDPublicationComment,
    LGDMolecularMechanismEvidence,
    LGDMolecularMechanismSynopsis,
    LGDPhenotype,
    LGDPhenotypeSummary,
    LGDVariantType,
    LGDVariantTypeDescription,
    LGDMinedPublication,
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
        "gene2phenotype_app/fixtures/lgd_mechanism_evidence.json",
        "gene2phenotype_app/fixtures/lgd_mechanism_synopsis.json",
        "gene2phenotype_app/fixtures/lgd_phenotype.json",
        "gene2phenotype_app/fixtures/lgd_phenotype_summary.json",
        "gene2phenotype_app/fixtures/lgd_panel.json",
        "gene2phenotype_app/fixtures/locus_genotype_disease.json",
        "gene2phenotype_app/fixtures/locus.json",
        "gene2phenotype_app/fixtures/publication.json",
        "gene2phenotype_app/fixtures/sequence.json",
        "gene2phenotype_app/fixtures/user_panels.json",
        "gene2phenotype_app/fixtures/ontology_term.json",
        "gene2phenotype_app/fixtures/source.json",
        "gene2phenotype_app/fixtures/lgd_publication.json",
        "gene2phenotype_app/fixtures/lgd_publication_comment.json",
        "gene2phenotype_app/fixtures/mined_publication.json",
        "gene2phenotype_app/fixtures/lgd_mined_publication.json",
    ]

    def setUp(self):
        self.url_add_publication = reverse(
            "lgd_publication", kwargs={"stable_id": "G2P00001"}
        )
        # test activity logs after insertion
        self.url_base_activity_logs = reverse("activity_logs")

    def test_add_no_permission(self):
        """
        Test the endpoint to add a publication for non authenticated user
        """
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
        }

        response = self.client.post(
            self.url_add_publication,
            publication_to_add,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 401)

    def test_add_lgd_publication(self):
        """
        Test the endpoint to add a publication to a record
        """
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
                    "summary": "Summary of phenotypes reported in PMID 15214012",
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

        # Check inserted data and history tables
        lgd_publications = LGDPublication.objects.filter(
            lgd__stable_id__stable_id="G2P00001", is_deleted=0
        )
        self.assertEqual(len(lgd_publications), 2)
        history_lgd_publications = LGDPublication.history.all()
        self.assertEqual(len(history_lgd_publications), 1)

        lgd_mechanism_evidence = LGDMolecularMechanismEvidence.objects.filter(
            lgd__stable_id__stable_id="G2P00001", is_deleted=0
        )
        self.assertEqual(len(lgd_mechanism_evidence), 2)
        history_mechanism_evidence = LGDMolecularMechanismEvidence.history.all()
        self.assertEqual(len(history_mechanism_evidence), 1)

        lgd_mechanism_synopsis = LGDMolecularMechanismSynopsis.objects.filter(
            lgd__stable_id__stable_id="G2P00001", is_deleted=0
        )
        self.assertEqual(len(lgd_mechanism_synopsis), 1)
        history_mechanism_synopsis = LGDMolecularMechanismSynopsis.history.all()
        self.assertEqual(len(history_mechanism_synopsis), 0)  # there was no insertion

        lgd_phenotypes = LGDPhenotype.objects.filter(
            lgd__stable_id__stable_id="G2P00001", is_deleted=0
        )
        self.assertEqual(len(lgd_phenotypes), 2)
        history_lgd_phenotypes = LGDPhenotype.history.all()
        self.assertEqual(len(history_lgd_phenotypes), 1)

        lgd_phenotype_summary = LGDPhenotypeSummary.objects.filter(
            lgd__stable_id__stable_id="G2P00001", is_deleted=0
        )
        self.assertEqual(len(lgd_phenotype_summary), 1)
        history_phenotype_summary = LGDPhenotypeSummary.history.all()
        self.assertEqual(len(history_phenotype_summary), 1)

        lgd_variant_types = LGDVariantType.objects.filter(
            lgd__stable_id__stable_id="G2P00001", is_deleted=0
        )
        self.assertEqual(len(lgd_variant_types), 1)
        history_lgd_variant_types = LGDVariantType.history.all()
        self.assertEqual(len(history_lgd_variant_types), 1)

        lgd_variant_descriptions = LGDVariantTypeDescription.objects.filter(
            lgd__stable_id__stable_id="G2P00001", is_deleted=0
        )
        self.assertEqual(len(lgd_variant_descriptions), 1)
        history_variant_descriptions = LGDVariantTypeDescription.history.all()
        self.assertEqual(len(history_variant_descriptions), 1)

        # Query the activity logs
        url_activity_logs = f"{self.url_base_activity_logs}?stable_id=G2P00001"
        response_logs = self.client.get(url_activity_logs)
        self.assertEqual(response_logs.status_code, 200)
        response_logs_data = response_logs.json()
        self.assertEqual(len(response_logs_data), 6)

    def test_add_lgd_publication_linked_mined_publication(self):
        """
        Test the endpoint to add multiple publications to a record which also includes a linked mined publication.
        It will test adding following 3 different publications:
        1. Publication that is not present in mined publication table
        2. Publication that is present in mined publication table but is not linked to this record
        3. Publication that is present in mined publication table and is linked to this record
        This test should add the 3 publications and should also update status of the 3rd mined publicationto "curated"
        """
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
                },
                {
                    "publication": {"pmid": 32302040},
                    "comment": {"comment": "", "is_public": 1},
                    "families": {
                        "families": 0,
                        "consanguinity": "unknown",
                        "ancestries": None,
                        "affected_individuals": 0,
                    },
                },
                {
                    "publication": {"pmid": 7866404},
                    "comment": {"comment": "", "is_public": 1},
                    "families": {
                        "families": 0,
                        "consanguinity": "unknown",
                        "ancestries": None,
                        "affected_individuals": 0,
                    },
                },
            ],
            "phenotypes": [
                {
                    "pmid": "15214012",
                    "summary": "Summary of phenotypes reported in PMID 15214012",
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

        # Initial status of the 3rd mined publication should be "mined"
        lgd_mined_publications = LGDMinedPublication.objects.filter(
            lgd__stable_id__stable_id="G2P00001", mined_publication__pmid=7866404
        )
        self.assertEqual(len(lgd_mined_publications), 1)
        self.assertEqual(lgd_mined_publications[0].status, "mined")

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

        # Check inserted data and history tables
        lgd_publications = LGDPublication.objects.filter(
            lgd__stable_id__stable_id="G2P00001", is_deleted=0
        )
        self.assertEqual(len(lgd_publications), 4)
        history_lgd_publications = LGDPublication.history.all()
        self.assertEqual(len(history_lgd_publications), 3)

        lgd_mechanism_evidence = LGDMolecularMechanismEvidence.objects.filter(
            lgd__stable_id__stable_id="G2P00001", is_deleted=0
        )
        self.assertEqual(len(lgd_mechanism_evidence), 2)
        history_mechanism_evidence = LGDMolecularMechanismEvidence.history.all()
        self.assertEqual(len(history_mechanism_evidence), 1)

        lgd_mechanism_synopsis = LGDMolecularMechanismSynopsis.objects.filter(
            lgd__stable_id__stable_id="G2P00001", is_deleted=0
        )
        self.assertEqual(len(lgd_mechanism_synopsis), 1)
        history_mechanism_synopsis = LGDMolecularMechanismSynopsis.history.all()
        self.assertEqual(len(history_mechanism_synopsis), 0)  # there was no insertion

        lgd_phenotypes = LGDPhenotype.objects.filter(
            lgd__stable_id__stable_id="G2P00001", is_deleted=0
        )
        self.assertEqual(len(lgd_phenotypes), 2)
        history_lgd_phenotypes = LGDPhenotype.history.all()
        self.assertEqual(len(history_lgd_phenotypes), 1)

        lgd_phenotype_summary = LGDPhenotypeSummary.objects.filter(
            lgd__stable_id__stable_id="G2P00001", is_deleted=0
        )
        self.assertEqual(len(lgd_phenotype_summary), 1)
        history_phenotype_summary = LGDPhenotypeSummary.history.all()
        self.assertEqual(len(history_phenotype_summary), 1)

        lgd_variant_types = LGDVariantType.objects.filter(
            lgd__stable_id__stable_id="G2P00001", is_deleted=0
        )
        self.assertEqual(len(lgd_variant_types), 1)
        history_lgd_variant_types = LGDVariantType.history.all()
        self.assertEqual(len(history_lgd_variant_types), 1)

        lgd_variant_descriptions = LGDVariantTypeDescription.objects.filter(
            lgd__stable_id__stable_id="G2P00001", is_deleted=0
        )
        self.assertEqual(len(lgd_variant_descriptions), 1)
        history_variant_descriptions = LGDVariantTypeDescription.history.all()
        self.assertEqual(len(history_variant_descriptions), 1)

        # Should update status of the 3rd mined publication to "curated"
        lgd_mined_publications = LGDMinedPublication.objects.filter(
            lgd__stable_id__stable_id="G2P00001", mined_publication__pmid=7866404
        )
        self.assertEqual(len(lgd_mined_publications), 1)
        self.assertEqual(lgd_mined_publications[0].status, "curated")

    def test_add_lgd_publication_wrong_mechanism_evidence(self):
        """
        Test to add mechanism evidence with wrong value
        """
        publication_to_add = {
            "publications": [
                {
                    "publication": {"pmid": 15214012},
                    "comment": {"comment": "This is new evidence", "is_public": 0},
                    "families": {
                        "families": 1,
                        "consanguinity": "unknown",
                        "ancestries": None,
                        "affected_individuals": 1,
                    },
                }
            ],
            "mechanism_evidence": [
                {
                    "pmid": "15214012",
                    "description": "This is new evidence for the existing mechanism evidence.",
                    "evidence_types": [
                        {"primary_type": "Function", "secondary_type": ["Biochemicals"]}
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
        self.assertEqual(response.status_code, 400)

        response_data = response.json()
        self.assertEqual(
            response_data["error"], "Invalid mechanism evidence 'Biochemicals'"
        )

    def test_add_lgd_publication_wrong_mechanism_synopsis(self):
        """
        Test to add mechanism synopsis with wrong value
        """
        publication_to_add = {
            "publications": [
                {
                    "publication": {"pmid": 15214012},
                    "comment": {"comment": "This is new evidence", "is_public": 0},
                    "families": {
                        "families": 1,
                        "consanguinity": "unknown",
                        "ancestries": None,
                        "affected_individuals": 1,
                    },
                }
            ],
            "mechanism_synopsis": [{"name": "destabilising", "support": "inferred"}],
            "mechanism_evidence": [
                {
                    "pmid": "15214012",
                    "description": "This is new evidence for the existing mechanism evidence.",
                    "evidence_types": [
                        {"primary_type": "Function", "secondary_type": ["Biochemicals"]}
                    ],
                }
            ],
        }

        # Login
        user = User.objects.get(email="user5@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        response = self.client.post(
            self.url_add_publication,
            publication_to_add,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

        response_data = response.json()
        self.assertEqual(
            response_data["error"], "Invalid mechanism synopsis value 'destabilising'"
        )

    def test_add_lgd_publication_wrong_mechanism_synopsis_support(self):
        """
        Test to add mechanism synopsis with wrong support value
        """
        publication_to_add = {
            "publications": [
                {
                    "publication": {"pmid": 15214012},
                    "comment": {"comment": "This is new evidence", "is_public": 0},
                    "families": {
                        "families": 1,
                        "consanguinity": "unknown",
                        "ancestries": None,
                        "affected_individuals": 1,
                    },
                }
            ],
            "mechanism_synopsis": [
                {"name": "destabilising LOF", "support": "inferreds"}
            ],
        }

        # Login
        user = User.objects.get(email="user5@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        response = self.client.post(
            self.url_add_publication,
            publication_to_add,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

        response_data = response.json()
        self.assertEqual(
            response_data["error"], "Invalid mechanism synopsis support 'inferreds'"
        )

    def test_add_lgd_publication_with_comment(self):
        """
        Test the endpoint to add a publication with commment to a record
        """
        publication_to_add = {
            "publications": [
                {
                    "publication": {"pmid": 15214012},
                    "comment": {
                        "comment": "Cardiac anomalies are reported in less than 20% of affected males",
                        "is_public": 0,
                    },
                    "families": {
                        "families": 1,
                        "consanguinity": "unknown",
                        "ancestries": "European, American",
                        "affected_individuals": 1,
                    },
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

        for lgd_publication in lgd_publications:
            # Check the comments linked to the LGD-publication
            lgd_publication_comments = LGDPublicationComment.objects.filter(
                lgd_publication_id=lgd_publication.id, is_deleted=0
            )
            self.assertEqual(len(lgd_publication_comments), 1)

        # Check the families/affected individuals for the new publication
        lgd_publication = LGDPublication.objects.get(
            lgd__stable_id__stable_id="G2P00001",
            publication__pmid=15214012,
            is_deleted=0,
        )
        self.assertEqual(lgd_publication.number_of_families, 1)
        self.assertEqual(lgd_publication.affected_individuals, 1)
        self.assertEqual(lgd_publication.ancestry, "European, American")
        self.assertEqual(lgd_publication.consanguinity.value, "unknown")

        # Check history tables
        history_records = LGDPublication.history.all()
        self.assertEqual(len(history_records), 1)
        history_records_comments = LGDPublicationComment.history.all()
        self.assertEqual(len(history_records_comments), 1)

    def test_add_lgd_publication_invalid_pmid(self):
        """
        Test the endpoint to add a LGD-publication with invalid PMID
        """
        publication_to_add = {
            "publications": [
                {
                    "publication": {"pmid": 0},
                    "comment": {
                        "comment": "Cardiac anomalies are reported in less than 20% of affected males",
                        "is_public": 0,
                    },
                    "families": {
                        "families": 1,
                        "consanguinity": "unknown",
                        "ancestries": "European, American",
                        "affected_individuals": 1,
                    },
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
        self.assertEqual(response.status_code, 400)

        response_data = response.json()
        self.assertEqual(response_data["error"], "Invalid PMID 0")

    def test_add_lgd_publication_invalid(self):
        """
        Test the endpoint to add a LGD-publication with invalid consanguinity
        """
        publication_to_add = {
            "publications": [
                {
                    "publication": {"pmid": 15214012},
                    "comment": {
                        "comment": "Cardiac anomalies are reported in less than 20% of affected males",
                        "is_public": 0,
                    },
                    "families": {
                        "families": 1,
                        "consanguinity": "u",
                        "ancestries": "European, American",
                        "affected_individuals": 1,
                    },
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
        self.assertEqual(response.status_code, 400)

        response_data = response.json()
        self.assertEqual(response_data["error"], "Invalid consanguinity value 'u'")

    def test_add_lgd_publication_invalid_input(self):
        """
        Test the endpoint to add a LGD-publication with invalid consanguinity
        """
        publication_to_add = {
            "publication": [
                {
                    "publication": {"pmid": 15214012},
                    "comment": {"comment": "", "is_public": 0},
                    "families": {
                        "families": 1,
                        "consanguinity": "",
                        "ancestries": "European, American",
                        "affected_individuals": 1,
                    },
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
        self.assertEqual(response.status_code, 400)

        response_data = response.json()
        self.assertEqual(
            response_data["error"], {"publications": ["This field is required."]}
        )
