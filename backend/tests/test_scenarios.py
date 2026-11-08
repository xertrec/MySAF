"""The 14 required scenarios, with a scripted LLM and Android-shaped tool outputs
taken from the real database (contracts/fixtures/device_tool_outputs.json).

Each test checks what the backend controls: which tool requests reach Android,
what the model receives back, and the metadata returned to the app.
"""
from __future__ import annotations

import json

from tests.conftest import answer, call, say, tool_messages, tools

WEEKDAYS_MON_FRI = ["dl", "dt", "dc", "dj", "dv"]


def _chat(client, message, cid=None, **kw):
    body = {"message": message, **kw}
    if cid:
        body["conversation_id"] = cid
    r = client.post("/v1/chat", json=body)
    assert r.status_code == 200, r.text
    return r.json()


def _tool_payload(llm, i=-1):
    return [json.loads(m["content"]) for m in tool_messages(llm.calls[i])]


# 1 + 8: opening hours, Catalan
def test_01_opening_hours_catalan(make_client, fx):
    client, llm = make_client([
        tools(call("get_opening_hours", {"weekdays": ["ds"]})),
        say("Els dissabtes el SAF obre de 08:00 a 20:00 (horari general)."),
    ])
    r = _chat(client, "A quina hora tanca el SAF els dissabtes?")
    assert r["tool_calls"] == [{"call_id": "call_get_opening_hours", "name": "get_opening_hours",
                                "arguments": {"weekdays": ["ds"]}}]
    final = answer(client, r, {"get_opening_hours": fx["get_opening_hours"]})
    sent = _tool_payload(llm)[0]
    assert [d["weekday"] for d in sent["opening_hours"]] == ["ds"]  # Android sent all 7; narrowed to the request
    sat = sent["opening_hours"][0]
    assert (sat["open"], sat["close"]) == ("08:00", "20:00")
    assert final["status"] == "final" and final["language"] == "ca"
    assert final["reply"].startswith("Els dissabtes")
    assert [s["table"] for s in final["sources"]] == ["opening_hours"]
    assert "general_hours_only" in final["limitations"]
    assert "Answer in that language" in llm.calls[0]["messages"][0]["content"]


# 2 + 9: capacity, Spanish
def test_02_capacity_spanish(make_client, fx):
    client, llm = make_client([
        tools(call("get_facility_info", {"activity_id": "tennis"})),
        say("Hay 5 pistas de tenis según el inventario del SAF (dato provisional)."),
    ])
    r = _chat(client, "¿Cuántas pistas de tenis hay?")
    final = answer(client, r, {"get_facility_info": fx["get_facility_info__tennis"]})
    sent = _tool_payload(llm)[0]["activity"]
    assert sent["capacity"] == 5 and sent["unit"] == "courts" and sent["capacity_status"] == "provisional_inventory"
    assert final["language"] == "es"
    assert "provisional_capacity" in final["limitations"]
    assert final["context"]["activity_id"] == "tennis"


# 3: historical occupancy
def test_03_historical_occupancy(make_client, fx):
    client, llm = make_client([
        tools(call("get_hourly_occupancy", {"activity_id": "piscina_25m", "weekdays": ["dl"]})),
        say("Els dilluns, la piscina té l'ocupació històrica més baixa a les 11:00 (27 %) i la més alta a les 19:00 (65 %)."),
    ])
    r = _chat(client, "Com està d'ocupada la piscina els dilluns?")
    assert r["tool_calls"][0]["arguments"]["period"] == "lectiu"  # default filled in by validation
    final = answer(client, r, {"get_hourly_occupancy": fx["get_hourly_occupancy__piscina_25m_dl"]})
    hours = {h["hour"]: h for h in _tool_payload(llm)[0]["days"][0]["hours"]}
    assert hours[11]["load_pct"] == 27 and hours[19]["load_pct"] == 65 and hours[19]["unit"] == "people"
    assert "27 %" in final["reply"]  # grounded, kept
    assert {"historical_only", "bookings_not_attendance"} <= set(final["limitations"])


# 4: activities
def test_04_available_activities(make_client, fx):
    client, llm = make_client([
        tools(call("list_activities", {})),
        say("Al SAF hi ha dades de piscina, sala fitness, pàdel, tennis, esquaix, pavelló, futbol sala, "
            "futbol 7/11, espai barbell, cal·listènia i rocòdrom."),
    ])
    final = answer(client, _chat(client, "Quines activitats hi ha al SAF?"), {"list_activities": fx["list_activities"]})
    assert len(_tool_payload(llm)[0]["activities"]) == 11
    assert final["sources"][0]["tool"] == "list_activities"


# 5: facility recommendation through P2
def test_05_alternative_recommendation_uses_p2(make_client, fx):
    client, llm = make_client([
        tools(call("recommend_alternatives", {"activity_id": "tennis", "weekday": "dl", "hour": 18})),
        say("Els dilluns a les 18:00 el tennis sol estar ple (91 %). Alternatives més tranquil·les segons "
            "l'historial: tennis a les 15:00 (6 %), dissabte a les 18:00 (55 %) o futbol sala a les 18:00 (6 %)."),
    ])
    r = _chat(client, "Vull jugar a tennis dilluns a les 18, però sol estar ple. Què em recomanes?")
    assert r["tool_calls"][0]["name"] == "recommend_alternatives"
    final = answer(client, r, {"recommend_alternatives": fx["recommend_alternatives__tennis_dl_18"]})
    assert final["recommendation"]["type"] == "alternatives"
    kinds = [a["kind"] for a in final["recommendation"]["data"]["alternatives"]]
    assert kinds == ["SAME_DAY", "OTHER_DAY", "OTHER_ACTIVITY"]
    assert final["recommendation"]["data"]["source"] == "P2 recommendation engine"
    assert final["reply"].endswith("(6 %).")
    assert "long_block" in final["limitations"]  # 18:00 tennis includes club blocks


# 6 + 7: quieter slots, then a follow-up that keeps the facility
def test_06_07_quieter_slots_and_follow_up(make_client, fx):
    def follow_up(messages, _tools, _choice):
        # The previous turn (tool call + result) is in the history the model sees...
        assert any(m.get("tool_calls") and m["tool_calls"][0]["function"]["name"] == "find_quieter_slots"
                   for m in messages)
        # ...and the system prompt carries the conversation focus.
        assert '"activity_id": "sala_fitness"' in messages[0]["content"]
        return tools(call("find_quieter_slots", {"activity_id": "sala_fitness", "weekdays": ["ds", "dg"]}, "c2"))

    client, llm = make_client([
        tools(call("find_quieter_slots", {"activity_id": "sala_fitness", "weekdays": ["dl"]}, "c1")),
        say("Els dilluns, la sala fitness sol estar més tranquil·la a les 07:00 (58 %), a les 14:00 (68 %) "
            "i a les 09:00 (72 %). Són patrons històrics, no ocupació en directe."),
        follow_up,
        say("Els caps de setmana, les franges més tranquil·les són dissabte a les 14:00 (18 %) i diumenge "
            "a les 09:00 (27 %)."),
    ])
    r1 = _chat(client, "Quan hi ha menys gent al gimnàs els dilluns?")
    f1 = answer(client, r1, {"c1": fx["find_quieter_slots__sala_fitness_dl"]})
    assert f1["recommendation"]["type"] == "quieter_slots"
    assert f1["context"] == {"activity_id": "sala_fitness", "weekdays": ["dl"], "hour": None, "period": "lectiu"}

    r2 = _chat(client, "I els caps de setmana?", cid=f1["conversation_id"])
    assert r2["conversation_id"] == f1["conversation_id"]
    f2 = answer(client, r2, {"c2": fx["find_quieter_slots__sala_fitness_ds_dg"]})
    assert f2["context"]["weekdays"] == ["ds", "dg"] and f2["context"]["activity_id"] == "sala_fitness"
    assert "18 %" in f2["reply"]


# 10: ambiguous facility -> clarification, no tool request
def test_10_ambiguous_facility_asks(make_client):
    client, llm = make_client([say("Quina pista vols dir: tennis, pàdel, esquaix o pavelló?")])
    final = _chat(client, "Quan hi ha menys gent a la pista?")
    assert final["status"] == "final" and final["needs_clarification"] is True
    assert final["sources"] == [] and final["recommendation"] is None


# 11: data unavailable — both "not in the data" and "device couldn't read it"
def test_11a_question_not_covered(make_client):
    client, llm = make_client([say("No ho sé: les dades de mySAF no inclouen preus ni abonaments.")])
    final = _chat(client, "Quant costa l'abonament del SAF?")
    assert final["sources"] == [] and final["needs_clarification"] is False
    assert "prices" in llm.calls[0]["messages"][0]["content"]  # NOT COVERED list is in the prompt


def test_11b_device_tool_failure(make_client):
    client, llm = make_client([
        tools(call("get_facility_info", {"activity_id": "padel"})),
        say("Ara mateix no puc consultar les dades de pàdel, ho sento."),
    ])
    final = answer(client, _chat(client, "Quantes pistes de pàdel hi ha?"),
                   {"get_facility_info": {"__fail__": "DB_UNAVAILABLE"}})
    sent = _tool_payload(llm)[0]
    assert sent["ok"] is False and sent["error"] == "DB_UNAVAILABLE"
    assert "data_unavailable" in final["limitations"] and final["sources"] == []


# 12: real-time request
def test_12_real_time_request_is_historical(make_client, fx):
    client, llm = make_client([
        tools(call("get_hourly_occupancy", {"activity_id": "sala_fitness", "weekdays": ["dl"],
                                            "hour_from": 9, "hour_to": 11})),
        say("No tinc dades en temps real. Històricament, els dilluns a les 09:00 la sala fitness està al 72 %."),
    ])
    final = answer(client, _chat(client, "Hi ha molta gent ara al gimnàs?"),
                   {"get_hourly_occupancy": fx["get_hourly_occupancy__sala_fitness_dl_9_11"]})
    system = llm.calls[0]["messages"][0]["content"]
    assert "NOT live" in system and "today is" in system
    assert "historical_only" in final["limitations"]
    # The 10:00 shift change reaches the model flagged, without a percentage.
    h10 = next(h for h in _tool_payload(llm)[0]["days"][0]["hours"] if h["hour"] == 10)
    assert h10["status"] == "shift_change_no_data" and "load_pct" not in h10
    assert "shift_change_hours" in final["limitations"]


# 13: unvalidated resource
def test_13_unvalidated_metric_flagged(make_client, fx):
    client, llm = make_client([
        tools(call("get_hourly_occupancy", {"activity_id": "rocodrom", "weekdays": ["dl"], "hour_from": 17, "hour_to": 19})),
        say("Les dades del rocòdrom no estan validades; en general, els dilluns a la tarda hi ha poca ocupació registrada."),
    ])
    final = answer(client, _chat(client, "Hi ha gent al rocòdrom els dilluns a la tarda?"),
                   {"get_hourly_occupancy": fx["get_hourly_occupancy__rocodrom_dl_17_19"]})
    assert _tool_payload(llm)[0]["metric_validated"] is False
    assert "unvalidated_metric" in final["limitations"]


# 14: different measurement types reach the model labelled with their unit
def test_14_units_are_explicit(make_client, fx):
    client, llm = make_client([
        tools(call("recommend_alternatives", {"activity_id": "tennis", "weekday": "dl", "hour": 18}, "a"),
              call("get_facility_info", {"activity_id": "piscina_25m"}, "b")),
        say("D'acord."),
    ])
    answer(client, _chat(client, "Compara tennis i piscina dilluns a les 18"),
           {"a": fx["recommend_alternatives__tennis_dl_18"], "b": fx["get_facility_info__piscina_25m"]})
    rec, pool = _tool_payload(llm)
    assert rec["unit"] == "courts" and rec["requested"]["unit"] == "courts"
    assert {a["unit"] for a in rec["alternatives"]} == {"courts"}  # P2 only offers same-unit activities
    assert pool["activity"]["unit"] == "people"
    assert "Never compare or rank a people-based activity" in llm.calls[0]["messages"][0]["content"]
