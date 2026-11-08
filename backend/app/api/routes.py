from __future__ import annotations

from fastapi import APIRouter, Request

from app.api import schemas as s

router = APIRouter()


@router.get("/health")
async def health(request: Request) -> dict:
    settings = request.app.state.settings
    return {"status": "ok", "model": settings.llm_model, "llm_configured": settings.has_api_key}


@router.post("/v1/chat", response_model=s.ChatResponse,
             responses={400: {"model": s.ErrorResponse}, 422: {"model": s.ErrorResponse},
                        502: {"model": s.ErrorResponse}, 504: {"model": s.ErrorResponse}})
async def chat(body: s.ChatRequest, request: Request) -> s.ToolCallsResponse | s.FinalResponse:
    return await request.app.state.orchestrator.handle_message(body)


@router.post("/v1/chat/{turn_id}/tool-results", response_model=s.ChatResponse,
             responses={404: {"model": s.ErrorResponse}, 410: {"model": s.ErrorResponse},
                        422: {"model": s.ErrorResponse}, 502: {"model": s.ErrorResponse}})
async def tool_results(turn_id: str, body: s.ToolResultsRequest, request: Request) -> s.ToolCallsResponse | s.FinalResponse:
    return await request.app.state.orchestrator.handle_tool_results(turn_id, body)


@router.get("/v1/tools")
async def tools() -> dict:
    """The tool contract Android must implement (same schemas the model sees)."""
    from app.tools.registry import tool_schemas
    return {"tools": tool_schemas()}
