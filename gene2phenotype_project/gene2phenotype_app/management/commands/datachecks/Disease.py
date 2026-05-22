from django.core.checks import Error
from django.db.models import F
from difflib import SequenceMatcher
from collections import defaultdict
import re

from gene2phenotype_app.models import (
    DiseaseOntologyTerm,
    LocusGenotypeDisease,
    DiseaseSynonym,
)

from gene2phenotype_app.utils import (
    clean_string,
    clean_omim_disease,
    check_synonyms_disease,
)


def check_cross_references():
    """Check whether linked ontology terms look compatible with the G2P disease."""
    errors = []

    # Select disease with ontology terms that are linked to visible panels
    disease_ontology_list = (
        DiseaseOntologyTerm.objects.select_related("disease", "ontology_term")
        .annotate(
            disease_name=F("disease__name"),
            term=F("ontology_term__term"),
            accession=F("ontology_term__accession"),
        )
        .filter(
            disease__id__in=LocusGenotypeDisease.objects.filter(
                lgdpanel__panel__is_visible=1, is_deleted=0
            ).values("disease")
        )
        .distinct()
    )

    disease_ontology_list = list(disease_ontology_list)
    disease_ids = {obj.disease_id for obj in disease_ontology_list}

    disease_synonyms_map = defaultdict(set)
    disease_synonyms = DiseaseSynonym.objects.filter(
        disease_id__in=disease_ids
    ).values_list("disease_id", "synonym")
    for disease_id, synonym in disease_synonyms:
        disease_synonyms_map[disease_id].add(clean_string(synonym))

    for obj in disease_ontology_list:
        new_disease_name = re.sub(r".*\-related\s*", "", obj.disease_name).strip()
        clean_disease_name = clean_string(new_disease_name)
        term_without_type = clean_omim_disease(obj.term)
        clean_term = clean_string(term_without_type)

        known_names = {clean_disease_name}
        known_names.update(disease_synonyms_map[obj.disease_id])

        synonyms_g2p_name = check_synonyms_disease(obj.term.lower())
        if synonyms_g2p_name:
            known_names.add(clean_string(synonyms_g2p_name))

        if clean_term in known_names:
            continue

        # Check for deafness
        if "deafness" in new_disease_name and "hearing loss" in term_without_type:
            continue

        # Calculate the string similarity
        score = SequenceMatcher(
            None, clean_disease_name.lower(), clean_term.lower()
        ).ratio()

        if (
            score < 0.2
            and new_disease_name.lower() not in term_without_type
            and term_without_type not in new_disease_name.lower()
        ):
            # Add the error message to the list
            # Do not add a hint as the messages are already long and self explanatory
            errors.append(
                Error(
                    f"Disease '{obj.disease_name}' associated with suspicious ontology disease '{obj.term}' ({obj.accession})",
                    id="gene2phenotype_app.E401",
                )
            )

    return errors


def check_disease_name():
    """Check that visible record disease names start with the linked locus name."""
    errors = []

    lgd_records = (
        LocusGenotypeDisease.objects.select_related("disease")
        .annotate(
            g2p_id=F("stable_id__stable_id"),
            disease_name=F("disease__name"),
            locus_name=F("locus__name"),
        )
        .filter(lgdpanel__panel__is_visible=1, is_deleted=0)
        .distinct()
    )

    for obj in lgd_records:
        if not (
            obj.disease_name.startswith(f"{obj.locus_name}-")
            or obj.disease_name.startswith(f"{obj.locus_name} ")
        ):
            # Do not add a hint as the messages are already long and self explanatory
            errors.append(
                Error(
                    f"For record {obj.g2p_id} disease '{obj.disease_name}' is missing the locus name '{obj.locus_name}'",
                    id="gene2phenotype_app.E402",
                )
            )

    return errors


def check_mondo_single_gene_link():
    """Check that each MONDO ID is linked to only one visible active locus."""
    errors = []
    mondo_gene_map = defaultdict(set)
    mondo_disease_map = defaultdict(set)

    lgd_records = list(
        LocusGenotypeDisease.objects.annotate(
            disease_name=F("disease__name"), locus_name=F("locus__name")
        )
        .filter(
            lgdpanel__panel__is_visible=1,
            lgdpanel__is_deleted=0,
            is_deleted=0,
        )
        .values("disease_id", "disease_name", "locus_name")
        .distinct()
    )

    disease_gene_map = defaultdict(set)
    disease_name_map = {}
    for obj in lgd_records:
        disease_gene_map[obj["disease_id"]].add(obj["locus_name"])
        disease_name_map[obj["disease_id"]] = obj["disease_name"]

    mondo_links = (
        DiseaseOntologyTerm.objects.annotate(
            mondo_id=F("ontology_term__accession"),
        )
        .filter(
            disease_id__in=disease_gene_map.keys(),
            ontology_term__accession__startswith="MONDO:",
        )
        .values("disease_id", "mondo_id")
        .distinct()
    )

    for obj in mondo_links:
        disease_id = obj["disease_id"]
        mondo_id = obj["mondo_id"]
        mondo_gene_map[mondo_id].update(disease_gene_map[disease_id])
        mondo_disease_map[mondo_id].add(disease_name_map[disease_id])

    for mondo_id, genes in mondo_gene_map.items():
        if len(genes) > 1:
            errors.append(
                Error(
                    f"'{mondo_id}' is linked to multiple genes: {', '.join(sorted(genes))}. Diseases: {', '.join(sorted(mondo_disease_map[mondo_id]))}",
                    id="gene2phenotype_app.E403",
                )
            )

    return errors
