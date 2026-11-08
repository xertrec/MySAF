"""Live tests against the real UAB Ornith gateway.

Run from backend/:   python -m pytest -m live -v
They need backend/.env with UTH_KEY and network access to dcc-llm-gw.uab.cat.
Assertions are deliberately tolerant about wording; they check behaviour.
"""
from __future__ import annotations

import asyncio
import json

import pytest
from fastapi.testclient import TestClient

from app.config import load_settings
from app.language import detect_language
from app.llm.client import OrnithClient
from app.main import create_app
from app.tools.registry import check_call, tool_schemas
from tests.conftest import answer

pytestmark = pytest.mark.live

SETTINGS = load_settings()
if not SETTINGS.has_api_key:
    pytest.skip("UTH_KEY not configured in backend/.env", allow_module_level=True)


def _run(coro):
    return asyncio.run(coro)


@pytest.fixture(scope="module")
def llm() -> OrnithClient:
    return OrnithClient(SETTINGS)


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app(settings=SETTINGS))


def test_1_basic_text_generation(llm):
    r = _run(llm.complete([{"role": "user", "content": "Reply with the single word: pong"}], tools=None))
    assert r.content and "pong" in r.content.lower()


def test_2_3_tool_call_is_structured_and_parsable(llm):
    r = _run(llm.complete([{"role": "system", "content": "Use the tools to answer questions about the SAF."},
                           {"role": "user", "content": "A quina hora tanca el SAF els dissabtes?"}],
                          tools=tool_schemas()))
    assert r.tool_calls, f"no tool call; content={r.content[:200]!r}"
    c = r.tool_calls[0]
    checked = check_call(c.id, c.name, c.arguments)
    assert checked.ok, checked.error
    assert c.name == "get_opening_hours"
    print(f"\n  structured={not r.parsed_from_text} id={c.id} args={c.arguments}")


def _complete_exchange(client, fx, question):
    r = client.post("/v1/chat", json={"message": question})
    assert r.status_code == 200, r.text
    body = r.json()
    rounds = 0
    while body["status"] == "tool_calls":
        rounds += 1
        assert rounds <= 3
        outputs = {}
        for c in body["tool_calls"]:
            key = c["name"] if c["name"] in fx else next((k for k in fx if k.startswith(c["name"])), None)
            assert key, f"no fixture for {c['name']}"
            outputs[c["call_id"]] = fx[key]
        body = answer(client, body, outputs)
    return body, rounds


def test_4_5_full_exchange_catalan(client, fx):
    final, rounds = _complete_exchange(client, fx, "A quina hora tanca el SAF els dissabtes?")
    print(f"\n  CA ({rounds} round): {final['reply']}")
    assert rounds >= 1 and "20" in final["reply"]
    assert detect_language(final["reply"]) == "ca"


def test_6_spanish_answer(client, fx):
    final, _ = _complete_exchange(client, fx, "¿A qué hora cierra el SAF los domingos?")
    print(f"\n  ES: {final['reply']}")
    assert "14" in final["reply"] and detect_language(final["reply"]) == "es"


def test_7_recommendation_goes_through_p2(client, fx):
    r = client.post("/v1/chat", json={"message": "Vull jugar a tennis dilluns a les 18 però sol estar ple. "
                                                 "Quina alternativa em recomanes?"}).json()
    assert r["status"] == "tool_calls"
    assert any(c["name"] == "recommend_alternatives" for c in r["tool_calls"]), r["tool_calls"]
    final, _ = _complete_exchange_from(client, fx, r)
    print(f"\n  P2: {final['reply']}")
    assert final["recommendation"] is not None


def _complete_exchange_from(client, fx, body):
    rounds = 0
    while body["status"] == "tool_calls":
        rounds += 1
        outputs = {c["call_id"]: fx[next(k for k in fx if k.startswith(c["name"]))] for c in body["tool_calls"]}
        body = answer(client, body, outputs)
    return body, rounds


def test_8_follow_up_keeps_facility(client, fx):
    first, _ = _complete_exchange(client, fx, "Quan hi ha menys gent a la sala fitness els dilluns?")
    r = client.post("/v1/chat", json={"message": "I els caps de setmana?",
                                      "conversation_id": first["conversation_id"]}).json()
    assert r["status"] == "tool_calls"
    args = r["tool_calls"][0]["arguments"]
    print(f"\n  follow-up call: {json.dumps(r['tool_calls'])}")
    assert args.get("activity_id") == "sala_fitness" and set(args.get("weekdays", [])) >= {"ds", "dg"}


def test_9_real_time_is_declined_as_historical(client, fx):
    final, _ = _complete_exchange(client, fx, "Hi ha molta gent ara mateix a la piscina?")
    print(f"\n  now: {final['reply']}")
    assert "historical_only" in final["limitations"] or "històric" in final["reply"].lower()
