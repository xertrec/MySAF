"""Settings loaded from environment variables (and ``backend/.env`` if present).

The API key is held as a ``SecretStr`` so it never appears in ``repr()``, logs or
error messages. Nothing in this module prints it.
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field, SecretStr, field_validator

BACKEND_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BACKEND_DIR / ".env"

# The official public OpenAI endpoint must never be used for this project.
FORBIDDEN_BASE_URL_HOSTS = ("api.openai.com",)


class Settings(BaseModel):
    llm_provider: str = "openai"
    llm_model: str = "ornith"
    llm_base_url: str = "https://dcc-llm-gw.uab.cat/uabthehack/v1"
    uth_key: SecretStr = SecretStr("")

    llm_timeout_s: float = 60.0
    llm_max_retries: int = 1
    llm_temperature: float = 0.2
    llm_max_tokens: int = 800
    # Ask the gateway to parallelise tool calls. Some OpenAI-compatible servers
    # reject the parameter, so it can be switched off.
    llm_parallel_tool_calls: bool = True
    # Parse tool calls written as text (e.g. <tool_call>{...}</tool_call>) when the
    # gateway does not return structured tool_calls.
    llm_text_tool_call_fallback: bool = True

    # Conversation handling.
    conversation_ttl_s: int = 3600
    turn_ttl_s: int = 300
    max_tool_rounds: int = 3
    max_history_messages: int = 30
    max_conversations: int = 1000

    # "strict": unverifiable numbers trigger one regeneration, then a safe fallback.
    # "warn": unverifiable numbers are only flagged in `limitations`.
    grounding_mode: str = Field(default="strict", pattern="^(strict|warn)$")

    timezone: str = "Europe/Madrid"
    log_level: str = "INFO"

    @field_validator("llm_base_url")
    @classmethod
    def _not_public_openai(cls, v: str) -> str:
        if any(h in v for h in FORBIDDEN_BASE_URL_HOSTS):
            raise ValueError("LLM_BASE_URL must point to the UAB gateway, not the public OpenAI API")
        return v.rstrip("/")

    @property
    def has_api_key(self) -> bool:
        return bool(self.uth_key.get_secret_value())


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def load_settings(env_file: Path | None = ENV_FILE) -> Settings:
    if env_file is not None and env_file.exists():
        # Real environment variables win over the file.
        load_dotenv(env_file, override=False)
    d = Settings()
    return Settings(
        llm_provider=os.getenv("LLM_PROVIDER", d.llm_provider),
        llm_model=os.getenv("LLM_MODEL", d.llm_model),
        llm_base_url=os.getenv("LLM_BASE_URL", d.llm_base_url),
        uth_key=SecretStr(os.getenv("UTH_KEY", "").strip()),
        llm_timeout_s=float(os.getenv("LLM_TIMEOUT_S", d.llm_timeout_s)),
        llm_max_retries=int(os.getenv("LLM_MAX_RETRIES", d.llm_max_retries)),
        llm_temperature=float(os.getenv("LLM_TEMPERATURE", d.llm_temperature)),
        llm_max_tokens=int(os.getenv("LLM_MAX_TOKENS", d.llm_max_tokens)),
        llm_parallel_tool_calls=_env_bool("LLM_PARALLEL_TOOL_CALLS", d.llm_parallel_tool_calls),
        llm_text_tool_call_fallback=_env_bool("LLM_TEXT_TOOL_CALL_FALLBACK", d.llm_text_tool_call_fallback),
        conversation_ttl_s=int(os.getenv("CONVERSATION_TTL_S", d.conversation_ttl_s)),
        turn_ttl_s=int(os.getenv("TURN_TTL_S", d.turn_ttl_s)),
        max_tool_rounds=int(os.getenv("MAX_TOOL_ROUNDS", d.max_tool_rounds)),
        max_history_messages=int(os.getenv("MAX_HISTORY_MESSAGES", d.max_history_messages)),
        grounding_mode=os.getenv("GROUNDING_MODE", d.grounding_mode),
        timezone=os.getenv("SAFIA_TIMEZONE", d.timezone),
        log_level=os.getenv("LOG_LEVEL", d.log_level),
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return load_settings()
