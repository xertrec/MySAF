"""Regenerate contracts/tools.schema.json from the backend's tool definitions.

    cd backend
    python scripts/export_contract.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.tools.definitions import P2_TOOLS  # noqa: E402
from app.tools.registry import tool_schemas  # noqa: E402
from app.tools.results import RESULT_MODELS  # noqa: E402

out = Path(__file__).resolve().parents[2] / "contracts" / "tools.schema.json"
doc = {
    "description": "SAFIA tool contract. 'arguments' is what the backend sends to Android (already validated); "
                   "'output' is what Android must return as ToolResult.output when ok=true.",
    "tools": [{
        "name": t["function"]["name"],
        "executed_by": "android",
        "uses_p2": t["function"]["name"] in P2_TOOLS,
        "description": t["function"]["description"],
        "arguments": t["function"]["parameters"],
        "output": RESULT_MODELS[t["function"]["name"]].model_json_schema(),
    } for t in tool_schemas()],
}
out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"wrote {out}")
