"""文案与词条的归一化及原文位置映射。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NormalizedText:
    """归一化结果。

    text: 归一化后的字符串。
    sources: 与 text 等长，sources[i] 是归一化第 i 个字符
        覆盖的原文字符下标集合（frozenset，升序语义）。
    """

    text: str
    sources: tuple[frozenset[int], ...]


def normalize(text: str) -> NormalizedText:
    """按比较规则归一化文本，并记录每个归一化字符的原文来源。"""
    # 第 1-3 步：全角映射、casefold、删除隐藏字符，
    # 得到 (输出字符, 原文字符下标) 序列。
    pairs: list[tuple[str, int]] = []
    for index, char in enumerate(text):
        code = ord(char)
        if 0xFF01 <= code <= 0xFF5E:
            char = chr(code - 0xFEE0)
        elif code == 0x3000:
            char = " "
        if char in ("\u200b", "\ufeff"):
            continue
        for folded in char.casefold():
            pairs.append((folded, index))

    # 第 4 步：连续空白折叠为一个 ASCII 空格，来源取全部参与折叠的原字符。
    chars: list[str] = []
    sources: list[frozenset[int]] = []
    pending: list[int] = []
    for char, index in pairs:
        if char.isspace():
            pending.append(index)
            continue
        if pending:
            chars.append(" ")
            sources.append(frozenset(pending))
            pending = []
        chars.append(char)
        sources.append(frozenset((index,)))
    if pending:
        chars.append(" ")
        sources.append(frozenset(pending))

    return NormalizedText(text="".join(chars), sources=tuple(sources))
