# Container-based setup (Docker)

Run the full stack (Milvus, Todo MCP, backend, agent-ui) in containers with Docker Compose.

## Prerequisites

- **Docker** and **Docker Compose**
- **OpenAI API key** and **JWT secret** (in `.env`)

## 1. Configure environment

In the project root:

```bash
cp .env.example .env
```

Edit `.env`: set **`OPENAI_API_KEY`** and **`JWT_SECRET`**. Optional for remote/ngrok: `AGENT_UI_URL`, `AGENTOS_API_URL`.

## 2. Start the stack

```bash
docker compose up -d
```

Wait until all services are healthy (~1–2 min): `docker compose ps`.

## 3. Access

| What | URL |
|------|-----|
| **Login page** | http://localhost:8000 or http://localhost:8000/login |
| **Chat UI** | http://localhost:3000 |
| **API docs** | http://localhost:8000/docs |

Sign in with **demo** / **password** at the login page; you are redirected to the Chat UI with endpoint and team set.

## 4. From another machine

Use your host IP instead of `localhost` (e.g. http://192.168.1.10:8000 and http://192.168.1.10:3000). In `.env` set:

- `AGENT_UI_URL=http://<host-ip>:3000`
- `AGENTOS_API_URL=http://<host-ip>:8000`

Then rebuild and restart:

```bash
docker compose build agent-ui app && docker compose up -d
```

## 5. Public HTTPS (ngrok)

To expose login and UI on public URLs: [NGROK.md](NGROK.md).

## Troubleshooting

| Issue | Check |
|-------|--------|
| **Can't open login or UI** | Use **http://** (not https). Ensure `app` and `agent-ui` are healthy: `docker compose ps`. |
| **401 on API** | Get JWT from `POST /auth/login`, send `Authorization: Bearer <token>`. |
| **RAG empty** | Milvus healthy? FAQ at `data/faq.xlsx`? Logs: "FAQ knowledge ready". |
| **Todo not working** | `todo-mcp` container healthy on 8001. |

## How the app gets env vars

The **`.env`** file lives on the **host** (project root). Docker Compose reads it when you run `docker compose up` and **injects** variables (e.g. `OPENAI_API_KEY`) into the container as environment variables. The container does not mount or read the file; it only receives the values. See [README](../README.md#prerequisites).
