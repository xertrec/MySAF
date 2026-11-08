"""Numeric grounding check: every number in SAFIA's reply must be traceable to
tool results, the user's own messages or the fixed facts in the system prompt.

It is a safety net, not a parser: it catches invented capacities, percentages
and hours, which are the failure mode that matters most here.
"""
from __future__ import annotations

import re
from typing import Any, Iterable

_TIME = re.compile(r"\b(\d{1,2})[:.h](\d{2})\b")
_NUM = re.compile(r"(?<![\w])(\d+(?:[.,]\d+)?)")

# Numbers that appear in the fixed prompt/catalogue, plus trivially safe ones.
BASE_ALLOWED: frozenset[float] = frozenset({0, 1, 2, 7, 10, 11, 15, 16, 25, 30, 31, 100, 2026})
# 10 / 15: fitness shift-change hours (and 10 = P2 threshold in points); 16 / 25: pool
# lengths; 1, 30, 31, 2026: dataset dates; 7 / 11: "futbol 7/11"; 100: "100 %".


def _numbers_in_text(text: str) -> list[float]:
    out: list[float] = []
    for m in _TIME.finditer(text):
        out.append(float(m.group(1)))
        if m.group(2) not in ("00", "30"):
            out.append(float(m.group(2)))
    text = _TIME.sub(" ", text)
    for m in _NUM.finditer(text):
        out.append(float(m.group(1).replace(",", ".")))
    return out


def _walk(value: Any) -> Iterable[float]:
    if isinstance(value, bool) or value is None:
        return
    if isinstance(value, (int, float)):
        yield float(value)
    elif isinstance(value, str):
        yield from _numbers_in_text(value)
    elif isinstance(value, dict):
        for v in value.values():
            yield from _walk(v)
    elif isinstance(value, (list, tuple)):
        for v in value:
            yield from _walk(v)


def allowed_numbers(tool_outputs: Iterable[Any], user_texts: Iterable[str]) -> set[float]:
    allowed: set[float] = set(BASE_ALLOWED)
    for out in tool_outputs:
        allowed.update(_walk(out))
    for t in user_texts:
        allowed.update(_numbers_in_text(t))
    extra: set[float] = set()
    for n in allowed:
        if 13 <= n <= 23 and n == int(n):
            extra.add(n - 12)  # "a les 6 de la tarda" for 18:00
        if 0 < n < 10 and n != int(n):
            extra.add(round(n))
    return allowed | extra


def ungrounded_numbers(reply: str, allowed: set[float]) -> list[str]:
    bad: list[str] = []
    for n in _numbers_in_text(reply):
        if not any(abs(n - a) <= 0.5 for a in allowed):
            label = str(int(n)) if n == int(n) else str(n)
            if label not in bad:
                bad.append(label)
    return bad
