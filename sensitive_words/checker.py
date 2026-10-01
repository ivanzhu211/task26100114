"""Batch checking of independent copy fields against a dictionary."""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass

from .dictionary import WHOLE_WORD, Dictionary, _PreparedRule
from .normalizer import NormalizedText, normalize


@dataclass(frozen=True)
class Hit:
    """One sensitive-word hit.

    ``start``/``end`` locate the highlight range in the *original* field
    text, counted in Unicode code points, 0-based, ``end`` exclusive.
    """

    rule_id: str
    field: str
    start: int
    end: int


class Checker:
    """Checks fields against a preloaded dictionary.

    The checker keeps no state between calls and never stores the checked
    copy, so results are unaffected by previous checks.
    """

    def __init__(self, dictionary: Dictionary) -> None:
        self._prepared = dictionary.prepared

    def check(self, fields: dict[str, str]) -> list[Hit]:
        """Check each field independently and return all hits.

        Hits are grouped by field in the order the fields were given and
        sorted by ``(start, end, rule_id)`` within a field.
        """
        hits: list[Hit] = []
        for field, text in fields.items():
            hits.extend(self._check_field(field, text))
        return hits

    def _check_field(self, field: str, text: str) -> list[Hit]:
        normalized = normalize(text)
        found: set[Hit] = set()
        for prepared in self._prepared:
            for hit in self._match(field, normalized, prepared):
                found.add(hit)
        return sorted(found, key=lambda hit: (hit.start, hit.end, hit.rule_id))

    def _match(
        self, field: str, normalized: NormalizedText, prepared: _PreparedRule
    ) -> list[Hit]:
        text = normalized.text
        needle = prepared.normalized_term
        whole_word = prepared.rule.mode == WHOLE_WORD
        hits: list[Hit] = []
        position = text.find(needle)
        while position != -1:
            end = position + len(needle)
            if not whole_word or _has_word_boundaries(text, position, end):
                hits.append(
                    Hit(
                        rule_id=prepared.rule.id,
                        field=field,
                        **_locate(normalized, position, end),
                    )
                )
            position = text.find(needle, position + 1)
        return hits


def _locate(normalized: NormalizedText, start: int, end: int) -> dict[str, int]:
    """Map a normalized range to the shortest covering original range."""
    owners: set[int] = set()
    for entry in normalized.index_map[start:end]:
        owners.update(entry)
    return {"start": min(owners), "end": max(owners) + 1}


def _has_word_boundaries(text: str, start: int, end: int) -> bool:
    left_ok = start == 0 or not _is_word_char(text[start - 1])
    right_ok = end == len(text) or not _is_word_char(text[end])
    return left_ok and right_ok


def _is_word_char(char: str) -> bool:
    category = unicodedata.category(char)
    return category[0] in ("L", "M", "N") or category == "Pc"
