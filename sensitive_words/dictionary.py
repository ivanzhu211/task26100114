"""Dictionary of sensitive-word rules, loaded from a local JSON file."""

from __future__ import annotations

import json
from dataclasses import dataclass

from .normalizer import normalize_term

SUBSTRING = "substring"
WHOLE_WORD = "whole_word"
MODES = (SUBSTRING, WHOLE_WORD)


@dataclass(frozen=True)
class Rule:
    """One sensitive-word rule.

    ``id`` is unique within a dictionary, ``term`` is the entry text and
    ``mode`` is either ``SUBSTRING`` or ``WHOLE_WORD``.
    """

    id: str
    term: str
    mode: str


@dataclass(frozen=True)
class _PreparedRule:
    """A rule with its normalized term precomputed for reuse."""

    rule: Rule
    normalized_term: str


class Dictionary:
    """An immutable, reusable collection of prepared rules."""

    def __init__(self, rules: list[Rule]) -> None:
        seen: set[str] = set()
        prepared: list[_PreparedRule] = []
        for rule in rules:
            if rule.id in seen:
                raise ValueError(f"duplicate rule id: {rule.id!r}")
            seen.add(rule.id)
            if rule.mode not in MODES:
                raise ValueError(
                    f"rule {rule.id!r}: unknown mode {rule.mode!r}, "
                    f"expected one of {MODES}"
                )
            normalized = normalize_term(rule.term)
            if not normalized:
                raise ValueError(f"rule {rule.id!r}: term normalizes to empty")
            prepared.append(_PreparedRule(rule=rule, normalized_term=normalized))
        self._prepared = tuple(prepared)

    @classmethod
    def load(cls, path: str) -> "Dictionary":
        """Load a dictionary from a JSON file.

        Expected format::

            {"rules": [{"id": "r1", "term": "as", "mode": "substring"}]}
        """
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        rules = [
            Rule(id=entry["id"], term=entry["term"], mode=entry["mode"])
            for entry in data["rules"]
        ]
        return cls(rules)

    @property
    def rules(self) -> tuple[Rule, ...]:
        return tuple(item.rule for item in self._prepared)

    @property
    def prepared(self) -> tuple[_PreparedRule, ...]:
        return self._prepared
