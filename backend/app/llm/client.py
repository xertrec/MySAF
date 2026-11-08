"""Ornith client (UAB DCC gateway) built on the official OpenAI Python SDK."""
from __future__ import annotations

import logging
import time
from typing import Any, Protocol

import openai
from openai import AsyncOpenAI

from app import errors
from app.config import Settings
from app.llm.parsing import LLMReply, ToolCall, arguments_to_text, extract_text_tool_calls, new_call_id, strip_reasoning

log = logging.getLogger("safia.llm")


class LLMClient(Protocol):
    async def complete(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]] | None,
                       tool_choice: str = "auto") -> LLMReply: ...


class OrnithClient:
    def __init__(self, settings: Settings, http_client: Any | None = None) -> None:
        if not settings.has_api_key:
            raise errors.SafiaError("LLM_NOT_CONFIGURED", "UTH_KEY is not set in backend/.env.", 503)
        self._s = settings
        self._client = AsyncOpenAI(
            api_key=settings.uth_key.get_secret_value(),
            base_url=settings.llm_base_url,
            timeout=settings.llm_timeout_s,
            max_retries=settings.llm_max_retries,
            http_client=http_client,  # injectable for wire-level tests
        )
        # Optional parameters the gateway turned out not to support (learned at runtime).
        self._unsupported: set[str] = set() if settings.llm_parallel_tool_calls else {"parallel_tool_calls"}

    async def complete(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]] | None,
                       tool_choice: str = "auto") -> LLMReply:
        kwargs: dict[str, Any] = {
            "model": self._s.llm_model,
            "messages": messages,
            "temperature": self._s.llm_temperature,
            "max_tokens": self._s.llm_max_tokens,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = tool_choice
            if tool_choice != "none":
                kwargs["parallel_tool_calls"] = True
        for p in self._unsupported:
            kwargs.pop(p, None)
        t0 = time.perf_counter()
        resp = None
        for _ in range(3):
            try:
                resp = await self._client.chat.completions.create(**kwargs)
                break
            except openai.BadRequestError as e:
                text = str(e).lower()
                culprit = next((p for p in ("parallel_tool_calls", "tool_choice") if p in kwargs and p in text), None)
                if culprit is None:
                    log.error("LLM bad request: %s", type(e).__name__)
                    raise errors.llm_unavailable("The language model rejected the request.") from e
                log.warning("Gateway rejected %s; retrying without it", culprit)
                self._unsupported.add(culprit)
                kwargs.pop(culprit)
            except Exception as e:  # noqa: BLE001 - mapped below
                raise _map_error(e) from e
        if resp is None:
            raise errors.llm_unavailable("The language model rejected the request.")
        log.info("llm call model=%s tools=%d %.0fms", self._s.llm_model, len(tools or []),
                 (time.perf_counter() - t0) * 1000)
        return self._normalise(resp, tools)

    def _normalise(self, resp: Any, tools: list[dict[str, Any]] | None) -> LLMReply:
        if not getattr(resp, "choices", None):
            raise errors.llm_unavailable("The language model returned no answer.")
        choice = resp.choices[0]
        msg = choice.message
        calls: list[ToolCall] = []
        for tc in (getattr(msg, "tool_calls", None) or []):
            fn = getattr(tc, "function", None)
            if fn is None or not getattr(fn, "name", None):
                continue
            calls.append(ToolCall(id=getattr(tc, "id", None) or new_call_id(), name=fn.name,
                                  arguments=arguments_to_text(fn.arguments)))
        content = strip_reasoning(getattr(msg, "content", None))
        parsed = False
        if not calls and tools and self._s.llm_text_tool_call_fallback and content:
            known = {t["function"]["name"] for t in tools}
            calls, content = extract_text_tool_calls(content, known)
            parsed = bool(calls)
            if parsed:
                log.warning("tool calls parsed from text content (gateway returned no tool_calls)")
        return LLMReply(content=content, tool_calls=calls, finish_reason=getattr(choice, "finish_reason", None),
                        parsed_from_text=parsed)


def _map_error(e: Exception) -> errors.SafiaError:
    # Only exception class names are logged: messages can echo request headers.
    log.error("LLM call failed: %s", type(e).__name__)
    if isinstance(e, errors.SafiaError):
        return e
    if isinstance(e, openai.APITimeoutError):
        return errors.llm_timeout()
    if isinstance(e, openai.RateLimitError):
        return errors.rate_limited()
    if isinstance(e, (openai.AuthenticationError, openai.PermissionDeniedError)):
        return errors.llm_auth()
    if isinstance(e, openai.NotFoundError):
        return errors.llm_unavailable("Model or endpoint not found. Check LLM_MODEL and LLM_BASE_URL.")
    return errors.llm_unavailable()
