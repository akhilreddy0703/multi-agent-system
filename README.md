# Multi-Agent RAG System

Multi-agent backend that routes user queries to **RAG (FAQ)**, **weather**, and **Todo** agents. Built with **Agno**, **FastAPI**, and **FastMCP**. JWT-protected APIs; optional chat UI via [agent-ui](https://github.com/agno-agi/agent-ui).

---

## Prerequisites

| Requirement | Purpose |
|-------------|---------|
| **Python 3.11+** | Runtime |
| **[uv](https://docs.astral.sh/uv/)** | Install: `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| **Docker & Docker Compose** | Milvus (local) or full stack (containers) |
| **OpenAI API key** | LLM + embeddings |

---

## Architecture

```
                    ┌─────────────────────────────────────────────────────────┐
                    │                     User / Browser                        │
                    └───────────────────────────┬─────────────────────────────┘
                                                │
              ┌─────────────────────────────────┼─────────────────────────────────┐
              │                                 │                                 │
              ▼                                 ▼                                 │
     ┌─────────────────┐              ┌─────────────────┐                        │
     │   agent-ui      │              │  POST /chat     │                         │
     │   (Next.js)     │◄─────────────│  /chat/stream   │                         │
     │   port 3000     │   redirect   │  /auth/login    │                         │
     └────────┬────────┘   + JWT     └────────┬────────┘                         │
              │                                │                                  │
              │  JWT + AgentOS API             │                                  │
              └────────────────────────────────┼──────────────────────────────────┘
                                                │
                                                ▼
                    ┌───────────────────────────────────────────────────────────┐
                    │  FastAPI + AgentOS (port 8000)                             │
                    │  • JWT middleware  • CORS  • /login → redirect to agent-ui │
                    │  • Lifespan: load FAQ into Milvus                          │
                    └───────────────────────────┬─────────────────────────────────┘
                                                │
                                                ▼
                    ┌───────────────────────────────────────────────────────────┐
                    │  Orchestrator Team (route mode)                            │
                    │  Routes to RAG Agent or Tool Agent by intent               │
                    └───────────────┬─────────────────────┬─────────────────────┘
                                    │                     │
                    ┌───────────────▼──────────┐  ┌───────▼──────────────────────┐
                    │  RAG Agent               │  │  Tool Agent                    │
                    │  • FAQ from Milvus       │  │  • Weather tool                │
                    │  • search_knowledge      │  │  • Todo MCP (create/list/…)   │
                    └───────────────┬──────────┘  └───────┬──────────────────────┘
                                    │                     │
                    ┌───────────────▼──────────┐  ┌───────▼──────────────────────┐
                    │  Milvus (vector DB)      │  │  Todo MCP server (port 8001)  │
                    │  • faq.xlsx ingested     │  │  • FastMCP streamable-http     │
                    └──────────────────────────┘  └───────────────────────────────┘
```

**Flow:** User hits the login page or agent-ui → gets a JWT → backend (FastAPI + AgentOS) runs the **Orchestrator** team. The orchestrator routes to the **RAG Agent** (Milvus-backed FAQ) or **Tool Agent** (weather + Todo MCP). Responses stream back via `/chat/stream` or AgentOS team runs.

---

## Getting started

| How you want to run | Doc |
|---------------------|-----|
| **Local development** (uv, Milvus in Docker, optional Todo MCP + agent-ui) | [docs/LOCAL_SETUP.md](docs/LOCAL_SETUP.md) |
| **Containers** (Docker Compose: backend + UI + Milvus + Todo MCP) | [docs/DOCKER_SETUP.md](docs/DOCKER_SETUP.md) |
| **Testing** (E2E, pytest, manual API/UI) | [docs/TESTING.md](docs/TESTING.md) |

---

## Project structure

```
├── pyproject.toml, docker-compose.yml, Dockerfile, .dockerignore
├── data/faq.xlsx, data/sample_queries.json
├── src/
│   ├── main.py          # FastAPI, JWT, lifespan, AgentOS
│   ├── config.py        # Settings from env
│   ├── agents/          # Orchestrator, RAG agent, Tool agent
│   ├── tools/           # Weather, Todo FastMCP server
│   ├── knowledge/       # Milvus + FAQ loader
│   ├── prompts/         # Agent and orchestrator prompts
│   ├── auth/, routes/
├── agent-ui/             # Chat UI (Next.js)
├── tests/                # e2e_test.py, test_*.py
└── docs/                 # LOCAL_SETUP, DOCKER_SETUP, TESTING, UI_SETUP, MANUAL_API_TEST, NGROK
```

---

## Tech stack

- **Agno** — Orchestrator (Team route mode), RAG and tool agents  
- **OpenAI** — gpt-4.1-mini, text-embedding-3-small  
- **Milvus** — Vector store for FAQ RAG  
- **FastMCP** — Todo server (streamable-http, port 8001)  
- **FastAPI + JWT** — Protected routes; login at `/auth/login`  
- **Loguru** — Logging  

---

## Troubleshooting

| Issue | Check |
|-------|--------|
| **Can't open login or UI** | Use **http://** (not https). Backend: http://localhost:8000/login. UI: http://localhost:3000. Docker: `docker compose ps` — app and agent-ui healthy. |
| **401** | Get JWT from `POST /auth/login`, send `Authorization: Bearer <token>`. |
| **RAG empty** | Milvus up? FAQ at `data/faq.xlsx`? Logs: "FAQ knowledge ready". |
| **Todo not working** | Todo MCP on 8001 (local: `uv run python -m src.tools.todo_mcp_server`; Docker: todo-mcp healthy). |
| **UI red status** | Endpoint http://localhost:8000; token from /login; refresh sidebar. |

More detail in [LOCAL_SETUP.md](docs/LOCAL_SETUP.md), [DOCKER_SETUP.md](docs/DOCKER_SETUP.md), and [UI_SETUP.md](docs/UI_SETUP.md).

---

## License

MIT. See [LICENSE](LICENSE). For open-source checklist and practices (contributing, security, licensing), see [docs/OPEN_SOURCE.md](docs/OPEN_SOURCE.md).
