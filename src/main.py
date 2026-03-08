"""FastAPI app: AgentOS-owned orchestrator with MCP, RAG, and JWT auth."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from agno.os import AgentOS
from agno.os.middleware import JWTMiddleware
from agno.tools.mcp import MCPTools, StreamableHTTPClientParams

from src import log_config
from src.agents.orchestrator import build_orchestrator
from src.auth.routes import router as auth_router
from src.config import settings
from src.knowledge.loader import get_faq_knowledge, load_faq_from_path
from src.routes.chat import router as chat_router
from src.routes.todo import router as todo_router
from src.routes.weather import router as weather_router

log = log_config.logger


LOGIN_PAGE_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Sign in | Multi-Agent RAG</title>
  <style>
    * { box-sizing: border-box; }
    body { font-family: system-ui, sans-serif; margin: 0; min-height: 100vh; display: flex; align-items: center; justify-content: center; background: #0f0f12; color: #e4e4e7; }
    .card { background: #18181c; border: 1px solid #2a2a30; border-radius: 12px; padding: 2rem; width: 100%; max-width: 360px; }
    h1 { margin: 0 0 0.25rem 0; font-size: 1.5rem; }
    .sub { margin: 0 0 1.5rem 0; color: #a1a1aa; font-size: 0.9rem; }
    form { display: flex; flex-direction: column; gap: 1rem; }
    input { padding: 0.75rem 1rem; border: 1px solid #2a2a30; border-radius: 8px; background: #0f0f12; color: #e4e4e7; font-size: 1rem; }
    button { padding: 0.75rem 1rem; background: #6366f1; color: white; border: none; border-radius: 8px; font-size: 1rem; font-weight: 500; cursor: pointer; }
    button:disabled { opacity: 0.6; cursor: not-allowed; }
    .err { color: #f87171; font-size: 0.875rem; min-height: 1.25rem; }
  </style>
</head>
<body>
  <div class="card">
    <h1>Multi-Agent RAG</h1>
    <p class="sub">Sign in to use the chat (agent-ui)</p>
    <form id="f">
      <input type="text" name="username" placeholder="Username" required autocomplete="username" />
      <input type="password" name="password" placeholder="Password" required autocomplete="current-password" />
      <p id="err" class="err" aria-live="polite"></p>
      <button type="submit" id="btn">Sign in</button>
    </form>
  </div>
  <script>
    var agentUiUrl = """ + f'"{settings.agent_ui_url}"' + """;
    var backendUrl = """ + f'"{settings.agentos_api_url.rstrip("/")}"' + """;
    var defaultTeam = "orchestrator";
    document.getElementById("f").onsubmit = async function(e) {
      e.preventDefault();
      var err = document.getElementById("err");
      var btn = document.getElementById("btn");
      err.textContent = "";
      btn.disabled = true;
      try {
        var fd = new FormData(this);
        var r = await fetch("/auth/login", { method: "POST", body: new URLSearchParams(fd) });
        var j = await r.json().catch(function() { return {}; });
        if (!r.ok) { err.textContent = j.detail || "Invalid credentials"; return; }
        var token = j.access_token;
        if (!token) { err.textContent = "No token in response"; return; }
        var hash = "#access_token=" + encodeURIComponent(token) + "&endpoint=" + encodeURIComponent(backendUrl) + "&team=" + encodeURIComponent(defaultTeam);
        window.location.href = agentUiUrl + hash;
      } catch (x) {
        err.textContent = "Network error";
      } finally {
        btn.disabled = false;
      }
    };
  </script>
</body>
</html>
"""


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load FAQ into Milvus on startup; MCP lifecycle is managed by AgentOS."""
    log.info("Lifespan: loading FAQ knowledge into Milvus...")
    try:
        knowledge = get_faq_knowledge()
        await load_faq_from_path(knowledge)
        log.info("Lifespan: FAQ knowledge ready")
    except Exception as e:
        log.warning(f"Lifespan: FAQ load failed, RAG may have no documents error={e}")

    yield


def create_app() -> FastAPI:
    # --- MCP tools (Todo server) ---
    mcp_tools = MCPTools(
        server_params=StreamableHTTPClientParams(url=settings.todo_mcp_url),
        transport="streamable-http",
    )
    log.info(f"App: MCPTools configured for todo_mcp_url={settings.todo_mcp_url}")

    # --- Orchestrator team (RAG + Tool agents, MCP connected) ---
    # AgentOS discovers MCPTools inside the team and manages connect/close via mcp_lifespan.
    orchestrator = build_orchestrator(mcp_tools=mcp_tools)
    log.info("App: orchestrator team built with RAG and Tool agents")

    # --- FastAPI base app ---
    base_app = FastAPI(title="Multi-Agent RAG API", version="0.1.0", lifespan=lifespan)

    base_app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.agent_ui_url.rstrip("/")],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    base_app.add_middleware(
        JWTMiddleware,
        verification_keys=[settings.jwt_secret],
        algorithm="HS256",
        excluded_route_paths=["/", "/auth/login", "/login", "/docs", "/redoc", "/openapi.json"],
        validate=True,
    )

    base_app.include_router(auth_router)
    base_app.include_router(chat_router)
    base_app.include_router(weather_router)
    base_app.include_router(todo_router)

    @base_app.get("/", include_in_schema=False)
    def root():
        """Redirect root to the login page."""
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/login")

    @base_app.get("/login", response_class=HTMLResponse, include_in_schema=False)
    def login_page():
        """Login page — on success redirects to agent-ui with JWT in URL hash."""
        return LOGIN_PAGE_HTML

    # --- AgentOS: owns the team, manages MCP lifecycle, mounts /teams/* routes ---
    agent_os = AgentOS(
        base_app=base_app,
        teams=[orchestrator],
        on_route_conflict="preserve_base_app",
    )
    app = agent_os.get_app()

    # Expose orchestrator on app.state for /chat and /chat/stream routes
    app.state.orchestrator = orchestrator
    log.info("App: AgentOS ready, orchestrator available on app.state")

    return app


app = create_app()


def main() -> None:
    import uvicorn
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    main()
