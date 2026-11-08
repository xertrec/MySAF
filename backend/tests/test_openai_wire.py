"""OrnithClient against a simulated OpenAI-compatible gateway (HTTP level).

Verifies the real SDK path without network: URL, auth header, request body,
structured tool calls, and the compatibility fallbacks.
"""
from __future__ import annotations

import asyncio
import json

import httpx
import pytest

from app.llm.client import OrnithClient
from app.tools.registry import tool_schemas
from tests.conftest import make_settings

KEY = "test-key-not-real-0000"


def _completion(message: dict, finish="stop") -> dict:
    return {"id": "x", "object": "chat.completion", "created": 0, "model": "ornith",
            "choices": [{"index": 0, "message": {"role": "assistant", **message}, "finish_reason": finish}]}


def _client(handler, **settings) -> tuple[OrnithClient, list[httpx.Request]]:
    seen: list[httpx.Request] = []

    def wrapped(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return handler(request, len(seen))

    http = httpx.AsyncClient(transport=httpx.MockTransport(wrapped))
    return OrnithClient(make_settings(**settings), http_client=http), seen


def _run(c, msgs, tools=None):
    return asyncio.run(c.complete(msgs, tools))


def test_request_shape_and_structured_tool_calls():
    def h(req, n):
        return httpx.Response(200, json=_completion({"content": None, "tool_calls": [
            {"id": "call_1", "type": "function", "function": {"name": "get_opening_hours", "arguments": '{"weekdays":["ds"]}'}},
            {"id": "call_2", "type": "function", "function": {"name": "list_activities", "arguments": ""}},
        ]}, "tool_calls"))
    c, seen = _client(h)
    r = _run(c, [{"role": "user", "content": "hola"}], tool_schemas())
    req = seen[0]
    assert str(req.url) == "https://dcc-llm-gw.uab.cat/uabthehack/v1/chat/completions"
    assert req.headers["authorization"] == f"Bearer {KEY}"
    body = json.loads(req.content)
    assert body["model"] == "ornith" and body["tool_choice"] == "auto" and body["parallel_tool_calls"] is True
    assert len(body["tools"]) == 7
    assert [(t.id, t.name, t.arguments) for t in r.tool_calls] == [
        ("call_1", "get_opening_hours", '{"weekdays":["ds"]}'), ("call_2", "list_activities", "{}")]


def test_parallel_tool_calls_rejected_is_retried_without_it():
    def h(req, n):
        if "parallel_tool_calls" in json.loads(req.content):
            return httpx.Response(400, json={"error": {"message": "Unsupported parameter: parallel_tool_calls"}})
        return httpx.Response(200, json=_completion({"content": "ok"}))
    c, seen = _client(h)
    assert _run(c, [{"role": "user", "content": "x"}], tool_schemas()).content == "ok"
    assert _run(c, [{"role": "user", "content": "x"}], tool_schemas()).content == "ok"
    assert len(seen) == 3  # rejected once, then remembered


def test_text_tool_calls_and_reasoning_are_normalised():
    def h(req, n):
        return httpx.Response(200, json=_completion({"content":
            '<think>I should call a tool</think><tool_call>{"name": "get_facility_info", '
            '"arguments": {"activity_id": "tennis"}}</tool_call>'}))
    c, _ = _client(h)
    r = _run(c, [{"role": "user", "content": "x"}], tool_schemas())
    assert r.parsed_from_text and r.tool_calls[0].name == "get_facility_info"
    assert json.loads(r.tool_calls[0].arguments) == {"activity_id": "tennis"} and r.content == ""


def test_missing_tool_call_id_gets_one():
    def h(req, n):
        return httpx.Response(200, json=_completion({"content": "", "tool_calls": [
            {"id": "", "type": "function", "function": {"name": "list_activities", "arguments": "{}"}}]}))
    c, _ = _client(h)
    assert _run(c, [{"role": "user", "content": "x"}], tool_schemas()).tool_calls[0].id.startswith("call_")


@pytest.mark.parametrize("status,code", [(401, "LLM_AUTH"), (404, "LLM_UNAVAILABLE"), (429, "RATE_LIMITED"),
                                         (500, "LLM_UNAVAILABLE")])
def test_http_errors_are_mapped(status, code):
    c, _ = _client(lambda req, n: httpx.Response(status, json={"error": {"message": "nope"}}), llm_max_retries=0)
    from app.errors import SafiaError
    with pytest.raises(SafiaError) as e:
        _run(c, [{"role": "user", "content": "x"}])
    assert e.value.code == code and KEY not in e.value.message


def test_tool_choice_rejected_is_dropped():
    def h(req, n):
        if "tool_choice" in json.loads(req.content):
            return httpx.Response(400, json={"error": {"message": "tool_choice is not supported"}})
        return httpx.Response(200, json=_completion({"content": "ok"}))
    c, seen = _client(h)
    assert _run(c, [{"role": "user", "content": "x"}], tool_schemas()).content == "ok"
    assert "tool_choice" not in json.loads(seen[-1].content)
