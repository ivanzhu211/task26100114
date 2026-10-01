"""广告文案敏感词检查库。"""

from .checker import Checker, Hit
from .rules import MatchMode, Rule, load_dictionary

__all__ = [
    "Checker",
    "Hit",
    "MatchMode",
    "Rule",
    "load_dictionary",
]
