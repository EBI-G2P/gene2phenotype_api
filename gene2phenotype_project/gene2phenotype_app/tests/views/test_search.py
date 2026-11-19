from urllib.parse import parse_qs, urlencode, urlsplit

from django.conf import settings
from django.test import TestCase
from django.urls import reverse
from rest_framework_simplejwt.tokens import RefreshToken

from gene2phenotype_app.models import (
    Attrib,
    AttribType,
    Disease,
    G2PStableID,
    LGDPanel,
    Locus,
    LocusAttrib,
    LocusGenotypeDisease,
    User,
)


class SearchTests(TestCase):
    """
    Test the search endpoint: SearchView
    """

    fixtures = [
        "gene2phenotype_app/fixtures/auth_groups.json",
        "gene2phenotype_app/fixtures/locus.json",
        "gene2phenotype_app/fixtures/attribs.json",
        "gene2phenotype_app/fixtures/source.json",
        "gene2phenotype_app/fixtures/sequence.json",
        "gene2phenotype_app/fixtures/cv_molecular_mechanism.json",
        "gene2phenotype_app/fixtures/disease.json",
        "gene2phenotype_app/fixtures/g2p_stable_id.json",
        "gene2phenotype_app/fixtures/lgd_panel.json",
        "gene2phenotype_app/fixtures/locus_genotype_disease.json",
        "gene2phenotype_app/fixtures/publication.json",
        "gene2phenotype_app/fixtures/user_panels.json",
        "gene2phenotype_app/fixtures/ontology_term.json",
        "gene2phenotype_app/fixtures/lgd_publication.json",
        "gene2phenotype_app/fixtures/lgd_phenotype.json",
        "gene2phenotype_app/fixtures/lgd_variant_consequence.json",
        "gene2phenotype_app/fixtures/curation_data.json",
    ]

    def setUp(self):
        self.base_url_search = reverse("search")
        self.expected_data = [
            {
                "stable_id": "G2P00001",
                "gene": "CEP290",
                "genotype": "biallelic_autosomal",
                "disease": "CEP290-related JOUBERT SYNDROME TYPE 5",
                "mechanism": "loss of function",
                "panel": ["DD", "Eye"],
                "confidence": "definitive",
            }
        ]
        self.expected_data_mpi = [
            {
                "stable_id": "G2P00009",
                "gene": "MPI",
                "genotype": "biallelic_autosomal",
                "disease": "MPI-related congenital disorder of glycosylation",
                "mechanism": "undetermined",
                "panel": ["Eye"],
                "confidence": "definitive",
            }
        ]

    def test_search_gene(self):
        """
        Test the response when searching by gene
        """
        url_search_gene = f"{self.base_url_search}?type=gene&query=CEP290"
        response = self.client.get(url_search_gene)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["next"], None)
        self.assertEqual(response.data["previous"], None)
        self.assertEqual(response.data["results"], self.expected_data)

    def test_search_pagination_preserves_filters_and_returns_all_records(self):
        """Follow three pages without losing filters, records or total counts."""
        template = LocusGenotypeDisease.objects.get(stable_id__stable_id="G2P00001")
        panel = template.lgdpanel_set.get(panel__name="DD").panel
        expected_ids = []
        for index in range(45):
            stable_id = G2PStableID.objects.create(
                stable_id=f"G2P{90000 + index}", is_live=True
            )
            record = LocusGenotypeDisease.objects.create(
                stable_id=stable_id,
                locus=template.locus,
                genotype=template.genotype,
                disease=Disease.objects.create(name=f"Pagination regression {index:02d}"),
                mechanism=template.mechanism,
                mechanism_support=template.mechanism_support,
                confidence=template.confidence,
                is_reviewed=1,
            )
            LGDPanel.objects.create(lgd=record, panel=panel)
            expected_ids.append(stable_id.stable_id)

        filters = {
            "query": "Pagination regression",
            "type": "disease",
            "panel": panel.name,
            "genotype": template.genotype.value,
            "mechanism": template.mechanism.value,
        }
        next_url = f"{self.base_url_search}?{urlencode(filters)}"
        returned_ids = []
        pages = []
        # A fixed traversal also catches repeated links without an unbounded loop.
        for page_number, expected_size in enumerate((20, 20, 5), start=1):
            with self.subTest(page=page_number):
                self.assertIsNotNone(next_url)
                response = self.client.get(next_url)
                self.assertEqual(response.status_code, 200)
                data = response.data
                self.assertEqual(data["count"], 45)
                self.assertEqual(len(data["results"]), expected_size)
                pages.append(data["results"])
                returned_ids.extend(row["stable_id"] for row in data["results"])

                for direction, target_page in (
                    ("previous", page_number - 1),
                    ("next", page_number + 1),
                ):
                    link = data[direction]
                    if target_page not in (1, 2, 3):
                        self.assertIsNone(link)
                        continue
                    self.assertIsNotNone(link)
                    parsed = urlsplit(link)
                    self.assertEqual(parsed.path, self.base_url_search)
                    params = parse_qs(parsed.query)
                    self.assertEqual(params.pop("page", ["1"]), [str(target_page)])
                    self.assertEqual(params, {key: [value] for key, value in filters.items()})

                next_url = data["next"]

        self.assertIsNone(next_url)
        self.assertEqual(len(returned_ids), len(set(returned_ids)))
        self.assertCountEqual(returned_ids, expected_ids)
        previous_response = self.client.get(data["previous"])
        self.assertEqual(previous_response.status_code, 200)
        self.assertEqual(previous_response.data["results"], pages[1])

    def assert_search_results_equal(self, actual, expected):
        # Neither record order nor panel order is relevant to locus-type filtering.
        self.assertCountEqual(
            [dict(row, panel=sorted(row["panel"])) for row in actual],
            [dict(row, panel=sorted(row["panel"])) for row in expected],
        )

    def test_gene_search_excludes_non_gene_loci(self):
        locus = Locus.objects.get(name="CEP290")
        for locus_type in ["variant", "region"]:
            locus.type = Attrib.objects.get(type__code="locus_type", value=locus_type)
            locus.save(update_fields=["type"])
            for query in ["CEP290", "BBS14", "HGNC:29021"]:
                with self.subTest(locus_type=locus_type, query=query):
                    response = self.client.get(
                        self.base_url_search, {"type": "gene", "query": query}
                    )
                    self.assertEqual(response.status_code, 404)
                    self.assertEqual(
                        response.data["error"], f"No matching Gene found for: {query}"
                    )

            # Generic search should continue to include other locus types.
            response = self.client.get(self.base_url_search, {"query": "CEP290"})
            self.assertEqual(response.status_code, 200)
            self.assert_search_results_equal(response.data["results"], self.expected_data)

    def test_gene_search_filters_non_gene_alias_matches(self):
        locus = Locus.objects.get(name="RAB27A")
        LocusAttrib.objects.create(
            locus=locus,
            attrib_type=AttribType.objects.get(code="gene_synonym"),
            value="CEP290",
        )
        for locus_type in ["variant", "region"]:
            with self.subTest(locus_type=locus_type):
                locus.type = Attrib.objects.get(type__code="locus_type", value=locus_type)
                locus.save(update_fields=["type"])
                response = self.client.get(
                    self.base_url_search, {"type": "gene", "query": "CEP290"}
                )
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.data["count"], 1)
                self.assert_search_results_equal(response.data["results"], self.expected_data)

    def test_search_disease(self):
        """
        Test the response when searching by disease type of search
        """
        url_search_disease = f"{self.base_url_search}?type=disease&query=CEP290-related JOUBERT SYNDROME TYPE 5"
        response = self.client.get(url_search_disease)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["next"], None)
        self.assertEqual(response.data["previous"], None)
        self.assertEqual(response.data["results"], self.expected_data)

    def test_search_disease_2(self):
        """
        Test the response when searching by disease and by panel
        """
        url_search_disease = f"{self.base_url_search}?type=disease&panel=DD&query=CEP290-related JOUBERT SYNDROME TYPE 5"
        response = self.client.get(url_search_disease)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["next"], None)
        self.assertEqual(response.data["previous"], None)
        self.assertEqual(response.data["results"], self.expected_data)

    def test_search_disease_not_found(self):
        """
        Test the response when searching by disease and by panel return 404
        """
        url_search_disease = f"{self.base_url_search}?type=disease&panel=DD&query=CEP290-related SYNDROME TYPE"
        response = self.client.get(url_search_disease)

        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            response.data["error"],
            "No matching Disease found for: CEP290-related SYNDROME TYPE",
        )

    def test_search_disease_generic(self):
        """
        Test the response when searching a disease
        """
        url_search_disease = (
            f"{self.base_url_search}?query=CEP290-related JOUBERT SYNDROME TYPE 5"
        )
        response = self.client.get(url_search_disease)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["next"], None)
        self.assertEqual(response.data["previous"], None)
        self.assertEqual(response.data["results"], self.expected_data)

    def test_search_by_phenotype(self):
        """
        Test the response when searching by phenotype and by panel
        """
        url_search_disease = (
            f"{self.base_url_search}?type=phenotype&panel=DD&query=HP:0033127"
        )
        response = self.client.get(url_search_disease)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["next"], None)
        self.assertEqual(response.data["previous"], None)
        self.assertEqual(response.data["results"], self.expected_data)

    def test_search_by_phenotype_2(self):
        """
        Test the response when searching by phenotype
        """
        url_search_disease = f"{self.base_url_search}?type=phenotype&query=HP:0033127"
        response = self.client.get(url_search_disease)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 2)
        self.assertEqual(response.data["next"], None)
        self.assertEqual(response.data["previous"], None)

    def test_search_by_phenotype_not_found(self):
        """
        Test the response when searching by phenotype without results
        """
        url_search_disease = f"{self.base_url_search}?type=phenotype&query=HP:0033126"
        response = self.client.get(url_search_disease)

        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            response.data["error"], "No matching Phenotype found for: HP:0033126"
        )

    def test_search_g2p_id(self):
        """
        Test the response when searching by G2P stable ID
        """
        url_search_id = f"{self.base_url_search}?type=stable_id&query=G2P00001"
        response = self.client.get(url_search_id)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["next"], None)
        self.assertEqual(response.data["previous"], None)
        self.assertEqual(response.data["results"], self.expected_data)

    def test_search_g2p_id_2(self):
        """
        Test the response when searching by G2P stable ID and by panel
        """
        url_search_id = f"{self.base_url_search}?type=stable_id&panel=DD&query=G2P00001"
        response = self.client.get(url_search_id)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["next"], None)
        self.assertEqual(response.data["previous"], None)
        self.assertEqual(response.data["results"], self.expected_data)

    def test_search_g2p_id_not_found(self):
        """
        Test the response when searching by G2P stable ID that has been deleted
        """
        url_search_id = f"{self.base_url_search}?type=stable_id&query=G2P00003"
        response = self.client.get(url_search_id)

        self.assertEqual(response.status_code, 410)
        self.assertEqual(response.data["message"], "G2P00003 is no longer available.")

    def test_search_g2p_id_merged(self):
        """
        Test the response when searching by G2P stable ID that has been merged
        """
        url_search_id = f"{self.base_url_search}?type=stable_id&query=G2P00007"
        response = self.client.get(url_search_id)

        self.assertEqual(response.status_code, 410)
        self.assertEqual(
            response.data["message"],
            "G2P00007 is no longer available. It has been merged into G2P00001",
        )
        self.assertEqual(response.data["stable_id"], "G2P00001")

    def test_generic_search_merged(self):
        """
        Test the response when searching by a record that has been merged
        """
        url_search_id = f"{self.base_url_search}?query=G2P00007"
        response = self.client.get(url_search_id)

        self.assertEqual(response.status_code, 410)
        self.assertEqual(
            response.data["message"],
            "G2P00007 is no longer available. It has been merged into G2P00001",
        )
        self.assertEqual(response.data["stable_id"], "G2P00001")

    def test_search_draft(self):
        """
        Test the response when searching a draft
        """
        # Login
        user = User.objects.get(email="user5@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        # Authenticate by setting cookie on the test client
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        url_search_id = f"{self.base_url_search}?type=draft&query=CEP290"
        response = self.client.get(url_search_id)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)

    def test_search_draft_not_found(self):
        """
        Test the response when searching a draft without results
        """
        # Login
        user = User.objects.get(email="user5@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        # Authenticate by setting cookie on the test client
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        url_search_id = f"{self.base_url_search}?type=draft&query=CDH1"
        response = self.client.get(url_search_id)

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data["error"], "No matching draft found for: CDH1")

    def test_search_draft_found_automatic(self):
        """
        Test automatic drafts are included in the response when the owner is not in g2p_admin.
        """
        # Login
        user = User.objects.get(email="user5@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        # Authenticate by setting cookie on the test client
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        url_search_id = f"{self.base_url_search}?type=draft&query=MPI"
        response = self.client.get(url_search_id)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)

    def test_search_draft_automatic_for_g2p_admin(self):
        """
        Test automatic drafts are included when the owner is in g2p_admin.
        """
        # Login
        user = User.objects.get(email="user5@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        # Authenticate by setting cookie on the test client
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        url_search_id = f"{self.base_url_search}?type=draft&query=TUBB4A"
        response = self.client.get(url_search_id)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 2)
        self.assertEqual(
            {result["status"] for result in response.data["results"]}, {"automatic"}
        )

    def test_search_all(self):
        """
        Test the response when searching without specific type
        """
        url_search = f"{self.base_url_search}?query=CEP290"
        response = self.client.get(url_search)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["next"], None)
        self.assertEqual(response.data["previous"], None)
        self.assertEqual(response.data["results"], self.expected_data)

    def test_search_not_found(self):
        """
        Test the response when not found
        """
        url_search_gene = f"{self.base_url_search}?type=gene&query=TUBB4A"
        response = self.client.get(url_search_gene)

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data["error"], "No matching Gene found for: TUBB4A")

    def test_search_gene_with_really_long_query(self):
        """
        Test the endpoint rejects a very long search query.
        """
        long_query = "TUBB4A" * 300
        url_search_gene = f"{self.base_url_search}?type=gene&query={long_query}"
        response = self.client.get(url_search_gene)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data["error"],
            "Search query is too long. Maximum length is 255 characters.",
        )

    def test_search_not_found_2(self):
        """
        Test the response when not found because the record is deleted
        """
        url_search_gene = f"{self.base_url_search}?type=gene&query=STRA6"
        response = self.client.get(url_search_gene)

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data["error"], "No matching Gene found for: STRA6")

    def test_search_not_found_3(self):
        """
        Test the response when not found because the record is private
        """
        url_search_gene = f"{self.base_url_search}?query=BAAT"
        response = self.client.get(url_search_gene)

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data["error"], "No matching results found for: BAAT")

    def test_search_not_found_4(self):
        """
        Test the response when gene not found because the record is private
        """
        url_search_gene = f"{self.base_url_search}?type=gene&query=BAAT"
        response = self.client.get(url_search_gene)

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data["error"], "No matching Gene found for: BAAT")

    def test_search_without_query(self):
        """
        Test the endpoint when querying without a query text
        """
        url_search_gene = f"{self.base_url_search}?type=gene"
        response = self.client.get(url_search_gene)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 0)

    def test_generic_search_by_panel(self):
        """
        Test the response when searching by panel
        """
        url_search_disease = f"{self.base_url_search}?query=CEP290&panel=DD"
        response = self.client.get(url_search_disease)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["next"], None)
        self.assertEqual(response.data["previous"], None)
        self.assertEqual(response.data["results"], self.expected_data)

    def test_generic_search_by_panel_2(self):
        """
        Test the response when searching by panel without results
        """
        url_search_disease = f"{self.base_url_search}?query=GS2&panel=DD"
        response = self.client.get(url_search_disease)

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data["error"], "No matching results found for: GS2")

    def test_generic_search_by_panel_3(self):
        """
        Test the response when searching by panel
        """
        url_search_disease = f"{self.base_url_search}?type=gene&query=CEP290&panel=DD"
        response = self.client.get(url_search_disease)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["next"], None)
        self.assertEqual(response.data["previous"], None)
        self.assertEqual(response.data["results"], self.expected_data)

    def test_invalid_search_type(self):
        """
        Test the endpoint with an invalid search type
        """
        url_search_disease = f"{self.base_url_search}?type=g2p&query=CEP290"
        response = self.client.get(url_search_disease)

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data["error"], "Search type is not valid")

    def test_search_authenticated_user(self):
        """
        Test the response for authenticated users
        """
        # Login
        user = User.objects.get(email="user5@test.ac.uk")
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        # Authenticate by setting cookie on the test client
        self.client.cookies[settings.SIMPLE_JWT["AUTH_COOKIE"]] = access_token

        url_search_id = f"{self.base_url_search}?query=G2P00006"
        response = self.client.get(url_search_id)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)

        expected_data = [
            {
                "stable_id": "G2P00006",
                "gene": "RAB27A",
                "genotype": "biallelic_autosomal",
                "disease": "RAB27A-related Griscelli syndrome biallelic",
                "mechanism": "loss of function",
                "panel": ["Ear", "Eye"],
                "confidence": "strong",
            }
        ]
        self.assertEqual(response.data["results"], expected_data)

    def test_search_with_mechanism(self):
        """
        Test the response when searching a gene and filtering by mechanism
        """
        url_search_mechanism = (
            f"{self.base_url_search}?query=CEP290&mechanism=loss of function"
        )
        response = self.client.get(url_search_mechanism)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["next"], None)
        self.assertEqual(response.data["previous"], None)
        self.assertEqual(response.data["results"], self.expected_data)

    def test_search_with_mechanism_not_found(self):
        """
        Test the response when searching a gene and filtering by mechanism that does not match
        """
        url_search_mechanism_not_found = (
            f"{self.base_url_search}?query=CEP290&mechanism=undetermined"
        )
        response_not_found = self.client.get(url_search_mechanism_not_found)

        self.assertEqual(response_not_found.status_code, 404)
        self.assertEqual(
            response_not_found.data["error"], "No matching results found for: CEP290"
        )

    def test_search_with_variant_consequence(self):
        """
        Test the response when searching a gene and filtering by variant consequence
        """
        url_search_variant_consequence = (
            f"{self.base_url_search}?query=MPI&variant_consequence=absent gene product"
        )
        response = self.client.get(url_search_variant_consequence)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["next"], None)
        self.assertEqual(response.data["previous"], None)
        self.assertEqual(response.data["results"], self.expected_data_mpi)

    def test_search_with_variant_consequence_accession(self):
        """
        Test the response when searching a gene and filtering by variant consequence (SO accession)
        """
        url_search_variant_consequence = (
            f"{self.base_url_search}?query=MPI&variant_consequence=SO:0002317"
        )
        response = self.client.get(url_search_variant_consequence)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["next"], None)
        self.assertEqual(response.data["previous"], None)
        self.assertEqual(response.data["results"], self.expected_data_mpi)
