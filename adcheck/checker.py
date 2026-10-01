"""敏感词检查器：批量检查独立字段并返回命中。"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Union

from .normalize import normalize
from .rules import MatchMode, Rule, load_dictionary


@dataclass(frozen=True)
class Hit:
    """一次命中：关联规则与字段，定位原文范围（码点计，终点不含）。"""

    rule_id: str
    field: str
    start: int
    end: int


class Checker:
    """预加载词典、可复用的检查器。检查状态仅保存在单次调用内。"""

    def __init__(self, rules: list[Rule]) -> None:
        self._entries = [(rule, normalize(rule.term).text) for rule in rules]

    @classmethod
    def from_json(cls, path: Union[str, Path]) -> "Checker":
        """从本地 JSON 词典文件构造检查器。"""
        return cls(load_dictionary(path))

    def check(self, fields: Mapping[str, str]) -> list[Hit]:
        """批量检查若干独立字段，返回全部命中。"""
        hits: list[Hit] = []
        reported: set[tuple[str, str, int, int]] = set()
        for field, text in fields.items():
            normalized = normalize(text)
            for rule, term in self._entries:
                for start, end in _find_occurrences(normalized.text, term, rule.mode):
                    covered = set().union(*normalized.sources[start:end])
                    hit = Hit(
                        rule_id=rule.rule_id,
                        field=field,
                        start=min(covered),
                        end=max(covered) + 1,
                    )
                    key = (hit.rule_id, hit.field, hit.start, hit.end)
                    if key not in reported:
                        reported.add(key)
                        hits.append(hit)
        return hits


def _find_occurrences(
    text: str, term: str, mode: MatchMode
) -> list[tuple[int, int]]:
    """在归一化文本中查找词条的全部出现（含重叠），返回 [start, end) 列表。"""
    occurrences: list[tuple[int, int]] = []
    position = text.find(term)
    while position != -1:
        end = position + len(term)
        if mode is MatchMode.SUBSTRING or _is_word_match(text, position, end):
            occurrences.append((position, end))
        position = text.find(term, position + 1)
    return occurrences


def _is_word_match(text: str, start: int, end: int) -> bool:
    """整词边界：两端相邻字符均不属于 L、M、N、Pc，字段边缘视为有效边界。"""
    if start > 0 and _is_word_char(text[start - 1]):
        return False
    if end < len(text) and _is_word_char(text[end]):
        return False
    return True


def _is_word_char(char: str) -> bool:
    category = unicodedata.category(char)
    return category[0] in ("L", "M", "N") or category == "Pc"
