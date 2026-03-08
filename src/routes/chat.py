"""Chat API: POST /chat via orchestrator."""

from fastapi import APIRouter, Request
from pydantic import BaseModel

router = APIRouter(tags=["chat"])


class ChatRequest(BaseModel):
    query: str


class ChatResponse(BaseModel):
    response: str


@router.post("/chat", response_model=ChatResponse)
async def chat(request: Request, body: ChatRequest):
    """Route the query through the parent agent and return the response."""
    orchestrator = getattr(request.app.state, "orchestrator", None)
    if orchestrator is None:
        return ChatResponse(
            response="Orchestrator not available. Ensure the app has started correctly."
        )
    run_response = await orchestrator.arun(body.query)
    content = run_response.content if hasattr(run_response, "content") else str(run_response)
    return ChatResponse(response=content or "")
