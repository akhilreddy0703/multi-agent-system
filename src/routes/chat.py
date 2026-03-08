"""Chat API: POST /chat and POST /chat/stream via orchestrator."""

import json

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from src.log_config import logger as log

router = APIRouter(tags=["chat"])


class ChatRequest(BaseModel):
    query: str


class ChatStreamRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    response: str


def _sse_message(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


async def _stream_events(message: str, orchestrator):
    try:
        async for event in orchestrator.arun(message, stream=True, stream_events=True):
            ev = getattr(event, "event", None)
            content = getattr(event, "content", None)
            if ev is None:
                continue
            ev_str = str(ev)
            if ev_str == "TeamRunContent" and content:
                yield _sse_message("run_content", {"content": content})
            elif ev_str == "TeamRunContentCompleted":
                yield _sse_message("run_content_completed", {})
            elif ev_str == "TeamRunCompleted":
                yield _sse_message("run_completed", {"content": content or ""})
            elif ev_str == "TeamRunStarted":
                yield _sse_message("run_started", {})
            elif "ToolCallStarted" in ev_str or ev_str == "TeamToolCallStarted":
                tool_name = getattr(event, "tool_name", None) or getattr(getattr(event, "tool_call", None), "name", None) or "tool"
                log.debug(f"Chat stream tool_call_started tool={tool_name}")
                yield _sse_message("tool_call_started", {"tool": tool_name})
            elif "ToolCallCompleted" in ev_str or ev_str == "TeamToolCallCompleted":
                tool_name = getattr(event, "tool_name", None) or getattr(getattr(event, "tool_call", None), "name", None) or "tool"
                result = getattr(event, "result", None)
                result_summary = str(result)[:200] if result is not None else ""
                yield _sse_message("tool_call_completed", {"tool": tool_name, "result_summary": result_summary})
            elif "RunError" in ev_str or ev_str == "TeamRunError":
                yield _sse_message("error", {"detail": str(getattr(event, "content", event))})
    except Exception as e:
        yield _sse_message("error", {"detail": str(e)})


@router.post("/chat", response_model=ChatResponse)
async def chat(request: Request, body: ChatRequest):
    """Route the query through the parent agent and return the response."""
    log.info(f"Chat request query={body.query[:80]}{'...' if len(body.query) > 80 else ''}")
    orchestrator = getattr(request.app.state, "orchestrator", None)
    if orchestrator is None:
        log.error("Chat: orchestrator not available")
        return ChatResponse(
            response="Orchestrator not available. Ensure the app has started correctly."
        )
    run_response = await orchestrator.arun(body.query)
    content = run_response.content if hasattr(run_response, "content") else str(run_response)
    out = content or ""
    log.info(f"Chat response length={len(out)}")
    return ChatResponse(response=out)


@router.post("/chat/stream")
async def chat_stream(request: Request, body: ChatStreamRequest):
    """Stream orchestrator response as SSE. Requires JWT."""
    log.info(f"Chat stream request message={body.message[:80]}{'...' if len(body.message) > 80 else ''}")
    orchestrator = getattr(request.app.state, "orchestrator", None)
    if orchestrator is None:
        async def _err():
            yield _sse_message("error", {"detail": "Orchestrator not available."})
        return StreamingResponse(
            _err(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )
    return StreamingResponse(
        _stream_events(body.message, orchestrator),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"},
    )
