#!/usr/bin/env python3

import os
import sys
import requests


def query_ensembl(url):
    r = requests.get(url, headers={"Content-Type": "application/json"})

    if not r.ok:
        r.raise_for_status()
        sys.exit()

    decoded = r.json()

    return decoded


def validate_gene(gene_name):
    url = f"https://rest.ensembl.org/xrefs/name/human/{gene_name}?content-type=application/json"
    url_symbol = f"https://rest.ensembl.org/xrefs/symbol/homo_sapiens/{gene_name}?content-type=application/json"
    url_phenotype = f"https://rest.ensembl.org/phenotype/gene/homo_sapiens/{gene_name}?content-type=application/json"

    decoded = query_ensembl(url)
    validated = None

    if len(decoded) > 0:
        for data in decoded:
            if data["db_display_name"] == "HGNC Symbol":
                validated = data

        decoded_symbol = query_ensembl(url_symbol)
        if len(decoded_symbol) > 0:
            validated["ensembl_id"] = decoded_symbol[0]["id"]

        decoded_phenotype = query_ensembl(url_phenotype)
        if len(decoded_phenotype) > 0:
            for pheno in decoded_phenotype:
                if pheno["source"] == "MIM morbid":
                    if "mim" not in validated:
                        validated["mim"] = [
                            {
                                "id": pheno["attributes"]["external_id"],
                                "ensembl_id": pheno["Gene"],
                                "disease": pheno["description"],
                            }
                        ]
                    else:
                        validated["mim"].append(
                            {
                                "id": pheno["attributes"]["external_id"],
                                "ensembl_id": pheno["Gene"],
                                "disease": pheno["description"],
                            }
                        )

    return validated
