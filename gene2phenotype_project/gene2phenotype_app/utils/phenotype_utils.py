#!/usr/bin/env python3

import os
import sys
import requests

"""
    Queries the HPO API to fetch the phenotype data.
"""
def validate_phenotype(accession):
    r = requests.get(f"https://ontology.jax.org/api/hp/terms/{accession}")
    obj = None
    try:
        obj = r.json()
    except requests.exceptions.JSONDecodeError:
        pass

    return obj
