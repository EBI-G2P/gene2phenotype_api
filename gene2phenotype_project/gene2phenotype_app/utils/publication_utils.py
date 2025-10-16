#!/usr/bin/env python3

import sys
import html
import re
import time
import requests


def get_publication(pmid):
    url = f"https://www.ebi.ac.uk/europepmc/webservices/rest/article/MED/{pmid}?format=json"

    max_retries=3
    wait_seconds=30

    for attempt in range(1, max_retries + 1):
        try:
            r = requests.get(url, headers={"Content-Type": "application/json"})

            # Check if the response was successful
            if r.ok:
                return r.json()
            else:
                print(f"Attempt {attempt}: Request failed with status {r.status_code}")
                r.raise_for_status()

        except requests.RequestException as e:
            print(f"Attempt {attempt} failed due to: {e}")

            # Only wait if we have retries left
            if attempt < max_retries:
                print(f"Retrying in {wait_seconds} seconds...")
                time.sleep(wait_seconds)
            else:
                print("Max retries reached. Exiting.")
                sys.exit(1)


def get_authors(response):
    authors = None

    if "authorString" in response["result"]:
        authors = response["result"]["authorString"]
        if len(authors) > 250:
            authors_split = authors.split(",")
            authors = f"{authors_split[0]} et al."

    return authors


def clean_title(title):
    title = re.sub(r"<.*?>", "", html.unescape(title))
    title = re.sub(r"^\[", "", title)
    title = re.sub(r"\]\.$", ".", title)

    return title
