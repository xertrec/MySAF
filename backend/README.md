# SAFIA backend

FastAPI service that runs SAFIA's conversations with the UAB **Ornith** model
(`https://dcc-llm-gw.uab.cat/uabthehack/v1`, OpenAI-compatible). It holds **no database**:
whenever SAF data is needed, it returns tool calls that the Android app executes on Room and the
Kotlin P2 engine, then it turns the results into an answer.

- Architecture: [`docs/safia/ARCHITECTURE.md`](../docs/safia/ARCHITECTURE.md)
- Android contract: [`docs/safia/ANDROID_INTEGRATION.md`](../docs/safia/ANDROID_INTEGRATION.md)
- Tool contract (generated): [`contracts/tools.schema.json`](../contracts/tools.schema.json)

## 1. Setup on Windows (PowerShell)

Python 3.10 or newer (the repo's `.venv` uses 3.13).

```powershell
cd C:\workspace\UABTheHack\backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1          # if blocked: Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
pip install -r requirements-dev.txt
```

`backend\.env` already holds the team key. If you need to recreate it, copy `.env.example` to `.env` and
set `UTH_KEY`. `.env` is git-ignored (root `.gitignore` and `backend\.gitignore`); never commit it.

```env
LLM_PROVIDER=openai
LLM_MODEL=ornith
LLM_BASE_URL=https://dcc-llm-gw.uab.cat/uabthehack/v1
UTH_KEY=<team key>
```

## 2. Check the Ornith connection

```powershell
python scripts\smoke_ornith.py
```

Expected: 5 `PASS` lines (basic generation, tool call returned, tool call parsed, Catalan and Spanish
round trips). It reports whether tool calls came back structured or had to be parsed from text.

## 3. Run the server

```powershell
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

- `GET  http://127.0.0.1:8000/health` → `{"status":"ok","model":"ornith","llm_configured":true}`
- `GET  http://127.0.0.1:8000/docs` → interactive OpenAPI docs
- `GET  http://127.0.0.1:8000/v1/tools` → tool schemas Android must implement

`--host 0.0.0.0` is needed for a physical phone on the same Wi-Fi (allow Python through the Windows
firewall when prompted). The Android emulator reaches the PC at `http://10.0.2.2:8000`.

## 4. Talk to SAFIA without the app

In a second terminal (venv activated):

```powershell
python scripts\chat_cli.py
```

Type a question. When SAFIA needs data, the CLI shows the tool call Android would run and lets you
answer with a sample output from `contracts\fixtures\device_tool_outputs.json` (real database values),
paste your own JSON, or simulate a failure. Example session:

```
you> A quina hora tanca el SAF els dissabtes?
  >> Android must run: get_opening_hours({"weekdays": ["ds"]})
     1) fixture get_opening_hours
     choice [1]:
safia> Els dissabtes el SAF tanca a les 20:00 (horari general).
```

Or with raw HTTP (PowerShell):

```powershell
$r = Invoke-RestMethod -Method Post http://127.0.0.1:8000/v1/chat -ContentType 'application/json' `
     -Body '{"message":"A quina hora tanca el SAF els dissabtes?"}'
$r | ConvertTo-Json -Depth 10
$out = (Get-Content ..\contracts\fixtures\device_tool_outputs.json -Raw | ConvertFrom-Json).get_opening_hours
$body = @{ results = @(@{ call_id = $r.tool_calls[0].call_id; ok = $true; output = $out }) } | ConvertTo-Json -Depth 10
Invoke-RestMethod -Method Post "http://127.0.0.1:8000/v1/chat/$($r.turn_id)/tool-results" -ContentType 'application/json' -Body $body
```

## 5. Tests

```powershell
python -m pytest            # deterministic suite, scripted LLM, no network (~1 s)
python -m pytest -m live -v -s   # real Ornith endpoint (needs .env + network)
```

| File | What it covers |
|---|---|
| `tests/test_scenarios.py` | The 14 required scenarios (opening hours, capacity, occupancy, activities, P2 recommendations, quieter slots, follow-ups, Catalan, Spanish, ambiguity, unavailable data, real-time requests, unvalidated metrics, units) |
| `tests/test_protocol.py` | Full exchange, parallel calls, call-id order, rejected tools/arguments, 422/404/410 handling, superseded turns, round cap, LLM error mapping, history seeding |
| `tests/test_openai_wire.py` | The real OpenAI SDK client against a simulated gateway: URL, auth header, body, tool-call parsing, rejected-parameter fallbacks, HTTP error mapping |
| `tests/test_units.py` | Argument and result validation, schema/contract consistency, `<think>` stripping, text tool-call parsing, numeric grounding, language detection |
| `tests/test_security.py` | Key never in responses, logs or `repr`; public OpenAI URL refused; `.env.example` safe; `.env` git-ignored; real key absent from all source files |
| `tests/live/test_ornith_live.py` | Real Ornith: generation, tool call, parsing, complete exchange in Catalan and Spanish, P2 routing, follow-up, real-time question |

## 6. Configuration

All settings are environment variables (see `.env.example`). Notable ones:

| Variable | Default | Purpose |
|---|---|---|
| `LLM_PARALLEL_TOOL_CALLS` | `true` | Ask for several tool calls per round. Dropped automatically if the gateway rejects it. |
| `LLM_TEXT_TOOL_CALL_FALLBACK` | `true` | Accept tool calls the model writes as text (`<tool_call>{…}</tool_call>` or JSON). |
| `MAX_TOOL_ROUNDS` | `3` | Device round trips per user message before forcing an answer. |
| `TURN_TTL_S` | `300` | How long the backend waits for Android's tool results. |
| `GROUNDING_MODE` | `strict` | `strict`: an answer with figures not found in tool results is regenerated once, then replaced by a safe message. `warn`: only flagged in `limitations`. |

## 7. Code map

```
app/main.py                  FastAPI app, error envelope, secret-redacting log filter
app/config.py                settings (.env), key as SecretStr, public OpenAI URL refused
app/api/                     routes + Pydantic request/response schemas
app/conversation/            orchestrator (tool loop) + in-memory conversation/turn store
app/llm/                     Ornith client (OpenAI SDK), system prompt, output normalisation
app/tools/                   tool schemas, argument validation, result validation/presentation
app/catalog.py               activity ids, names, units, validation flags, coverage (no figures)
app/grounding.py             numeric grounding check
app/language.py              ca/es/en detection (metadata + prompt hint)
app/retrieval/               empty extension point for a later RAG phase
```

## 8. Known limitations

- Conversations live in memory: restarting the server forgets them (Android can resend `history`). One
  worker process only (`uvicorn` without `--workers`).
- The test fixtures for P2 outputs were derived by hand from `Recommendations.kt`; replace them with
  fixtures recorded from the Android executor (see the Android guide).
- Language detection for the `language` field is heuristic; the reply language is decided by the model.
- The grounding check works on numbers only; it doesn't catch an invented facility name.
