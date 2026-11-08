"""In-memory conversation and pending-turn store (single-process MVP).

Restarting the server forgets conversations; clients may then resend ``history``
to seed a new one. Replace with Redis or SQLite if several workers are needed.
"""
from __future__ import annotations

import asyncio
import time
import uuid
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any

from app.tools.registry import CheckedCall


@dataclass
class TurnState:
    turn_id: str
    start_index: int  # index in Conversation.messages where this turn's user message sits
    user_text: str
    language: str
    round: int = 0  # device rounds performed
    llm_calls: int = 0
    # Filled while waiting for Android:
    expected: dict[str, CheckedCall] = field(default_factory=dict)
    call_order: list[str] = field(default_factory=list)
    prefilled: dict[str, str] = field(default_factory=dict)  # call_id -> tool message content
    created_at: float = field(default_factory=time.monotonic)
    # Collected during the turn:
    used: list[tuple[str, dict[str, Any], dict[str, Any] | None]] = field(default_factory=list)  # name, args, presented
    failed_tools: list[str] = field(default_factory=list)


@dataclass
class Conversation:
    id: str
    messages: list[dict[str, Any]] = field(default_factory=list)
    tool_outputs: list[Any] = field(default_factory=list)  # presented outputs, for grounding
    context: dict[str, Any] = field(default_factory=dict)
    pending: TurnState | None = None
    updated_at: float = field(default_factory=time.monotonic)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    def user_texts(self) -> list[str]:
        return [m["content"] for m in self.messages if m.get("role") == "user" and isinstance(m.get("content"), str)]


def new_conversation_id() -> str:
    return "conv_" + uuid.uuid4().hex


def new_turn_id() -> str:
    return "turn_" + uuid.uuid4().hex


class ConversationStore:
    def __init__(self, ttl_s: int, turn_ttl_s: int, max_conversations: int) -> None:
        self._convs: OrderedDict[str, Conversation] = OrderedDict()
        self._turns: dict[str, str] = {}
        self.ttl_s = ttl_s
        self.turn_ttl_s = turn_ttl_s
        self.max = max_conversations

    def _evict(self) -> None:
        now = time.monotonic()
        for cid in [c for c, v in self._convs.items() if now - v.updated_at > self.ttl_s]:
            self._drop(cid)
        while len(self._convs) > self.max:
            self._drop(next(iter(self._convs)))

    def _drop(self, cid: str) -> None:
        conv = self._convs.pop(cid, None)
        if conv and conv.pending:
            self._turns.pop(conv.pending.turn_id, None)

    def get_or_create(self, cid: str | None) -> tuple[Conversation, bool]:
        self._evict()
        if cid and cid in self._convs:
            conv = self._convs[cid]
            self._convs.move_to_end(cid)
            conv.updated_at = time.monotonic()
            return conv, False
        conv = Conversation(id=cid or new_conversation_id())
        self._convs[conv.id] = conv
        return conv, True

    def register_turn(self, conv: Conversation, turn: TurnState) -> None:
        conv.pending = turn
        self._turns[turn.turn_id] = conv.id

    def release_turn(self, conv: Conversation) -> None:
        if conv.pending:
            self._turns.pop(conv.pending.turn_id, None)
        conv.pending = None

    def by_turn(self, turn_id: str) -> Conversation | None:
        cid = self._turns.get(turn_id)
        return self._convs.get(cid) if cid else None

    def turn_expired(self, turn: TurnState) -> bool:
        return time.monotonic() - turn.created_at > self.turn_ttl_s
