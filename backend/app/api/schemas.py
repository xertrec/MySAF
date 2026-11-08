"""HTTP request/response models (the contract with Android)."""
from __future__ import annotations

from typing import Any, Literal, Union

from pydantic import BaseModel, ConfigDict, Field

Weekday = Literal["dl", "dt", "dc", "dj", "dv", "ds", "dg"]
Language = Literal["ca", "es", "en"]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class HistoryMessage(_Strict):
    role: Literal["user", "assistant"]
    text: str = Field(min_length=1, max_length=4000)


class ChatContext(_Strict):
    activity_id: str | None = None
    weekdays: list[Weekday] | None = None
    hour: int | None = Field(default=None, ge=0, le=23)
    period: Literal["lectiu", "all"] | None = None


class ChatRequest(_Strict):
    conversation_id: str | None = Field(default=None, pattern=r"^[A-Za-z0-9_-]{8,64}$",
                                        description="Omit on the first message; reuse the returned id afterwards.")
    message: str = Field(min_length=1, max_length=2000)
    locale: Language | None = Field(default=None, description="App UI language; used only as a tie-breaker.")
    history: list[HistoryMessage] = Field(default_factory=list, max_length=40,
                                          description="Optional. Used only if the server no longer knows the conversation.")
    context: ChatContext | None = Field(default=None, description="Optional echo of the last returned context.")


class ToolCallOut(_Strict):
    call_id: str
    name: str
    arguments: dict[str, Any]


class ToolCallsResponse(_Strict):
    status: Literal["tool_calls"] = "tool_calls"
    conversation_id: str
    turn_id: str
    expires_in_s: int
    round: int
    tool_calls: list[ToolCallOut]


class ToolResultItem(_Strict):
    call_id: str = Field(min_length=1, max_length=100)
    ok: bool
    output: dict[str, Any] | None = None
    error: str | None = Field(default=None, max_length=200)


class ToolResultsRequest(_Strict):
    results: list[ToolResultItem] = Field(min_length=1, max_length=10)


class Source(_Strict):
    tool: str
    table: str
    label: str


class Recommendation(_Strict):
    type: Literal["alternatives", "quieter_slots"]
    data: dict[str, Any]


class FinalResponse(_Strict):
    status: Literal["final"] = "final"
    conversation_id: str
    reply: str
    language: Language
    sources: list[Source]
    limitations: list[str]
    recommendation: Recommendation | None = None
    needs_clarification: bool = False
    context: ChatContext


ChatResponse = Union[ToolCallsResponse, FinalResponse]


class ErrorBody(_Strict):
    code: str
    message: str
    retryable: bool = False
    details: dict[str, Any] = Field(default_factory=dict)


class ErrorResponse(_Strict):
    error: ErrorBody
