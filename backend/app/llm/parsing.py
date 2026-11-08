"""Normalising model output from an OpenAI-compatible gateway.

OpenAI compatibility does not guarantee identical tool-calling behaviour. Some
open-weight models served behind such gateways:
- emit reasoning in <think>...</think> blocks inside ``content``;
- write tool calls as text (``<tool_call>{...}</tool_call>`` or a JSON object)
  instead of structured ``tool_calls``;
- return ``arguments`` as an object instead of a JSON string.
These helpers handle all three.
"""
from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass, field
from typing import Any

_THINK = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)
_UNCLOSED_THINK = re.compile(r"^.*?</think>", re.DOTALL | re.IGNORECASE)
_TOOL_TAG = re.compile(r"<tool_call>\s*(\{.*?\})\s*</tool_call>", re.DOTALL)
_FENCED = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: str  # JSON text, as in the OpenAI protocol


@dataclass
class LLMReply:
    content: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    finish_reason: str | None = None
    parsed_from_text: bool = False


def strip_reasoning(text: str | None) -> str:
    if not text:
        return ""
    text = _THINK.sub("", text)
    if "</think>" in text.lower():
        text = _UNCLOSED_THINK.sub("", text)
    return text.strip()


def arguments_to_text(arguments: Any) -> str:
    if arguments is None:
        return "{}"
    if isinstance(arguments, str):
        return arguments.strip() or "{}"
    return json.dumps(arguments, ensure_ascii=False)


def new_call_id() -> str:
    return "call_" + uuid.uuid4().hex[:24]


def _as_call(obj: Any, known_tools: set[str]) -> ToolCall | None:
    if not isinstance(obj, dict):
        return None
    if "function" in obj and isinstance(obj["function"], dict):
        obj = obj["function"]
    name = obj.get("name")
    if not isinstance(name, str) or name not in known_tools:
        return None
    args = obj.get("arguments", obj.get("parameters", {}))
    return ToolCall(new_call_id(), name, arguments_to_text(args))


def extract_text_tool_calls(content: str, known_tools: set[str]) -> tuple[list[ToolCall], str]:
    """Find tool calls written as text. Returns (calls, remaining text)."""
    calls: list[ToolCall] = []
    for m in _TOOL_TAG.finditer(content):
        try:
            c = _as_call(json.loads(m.group(1)), known_tools)
        except json.JSONDecodeError:
            c = None
        if c:
            calls.append(c)
    if calls:
        return calls, _TOOL_TAG.sub("", content).strip()
    candidates = [m.group(1) for m in _FENCED.finditer(content)]
    stripped = content.strip()
    if stripped.startswith("{") and stripped.endswith("}"):
        candidates.append(stripped)
    for cand in candidates:
        try:
            obj = json.loads(cand)
        except json.JSONDecodeError:
            continue
        items = obj if isinstance(obj, list) else [obj]
        for it in items:
            c = _as_call(it, known_tools)
            if c:
                calls.append(c)
        if calls:
            return calls, ""
    return [], content
