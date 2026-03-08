# Local development setup

Run the backend and UI on your machine with **uv**, **Milvus** (Docker), and **Todo MCP**.

## Prerequisites

| Requirement | Purpose |
|-------------|---------|
| **Python 3.11+** | Runtime |
| **[uv](https://docs.astral.sh/uv/)** | Install: `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| **Docker & Docker Compose** | Milvus only |
| **Node 18+ / pnpm** | agent-ui (optional; can use API only) |
| **OpenAI API key** | LLM + embeddings |

## 1. Install and configure

```bash
cd multi-agent-system
uv sync
cp .env.example .env
```

Edit `.env`: set **`OPENAI_API_KEY`** and **`JWT_SECRET`**. Optional: `MILVUS_URI`, `TODO_MCP_URL`, `AGENT_UI_URL`, `AGENTOS_API_URL`.

## 2. Start Milvus (RAG)

```bash
docker compose up -d etcd minio milvus-standalone
```

Wait until healthy (~1–2 min). Check: `docker compose ps`.

## 3. Start Todo MCP (optional)

In a **separate terminal**:

```bash
uv run python -m src.tools.todo_mcp_server
```

Listens at **http://localhost:8001/mcp**. Without it, Todo tools are unavailable.

## 4. Start the backend

```bash
uv run uvicorn src.main:app --host 0.0.0.0 --port 8000
```

You should see: `Lifespan: FAQ knowledge ready`, `App: AgentOS ready`. Backend: **http://localhost:8000**.

**FAQ data:** Place **`data/faq.xlsx`** (or CSV) for RAG. Loaded on startup; re-ingestion is skipped if unchanged (`skip_if_exists=True`).

## 5. Run the UI (optional)

```bash
cd agent-ui
cp .env.local.example .env.local   # NEXT_PUBLIC_AGENTOS_ENDPOINT=http://localhost:8000
pnpm install && pnpm dev
```

Open **http://localhost:3000**. Sign in via **http://localhost:8000/login** (demo / password); you are redirected to the UI with token, endpoint, and **orchestrator** team set.

## 6. Use the API

Get a JWT:

```bash
curl -s -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=demo&password=password"
```

Use the `access_token` with `Authorization: Bearer <token>` for `/chat`, `/chat/stream`, `/weather`, `/todos`. Interactive docs: **http://localhost:8000/docs**.

## Sample queries

| Intent | Example (UI or API) |
|--------|---------------------|
| **FAQ / RAG** | "What are the company working hours?" |
| **Weather** | "What is the weather in London?" |
| **Todos** | "Create a task called Buy milk" / "List all my tasks" |

## See also

- [UI_SETUP.md](UI_SETUP.md) — Detailed agent-ui connection and troubleshooting
- [MANUAL_API_TEST.md](MANUAL_API_TEST.md) — Step-by-step curl for all endpoints
- [TESTING.md](TESTING.md) — E2E and unit tests
