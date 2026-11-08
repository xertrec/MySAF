"""FastAPI entry point.

Run (from the ``backend`` folder):  uvicorn app.main:app --host 0.0.0.0 --port 8000
"""
from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.routes import router
from app.config import Settings, get_settings
from app.conversation.orchestrator import Orchestrator
from app.conversation.store import ConversationStore
from app.errors import SafiaError
from app.llm.client import LLMClient, OrnithClient


class _RedactSecret(logging.Filter):
    """Last line of defence: blank out the API key if it ever reaches a log line."""

    def __init__(self, secret: str) -> None:
        super().__init__()
        self._secret = secret

    def filter(self, record: logging.LogRecord) -> bool:
        if self._secret and len(self._secret) >= 8:
            msg = record.getMessage()
            if self._secret in msg:
                record.msg = msg.replace(self._secret, "***")
                record.args = ()
        return True


def _setup_logging(settings: Settings) -> None:
    logging.basicConfig(level=settings.log_level.upper(),
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    # The HTTP client logs full request lines at DEBUG; keep it quiet.
    for noisy in ("httpx", "httpx2", "httpcore", "openai"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    f = _RedactSecret(settings.uth_key.get_secret_value())
    for h in logging.getLogger().handlers:
        h.addFilter(f)


class _LazyOrnith:
    """Creates the real client on first use so the app (and /health) start without a key."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client: OrnithClient | None = None

    async def complete(self, messages, tools, tool_choice="auto"):  # type: ignore[no-untyped-def]
        if self._client is None:
            self._client = OrnithClient(self._settings)
        return await self._client.complete(messages, tools, tool_choice)


def create_app(settings: Settings | None = None, llm: LLMClient | None = None) -> FastAPI:
    settings = settings or get_settings()
    _setup_logging(settings)
    app = FastAPI(title="SAFIA backend", version="0.1.0",
                  description="Conversational assistant of mySAF. Data tools run on the Android device.")
    store = ConversationStore(settings.conversation_ttl_s, settings.turn_ttl_s, settings.max_conversations)
    app.state.settings = settings
    app.state.store = store
    app.state.orchestrator = Orchestrator(settings, llm or _LazyOrnith(settings), store)
    app.include_router(router)

    @app.exception_handler(SafiaError)
    async def _safia_error(_: Request, exc: SafiaError) -> JSONResponse:
        return JSONResponse(status_code=exc.status, content={"error": {
            "code": exc.code, "message": exc.message, "retryable": exc.retryable, "details": exc.details}})

    @app.exception_handler(RequestValidationError)
    async def _validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        details = [{"loc": ".".join(str(x) for x in e.get("loc", ())), "msg": e.get("msg")} for e in exc.errors()[:10]]
        return JSONResponse(status_code=422, content={"error": {
            "code": "BAD_REQUEST", "message": "Request body does not match the API contract.",
            "retryable": False, "details": {"errors": details}}})

    @app.exception_handler(Exception)
    async def _unexpected(_: Request, exc: Exception) -> JSONResponse:
        logging.getLogger("safia").exception("Unhandled error: %s", type(exc).__name__)
        return JSONResponse(status_code=500, content={"error": {
            "code": "INTERNAL", "message": "Unexpected server error.", "retryable": True, "details": {}}})

    return app


app = create_app()
