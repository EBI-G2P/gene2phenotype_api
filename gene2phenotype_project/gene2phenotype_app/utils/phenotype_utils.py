#!/usr/bin/env python3

import os
import sys
import requests

def validate_phenotype(accession):
    r = requests.get(f"https://hpo.jax.org/api/hpo/term/{accession}")
    obj = None
    try:
        obj = r.json()
    except requests.exceptions.JSONDecodeError:
        pass

    return obj
