"""Orchestrator: routes user requests to RAG or Tool agent."""

from typing import Any

from agno.models.openai import OpenAIChat
from agno.team import Team
from agno.team.mode import TeamMode

from src.agents.rag_agent import get_rag_agent
from src.agents.tool_agent import get_tool_agent
from src.prompts.prompts import ORCHESTRATOR_INSTRUCTIONS, ORCHESTRATOR_SYSTEM_PROMPT

_model = OpenAIChat(id="gpt-4.1-mini")


def build_orchestrator(mcp_tools: Any = None) -> Team:
    return Team(
        id="orchestrator",
        name="Orchestrator",
        description=ORCHESTRATOR_SYSTEM_PROMPT,
        model=_model,
        mode=TeamMode.route,
        respond_directly=True,
        members=[get_rag_agent(), get_tool_agent(mcp_tools=mcp_tools)],
        instructions=ORCHESTRATOR_INSTRUCTIONS,
        markdown=True,
    )
