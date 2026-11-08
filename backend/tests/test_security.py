"""Credentials must never leak: not in responses, logs, repr, or tracked files."""
from __future__ import annotations

import logging
import subprocess
from pathlib import Path

import pytest
from pydantic import SecretStr, ValidationError

from app.config import ENV_FILE, Settings, load_settings
from tests.conftest import say

BACKEND = Path(__file__).resolve().parents[1]
REPO = BACKEND.parent
FAKE_KEY = "test-key-not-real-0000"


def test_settings_never_render_the_key():
    s = Settings(uth_key=SecretStr(FAKE_KEY))
    assert FAKE_KEY not in repr(s) and FAKE_KEY not in str(s.model_dump())


def test_public_openai_endpoint_is_refused():
    with pytest.raises(ValidationError):
        Settings(llm_base_url="https://api.openai.com/v1")


def test_key_not_in_responses_or_logs(make_client, caplog):
    caplog.set_level(logging.DEBUG)
    client, _ = make_client([say("Hola!")])
    bodies = [client.get("/health").text, client.get("/v1/tools").text,
              client.post("/v1/chat", json={"message": "hola"}).text]
    assert all(FAKE_KEY not in b for b in bodies)
    assert FAKE_KEY not in caplog.text


def test_env_example_is_safe_and_env_is_ignored():
    example = (BACKEND / ".env.example").read_text(encoding="utf-8")
    assert "UTH_KEY=" in example
    value = example.split("UTH_KEY=", 1)[1].splitlines()[0].strip()
    assert value in ("", "your_existing_team_key")
    assert "dcc-llm-gw.uab.cat" in example and "api.openai.com" not in example
    try:
        out = subprocess.run(["git", "check-ignore", "-q", str(ENV_FILE)], cwd=REPO, capture_output=True)
    except FileNotFoundError:
        pytest.skip("git not available")
    if out.returncode == 128:
        pytest.skip("not a git checkout")
    assert out.returncode == 0, "backend/.env must be ignored by git"


def test_real_key_not_present_in_any_tracked_or_source_file():
    if not ENV_FILE.exists():
        pytest.skip("no backend/.env on this machine")
    key = load_settings().uth_key.get_secret_value()
    if len(key) < 12:
        pytest.skip("no real key configured")
    for path in list(BACKEND.rglob("*")) + list((REPO / "docs").rglob("*")) + list((REPO / "contracts").rglob("*")):
        if not path.is_file() or path == ENV_FILE or ".venv" in path.parts or "__pycache__" in path.parts:
            continue
        if path.stat().st_size > 2_000_000:
            continue
        assert key not in path.read_text(encoding="utf-8", errors="ignore"), f"API key found in {path}"
