# Testing the UI (agent-ui) with the Multi-Agent RAG backend

This guide walks you through connecting **agent-ui** to the backend and verifying FAQ, weather, and Todo flows.

---

## Prerequisites

- Backend and dependencies are set up (see [README](../README.md)).
- **Milvus** is running (for RAG): `docker compose up -d etcd minio milvus-standalone`
- **Todo MCP** is running: `uv run python -m src.tools.todo_mcp_server` (port 8001)
- **Backend app** is running: `uv run uvicorn src.main:app --host 0.0.0.0 --port 8000`

---

## 1. Configure and start agent-ui

From the project root:

```bash
cd agent-ui
cp .env.local.example .env.local
# Edit .env.local if needed: NEXT_PUBLIC_AGENTOS_ENDPOINT=http://localhost:8000
pnpm install
pnpm dev
```

Open **http://localhost:3000**. The sidebar should show the AgentOS endpoint (default for this repo: `http://localhost:8000`). If you still see `http://localhost:7777`, click the endpoint in the sidebar and change it to **http://localhost:8000**, then save.

---

## 2. Sign in and get a token (two options)

### Option A: Login redirect (recommended)

1. In the browser, go to **http://localhost:8000/login** (the backend login page).
2. Sign in with **demo** / **password**.
3. You are redirected to agent-ui with the JWT in the URL (`#access_token=...`). The UI automatically reads this token and clears it from the URL.
4. You should see **Auth Token** in the sidebar showing a masked token (e.g. `********************...`). No copy-paste needed.

### Option B: Manual token

1. Get a JWT from the backend:
   ```bash
   curl -s -X POST "http://localhost:8000/auth/login" \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d "username=demo&password=password"
   ```
2. Copy the `access_token` value from the JSON response.
3. In agent-ui's left sidebar, find **Auth Token**, click it to edit, paste the token, and save.

---

## 3. Connect and select the team

1. In the sidebar, ensure **AgentOS** is set to **http://localhost:8000** (no trailing slash).
2. Click the **refresh** icon next to the endpoint. The UI will call the backend; when the connection is successful, the status dot turns **green** and **Mode** / **Entity** selectors appear.
3. Set **Mode** to **Team**.
4. In **Entity**, select **orchestrator** (the only team in this backend).

---

## 4. Test the agent

Send these in the chat and confirm you get appropriate answers:

| What to test | Example message | What you should see |
|--------------|------------------|----------------------|
| **FAQ / RAG** | "What are the company working hours?" or "How does BigRock help small businesses?" | Answer based on FAQ data (or a fallback if no match). |
| **Weather** | "What is the weather in London?" | Weather tool response (mock temp/condition). |
| **Todo** | "Create a task called Test from UI" then "List all my tasks" | Confirmation of creation, then a list including the new task. |

Responses stream in the chat. Tool calls (weather, todo) appear inline as the agent works.

---

## 5. Troubleshooting

| Issue | What to do |
|-------|------------|
| **Red dot / "Endpoint not active"** | Backend running on 8000? CORS allows `http://localhost:3000` (see backend `AGENT_UI_URL`). Try refreshing the endpoint. |
| **401 Unauthorized** | Token may be missing or expired. Use [Option A or B](#2-sign-in-and-get-a-token-two-options) again to get a new token. |
| **No teams / agents after refresh** | Check backend logs. Ensure AgentOS is mounted and `/teams` returns the orchestrator (e.g. run `curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:8000/teams`). |
| **FAQ answers are empty or generic** | Milvus running? FAQ data in `data/faq.xlsx`? Check backend logs for "FAQ load" and "orchestrator ready". |
| **Todo commands do nothing** | Todo MCP server running on 8001? Backend logs should show "Startup: MCP connected" and "AgentOS team updated to MCP-connected orchestrator". Restart backend and try again. |

---

## Quick checklist

- [ ] Milvus + Todo MCP + Backend app running
- [ ] agent-ui running at http://localhost:3000
- [ ] Endpoint set to http://localhost:8000 and status green
- [ ] Signed in (token in sidebar, from /login redirect or pasted)
- [ ] Mode = Team, Entity = orchestrator
- [ ] Test messages for FAQ, Weather, and Todo work

For API-only testing (no UI), see [MANUAL_API_TEST.md](MANUAL_API_TEST.md).
