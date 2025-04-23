from django.core.checks import Error
from django.db.models import F
from difflib import SequenceMatcher
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import re

from gene2phenotype_app.models import DiseaseOntologyTerm
from gene2phenotype_app.utils import clean_string, clean_omim_disease


def check_cross_references():
    errors = []

    disease_ontology_list = (
        DiseaseOntologyTerm.objects.all()
        .select_related("disease", "ontology_term")
        .annotate(disease_name=F("disease__name"), term=F("ontology_term__term"), accession=F("ontology_term__accession"))
    )

    model = SentenceTransformer('pritamdeka/BioBERT-mnli-snli-scinli-scitail-mednli-stsb')

    for obj in disease_ontology_list:
        new_disease_name = re.sub(".*\-related\s*", "", obj.disease_name).strip()
        clean_disease_name = clean_string(new_disease_name)
        term_without_type = clean_omim_disease(obj.term)
        clean_term = clean_string(term_without_type)

        # Calculate the string similarity
        score = SequenceMatcher(None, clean_disease_name.lower(), clean_term.lower()).ratio()

        embeddings = model.encode([clean_disease_name.lower(), clean_term.lower()])
        similarity = cosine_similarity([embeddings[0]], [embeddings[1]])

        if ((score < 0.3 and new_disease_name.lower() not in term_without_type
            and term_without_type not in new_disease_name.lower()) and similarity[0][0] < 0.3):
            errors.append(
            Error(
                    f"Disease '{obj.disease_name}' associated with suspicious ontology disease '{obj.term}' ({obj.accession})",
                    id="gene2phenotype_app.E013",
                )
            )

    return errors
