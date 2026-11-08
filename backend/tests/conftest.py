from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.config import Settings
from app.llm.parsing import LLMReply, ToolCall
from app.main import create_app

FIXTURES = Path(__file__).resolve().parents[2] / "contracts" / "fixtures" / "device_tool_outputs.json"


@pytest.fixture(scope="session")
def fx() -> dict[str, Any]:
    return json.loads(FIXTURES.read_text(encoding="utf-8"))


Step = LLMReply | Callable[[list[dict[str, Any]], list[dict[str, Any]] | None, str], LLMReply]


class FakeLLM:
    """Scripted stand-in for Ornith. Records every request for assertions."""

    def __init__(self, script: list[Step]) -> None:
        self.script = list(script)
        self.calls: list[dict[str, Any]] = []

    async def complete(self, messages, tools, tool_choice="auto"):  # type: ignore[no-untyped-def]
        self.calls.append({"messages": [dict(m) for m in messages], "tools": tools, "tool_choice": tool_choice})
        if not self.script:
            raise AssertionError("FakeLLM script exhausted")
        step = self.script.pop(0)
        return step(messages, tools, tool_choice) if callable(step) else step


def call(name: str, args: dict[str, Any], cid: str | None = None) -> ToolCall:
    return ToolCall(id=cid or f"call_{name}", name=name, arguments=json.dumps(args))


def tools(*calls: ToolCall, content: str = "") -> LLMReply:
    return LLMReply(content=content, tool_calls=list(calls), finish_reason="tool_calls")


def say(text: str) -> LLMReply:
    return LLMReply(content=text, finish_reason="stop")


def make_settings(**overrides: Any) -> Settings:
    base = dict(uth_key=SecretStr("test-key-not-real-0000"), turn_ttl_s=300, max_tool_rounds=3)
    base.update(overrides)
    return Settings(**base)


@pytest.fixture
def make_client() -> Callable[..., tuple[TestClient, FakeLLM]]:
    def _make(script: list[Step], **settings: Any) -> tuple[TestClient, FakeLLM]:
        llm = FakeLLM(script)
        app = create_app(settings=make_settings(**settings), llm=llm)
        return TestClient(app), llm
    return _make


def tool_messages(llm_call: dict[str, Any]) -> list[dict[str, Any]]:
    return [m for m in llm_call["messages"] if m["role"] == "tool"]


def answer(client: TestClient, resp: dict[str, Any], outputs: dict[str, Any]) -> dict[str, Any]:
    """Act as Android: answer every requested call by tool name (or call_id) from `outputs`."""
    assert resp["status"] == "tool_calls", resp
    results = []
    for c in resp["tool_calls"]:
        out = outputs.get(c["call_id"], outputs.get(c["name"]))
        if isinstance(out, dict) and out.get("__fail__"):
            results.append({"call_id": c["call_id"], "ok": False, "error": out["__fail__"]})
        else:
            results.append({"call_id": c["call_id"], "ok": True, "output": out})
    r = client.post(f"/v1/chat/{resp['turn_id']}/tool-results", json={"results": results})
    assert r.status_code == 200, r.text
    return r.json()
