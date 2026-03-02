#!/usr/bin/env python3

import re
from typing import Optional


def validate_mechanism_synopsis(mechanism: str, synopsis: str) -> bool:
    """
    Validate the mechanism synopsis according to the mechanism value.
    The synopsis (categorisation) is a more specific type of mechanism
    which means they have to match.


    Args:
        mechanism (str): molecular mechanism value
        synopsis (str): mechanism synopsis value

    Returns:
        bool: returns true if the mechanism and synopsis match
    """
    valid = True

    # undetermined and undetermined non-loss-of-function cannot have a synopsis
    if mechanism == "undetermined" or mechanism == "undetermined non-loss-of-function":
        valid = False
    # mechanism loss of function implies the synopsis is also LOF
    elif mechanism == "loss of function" and "LOF" not in synopsis:
        valid = False
    # mechanism dominant negative implies the synopsis is also DN
    elif mechanism == "dominant negative" and not re.search(
        r"dominant[-\s]+negative", synopsis
    ):
        valid = False
    # mechanism gain of function implies the synopsis is also GOF
    elif (
        mechanism == "gain of function"
        and "GOF" not in synopsis
        and "aggregation" not in synopsis
    ):
        valid = False

    return valid


def validate_confidence_publications(confidence: str, number_publications: int) -> bool:
    """
    Method to validate the number of publications for the confidence value.

    Args:
        confidence (str): confidence value
        number_publications (int): number of publications

    Returns:
        bool: returns true if the number of publications are enough for the confidence value
    """
    valid = True

    if (
        confidence == "definitive" or confidence == "strong"
    ) and number_publications < 2:
        valid = False

    return valid


def clean_summary_text(value: str) -> Optional[str]:
    """
    Normalise labels for summary output.
    Called by: build_lgd_record_summary() in LocusGenotypeDiseaseSerializer
    """
    if value is None:
        return None
    text = str(value).strip()
    text = text.replace("_", " ")
    text = re.sub(r"\s+", " ", text)
    return text


def join_summary_items(values: list[str]) -> str:
    """
    Join unique values to form a comma-separated string.
    Called by: build_lgd_record_summary() in LocusGenotypeDiseaseSerializer
    """
    unique_values = list(dict.fromkeys(v for v in values if v))
    return ", ".join(unique_values)


def join_with_and(values: list[str]) -> str:
    """
    Join values with commas and 'and' before the last value.
    Called by: build_lgd_record_summary() in LocusGenotypeDiseaseSerializer
    """
    unique_values = list(dict.fromkeys(v for v in values if v))
    if not unique_values:
        return ""
    if len(unique_values) == 1:
        return unique_values[0]
    if len(unique_values) == 2:
        return f"{unique_values[0]} and {unique_values[1]}"
    return f"{', '.join(unique_values[:-1])} and {unique_values[-1]}"


def article_for_phrase(value: str) -> str:
    """
    Choose a simple English article for the provided phrase.
    Called by: build_lgd_record_summary() in LocusGenotypeDiseaseSerializer
    """
    first_char = value.strip()[:1].lower() if value else ""
    return "an" if first_char in {"a", "e", "i", "o", "u"} else "a"


def plural_suffix(count: int) -> str:
    return "" if count == 1 else "s"


def cross_cutting_modifier_fragment(value: str) -> str:
    """
    Convert a cross cutting modifier value into a sentence fragment that follows 'This '.
    Called by: build_lgd_record_summary() in LocusGenotypeDiseaseSerializer
    """
    normalized = value.strip().lower()
    custom_fragments = {
        "displays anticipation": "displays anticipation",
        "imprinted region": "involves imprinting",
        "potential secondary finding": "is a potential secondary finding",
        "restricted mutation set": "involves a restricted mutation set",
        "typically de novo": "is typically de novo",
        "typically mosaic": "is typically mosaic",
        "typified by incomplete penetrance": "is typified by incomplete penetrance",
    }
    if normalized in custom_fragments:
        return custom_fragments[normalized]
    return f"has {article_for_phrase(value)} {value}"