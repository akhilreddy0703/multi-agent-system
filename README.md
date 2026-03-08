# Multi-Agent RAG System with FastMCP Integration

A multi-agent AI system built with **Agno**, **FastAPI**, and **FastMCP** that answers FAQ queries via RAG, provides weather information, and manages tasks through a Todo MCP server. All APIs are protected with JWT authentication.

## Features

- **Parent Agent (Orchestrator)**: Routes user queries to the appropriate specialist using Agno Team (route mode).
- **RAG Agent**: Answers FAQ questions using a Milvus vector database built from XLSX/CSV data; responds only from retrieved context with a fallback when no answer is found.
- **Tool Agent**: Handles weather (mock) and Todo CRUD via a FastMCP server.
- **APIs**: `POST /chat`, `GET /weather`, Todo CRUD (`POST/GET/PUT/DELETE /todos`), all with JWT auth.
- **Docker**: Optional Docker Compose setup for Milvus, Todo MCP server, and the app.

## Tech Stack

- **Framework**: Agno (multi-agent, Team route mode)
- **LLM**: OpenAI `gpt-4.1-mini`
- **Embeddings**: OpenAI `text-embedding-3-small`
- **Vector DB**: Milvus (Docker or `http://localhost:19530`)
- **Todo**: FastMCP server (streamable-http on port 8001)
- **Auth**: JWT (HS256) via Agno `JWTMiddleware`
- **Package manager**: uv

## Project Structure

```
├── pyproject.toml
├── docker-compose.yml
├── Dockerfile
├── data/
│   └── faq.xlsx          # Your FAQ data (XLSX or CSV)
├── src/
│   ├── main.py           # FastAPI app, JWT, lifespan, routes
│   ├── config.py         # Settings (env)
│   ├── auth/routes.py    # POST /auth/login
│   ├── agents/           # Orchestrator, RAG agent, Tool agent
│   ├── tools/            # Weather tool, Todo FastMCP server
│   ├── knowledge/        # Milvus + XLSX loader
│   └── routes/           # /chat, /weather, /todos
└── tests/                # Pytest happy-path tests
```

## Setup

### 1. Clone and install (uv)

```bash
cd multi-agent-system
uv sync
```

### 2. Environment

Copy `.env.example` to `.env` and set:

```bash
cp .env.example .env
```

Required:

- `OPENAI_API_KEY` – OpenAI API key (for LLM and embeddings)
- `JWT_SECRET` – Secret for JWT (e.g. a long random string for HS256)

Optional:

- `MILVUS_URI` – Default `http://localhost:19530`
- `WEATHER_CITY` – Default city for weather (default: London)
- `TODO_MCP_URL` – Todo MCP server URL (default: `http://localhost:8001/mcp`)

### 3. FAQ data

Place your FAQ file at `data/faq.xlsx` (or CSV). The app loads it into Milvus on startup. If the file is missing, the RAG agent still runs but has no documents to retrieve.

### 4. Run Milvus (for RAG)

**Option A – Docker Compose (Milvus + Todo + App)**

```bash
docker compose up -d
# App: http://localhost:8000
# Todo MCP: http://localhost:8001/mcp
# Milvus: localhost:19530
```

**Option B – Milvus only (then run app locally)**

```bash
docker compose up -d etcd minio milvus-standalone
# Then start Todo MCP and app locally (see below).
```

### 5. Run Todo MCP server (if not using Docker)

```bash
uv run python -m src.tools.todo_mcp_server
# Listens on http://localhost:8001/mcp
```

### 6. Run the app locally

```bash
uv run uvicorn src.main:app --host 0.0.0.0 --port 8000
# Or: uv run python -c "from src.main import main; main()"
```

API docs: http://localhost:8000/docs

## API Usage

### 1. Login (get JWT)

```bash
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=demo&password=password"
```

Response: `{"access_token":"<JWT>","token_type":"bearer"}`

Demo credentials: `username=demo`, `password=password`.

### 2. Chat (orchestrator)

```bash
export TOKEN="<access_token from login>"
curl -X POST "http://localhost:8000/chat" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the weather in London?"}'
```

### 3. Weather

```bash
curl "http://localhost:8000/weather?city=London" \
  -H "Authorization: Bearer $TOKEN"
```

### 4. Todos (CRUD)

- Create: `POST /todos` with body `{"title": "...", "description": "..."}`
- List: `GET /todos?status=all|open|done`
- Update: `PUT /todos/{task_id}` with body `{"title": "...", "status": "open|done"}`
- Delete: `DELETE /todos/{task_id}`

All require `Authorization: Bearer <token>`.

## Tests

```bash
uv run pytest tests/ -v
```

Uses test JWT secret and does not require a real Milvus or Todo server for the happy-path tests.

## Docker details

- **milvus-standalone**: Milvus 2.4 with etcd and MinIO.
- **todo-mcp**: FastMCP Todo server (streamable-http on 8001).
- **app**: FastAPI app (port 8000), connects to Milvus and Todo MCP via service names.

Ensure `.env` is present when running `docker compose up` so the app has `OPENAI_API_KEY` and `JWT_SECRET`.

## License

MIT.
