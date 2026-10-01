"""词典规则定义与装载。"""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Union


class MatchMode(Enum):
    """匹配模式：子串或整词。"""

    SUBSTRING = "substring"
    WORD = "word"


@dataclass(frozen=True)
class Rule:
    """一条敏感词规则。"""

    rule_id: str
    term: str
    mode: MatchMode


def load_dictionary(path: Union[str, Path]) -> list[Rule]:
    """从本地 JSON 文件装载词典。"""
    with open(path, "r", encoding="utf-8") as file:
        entries = json.load(file)
    rules = [
        Rule(
            rule_id=str(entry["id"]),
            term=entry["term"],
            mode=MatchMode(entry["mode"]),
        )
        for entry in entries
    ]
    seen: set[str] = set()
    for rule in rules:
        if rule.rule_id in seen:
            raise ValueError(f"词典中存在重复编号: {rule.rule_id}")
        seen.add(rule.rule_id)
    return rules
