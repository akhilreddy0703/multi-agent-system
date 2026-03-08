"""FastAPI app: JWT auth, routes, orchestrator with MCP and FAQ loading."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from agno.os.middleware import JWTMiddleware

from src.agents.orchestrator import get_orchestrator
from src.auth.routes import router as auth_router
from src.config import settings
from src.knowledge.loader import get_faq_knowledge, load_faq_from_path
from src.routes.chat import router as chat_router
from src.routes.todo import router as todo_router
from src.routes.weather import router as weather_router

# Try Agno MCPTools for Todo; if import or connect fails, orchestrator runs without Todo
try:
    from agno.tools.mcp import MCPTools
    _HAS_MCP = True
except Exception:
    _HAS_MCP = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Connect MCP (optional), load FAQ into Milvus, create orchestrator."""
    mcp_tools = None
    if _HAS_MCP and getattr(settings, "todo_mcp_url", None):
        try:
            mcp = MCPTools(transport="streamable-http", url=settings.todo_mcp_url)
            await mcp.connect()
            mcp_tools = mcp
            app.state.mcp_tools = mcp
        except Exception:
            app.state.mcp_tools = None
    else:
        app.state.mcp_tools = None

    try:
        knowledge = get_faq_knowledge()
        await load_faq_from_path(knowledge)
    except Exception:
        pass  # Milvus or file may not be available

    app.state.orchestrator = get_orchestrator(mcp_tools=mcp_tools)
    yield
    if getattr(app.state, "mcp_tools", None) is not None:
        if hasattr(app.state.mcp_tools, "disconnect"):
            await app.state.mcp_tools.disconnect()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Multi-Agent RAG API",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.add_middleware(
        JWTMiddleware,
        verification_keys=[settings.jwt_secret],
        algorithm="HS256",
        excluded_route_paths=["/auth/login", "/docs", "/redoc", "/openapi.json"],
        validate=True,
    )
    app.include_router(auth_router)
    app.include_router(chat_router)
    app.include_router(weather_router)
    app.include_router(todo_router)
    return app


app = create_app()


def main() -> None:
    import uvicorn
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )


if __name__ == "__main__":
    main()
