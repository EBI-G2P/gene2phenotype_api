from django.core.checks import Error
from django.db.models import F
from difflib import SequenceMatcher
import re

from gene2phenotype_app.models import (
    DiseaseOntologyTerm,
    LocusGenotypeDisease
)

from gene2phenotype_app.utils import (
    clean_string,
    clean_omim_disease,
    check_synonyms_disease
)


def check_cross_references():
    errors = []

    # Select disease with ontology terms that are linked to visible panels
    disease_ontology_list = (
        DiseaseOntologyTerm.objects.select_related("disease", "ontology_term")
        .annotate(
            disease_name=F("disease__name"),
            term=F("ontology_term__term"),
            accession=F("ontology_term__accession")
        )
        .filter(
            disease__id__in=LocusGenotypeDisease.objects.filter(
                lgdpanel__panel__is_visible=1
            ).values('disease')
        )
    )

    for obj in disease_ontology_list:
        new_disease_name = re.sub(r".*\-related\s*", "", obj.disease_name).strip()
        clean_disease_name = clean_string(new_disease_name)
        term_without_type = clean_omim_disease(obj.term)
        clean_term = clean_string(term_without_type)

        # Get the synonym name from our internal list of synonyms
        synonyms_g2p_name = check_synonyms_disease(obj.term.lower())

        if synonyms_g2p_name and synonyms_g2p_name == new_disease_name.lower():
            continue

        # Calculate the string similarity
        score = SequenceMatcher(None, clean_disease_name.lower(), clean_term.lower()).ratio()

        if ((score < 0.3 and new_disease_name.lower() not in term_without_type
            and term_without_type not in new_disease_name.lower())):
            # Add the error message to the list
            # Do not add a hint as the messages are already long and self explanatory
            errors.append(
            Error(
                    f"Disease '{obj.disease_name}' associated with suspicious ontology disease '{obj.term}' ({obj.accession})",
                    id="gene2phenotype_app.E013",
                )
            )

    return errors
