"""Parent Agent (orchestrator): routes to RAG or Tool agent."""

from typing import Any

from agno.models.openai import OpenAIChat
from agno.team import Team

from src.agents.rag_agent import get_rag_agent
from src.agents.tool_agent import get_tool_agent

ORCHESTRATOR_INSTRUCTIONS = [
    "You are the orchestrator. Route the user's request to the appropriate specialist.",
    "Route FAQ and knowledge questions to the RAG Agent (FAQ assistant).",
    "Route weather questions and todo/task management requests to the Tool Agent.",
    "Return the chosen agent's response directly to the user.",
]

_model = OpenAIChat(id="gpt-4.1-mini")


def get_orchestrator(mcp_tools: Any = None) -> Team:
    """Build the parent Team that routes to RAG and Tool agents."""
    rag_agent = get_rag_agent()
    tool_agent = get_tool_agent(mcp_tools=mcp_tools)
    return Team(
        name="Orchestrator",
        model=_model,
        respond_directly=True,
        members=[rag_agent, tool_agent],
        instructions=ORCHESTRATOR_INSTRUCTIONS,
        markdown=True,
    )
