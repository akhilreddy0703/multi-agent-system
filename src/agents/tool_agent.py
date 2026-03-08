"""Tool Agent: weather and FastMCP Todo tools."""

from typing import Any

from agno.agent import Agent
from agno.models.openai import OpenAIChat

from src.prompts.prompts import TOOL_AGENT_INSTRUCTIONS, TOOL_AGENT_SYSTEM_PROMPT
from src.tools.weather import get_weather

_model = OpenAIChat(id="gpt-4.1-mini")


def get_tool_agent(mcp_tools: Any = None) -> Agent:
    tools: list[Any] = [get_weather]
    if mcp_tools is not None:
        tools.append(mcp_tools)
    return Agent(
        name="Tool Agent",
        role="Specialist for weather lookups and todo task management.",
        description=TOOL_AGENT_SYSTEM_PROMPT,
        model=_model,
        tools=tools,
        instructions=TOOL_AGENT_INSTRUCTIONS,
        markdown=True,
    )
