"""Normalization shared by dictionary terms and checked copy.

The comparison pipeline, applied in order:

1. Map U+FF01..U+FF5E to the corresponding ASCII character and U+3000 to
   a space.
2. Apply Unicode casefold.
3. Delete U+200B and U+FEFF.
4. Collapse every run of whitespace (per ``str.isspace``) into one ASCII
   space.  No stripping of leading/trailing whitespace and no other
   equivalence transformations.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NormalizedText:
    """Normalized text plus a per-position map back to original indices.

    ``index_map[i]`` is the set of original code-point indices that
    contributed to normalized position ``i``.  A collapsed whitespace run
    maps its single normalized space to every original whitespace
    character that participated in the fold.
    """

    text: str
    index_map: tuple[frozenset[int], ...]


def normalize(text: str) -> NormalizedText:
    """Normalize ``text`` and keep the mapping to original indices."""
    chars: list[str] = []
    owners: list[int] = []
    for index, char in enumerate(text):
        code = ord(char)
        if 0xFF01 <= code <= 0xFF5E:
            char = chr(code - 0xFEE0)
        elif code == 0x3000:
            char = " "
        for folded in char.casefold():
            if folded in ("\u200b", "\ufeff"):
                continue
            chars.append(folded)
            owners.append(index)

    normalized: list[str] = []
    index_map: list[set[int]] = []
    for char, owner in zip(chars, owners):
        if char.isspace():
            if normalized and normalized[-1] == " ":
                index_map[-1].add(owner)
            else:
                normalized.append(" ")
                index_map.append({owner})
        else:
            normalized.append(char)
            index_map.append({owner})

    return NormalizedText(
        text="".join(normalized),
        index_map=tuple(frozenset(entry) for entry in index_map),
    )


def normalize_term(term: str) -> str:
    """Normalize a dictionary term; only the comparison string is kept."""
    return normalize(term).text
