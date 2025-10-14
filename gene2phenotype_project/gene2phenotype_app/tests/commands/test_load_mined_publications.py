import os
import tempfile
import csv
from io import StringIO

from django.core.management import call_command, CommandError
from django.test import TestCase

from gene2phenotype_app.models import MinedPublication, LGDMinedPublication


class TestLoadMinedPublicationsCommand(TestCase):
    fixtures = [
        "gene2phenotype_app/fixtures/attribs.json",
        "gene2phenotype_app/fixtures/disease.json",
        "gene2phenotype_app/fixtures/g2p_stable_id.json",
        "gene2phenotype_app/fixtures/cv_molecular_mechanism.json",
        "gene2phenotype_app/fixtures/locus_genotype_disease.json",
        "gene2phenotype_app/fixtures/ontology_term.json",
        "gene2phenotype_app/fixtures/source.json",
        "gene2phenotype_app/fixtures/locus.json",
        "gene2phenotype_app/fixtures/sequence.json",
        "gene2phenotype_app/fixtures/user_panels.json"
    ]

    def setUp(self):
        self.user_email = "john@test.ac.uk"

        # Make a temp input file
        self.tempfile = tempfile.NamedTemporaryFile(mode="w+", suffix=".csv", delete=False)
        writer = csv.writer(self.tempfile, delimiter=",")
        writer.writerow(["PMID", "G2P_IDs"])
        writer.writerow(["3897232", "G2P00001;G2P00002"])
        writer.writerow(["7866404", "G2P00003"])
        writer.writerow(["7866411", "G2P00006"])
        writer.writerow(["7868125", "G2P12346"])
        self.tempfile.flush()
        self.tempfile.close()

    def tearDown(self):
        # Clean up the temp file
        if os.path.exists(self.tempfile.name):
            os.remove(self.tempfile.name)

    def test_load_mined_publications(self):
        with self.assertLogs("gene2phenotype_app", level="WARNING") as cm:
            call_command(
                "load_mined_publications",
                "--data_file", self.tempfile.name,
                "--email", self.user_email
            )
        self.assertTrue(any("Invalid G2P ID 'G2P00003'. Skipping import." in msg for msg in cm.output))
        self.assertTrue(any("Invalid G2P ID 'G2P12346'. Skipping import." in msg for msg in cm.output))

        # Check database
        mined_publications = MinedPublication.objects.all()
        self.assertEqual(len(mined_publications), 4)
        history_mined_publications = MinedPublication.history.all()
        self.assertEqual(len(history_mined_publications), 4)
        lgd_mined_publications = LGDMinedPublication.objects.all()
        self.assertEqual(len(lgd_mined_publications), 3)
        history_lgd_mined_publications = LGDMinedPublication.history.all()
        self.assertEqual(len(history_lgd_mined_publications), 3)

    def test_invalid_file_extension(self):
        invalid_file = tempfile.NamedTemporaryFile(suffix=".txt")
        with self.assertRaises(CommandError):
            call_command(
                "load_mined_publications",
                "--data_file", invalid_file.name,
                "--email", self.user_email
            )
