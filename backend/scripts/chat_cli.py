"""Interactive client that plays the role of the Android app against a running backend.

    cd backend
    uvicorn app.main:app --port 8000          # terminal 1
    python scripts/chat_cli.py                # terminal 2

For every tool call it shows the request and lets you answer it with:
  - a sample output from contracts/fixtures/device_tool_outputs.json (real DB values),
  - JSON you paste yourself, or
  - a failure (ok=false), to see how SAFIA handles missing data.
Fixtures may not match the exact arguments requested; they exist to exercise the protocol.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import httpx

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
FIXTURES = json.loads((Path(__file__).resolve().parents[2] / "contracts" / "fixtures" /
                       "device_tool_outputs.json").read_text(encoding="utf-8"))


def pick_output(name: str, args: dict) -> dict:
    keys = [k for k in FIXTURES if k == name or k.startswith(name + "__")]
    print(f"\n  >> Android must run: {name}({json.dumps(args, ensure_ascii=False)})")
    for i, k in enumerate(keys, 1):
        print(f"     {i}) fixture {k}")
    print("     p) paste JSON output    f) fail (ok=false)")
    while True:
        choice = input("     choice [1]: ").strip() or "1"
        if choice == "f":
            return {"ok": False, "error": "NOT_AVAILABLE"}
        if choice == "p":
            raw = input("     JSON: ")
            try:
                return {"ok": True, "output": json.loads(raw)}
            except json.JSONDecodeError:
                print("     invalid JSON")
                continue
        if choice.isdigit() and 1 <= int(choice) <= len(keys):
            return {"ok": True, "output": FIXTURES[keys[int(choice) - 1]]}
        print("     ?")


def main() -> None:
    cid = None
    with httpx.Client(base_url=BASE, timeout=120) as http:
        print(f"SAFIA at {BASE} — {http.get('/health').json()}\nType a question (empty line to quit).")
        while True:
            msg = input("\nyou> ").strip()
            if not msg:
                return
            r = http.post("/v1/chat", json={"message": msg, **({"conversation_id": cid} if cid else {})})
            while True:
                body = r.json()
                if r.status_code != 200:
                    print(f"  x {r.status_code} {body}")
                    break
                cid = body["conversation_id"]
                if body["status"] == "final":
                    print(f"\nsafia> {body['reply']}")
                    print(f"  sources={[s['tool'] for s in body['sources']]} limitations={body['limitations']} "
                          f"context={body['context']}")
                    break
                results = [{"call_id": c["call_id"], **pick_output(c["name"], c["arguments"])} for c in body["tool_calls"]]
                r = http.post(f"/v1/chat/{body['turn_id']}/tool-results", json={"results": results})


if __name__ == "__main__":
    main()
