"""Quick compatibility check of the UAB Ornith gateway (no server needed).

    cd backend
    python scripts/smoke_ornith.py

Checks basic generation, structured tool calls, the tool-result round trip and
Catalan/Spanish answers. Prints PASS/FAIL lines; never prints the API key.
"""
from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import load_settings  # noqa: E402
from app.language import detect_language  # noqa: E402
from app.llm.client import OrnithClient  # noqa: E402
from app.llm.prompts import system_prompt  # noqa: E402
from app.tools.registry import check_call, tool_schemas  # noqa: E402

FIXTURES = Path(__file__).resolve().parents[2] / "contracts" / "fixtures" / "device_tool_outputs.json"
OPENING = {"opening_hours": [{"weekday": "ds", "weekday_name": {"ca": "dissabte", "es": "sábado", "en": "Saturday"},
                              "open": "08:00", "close": "20:00"}],
           "scope": "general SAF schedule (no per-facility hours available)"}

results: list[tuple[str, bool, str]] = []


def report(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))


async def exchange(llm: OrnithClient, question: str) -> tuple[str, dict]:
    msgs = [{"role": "system", "content": system_prompt()}, {"role": "user", "content": question}]
    first = await llm.complete(msgs, tool_schemas())
    info = {"tool_calls": [(c.name, c.arguments) for c in first.tool_calls], "from_text": first.parsed_from_text,
            "finish_reason": first.finish_reason}
    if not first.tool_calls:
        return first.content, info
    msgs.append({"role": "assistant", "content": first.content or None,
                 "tool_calls": [{"id": c.id, "type": "function", "function": {"name": c.name, "arguments": c.arguments}}
                                for c in first.tool_calls]})
    for c in first.tool_calls:
        msgs.append({"role": "tool", "tool_call_id": c.id, "content": json.dumps(OPENING, ensure_ascii=False)})
    final = await llm.complete(msgs, tool_schemas())
    info["second_has_tool_calls"] = bool(final.tool_calls)
    return final.content, info


async def main() -> int:
    s = load_settings()
    print(f"Endpoint: {s.llm_base_url}  model: {s.llm_model}  key configured: {s.has_api_key}")
    if not s.has_api_key:
        print("UTH_KEY missing in backend/.env")
        return 2
    llm = OrnithClient(s)

    t0 = time.perf_counter()
    try:
        r = await llm.complete([{"role": "user", "content": "Reply with the single word: pong"}], tools=None)
        report("1 basic generation", "pong" in r.content.lower(), f"{r.content[:60]!r} ({time.perf_counter() - t0:.1f}s)")
    except Exception as e:  # noqa: BLE001
        report("1 basic generation", False, f"{type(e).__name__}: {getattr(e, 'message', e)}")
        return 1

    try:
        r = await llm.complete([{"role": "system", "content": system_prompt()},
                                {"role": "user", "content": "A quina hora tanca el SAF els dissabtes?"}], tool_schemas())
        ok = bool(r.tool_calls)
        report("2 tool call returned", ok, "structured tool_calls" if ok and not r.parsed_from_text
               else ("parsed from text (fallback)" if ok else f"no tool call: {r.content[:120]!r}"))
        if ok:
            c = r.tool_calls[0]
            chk = check_call(c.id, c.name, c.arguments)
            report("3 tool call parsed and valid", chk.ok and c.name == "get_opening_hours",
                   f"id={c.id} name={c.name} args={c.arguments}" + (f" error={chk.error}" if chk.error else ""))
    except Exception as e:  # noqa: BLE001
        report("2 tool call returned", False, f"{type(e).__name__}")

    for label, q, lang in (("4-5-7 Catalan round trip", "A quina hora tanca el SAF els dissabtes?", "ca"),
                           ("4-5-6 Spanish round trip", "¿A qué hora cierra el SAF los sábados?", "es")):
        try:
            text, info = await exchange(llm, q)
            ok = bool(info["tool_calls"]) and "20" in text and detect_language(text) == lang
            report(label, ok, f"{text[:160]!r} | {info}")
        except Exception as e:  # noqa: BLE001
            report(label, False, f"{type(e).__name__}")

    failed = [n for n, ok, _ in results if not ok]
    print(f"\n{len(results) - len(failed)}/{len(results)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
