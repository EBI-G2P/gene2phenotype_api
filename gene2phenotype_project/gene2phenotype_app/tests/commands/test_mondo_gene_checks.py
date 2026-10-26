from django.test import TestCase

from gene2phenotype_app.management.commands.datachecks.Disease import (
    check_mondo_single_gene_link,
)
from gene2phenotype_app.models import (
    Attrib,
    DiseaseOntologyTerm,
    GeneDisease,
    LGDPanel,
    Locus,
    LocusGenotypeDisease,
    OntologyTerm,
    Panel,
    Source,
)


class MondoGeneChecksTests(TestCase):
    fixtures = [
        f"gene2phenotype_app/fixtures/{name}.json"
        for name in [
            "attribs", "source", "sequence", "locus", "ontology_term",
            "disease", "g2p_stable_id", "cv_molecular_mechanism",
            "locus_genotype_disease", "user_panels", "lgd_panel",
        ]
    ]

    def setUp(self):
        self.mondo_id = "MONDO:9999999"
        self.source = Source.objects.get(name="Mondo")
        template = DiseaseOntologyTerm.objects.first()
        term = OntologyTerm.objects.create(
            accession=self.mondo_id,
            term="Test shared disease",
            source=self.source,
            group_type=template.ontology_term.group_type,
        )
        self.supported_record = LocusGenotypeDisease.objects.get(pk=1)
        self.unsupported_record = LocusGenotypeDisease.objects.get(pk=2)
        LocusGenotypeDisease.objects.exclude(pk__in=[1, 2]).update(is_deleted=1)
        panel = Panel.objects.filter(is_visible=1).first()
        for record in [self.supported_record, self.unsupported_record]:
            DiseaseOntologyTerm.objects.create(
                disease=record.disease,
                ontology_term=term,
                mapped_by_attrib=template.mapped_by_attrib,
            )
            LGDPanel.objects.update_or_create(
                lgd=record, panel=panel, defaults={"is_deleted": 0}
            )
        # Keep external associations isolated from fixture mappings.
        GeneDisease.objects.all().delete()
        self.add_external_link(self.supported_record.locus)

    def add_external_link(self, locus):
        return GeneDisease.objects.create(
            gene=locus,
            disease="Test shared disease",
            identifier=self.mondo_id,
            source=self.source,
        )

    def test_unsupported_gene_is_reported(self):
        errors = check_mondo_single_gene_link()
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].id, "gene2phenotype_app.E403")
        self.assertIn(self.unsupported_record.locus.name, errors[0].msg)

    def test_supported_genes_are_accepted(self):
        self.add_external_link(self.unsupported_record.locus)
        self.assertEqual(check_mondo_single_gene_link(), [])

    def test_non_gene_lgd_records_are_excluded(self):
        for locus_type in ["variant", "region"]:
            with self.subTest(locus_type=locus_type):
                Locus.objects.filter(pk=self.unsupported_record.locus_id).update(
                    type=Attrib.objects.get(type__code="locus_type", value=locus_type)
                )
                self.assertEqual(check_mondo_single_gene_link(), [])

    def test_non_gene_external_associations_are_excluded(self):
        GeneDisease.objects.all().delete()
        locus = Locus.objects.get(pk=3)
        self.add_external_link(locus)
        for locus_type in ["variant", "region"]:
            with self.subTest(locus_type=locus_type):
                Locus.objects.filter(pk=locus.pk).update(
                    type=Attrib.objects.get(type__code="locus_type", value=locus_type)
                )
                # No external gene associations remain, so the existing check skips it.
                self.assertEqual(check_mondo_single_gene_link(), [])
