"""Tool-call protocol: ids, ordering, rejection, errors, turn lifecycle."""
from __future__ import annotations

import json

import openai
import pytest

from app import errors
from tests.conftest import answer, call, say, tool_messages, tools


def _post(client, msg, **kw):
    return client.post("/v1/chat", json={"message": msg, **kw})


def test_full_exchange_preserves_ids_and_order(make_client, fx):
    """User question -> 2 parallel tool calls -> Android results (reversed order) -> final answer."""
    client, llm = make_client([
        tools(call("get_opening_hours", {"weekdays": ["dg"]}, "id-A"),
              call("get_facility_info", {"activity_id": "piscina_25m"}, "id-B")),
        say("Diumenge el SAF obre de 09:00 a 14:00 i la piscina té un aforament aproximat de 40 persones."),
    ])
    r = _post(client, "Diumenge puc anar a la piscina? Quanta gent hi cap?").json()
    assert [c["call_id"] for c in r["tool_calls"]] == ["id-A", "id-B"]
    results = [{"call_id": "id-B", "ok": True, "output": fx["get_facility_info__piscina_25m"]},
               {"call_id": "id-A", "ok": True, "output": fx["get_opening_hours"]}]
    final = client.post(f"/v1/chat/{r['turn_id']}/tool-results", json={"results": results}).json()
    assert final["status"] == "final"

    msgs = llm.calls[1]["messages"]
    assistant = next(m for m in msgs if m.get("tool_calls"))
    assert [tc["id"] for tc in assistant["tool_calls"]] == ["id-A", "id-B"]
    assert [m["tool_call_id"] for m in tool_messages(llm.calls[1])] == ["id-A", "id-B"]  # call order kept
    assert {s["tool"] for s in final["sources"]} == {"get_opening_hours", "get_facility_info"}


def test_unknown_tool_is_rejected_without_reaching_android(make_client):
    client, llm = make_client([
        tools(call("run_sql", {"query": "DROP TABLE activity"}, "bad")),
        say("No puc fer això."),
    ])
    final = _post(client, "executa aquesta consulta").json()
    assert final["status"] == "final"  # never went to the device
    err = json.loads(tool_messages(llm.calls[1])[0]["content"])
    assert err["ok"] is False and "Unknown tool" in err["error"]


def test_invalid_arguments_rejected_and_valid_sibling_forwarded(make_client, fx):
    client, llm = make_client([
        tools(call("get_facility_info", {"activity_id": "gimnas"}, "bad"),
              call("get_facility_info", {"activity_id": "tennis"}, "good")),
        say("El tennis té 5 pistes."),
    ])
    r = _post(client, "pistes de tennis i del gimnàs").json()
    assert [c["call_id"] for c in r["tool_calls"]] == ["good"]
    answer(client, r, {"good": fx["get_facility_info__tennis"]})
    contents = {m["tool_call_id"]: json.loads(m["content"]) for m in tool_messages(llm.calls[1])}
    assert set(contents) == {"bad", "good"}  # every call id answered before the next model call
    assert contents["bad"]["ok"] is False and "activity_id" in contents["bad"]["error"]


def test_missing_and_unknown_call_ids_return_422_and_turn_stays_open(make_client, fx):
    client, _ = make_client([
        tools(call("get_opening_hours", {}, "x1"), call("list_activities", {}, "x2")),
        say("Fet."),
    ])
    r = _post(client, "horaris i activitats").json()
    bad = client.post(f"/v1/chat/{r['turn_id']}/tool-results",
                      json={"results": [{"call_id": "x1", "ok": True, "output": fx["get_opening_hours"]},
                                        {"call_id": "zzz", "ok": True, "output": {}}]})
    assert bad.status_code == 422
    body = bad.json()["error"]
    assert body["code"] == "INVALID_TOOL_RESULT"
    assert body["details"] == {"missing": ["x2"], "unknown": ["zzz"], "duplicated": []}
    ok = answer(client, r, {"x1": fx["get_opening_hours"], "x2": fx["list_activities"]})
    assert ok["status"] == "final"


def test_output_not_matching_contract_is_422(make_client):
    client, _ = make_client([tools(call("get_facility_info", {"activity_id": "tennis"}, "t"))])
    r = _post(client, "tennis").json()
    bad = client.post(f"/v1/chat/{r['turn_id']}/tool-results",
                      json={"results": [{"call_id": "t", "ok": True, "output": {"activity": {"capacity": "lots"}}}]})
    assert bad.status_code == 422 and "t" in bad.json()["error"]["details"]["calls"]


def test_unknown_and_expired_turns(make_client):
    client, _ = make_client([tools(call("list_activities", {}, "l"))], turn_ttl_s=0)
    r = client.post("/v1/chat/turn_nope/tool-results", json={"results": [{"call_id": "a", "ok": False}]})
    assert r.status_code == 404 and r.json()["error"]["code"] == "TURN_NOT_FOUND"
    t = _post(client, "activitats").json()
    r = client.post(f"/v1/chat/{t['turn_id']}/tool-results", json={"results": [{"call_id": "l", "ok": False}]})
    assert r.status_code == 410 and r.json()["error"]["retryable"] is True


def test_new_message_supersedes_pending_turn(make_client):
    client, llm = make_client([tools(call("list_activities", {}, "l")), say("Hola! Sóc SAFIA.")])
    t = _post(client, "activitats").json()
    final = _post(client, "hola", conversation_id=t["conversation_id"]).json()
    assert final["status"] == "final"
    roles = [m["role"] for m in llm.calls[1]["messages"]]
    assert roles == ["system", "user"]  # the abandoned turn was rolled back
    assert client.post(f"/v1/chat/{t['turn_id']}/tool-results",
                       json={"results": [{"call_id": "l", "ok": False}]}).status_code == 404


def test_tool_rounds_are_capped(make_client, fx):
    loop = [tools(call("get_opening_hours", {}, f"r{i}")) for i in range(3)]
    client, llm = make_client([*loop, say("Obre a les 07:00.")], max_tool_rounds=3)
    r = _post(client, "horari").json()
    for i in range(3):
        r = answer(client, r, {f"r{i}": fx["get_opening_hours"]})
    assert r["status"] == "final"
    assert llm.calls[-1]["tool_choice"] == "none"


@pytest.mark.parametrize("exc,status,code", [
    (errors.llm_timeout(), 504, "LLM_TIMEOUT"),
    (errors.rate_limited(), 429, "RATE_LIMITED"),
    (errors.llm_unavailable(), 502, "LLM_UNAVAILABLE"),
])
def test_llm_errors_are_mapped_and_conversation_rolled_back(make_client, exc, status, code):
    def boom(*_):
        raise exc
    client, llm = make_client([boom, say("Ja funciona.")])
    r = _post(client, "hola", conversation_id="conv_test_12345")
    assert r.status_code == status and r.json()["error"]["code"] == code
    ok = _post(client, "hola de nou", conversation_id="conv_test_12345").json()
    assert [m["role"] for m in llm.calls[1]["messages"]] == ["system", "user"]
    assert ok["status"] == "final"


def test_openai_sdk_errors_are_mapped():
    from app.llm.client import _map_error
    req = __import__("httpx").Request("POST", "https://example.invalid")
    resp = __import__("httpx").Response(401, request=req)
    assert _map_error(openai.AuthenticationError("no", response=resp, body=None)).code == "LLM_AUTH"
    assert _map_error(openai.APITimeoutError(request=req)).code == "LLM_TIMEOUT"
    assert _map_error(openai.APIConnectionError(request=req)).code == "LLM_UNAVAILABLE"


def test_request_validation_uses_error_envelope(make_client):
    client, _ = make_client([])
    r = client.post("/v1/chat", json={"message": ""})
    assert r.status_code == 422 and r.json()["error"]["code"] == "BAD_REQUEST"
    r = client.post("/v1/chat", json={"message": "hola", "conversation_id": "bad id!"})
    assert r.status_code == 422


def test_history_seeds_unknown_conversation(make_client):
    client, llm = make_client([say("Vols saber-ho pels caps de setmana?")])
    _post(client, "i el dissabte?", conversation_id="conv_after_restart",
          history=[{"role": "user", "text": "Quan tanca el gimnàs?"},
                   {"role": "assistant", "text": "Entre setmana el SAF tanca a les 21:00."}])
    roles = [m["role"] for m in llm.calls[0]["messages"]]
    assert roles == ["system", "user", "assistant", "user"]


def test_tools_endpoint_and_health(make_client):
    client, _ = make_client([])
    names = [t["function"]["name"] for t in client.get("/v1/tools").json()["tools"]]
    assert names == ["list_activities", "get_opening_hours", "get_facility_info", "get_hourly_occupancy",
                     "find_quieter_slots", "recommend_alternatives", "get_dataset_info"]
    h = client.get("/health").json()
    assert h == {"status": "ok", "model": "ornith", "llm_configured": True}
