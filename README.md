# Multi-Agent RAG System

Multi-agent backend that routes queries to **RAG (FAQ)**, **weather**, and **Todo** agents. Built with **Agno**, **FastAPI**, and **FastMCP**. JWT-protected APIs; optional chat UI via [agent-ui](https://github.com/agno-agi/agent-ui).

---

## Prerequisites

| Requirement | Purpose |
|-------------|---------|
| **Python 3.11+** | Runtime |
| **[uv](https://docs.astral.sh/uv/)** | Install: `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| **Docker & Docker Compose** | Milvus (and optionally full stack) |
| **OpenAI API key** | LLM + embeddings |

---

## Setup

### 1. Install and configure

```bash
cd multi-agent-system
uv sync
cp .env.example .env
```

Edit `.env`: set **`OPENAI_API_KEY`** and **`JWT_SECRET`** (at least a long random string). Optional: `MILVUS_URI`, `TODO_MCP_URL`, `AGENT_UI_URL`, `AGENTOS_API_URL`.

### 2. Start dependencies

**Milvus** (required for RAG):

```bash
docker compose up -d etcd minio milvus-standalone
```

Wait until healthy (~1–2 min). **Todo MCP** (for task tools) in a separate terminal:

```bash
uv run python -m src.tools.todo_mcp_server
```

Runs at **http://localhost:8001/mcp**.

### 3. Start the backend

```bash
uv run uvicorn src.main:app --host 0.0.0.0 --port 8000
```

You should see: `Lifespan: FAQ knowledge ready`, `App: AgentOS ready`. Backend: **http://localhost:8000**.

### 4. (Optional) FAQ data

Place **`data/faq.xlsx`** (or CSV) for RAG. Loaded on startup; re-ingestion is skipped if content is unchanged (`skip_if_exists=True`).

---

## Running with the UI

Use the included **agent-ui** for a chat interface. After sign-in, endpoint, token, and **orchestrator** team are set automatically.

### Start the UI

```bash
cd agent-ui
cp .env.local.example .env.local   # optional: NEXT_PUBLIC_AGENTOS_ENDPOINT=http://localhost:8000
pnpm install && pnpm dev
```

Open **http://localhost:3000**.

### Sign in and chat

1. Open **http://localhost:8000/login** (or **http://localhost:8000** → redirects to login).
2. Sign in: **demo** / **password**.
3. You are redirected to agent-ui with token, endpoint (**http://localhost:8000**), and **orchestrator** team pre-filled. Wait for the sidebar to show a green status.
4. Start chatting.

### Sample queries (UI)

| Intent | Example message |
|--------|------------------|
| **FAQ / RAG** | What are the company working hours? |
| | How does BigRock help small businesses? |
| **Weather** | What is the weather in London? |
| **Todos** | Create a task called Buy milk |
| | List all my tasks |

Responses stream in the chat; tool calls appear inline. Full walkthrough: **[docs/UI_SETUP.md](docs/UI_SETUP.md)**.

---

## Running with the API

All endpoints require a JWT except `/`, `/login`, and `/auth/login`.

### Get a token

```bash
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=demo&password=password"
```

Use the `access_token` from the response.

### Sample requests

Set your token:

```bash
export TOKEN="<paste_access_token_here>"
```

**Single response (POST /chat):**

```bash
curl -X POST "http://localhost:8000/chat" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the weather in London?"}'
```

**Streaming (POST /chat/stream):**

```bash
curl -X POST "http://localhost:8000/chat/stream" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "List my tasks"}' \
  --no-buffer
```

### Sample queries (API)

| Intent | Example `query` or `message` |
|--------|------------------------------|
| **FAQ / RAG** | `"What are the company working hours?"` |
| | `"How does BigRock help small businesses?"` |
| **Weather** | `"What is the weather in London?"` |
| **Todos** | `"Create a task called Buy milk"` |
| | `"List all my tasks"` |

**Interactive docs:** **http://localhost:8000/docs** — use **Authorize** with the JWT, then try `/chat`, `/chat/stream`, `/weather`, `/todos`. Manual curl walkthrough: **[docs/MANUAL_API_TEST.md](docs/MANUAL_API_TEST.md)**.

---

## Verify with E2E tests

With backend and Todo MCP running:

```bash
uv run python tests/e2e_test.py
```

Runs auth, AgentOS, weather, Todo MCP, chat (weather/FAQ/todo), streaming, and edge cases. All should **PASS**.

Unit/integration tests:

```bash
uv run pytest tests/ -v
```

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
│   ├── prompts/          # Agent and orchestrator prompts
│   ├── auth/, routes/
├── agent-ui/             # Chat UI (Next.js)
├── tests/                # e2e_test.py, test_*.py
└── docs/                 # UI_SETUP.md, MANUAL_API_TEST.md
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

## Docker: full stack

Run everything in containers (including app and Todo MCP):

```bash
# .env must have OPENAI_API_KEY and JWT_SECRET
docker compose up -d
```

App: **http://localhost:8000**, Todo MCP: 8001, Milvus: 19530.

---

## Troubleshooting

| Issue | Check |
|-------|--------|
| **401 on /chat or /weather** | Get JWT from `POST /auth/login`, send `Authorization: Bearer <token>` |
| **RAG returns nothing** | Milvus up? `docker compose ps`. FAQ at `data/faq.xlsx`? Logs: "FAQ knowledge ready" |
| **Todo does nothing** | Todo MCP running on 8001? `uv run python -m src.tools.todo_mcp_server` |
| **UI: no teams / red status** | Backend on 8000? After login, endpoint and team should be set from redirect; refresh sidebar |
| **E2E fails** | Milvus + Todo MCP + app all running; then `uv run python tests/e2e_test.py` |

---

## License

MIT.
