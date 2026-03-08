"""Build FAQ knowledge base from XLSX and load into Milvus."""

from pathlib import Path

from agno.knowledge.embedder.openai import OpenAIEmbedder
from agno.knowledge.knowledge import Knowledge
from agno.vectordb.milvus import Milvus

from src.config import settings

COLLECTION_NAME = "faq_knowledge"
DEFAULT_FAQ_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "faq.xlsx"


def get_faq_knowledge(
    collection: str = COLLECTION_NAME,
    uri: str | None = None,
    embedder: OpenAIEmbedder | None = None,
) -> Knowledge:
    """Build and return a Knowledge instance backed by Milvus for FAQ data."""
    vector_db = Milvus(
        collection=collection,
        uri=uri or settings.milvus_uri,
        embedder=embedder or OpenAIEmbedder(),
    )
    return Knowledge(
        name="FAQ Knowledge Base",
        description="FAQ content for RAG retrieval. Answer only from retrieved context.",
        vector_db=vector_db,
    )


async def load_faq_from_path(
    knowledge: Knowledge,
    path: Path | str | None = None,
    name: str = "FAQ",
) -> None:
    """Insert FAQ content from an XLSX (or CSV) file into the knowledge base.

    Uses skip_if_exists=True so the same content is not re-ingested on every
    backend restart. Data is loaded once; subsequent restarts skip if the
    content hash already exists in Milvus. The RAG agent uses this same
    Knowledge (same collection) for retrieval.
    """
    path = path or DEFAULT_FAQ_PATH
    path = Path(path)
    if not path.exists():
        return
    await knowledge.ainsert(name=name, path=str(path), skip_if_exists=True)

