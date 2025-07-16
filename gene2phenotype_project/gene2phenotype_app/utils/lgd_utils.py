#!/usr/bin/env python3

import re


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
