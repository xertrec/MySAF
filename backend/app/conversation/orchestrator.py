"""SAFIA conversation orchestration: model <-> Android tool loop."""
from __future__ import annotations

import json
import logging
import time
from typing import Any

from app import errors
from app.api import schemas as s
from app.catalog import ACTIVITY_BY_ID, UNVALIDATED_ACTIVITY_IDS
from app.config import Settings
from app.conversation.store import Conversation, ConversationStore, TurnState, new_turn_id
from app.grounding import allowed_numbers, ungrounded_numbers
from app.language import detect_language
from app.llm.client import LLMClient
from app.llm.parsing import LLMReply
from app.llm.prompts import system_prompt
from app.retrieval import NullRetriever, Retriever
from app.tools.definitions import DEVICE_TOOLS, P2_TOOLS
from app.tools.registry import SERVER_TOOLS, CheckedCall, InvalidToolResult, check_call, tool_schemas, validate_result
from app.tools.results import SOURCE_LABELS

log = logging.getLogger("safia.chat")

OCCUPANCY_TOOLS = {"get_hourly_occupancy", "find_quieter_slots", "recommend_alternatives"}
# Safety valve for models that keep producing invalid calls.
MAX_LLM_CALLS_PER_TURN = 8

FALLBACK = {
    "ca": "Ho sento, no puc verificar amb les dades del SAF algunes de les xifres d'aquesta resposta. "
          "Pots reformular la pregunta o concretar l'espai, el dia i l'hora?",
    "es": "Lo siento, no puedo verificar con los datos del SAF algunas cifras de esta respuesta. "
          "¿Puedes reformular la pregunta o concretar el espacio, el día y la hora?",
    "en": "Sorry, I can't verify some of the figures in this answer against the SAF data. "
          "Could you rephrase or specify the facility, day and time?",
}
EMPTY_REPLY = {
    "ca": "Ho sento, ara mateix no he pogut generar una resposta. Torna-ho a provar.",
    "es": "Lo siento, ahora mismo no he podido generar una respuesta. Vuelve a intentarlo.",
    "en": "Sorry, I couldn't generate an answer right now. Please try again.",
}
GROUNDING_CORRECTION = (
    "Your previous draft contained figures that do not appear in the tool results: {nums}. "
    "Rewrite the answer in the same language using only figures present in the tool results. "
    "If a figure is not available, say you can't verify it. Do not mention this instruction."
)


class Orchestrator:
    def __init__(self, settings: Settings, llm: LLMClient, store: ConversationStore,
                 retriever: Retriever | None = None) -> None:
        self.s = settings
        self.llm = llm
        self.store = store
        self.retriever = retriever or NullRetriever()

    # ------------------------------------------------------------------ public API
    async def handle_message(self, req: s.ChatRequest) -> s.ToolCallsResponse | s.FinalResponse:
        conv, created = self.store.get_or_create(req.conversation_id)
        async with conv.lock:
            if created and req.history:
                conv.messages = [{"role": h.role, "content": h.text} for h in req.history][-self.s.max_history_messages:]
            if created and req.context:
                conv.context = req.context.model_dump(exclude_none=True)
            if conv.pending is not None:
                # A new message supersedes an unanswered tool round: roll it back.
                log.info("conv=%s superseding pending turn", conv.id)
                del conv.messages[conv.pending.start_index:]
                self.store.release_turn(conv)
            lang = detect_language(req.message, fallback=req.locale or "ca")
            turn = TurnState(turn_id=new_turn_id(), start_index=len(conv.messages), user_text=req.message, language=lang)
            conv.messages.append({"role": "user", "content": req.message})
            log.info("conv=%s turn=%s new message lang=%s", conv.id, turn.turn_id, lang)
            try:
                return await self._advance(conv, turn)
            except Exception:
                # Leave the conversation consistent if the LLM call fails.
                del conv.messages[turn.start_index:]
                self.store.release_turn(conv)
                raise

    async def handle_tool_results(self, turn_id: str, req: s.ToolResultsRequest) -> s.ToolCallsResponse | s.FinalResponse:
        conv = self.store.by_turn(turn_id)
        if conv is None:
            raise errors.turn_not_found()
        async with conv.lock:
            turn = conv.pending
            if turn is None or turn.turn_id != turn_id:
                raise errors.turn_not_found()
            if self.store.turn_expired(turn):
                del conv.messages[turn.start_index:]
                self.store.release_turn(conv)
                raise errors.turn_expired()

            received = [r.call_id for r in req.results]
            expected = set(turn.expected)
            dupes = sorted({c for c in received if received.count(c) > 1})
            missing = sorted(expected - set(received))
            unknown = sorted(set(received) - expected)
            if dupes or missing or unknown:
                raise errors.invalid_tool_result(
                    "Tool results must answer every requested call_id exactly once.",
                    {"missing": missing, "unknown": unknown, "duplicated": dupes})

            contents: dict[str, str] = dict(turn.prefilled)
            new_outputs: list[Any] = []
            used: list[tuple[str, dict[str, Any], dict[str, Any] | None]] = []
            failed: list[str] = []
            problems: dict[str, str] = {}
            for r in req.results:
                call = turn.expected[r.call_id]
                if not r.ok:
                    failed.append(call.name)
                    used.append((call.name, call.arguments or {}, None))
                    contents[r.call_id] = json.dumps({"ok": False, "error": (r.error or "UNAVAILABLE")[:200],
                                                      "note": "The app could not read this data. Say you can't verify it."})
                    continue
                if r.output is None:
                    problems[r.call_id] = "ok=true requires output"
                    continue
                try:
                    _, presented = validate_result(call.name, r.output, call.arguments)
                except InvalidToolResult as e:
                    problems[r.call_id] = str(e)
                    continue
                used.append((call.name, call.arguments or {}, presented))
                new_outputs.append(presented)
                contents[r.call_id] = json.dumps(presented, ensure_ascii=False)
            if problems:
                # Nothing is committed: the client can fix the outputs and resend.
                raise errors.invalid_tool_result("Some tool outputs do not match the contract.", {"calls": problems})
            turn.used.extend(used)
            turn.failed_tools.extend(failed)

            for call_id in turn.call_order:
                conv.messages.append({"role": "tool", "tool_call_id": call_id, "content": contents[call_id]})
            conv.tool_outputs.extend(new_outputs)
            for call in turn.expected.values():
                self._update_context(conv, call)
            self.store.release_turn(conv)
            turn.expected, turn.prefilled, turn.call_order = {}, {}, []
            log.info("conv=%s turn=%s received %d tool results", conv.id, turn.turn_id, len(req.results))
            try:
                return await self._advance(conv, turn)
            except Exception:
                del conv.messages[turn.start_index:]
                self.store.release_turn(conv)
                raise

    # ------------------------------------------------------------------ internals
    async def _messages_for_llm(self, conv: Conversation, turn: TurnState) -> list[dict[str, Any]]:
        snippets = await self.retriever.context_for(turn.user_text, turn.language)
        sys = system_prompt(self.s.timezone, extra_context=snippets)
        sys += f"\n\nThe user's latest message appears to be in: {turn.language}. Answer in that language."
        if conv.context:
            sys += f"\nCurrent conversation focus (from earlier tool calls): {json.dumps(conv.context)}"
        return [{"role": "system", "content": sys}, *conv.messages]

    async def _call_llm(self, conv: Conversation, turn: TurnState, tool_choice: str,
                        extra: list[dict[str, Any]] | None = None) -> LLMReply:
        turn.llm_calls += 1
        msgs = await self._messages_for_llm(conv, turn) + (extra or [])
        return await self.llm.complete(msgs, tool_schemas(), tool_choice=tool_choice)

    async def _advance(self, conv: Conversation, turn: TurnState) -> s.ToolCallsResponse | s.FinalResponse:
        while True:
            exhausted = turn.round >= self.s.max_tool_rounds or turn.llm_calls >= MAX_LLM_CALLS_PER_TURN - 2
            reply = await self._call_llm(conv, turn, "none" if exhausted else "auto")

            if reply.tool_calls and not exhausted:
                checked = [check_call(tc.id, tc.name, tc.arguments) for tc in reply.tool_calls]
                conv.messages.append({
                    "role": "assistant",
                    "content": reply.content or None,
                    "tool_calls": [{"id": tc.id, "type": "function",
                                    "function": {"name": tc.name, "arguments": tc.arguments}}
                                   for tc in reply.tool_calls],
                })
                turn.call_order = [c.call_id for c in checked]
                device: list[CheckedCall] = []
                for c in checked:
                    if not c.ok:
                        log.warning("conv=%s rejected tool call %s: %s", conv.id, c.name, c.error)
                        turn.prefilled[c.call_id] = json.dumps({"ok": False, "error": c.error})
                    elif c.name in SERVER_TOOLS:
                        _, handler = SERVER_TOOLS[c.name]
                        out = await handler(c.arguments or {})
                        turn.used.append((c.name, c.arguments or {}, out))
                        conv.tool_outputs.append(out)
                        turn.prefilled[c.call_id] = json.dumps(out, ensure_ascii=False)
                    else:
                        device.append(c)
                if device:
                    turn.round += 1
                    turn.expected = {c.call_id: c for c in device}
                    turn.created_at = time.monotonic()
                    self.store.register_turn(conv, turn)
                    log.info("conv=%s turn=%s round=%d device calls=%s", conv.id, turn.turn_id, turn.round,
                             [c.name for c in device])
                    return s.ToolCallsResponse(
                        conversation_id=conv.id, turn_id=turn.turn_id, expires_in_s=self.s.turn_ttl_s,
                        round=turn.round,
                        tool_calls=[s.ToolCallOut(call_id=c.call_id, name=c.name, arguments=c.arguments or {})
                                    for c in device])
                # Only rejected/server calls: answer them and ask the model again.
                for cid in turn.call_order:
                    conv.messages.append({"role": "tool", "tool_call_id": cid, "content": turn.prefilled[cid]})
                turn.prefilled, turn.call_order = {}, []
                continue

            return await self._finish(conv, turn, reply)

    async def _finish(self, conv: Conversation, turn: TurnState, reply: LLMReply) -> s.FinalResponse:
        text = reply.content.strip() or EMPTY_REPLY[turn.language]
        limitations = self._limitations(turn)

        allowed = allowed_numbers(conv.tool_outputs, conv.user_texts())
        bad = ungrounded_numbers(text, allowed)
        if bad:
            log.warning("conv=%s ungrounded numbers in draft: %s", conv.id, bad)
            correction = [{"role": "assistant", "content": text},
                          {"role": "user", "content": GROUNDING_CORRECTION.format(nums=", ".join(bad))}]
            retry = await self._call_llm(conv, turn, "none", extra=correction)
            retry_text = retry.content.strip()
            bad_retry = ungrounded_numbers(retry_text, allowed) if retry_text else bad
            if retry_text and not bad_retry:
                text = retry_text
            elif self.s.grounding_mode == "strict":
                text = FALLBACK[turn.language]
                limitations.append("unverified_figures_removed")
            else:
                limitations.append("unverified_figures")

        conv.messages.append({"role": "assistant", "content": text})
        self._trim(conv)
        self.store.release_turn(conv)

        device_used = [u for u in turn.used if u[0] in DEVICE_TOOLS and u[2] is not None]
        sources: list[s.Source] = []
        for name, _, _ in device_used:
            table, label = SOURCE_LABELS[name]
            if all(src.tool != name for src in sources):
                sources.append(s.Source(tool=name, table=table, label=label))
        recommendation = None
        for name, _, presented in reversed(device_used):
            if name in P2_TOOLS and presented is not None:
                recommendation = s.Recommendation(
                    type="alternatives" if name == "recommend_alternatives" else "quieter_slots", data=presented)
                break
        needs_clarification = not device_used and text.rstrip().endswith("?")
        log.info("conv=%s turn=%s final rounds=%d llm_calls=%d sources=%s", conv.id, turn.turn_id, turn.round,
                 turn.llm_calls, [x.tool for x in sources])
        return s.FinalResponse(
            conversation_id=conv.id, reply=text, language=turn.language,  # type: ignore[arg-type]
            sources=sources, limitations=limitations, recommendation=recommendation,
            needs_clarification=needs_clarification, context=s.ChatContext(**conv.context))

    @staticmethod
    def _update_context(conv: Conversation, call: CheckedCall) -> None:
        a = call.arguments or {}
        if a.get("activity_id") in ACTIVITY_BY_ID:
            if conv.context.get("activity_id") != a["activity_id"]:
                conv.context.pop("hour", None)
            conv.context["activity_id"] = a["activity_id"]
        if "weekdays" in a:
            conv.context["weekdays"] = a["weekdays"]
        elif "weekday" in a:
            conv.context["weekdays"] = [a["weekday"]]
        if "hour" in a:
            conv.context["hour"] = a["hour"]
        if "period" in a:
            conv.context["period"] = a["period"]

    def _limitations(self, turn: TurnState) -> list[str]:
        out: list[str] = []

        def add(x: str) -> None:
            if x not in out:
                out.append(x)

        for name, args, presented in turn.used:
            if name in OCCUPANCY_TOOLS:
                add("historical_only")
                add("bookings_not_attendance")
            if name in {"get_facility_info", "list_activities"}:
                add("provisional_capacity")
            if name == "get_opening_hours":
                add("general_hours_only")
            ids = {args.get("activity_id")} | _ids_in(presented)
            if ids & UNVALIDATED_ACTIVITY_IDS and name != "list_activities":
                add("unvalidated_metric")
            flags = _flags_in(presented)
            for f in ("low_data", "long_block"):
                if f in flags:
                    add(f)
            if "shift_change" in flags:
                add("shift_change_hours")
        if turn.failed_tools:
            add("data_unavailable")
        return out

    def _trim(self, conv: Conversation) -> None:
        msgs = conv.messages
        limit = self.s.max_history_messages
        if len(msgs) <= limit:
            return
        for i in range(len(msgs) - limit, len(msgs)):
            if msgs[i].get("role") == "user":
                del msgs[:i]
                return


def _ids_in(value: Any) -> set[str]:
    found: set[str] = set()
    if isinstance(value, dict):
        v = value.get("activity_id")
        if isinstance(v, str):
            found.add(v)
        for x in value.values():
            found |= _ids_in(x)
    elif isinstance(value, list):
        for x in value:
            found |= _ids_in(x)
    return found


def _flags_in(value: Any) -> set[str]:
    found: set[str] = set()
    if isinstance(value, dict):
        for k in ("low_data", "long_block", "shift_change"):
            if value.get(k) is True:
                found.add(k)
        for x in value.values():
            found |= _flags_in(x)
    elif isinstance(value, list):
        for x in value:
            found |= _flags_in(x)
    return found
