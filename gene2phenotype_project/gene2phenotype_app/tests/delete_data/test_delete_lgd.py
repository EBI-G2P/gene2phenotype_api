from django.test import TestCase
from django.urls import reverse
from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken
from gene2phenotype_app.models import (
    User,
    G2PStableID,
    LocusGenotypeDisease,
    LGDPanel,
    LGDComment,
    LGDMolecularMechanismEvidence,
    LGDMolecularMechanismSynopsis,
    LGDPhenotype,
    LGDPhenotypeSummary,
    LGDVariantType,
    LGDVariantTypeComment,
    LGDVariantTypeDescription,
    LGDVariantGenccConsequence,
    LGDCrossCuttingModifier
)

class LGDDeleteLGDEndpoint(TestCase):
    """
        Test endpoint to delete a record (LGD)
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
        "gene2phenotype_app/fixtures/lgd_comment.json",
        "gene2phenotype_app/fixtures/lgd_phenotype.json",
        "gene2phenotype_app/fixtures/lgd_phenotype_summary.json",
        "gene2phenotype_app/fixtures/lgd_variant_type.json",
        "gene2phenotype_app/fixtures/lgd_variant_type_comment.json",
        "gene2phenotype_app/fixtures/lgd_variant_type_description.json",
        "gene2phenotype_app/fixtures/lgd_variant_consequence.json",
        "gene2phenotype_app/fixtures/lgd_cross_cutting_modifier.json"
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
        lgd_comment_obj = LGDComment.objects.get(lgd=lgd_obj.id)
        self.assertEqual(lgd_comment_obj.is_deleted, 1)
        mechanism_evidence_obj = LGDMolecularMechanismEvidence.objects.get(lgd=lgd_obj.id)
        self.assertEqual(mechanism_evidence_obj.is_deleted, 1)
        mechanism_synopsys_list = LGDMolecularMechanismSynopsis.objects.filter(lgd=lgd_obj.id)
        for mechanism_synopsys in mechanism_synopsys_list:
            self.assertEqual(mechanism_synopsys.is_deleted, 1)
        phenotype_list = LGDPhenotype.objects.filter(lgd=lgd_obj.id)
        for phenotype in phenotype_list:
            self.assertEqual(phenotype.is_deleted, 1)
        phenotype_summary_list = LGDPhenotypeSummary.objects.filter(lgd=lgd_obj.id)
        for pheno_summary in phenotype_summary_list:
            self.assertEqual(pheno_summary.is_deleted, 1)
        lgd_variant_type_list = LGDVariantType.objects.filter(lgd=lgd_obj.id)
        for variant_type in lgd_variant_type_list:
            self.assertEqual(variant_type.is_deleted, 1)
            variant_type_comment_list = LGDVariantTypeComment.objects.filter(lgd_variant_type=variant_type.id)
            for variant_type_comment in variant_type_comment_list:
                self.assertEqual(variant_type_comment.is_deleted, 1)
        lgd_variant_type_desc_list = LGDVariantTypeDescription.objects.filter(lgd=lgd_obj.id)
        for variant_type_desc in lgd_variant_type_desc_list:
            self.assertEqual(variant_type_desc.is_deleted, 1)
        lgd_variant_consequence_list = LGDVariantGenccConsequence.objects.filter(lgd=lgd_obj.id)
        for variant_consequence in lgd_variant_consequence_list:
            self.assertEqual(variant_consequence.is_deleted, 1)
        lgd_ccm_list = LGDCrossCuttingModifier.objects.filter(lgd=lgd_obj.id)
        for lgd_ccm in lgd_ccm_list:
            self.assertEqual(lgd_ccm.is_deleted, 1)
