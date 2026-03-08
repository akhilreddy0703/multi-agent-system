"""RAG Agent: FAQ answers from Milvus vector knowledge base."""

from agno.agent import Agent
from agno.models.openai import OpenAIChat

from src.knowledge.loader import get_faq_knowledge
from src.prompts.prompts import RAG_INSTRUCTIONS, RAG_SYSTEM_PROMPT

_model = OpenAIChat(id="gpt-4.1-mini")


def get_rag_agent() -> Agent:
    return Agent(
        name="RAG Agent",
        role="FAQ assistant. Answer questions using only the retrieved FAQ context.",
        description=RAG_SYSTEM_PROMPT,
        model=_model,
        knowledge=get_faq_knowledge(),
        search_knowledge=True,
        instructions=RAG_INSTRUCTIONS,
        markdown=True,
    )
