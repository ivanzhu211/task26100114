"""Sensitive-word checking for ad copy.

Typical usage::

    from sensitive_words import Checker, Dictionary

    dictionary = Dictionary.load("dictionary.json")
    checker = Checker(dictionary)
    hits = checker.check({"title": title, "body": body, "cta": cta})
"""

from .checker import Checker, Hit
from .dictionary import SUBSTRING, WHOLE_WORD, Dictionary, Rule
from .normalizer import NormalizedText, normalize, normalize_term

__all__ = [
    "SUBSTRING",
    "WHOLE_WORD",
    "Checker",
    "Dictionary",
    "Hit",
    "NormalizedText",
    "Rule",
    "normalize",
    "normalize_term",
]
