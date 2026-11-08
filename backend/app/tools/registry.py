"""Validation of tool calls coming from the model and tool results coming from Android.

Server-side tools (``SERVER_TOOLS``) are executed by the backend itself and never
reach the device. None are registered for the MVP; this is the extension point for
a future retrieval/RAG tool (see app/retrieval).
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from pydantic import ValidationError

from app.tools.definitions import ARG_MODELS, DEVICE_TOOLS, TOOL_SCHEMAS
from app.tools.results import RESULT_MODELS, narrow, present

ServerToolHandler = Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]
SERVER_TOOLS: dict[str, tuple[dict[str, Any], ServerToolHandler]] = {}


@dataclass(frozen=True)
class CheckedCall:
    call_id: str
    name: str
    arguments: dict[str, Any] | None  # normalised arguments when valid
    error: str | None = None  # why the call was rejected (sent back to the model)

    @property
    def ok(self) -> bool:
        return self.error is None


def tool_schemas() -> list[dict[str, Any]]:
    return TOOL_SCHEMAS + [schema for schema, _ in SERVER_TOOLS.values()]


def _short(err: ValidationError) -> str:
    parts = []
    for e in err.errors()[:4]:
        loc = ".".join(str(x) for x in e.get("loc", ())) or "arguments"
        parts.append(f"{loc}: {e.get('msg')}")
    return "; ".join(parts)


def check_call(call_id: str, name: str, raw_arguments: str | dict[str, Any] | None) -> CheckedCall:
    if name not in DEVICE_TOOLS and name not in SERVER_TOOLS:
        return CheckedCall(call_id, name, None, f"Unknown tool '{name}'. Use only the tools provided.")
    if isinstance(raw_arguments, dict):
        args: Any = raw_arguments
    else:
        text = (raw_arguments or "").strip() or "{}"
        try:
            args = json.loads(text)
        except json.JSONDecodeError:
            return CheckedCall(call_id, name, None, "Arguments are not valid JSON.")
    if not isinstance(args, dict):
        return CheckedCall(call_id, name, None, "Arguments must be a JSON object.")
    if name in SERVER_TOOLS:
        return CheckedCall(call_id, name, args)
    try:
        model = ARG_MODELS[name].model_validate(args)
    except ValidationError as e:
        return CheckedCall(call_id, name, None, f"Invalid arguments: {_short(e)}")
    return CheckedCall(call_id, name, model.model_dump(exclude_none=True))


class InvalidToolResult(ValueError):
    pass


def validate_result(name: str, output: Any, args: dict[str, Any] | None = None) -> tuple[Any, dict[str, Any]]:
    """Returns (validated model, model-facing dict). Raises InvalidToolResult."""
    model_cls = RESULT_MODELS[name]
    try:
        result = model_cls.model_validate(output)
    except ValidationError as e:
        raise InvalidToolResult(f"{name}: {_short(e)}") from e
    result = narrow(result, args or {})
    return result, present(name, result)
