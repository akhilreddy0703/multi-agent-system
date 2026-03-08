"""RAG Agent: FAQ answers from vector database with fallback."""

from agno.agent import Agent
from agno.models.openai import OpenAIChat

from src.knowledge.loader import get_faq_knowledge

RAG_INSTRUCTIONS = [
    "You answer only from the retrieved knowledge base context.",
    "If the answer is not found in the retrieved context, respond with: "
    "'I could not find an answer to that in the FAQ. Please rephrase or ask something else.'",
    "Do not make up information. Only use the provided context.",
]

_model = OpenAIChat(id="gpt-4.1-mini")


def get_rag_agent() -> Agent:
    """Build RAG agent with FAQ knowledge and strict context-only answers."""
    knowledge = get_faq_knowledge()
    return Agent(
        name="RAG Agent",
        role="FAQ assistant. You answer questions using only the retrieved FAQ context.",
        model=_model,
        knowledge=knowledge,
        search_knowledge=True,
        instructions=RAG_INSTRUCTIONS,
        markdown=True,
    )
