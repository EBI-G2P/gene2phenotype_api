#!/usr/bin/env python3

import sys
import html
import re
import requests

def get_publication(pmid):
    url = f"https://www.ebi.ac.uk/europepmc/webservices/rest/article/MED/{pmid}?format=json"

    r = requests.get(url, headers={ "Content-Type" : "application/json"})

    if not r.ok:
        r.raise_for_status()
        sys.exit()

    decoded = r.json()

    return decoded

def get_authors(response):
    authors = None

    if 'authorString' in response['result']:
        authors = response['result']['authorString']
        if len(authors) > 250:
            authors_split = authors.split(',')
            authors = f"{authors_split[0]} et al."
    
    return authors

def clean_title(title):
    title = re.sub(r"<.*?>", "", html.unescape(title))
    title = re.sub(r"^\[", "", title)
    title = re.sub(r"\]\.$", ".", title)

    return title