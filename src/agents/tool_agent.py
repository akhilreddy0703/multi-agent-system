"""Tool Agent: weather and FastMCP Todo tools."""

from typing import Any

from agno.agent import Agent
from agno.models.openai import OpenAIChat

from src.tools.weather import get_weather

_model = OpenAIChat(id="gpt-4.1-mini")

TOOL_AGENT_INSTRUCTIONS = [
    "You have access to a weather tool and todo task tools (create, list, update, delete).",
    "Use the weather tool when asked about current weather.",
    "Use the todo tools when asked to create, list, update, or delete tasks.",
]


def get_tool_agent(mcp_tools: Any = None) -> Agent:
    """Build Tool Agent with weather and optional MCP Todo tools."""
    tools: list[Any] = [get_weather]
    if mcp_tools is not None:
        tools.append(mcp_tools)
    return Agent(
        name="Tool Agent",
        role="Assistant for weather and task management. Use the available tools.",
        model=_model,
        tools=tools,
        instructions=TOOL_AGENT_INSTRUCTIONS,
        markdown=True,
    )
