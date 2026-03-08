# Manual API testing (step by step)

Use these steps with the app running at `http://localhost:8000`. Run all `curl` commands from the project root (or any terminal). Export the token once after Step 1 and reuse it.

---

## Prerequisites

- App is running: `uv run uvicorn src.main:app --host 0.0.0.0 --port 8000`
- Optional: Todo MCP server for full Todo support: `uv run python -m src.tools.todo_mcp_server`

---

## Step 1: Login and get a JWT

**Request**

```bash
curl -s -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=demo&password=password"
```

**Expected**

JSON with `access_token` and `token_type`:

```json
{"access_token":"eyJ...","token_type":"bearer"}
```

**Save the token for later steps**

```bash
export TOKEN="<paste the access_token value here>"
```

Example (replace with your actual token):

```bash
export TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

---

## Step 2: (Optional) Get the login page without auth

**Request**

```bash
curl -s -o /dev/null -w "%{http_code}" "http://localhost:8000/login"
```

**Expected**

- Status: `200`
- No auth required.

---

## Step 3: List teams (AgentOS) — requires JWT

**Request**

```bash
curl -s "http://localhost:8000/teams" \
  -H "Authorization: Bearer $TOKEN"
```

**Expected**

JSON array of teams; at least one with `team_id` (or `id`) `"orchestrator"`.

---

## Step 4: Get config (AgentOS) — requires JWT

**Request**

```bash
curl -s "http://localhost:8000/config" \
  -H "Authorization: Bearer $TOKEN"
```

**Expected**

JSON config object (models, etc.). Status `200`.

---

## Step 5: Create a team run (AgentOS) — non‑streaming

**Request**

```bash
curl -s -X POST "http://localhost:8000/teams/orchestrator/runs" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "message=What is 2+2?&stream=false"
```

**Expected**

JSON with the run result (e.g. `content` or run metadata). Status `200`.

---

## Step 6: Create a team run (AgentOS) — streaming (SSE)

**Request**

```bash
curl -s -N -X POST "http://localhost:8000/teams/orchestrator/runs" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "message=Say hello in one sentence.&stream=true"
```

**Expected**

Server-Sent Events in the response body, e.g.:

```
event: RunStarted
data: {...}

event: RunContent
data: {"content": "Hello"}
...
```

Use `-N` to disable curl buffering so you see events as they arrive.

---

## Step 7: Chat (your API) — non‑streaming

**Request**

```bash
curl -s -X POST "http://localhost:8000/chat" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the weather in London?"}'
```

**Expected**

JSON with a `response` string (e.g. weather answer). Status `200`.

---

## Step 8: Chat stream (your API) — streaming (SSE)

**Request**

```bash
curl -s -N -X POST "http://localhost:8000/chat/stream" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "What is 2+2?"}'
```

**Expected**

SSE events, e.g. `event: run_content`, `event: run_completed`, etc. Status `200`.

---

## Step 9: Weather (requires JWT)

**Request**

```bash
curl -s "http://localhost:8000/weather?city=London" \
  -H "Authorization: Bearer $TOKEN"
```

**Expected**

JSON with weather-like fields. Status `200`.

---

## Step 10: Todos (requires JWT; needs Todo MCP)

**Request**

```bash
curl -s "http://localhost:8000/todos?status=all" \
  -H "Authorization: Bearer $TOKEN"
```

**Expected**

- If Todo MCP is running: JSON list of tasks or empty array. Status `200`.
- If not: may be 500 or empty depending on app behavior.

---

## Step 11: Without token — expect 401

**Request**

```bash
curl -s -o /dev/null -w "%{http_code}" "http://localhost:8000/teams"
```

**Expected**

Status `401` (no `Authorization` header).

---

## Quick copy‑paste sequence

After starting the app and (optionally) Todo MCP:

```bash
# 1. Login and set token (use one line, no newline inside the quoted token)
TOKEN=$(curl -s -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=demo&password=password" | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))")
export TOKEN

# 2. List teams
curl -s "http://localhost:8000/teams" -H "Authorization: Bearer $TOKEN" | head -c 500

# 3. AgentOS team run (streaming)
curl -s -N -X POST "http://localhost:8000/teams/orchestrator/runs" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "message=Hello&stream=true" | head -20

# 4. Your chat endpoint
curl -s -X POST "http://localhost:8000/chat" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "What is 2+2?"}'
```
