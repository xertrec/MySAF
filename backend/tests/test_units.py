"""Unit tests: argument validation, schema consistency, parsing, grounding, language."""
from __future__ import annotations

import json

import pytest

from app.grounding import allowed_numbers, ungrounded_numbers
from app.language import detect_language
from app.llm.parsing import extract_text_tool_calls, strip_reasoning
from app.tools.definitions import ARG_MODELS, TOOL_SCHEMAS
from app.tools.registry import check_call, validate_result, InvalidToolResult
from tests.conftest import say

KNOWN = {t["function"]["name"] for t in TOOL_SCHEMAS}


def test_every_schema_has_a_validator_with_the_same_fields():
    for t in TOOL_SCHEMAS:
        fn = t["function"]
        props = set(fn["parameters"]["properties"])
        assert props == set(ARG_MODELS[fn["name"]].model_fields), fn["name"]
        assert set(fn["parameters"]["required"]) <= props


@pytest.mark.parametrize("name,args,ok", [
    ("get_hourly_occupancy", {"activity_id": "tennis", "weekdays": ["dl"], "hour_from": 20, "hour_to": 8}, False),
    ("get_hourly_occupancy", {"activity_id": "tennis", "weekdays": ["monday"]}, False),
    ("recommend_alternatives", {"activity_id": "tennis", "weekday": "dl", "hour": 24}, False),
    ("recommend_alternatives", {"activity_id": "tennis", "weekday": "dl", "hour": 18, "period": "summer"}, False),
    ("find_quieter_slots", {"activity_id": "padel", "weekdays": ["ds"], "limit": 9}, False),
    ("find_quieter_slots", {"activity_id": "padel", "weekdays": ["ds"]}, True),
    ("get_opening_hours", {}, True),
])
def test_argument_validation(name, args, ok):
    assert check_call("c", name, json.dumps(args)).ok is ok


def test_arguments_may_arrive_as_object_or_bad_json():
    assert check_call("c", "get_facility_info", {"activity_id": "tennis"}).ok
    assert check_call("c", "get_facility_info", "{not json").error == "Arguments are not valid JSON."
    assert check_call("c", "get_facility_info", "[1]").error == "Arguments must be a JSON object."


def test_result_validation_drops_unknown_fields(fx):
    out = dict(fx["get_facility_info__tennis"])
    out["activity"] = {**out["activity"], "secret_extra": "x"}
    model, presented = validate_result("get_facility_info", out)
    assert "secret_extra" not in json.dumps(presented)
    with pytest.raises(InvalidToolResult):
        validate_result("recommend_alternatives", {"activity_id": "tennis"})


def test_strip_reasoning():
    assert strip_reasoning("<think>hmm 99%</think>Obre a les 7.") == "Obre a les 7."
    assert strip_reasoning("reasoning without opening tag</think>Hola") == "Hola"


def test_text_tool_call_fallbacks():
    calls, rest = extract_text_tool_calls(
        'Un moment.<tool_call>{"name": "get_opening_hours", "arguments": {"weekdays": ["ds"]}}</tool_call>', KNOWN)
    assert [c.name for c in calls] == ["get_opening_hours"] and json.loads(calls[0].arguments) == {"weekdays": ["ds"]}
    assert rest == "Un moment."
    calls, _ = extract_text_tool_calls('```json\n{"name": "list_activities", "parameters": {}}\n```', KNOWN)
    assert [c.name for c in calls] == ["list_activities"]
    calls, rest = extract_text_tool_calls('{"name": "not_a_tool"}', KNOWN)
    assert calls == [] and rest == '{"name": "not_a_tool"}'


def test_grounding():
    allowed = allowed_numbers([{"open": "08:00", "close": "20:00", "load_pct": 55, "load": 0.5521}], ["a les 18?"])
    assert ungrounded_numbers("Obre de 08:00 a 20:00, al 55 %.", allowed) == []
    assert ungrounded_numbers("A les 6 de la tarda.", allowed) == []  # 18h said as 6
    assert ungrounded_numbers("Hi caben 120 persones i està al 73 %.", allowed) == ["120", "73"]


def test_grounding_regenerates_then_falls_back(make_client, fx):
    from tests.conftest import answer, call, tools
    client, llm = make_client([
        tools(call("get_facility_info", {"activity_id": "tennis"})),
        say("Hi ha 7 pistes i 300 places."),          # invented
        say("Hi ha 5 pistes de tennis."),              # corrected on retry
    ])
    r = client.post("/v1/chat", json={"message": "Quantes pistes de tennis hi ha?"}).json()
    final = answer(client, r, {"get_facility_info": fx["get_facility_info__tennis"]})
    assert final["reply"] == "Hi ha 5 pistes de tennis."
    assert "300" in llm.calls[2]["messages"][-1]["content"] and llm.calls[2]["tool_choice"] == "none"
    # The rejected draft is not kept in the conversation history.
    client2, llm2 = make_client([
        tools(call("get_facility_info", {"activity_id": "tennis"})),
        say("Hi ha 300 places."), say("Encara 300."),
    ])
    r = client2.post("/v1/chat", json={"message": "Quantes pistes de tennis hi ha?"}).json()
    final = answer(client2, r, {"get_facility_info": fx["get_facility_info__tennis"]})
    assert final["reply"].startswith("Ho sento") and "unverified_figures_removed" in final["limitations"]


@pytest.mark.parametrize("text,lang", [
    ("A quina hora tanca el SAF els dissabtes?", "ca"),
    ("I els caps de setmana?", "ca"),
    ("Quan hi ha menys gent a la piscina?", "ca"),
    ("¿Cuántas pistas de tenis hay?", "es"),
    ("Cuando hay menos gente en el gimnasio", "es"),
    ("When is the pool less crowded?", "en"),
])
def test_language_detection(text, lang):
    assert detect_language(text) == lang


def test_exported_contract_is_up_to_date():
    from pathlib import Path
    from app.tools.registry import tool_schemas
    path = Path(__file__).resolve().parents[2] / "contracts" / "tools.schema.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    assert [t["arguments"] for t in doc["tools"]] == [t["function"]["parameters"] for t in tool_schemas()], \
        "run: python scripts/export_contract.py"
