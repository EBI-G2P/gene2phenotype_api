#!/usr/bin/env python3

import os
import sys
import re
import requests

def latin2arab(match):
    latin = match.group(1)

    return 'type ' + {
        'i': '1',
        'ii': '2',
        'iii': '3',
        'iv': '4',
        'v': '5',
        'vi': '6',
        'vii': '7',
        'viii': '8',
        'ix': '9',
        'xvii': '17'
    }[latin]

def clean_string(name):
    new_disease_name = name.strip()

    new_disease_name = new_disease_name.lstrip('?')
    new_disease_name = new_disease_name.rstrip('.')
    new_disease_name = re.sub(r',\s+', ' ', new_disease_name)
    new_disease_name = new_disease_name.replace('“', '').replace('”', '')
    new_disease_name = new_disease_name.replace('-', ' ')
    new_disease_name = re.sub(r'\t+', ' ', new_disease_name)

    new_disease_name = new_disease_name.lower()

    new_disease_name = re.sub(r'\s+and\s+', ' ', new_disease_name)
    new_disease_name = re.sub(r'\s+or\s+', ' ', new_disease_name)

    # remove 'biallelic' and 'autosomal'
    new_disease_name = re.sub(r'biallelic$', '', new_disease_name)
    new_disease_name = re.sub(r'autosomal$', '', new_disease_name)
    new_disease_name = re.sub(r'\(biallelic\)$', '', new_disease_name)
    new_disease_name = re.sub(r'\(autosomal\)$', '', new_disease_name)

    new_disease_name = re.sub(r'type ([xvi]+)$', latin2arab, new_disease_name)

    # remove 'type'
    if re.search(r'\s+type\s+[0-9]+[a-z]?$', new_disease_name):
        new_disease_name = re.sub(r'\s+type\s+', ' ', new_disease_name)

    new_disease_name = re.sub(r'\(|\)', ' ', new_disease_name)
    new_disease_name = re.sub(r'\s+', ' ', new_disease_name)

    # tokenise string
    disease_tokens = sorted(new_disease_name.split())

    return " ".join(disease_tokens)

# Clean OMIM disease name
# Removes the gene and subtype from the disease name
# Example: "BLEPHAROCHEILODONTIC SYNDROME 1; BCDS1" -> "blepharocheilodontic syndrome"
def clean_omim_disease(name):
    disease_name = name.split(";")[0]
    disease_name = re.sub(r',*\s*(TYPE)*,*\s+([0-9]+[A-Z]{0,2}|[IVX]{0,3})$', '', disease_name)

    # Some disease names have the subtype in the middle
    # Remove the integers but keep the word 'syndrome'
    # Example: "ALPORT SYNDROME 2, AUTOSOMAL RECESSIVE; ATS2"
    disease_name = re.sub(r'SYNDROME\s+[0-9]+,*', 'SYNDROME', disease_name)
    # After: "alport syndrome autosomal recessive"

    # If the integer is preceded by 'type' then remove both
    # Example before: "TYPE 1 DIABETES MELLITUS; T1D"
    disease_name = re.sub(r'TYPE\s+[0-9]+,*', '', disease_name)
    # After: "diabetes mellitus"

    return disease_name.lower().strip()


"""
    Get the ontology info from the disease ID

    Input:
            id: disease ID
            source: source name
    Output:
            ols response
            return None if no response or source is invalid
"""
def get_ontology(id, source):
    if source.lower() == "mondo":
        url = f"https://www.ebi.ac.uk/ols4/api/search?q={id}&ontology=mondo&exact=1"

    elif source.lower() == "omim":
        url = f"https://www.ebi.ac.uk/ols4/api/search?q={id}&ontology=cco"

    else:
        return None

    r = requests.get(url, headers={ "Content-Type" : "application/json"})

    if not r.ok:
        r.raise_for_status()
        return "query failed"

    decoded = r.json()

    if len(decoded['response']['docs']) > 0 and 'label' in decoded['response']['docs'][0]:
        name = decoded['response']['docs'][0]
    else:
        name = None

    return name


"""
    To store the ontology ID/term we have to know its source.
    The source can be OMIM or Mondo.

    Input: disease ID
    Output: source of the disease ID (Mondo or OMIM)
            the source name is going to be used to fetch the source id from the db (case sensitive)
"""
def get_ontology_source(id):
    source = None

    if id.startswith("MONDO"):
        source = "Mondo"
    elif id.isdigit():
        source = "OMIM"

    return source