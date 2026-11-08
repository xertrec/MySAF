"""Extension point for a later RAG phase (not implemented now).

A future retriever (e.g. over SAF regulations or FAQs) can either:
- implement ``Retriever.context_for`` to add grounded snippets to the system prompt, or
- register a server-side tool in ``app.tools.registry.SERVER_TOOLS``.

Both run inside this backend and need no change to the Android protocol.
"""
from __future__ import annotations

from typing import Protocol


class Retriever(Protocol):
    async def context_for(self, question: str, language: str) -> list[str]: ...


class NullRetriever:
    async def context_for(self, question: str, language: str) -> list[str]:
        return []
