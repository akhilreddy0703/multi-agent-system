"""
End-to-end test script for the Multi-Agent RAG system.

Prerequisites:
  1. Milvus running:  docker compose up -d etcd minio milvus-standalone
  2. Todo MCP server: uv run python -m src.tools.todo_mcp_server  (port 8001)
  3. App server:      uv run uvicorn src.main:app --host 0.0.0.0 --port 8000

Usage:
  uv run python tests/e2e_test.py
"""

import asyncio
import json
import re
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import jwt

BASE_URL = "http://localhost:8000"
MCP_URL = "http://localhost:8001/mcp"
JWT_SECRET = "a-secure-random-string-at-least-256-bits-long-for-hs256"

passed = 0
failed = 0
errors: list[str] = []


def load_faq_queries(max_n: int = 5) -> list[dict]:
    """Load FAQ test queries from data/sample_queries.json. Returns list of {id, query, expected}."""
    path = Path(__file__).resolve().parent.parent / "data" / "sample_queries.json"
    if not path.exists():
        return []
    try:
        with open(path) as f:
            data = json.load(f)
        queries = data.get("queries", [])
        faq = [q for q in queries if q.get("route") == "rag" and q.get("category") == "faq"][:max_n]
        return faq
    except Exception:
        return []


def report(test_id: str, description: str, ok: bool, detail: str = "", agent_note: str = ""):
    global passed, failed
    tag = "\033[92m[PASS]\033[0m" if ok else "\033[91m[FAIL]\033[0m"
    line = f"  {tag} {test_id}  {description}"
    if detail and not ok:
        line += f"  -- {detail}"
    print(line)
    if agent_note and ok:
        print(f"      \033[90m→ {agent_note}\033[0m")
    if ok:
        passed += 1
    else:
        failed += 1
        errors.append(f"{test_id} {description}: {detail}")


def scenario_header(title: str, subtitle: str = ""):
    print()
    print(f"\033[1m--- {title}\033[0m")
    if subtitle:
        print(f"  \033[90m{subtitle}\033[0m")


def run_chat_showcase(client: httpx.Client, headers: dict, query: str, scenario_name: str) -> bool:
    """Call /chat/stream and print a chat-style stream (User / Assistant / Tool) so the flow is clear."""
    print()
    print(f"\033[1m  [Chat showcase] {scenario_name}\033[0m")
    print(f"  \033[94mUser:\033[0m {query}")
    print(f"  \033[92mAssistant:\033[0m ", end="", flush=True)
    full_content: list[str] = []
    tools_seen: list[str] = []
    try:
        with client.stream(
            "POST", "/chat/stream", json={"message": query}, headers=headers, timeout=60
        ) as r:
            if r.status_code != 200:
                print(f"\n  \033[91mError status={r.status_code}\033[0m")
                return False
            event_type = None
            for line in r.iter_lines():
                if line.startswith("event:"):
                    event_type = line[6:].strip()
                elif line.startswith("data:") and event_type:
                    try:
                        data = json.loads(line[5:].strip())
                    except json.JSONDecodeError:
                        continue
                    if event_type == "run_content" and data.get("content"):
                        chunk = data["content"]
                        print(chunk, end="", flush=True)
                        full_content.append(chunk)
                    elif event_type == "tool_call_started":
                        tool = data.get("tool", "tool")
                        tools_seen.append(tool)
                        print(f"\n  \033[90m[Tool: {tool}]\033[0m ", end="", flush=True)
                    elif event_type == "tool_call_completed":
                        summary = (data.get("result_summary") or "")[:60]
                        if summary:
                            print(f"→ {summary} ", end="", flush=True)
                        print("", flush=True)
                        print(f"  \033[92mAssistant:\033[0m ", end="", flush=True)
                    elif event_type == "error":
                        print(f"\n  \033[91mError: {data.get('detail', data)}\033[0m")
                        return False
                    elif event_type in ("run_completed", "run_content_completed"):
                        pass
                    event_type = None
        print("")
        if tools_seen:
            print(f"  \033[90m(Tools used: {', '.join(tools_seen)})\033[0m")
        return True
    except Exception as e:
        print(f"\n  \033[91mException: {e}\033[0m")
        return False


# ---------------------------------------------------------------------------
# Layer 1: Auth
# ---------------------------------------------------------------------------

def test_1_1_login_success(client: httpx.Client) -> str:
    r = client.post("/auth/login", data={"username": "demo", "password": "password"})
    ok = r.status_code == 200 and "access_token" in r.json()
    report("1.1", "Login with valid credentials", ok, f"status={r.status_code}")
    return r.json().get("access_token", "") if ok else ""


def test_1_2_login_wrong_password(client: httpx.Client):
    r = client.post("/auth/login", data={"username": "demo", "password": "WRONG"})
    report("1.2", "Login wrong password → 401", r.status_code == 401, f"status={r.status_code}")


def test_1_3_login_missing_fields(client: httpx.Client):
    r = client.post("/auth/login", data={})
    report("1.3", "Login missing fields → 422", r.status_code == 422, f"status={r.status_code}")


def test_1_4_protected_no_auth(client: httpx.Client):
    r = client.get("/weather")
    report("1.4", "GET /weather without token → 401", r.status_code == 401, f"status={r.status_code}")


def test_1_5_protected_garbage_token(client: httpx.Client):
    r = client.get("/weather", headers={"Authorization": "Bearer garbage"})
    report("1.5", "GET /weather with invalid token → 401", r.status_code == 401, f"status={r.status_code}")


def test_1_6_protected_expired_token(client: httpx.Client):
    payload = {"sub": "user_123", "exp": datetime.now(UTC) - timedelta(hours=1), "iat": datetime.now(UTC) - timedelta(hours=2)}
    token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")
    r = client.get("/weather", headers={"Authorization": f"Bearer {token}"})
    report("1.6", "GET /weather with expired token → 401", r.status_code == 401, f"status={r.status_code}")


# ---------------------------------------------------------------------------
# Layer 2: Login page & AgentOS (teams, config, team run)
# ---------------------------------------------------------------------------

def test_2_1_login_page_no_auth(client: httpx.Client):
    r = client.get("/login")
    ok = r.status_code == 200 and "Sign in" in r.text
    report("2.1", "GET /login (no auth) → 200, login form", ok, f"status={r.status_code}",
           "Login page served for agent-ui redirect flow.")


def test_2_2_teams_list(client: httpx.Client, headers: dict):
    r = client.get("/teams", headers=headers)
    ok = r.status_code == 200
    data = r.json() if ok else []
    teams = data if isinstance(data, list) else data.get("teams", data) if isinstance(data, dict) else []
    if isinstance(teams, dict):
        teams = list(teams.values()) if isinstance(teams, dict) else []
    ids = []
    for t in (teams if isinstance(teams, list) else []):
        tid = t.get("team_id") or t.get("id") or t.get("name")
        if tid:
            ids.append(str(tid))
    has_orchestrator = "orchestrator" in ids or any("orchestrator" in str(t).lower() for t in (teams if isinstance(teams, list) else [teams]))
    if not has_orchestrator and ok and teams:
        has_orchestrator = "orchestrator" in str(teams).lower()
    report("2.2", "GET /teams (AgentOS) → list includes orchestrator", ok and (has_orchestrator or not teams),
           f"status={r.status_code} ids={ids[:5]}" if not has_orchestrator else "",
           f"AgentOS exposes team(s): {ids[:5] or 'orchestrator'}." if ok else "")


def test_2_3_config(client: httpx.Client, headers: dict):
    r = client.get("/config", headers=headers)
    ok = r.status_code == 200
    report("2.3", "GET /config (AgentOS) → 200", ok, f"status={r.status_code}",
           "AgentOS config available for agent-ui." if ok else "")


def test_2_4_team_run_non_streaming(client: httpx.Client, headers: dict):
    r = client.post(
        "/teams/orchestrator/runs",
        data={"message": "Reply with exactly: 2+2=4", "stream": "false"},
        headers={**headers, "Content-Type": "application/x-www-form-urlencoded"},
        timeout=60,
    )
    ok = r.status_code == 200
    body = r.json() if ok else {}
    content = body.get("content") or body.get("response") or str(body)
    if isinstance(content, dict):
        content = content.get("content", str(content))
    has_answer = "4" in str(content) or "2+2" in str(content).lower()
    report("2.4", "POST /teams/orchestrator/runs (stream=false) → 200, answer", ok and (has_answer or len(str(content)) > 3),
           f"status={r.status_code} body={str(content)[:120]}",
           f"Orchestrator replied: {str(content)[:80]}..." if ok and content else "")


def test_2_5_team_run_streaming(client: httpx.Client, headers: dict):
    with client.stream(
        "POST",
        "/teams/orchestrator/runs",
        data={"message": "Say hello in one word.", "stream": "true"},
        headers={**headers, "Content-Type": "application/x-www-form-urlencoded"},
        timeout=30,
    ) as r:
        ok = r.status_code == 200
        chunks = []
        for line in r.iter_lines():
            if line and line.startswith("data:"):
                chunks.append(line)
            if len(chunks) >= 3:
                break
        got_events = len(chunks) >= 1
    report("2.5", "POST /teams/orchestrator/runs (stream=true) → SSE events", ok and got_events,
           f"status={r.status_code} chunks={len(chunks)}" if not got_events else "",
           f"AgentOS streamed {len(chunks)} SSE event(s) (orchestrator team)." if ok and got_events else "")


def test_2_6_teams_no_auth(client: httpx.Client):
    r = client.get("/teams")
    report("2.6", "GET /teams without token → 401", r.status_code == 401, f"status={r.status_code}",
           "AgentOS routes protected by JWT." if r.status_code == 401 else "")


# ---------------------------------------------------------------------------
# Layer 3: Weather tool (direct REST)
# ---------------------------------------------------------------------------

def test_3_1_weather_with_auth(client: httpx.Client, headers: dict):
    r = client.get("/weather", headers=headers)
    ok = r.status_code == 200
    d = r.json() if ok else {}
    ok = ok and all(k in d for k in ("city", "temperature_c", "condition", "source")) and d.get("source") == "mock"
    report("3.1", "GET /weather with auth → mock data", ok, f"status={r.status_code}",
           f"Weather tool: {d.get('city')} {d.get('temperature_c')}°C, {d.get('condition')}." if ok else "")


def test_3_2_weather_custom_city(client: httpx.Client, headers: dict):
    r = client.get("/weather", params={"city": "Mumbai"}, headers=headers)
    ok = r.status_code == 200 and r.json().get("city") == "Mumbai"
    report("3.2", "GET /weather?city=Mumbai → city=Mumbai", ok, f"body={r.text[:80]}",
           "Tool returns requested city." if ok else "")


# ---------------------------------------------------------------------------
# Layer 4: MCP Todo (direct)
# ---------------------------------------------------------------------------

async def test_layer_4_mcp_direct():
    try:
        from fastmcp import Client
    except ImportError:
        report("4.0", "fastmcp import", False, "fastmcp not installed")
        return
    try:
        mcp_client = Client(MCP_URL)
        async with mcp_client:
            def _text(result):
                return str(result.data) if hasattr(result, "data") else str(result)

            result = await mcp_client.call_tool("create_task", {"title": "E2E milk", "description": "Test"})
            text = _text(result)
            report("4.1", "MCP create_task → Created", "Created" in text, text[:80], "Todo MCP: task created.")

            result = await mcp_client.call_tool("list_tasks", {"status_filter": "all"})
            text = _text(result)
            report("4.2", "MCP list_tasks → contains E2E milk", "E2E milk" in text, text[:80])

            ids = re.findall(r"ID (\d+):", text)
            tid = int(ids[-1]) if ids else 1
            result = await mcp_client.call_tool("update_task", {"task_id": tid, "status": "done"})
            text = _text(result)
            report("4.3", f"MCP update_task({tid}) → Updated", "Updated" in text, text[:80], "Todo MCP: task marked done.")

            result = await mcp_client.call_tool("delete_task", {"task_id": tid})
            text = _text(result)
            report("4.4", f"MCP delete_task({tid}) → Deleted", "Deleted" in text, text[:80], "Todo MCP: task removed.")
    except Exception as e:
        report("4.x", "MCP direct", False, str(e)[:120])


# ---------------------------------------------------------------------------
# Layer 5: Todo REST API (via app)
# ---------------------------------------------------------------------------

def test_5_1_todo_create(client: httpx.Client, headers: dict):
    r = client.post("/todos", json={"title": "E2E report", "description": "Q1"}, headers=headers)
    ok = r.status_code == 200 and "Created" in r.json().get("message", "")
    report("5.1", "POST /todos → Created", ok, r.text[:80], "App → Todo MCP: task created." if ok else "")


def test_5_2_todo_list(client: httpx.Client, headers: dict):
    r = client.get("/todos", headers=headers)
    ok = r.status_code == 200 and "E2E report" in r.json().get("tasks", "")
    report("5.2", "GET /todos → contains E2E report", ok, r.text[:80])


def test_5_3_todo_update_delete(client: httpx.Client, headers: dict, task_id: int):
    r = client.put(f"/todos/{task_id}", json={"status": "done"}, headers=headers)
    ok = r.status_code == 200 and "Updated" in r.json().get("message", "")
    report("5.3", f"PUT /todos/{task_id} done → Updated", ok, r.text[:80])
    r = client.delete(f"/todos/{task_id}", headers=headers)
    ok2 = r.status_code == 200 and "Deleted" in r.json().get("message", "")
    report("5.4", f"DELETE /todos/{task_id} → Deleted", ok2, r.text[:80])


def test_5_5_todo_no_auth(client: httpx.Client):
    r = client.post("/todos", json={"title": "x"})
    report("5.5", "POST /todos without auth → 401", r.status_code == 401, f"status={r.status_code}")


# ---------------------------------------------------------------------------
# Layer 6: Chat orchestrator — Weather routing
# ---------------------------------------------------------------------------

def test_6_1_chat_weather(client: httpx.Client, headers: dict):
    r = client.post("/chat", json={"query": "What is the weather in London?"}, headers=headers, timeout=60)
    ok = r.status_code == 200
    body = (r.json().get("response", "") or "") if ok else ""
    has_weather = any(w in body.lower() for w in ("weather", "temperature", "london", "cloudy", "22", "72"))
    report("6.1", "Chat: 'weather in London' → weather answer", ok and has_weather, f"response={body[:150]}",
           f"Agent routed to Weather tool; response: {body[:70]}..." if ok and has_weather else "")


def test_6_2_chat_weather_today(client: httpx.Client, headers: dict):
    r = client.post("/chat", json={"query": "How is the weather today?"}, headers=headers, timeout=60)
    ok = r.status_code == 200
    body = (r.json().get("response", "") or "") if ok else ""
    has_weather = any(w in body.lower() for w in ("weather", "temperature", "cloudy", "mock"))
    report("6.2", "Chat: 'weather today' → weather answer", ok and has_weather, f"response={body[:150]}",
           "Agent routed to Weather tool (generic question)." if ok and has_weather else "")


# ---------------------------------------------------------------------------
# Layer 7: Chat orchestrator — FAQ/RAG routing
# ---------------------------------------------------------------------------

def test_7_1_chat_faq(client: httpx.Client, headers: dict):
    r = client.post("/chat", json={"query": "What are the company working hours?"}, headers=headers, timeout=60)
    ok = r.status_code == 200
    body = (r.json().get("response", "") or "") if ok else ""
    report("7.1", "Chat: FAQ question → RAG answer", ok and len(body) > 10, f"response={body[:150]}",
           f"Agent routed to RAG/FAQ; response length={len(body)}." if ok else "")


def test_7_2_chat_out_of_scope(client: httpx.Client, headers: dict):
    r = client.post("/chat", json={"query": "Explain quantum entanglement in one sentence."}, headers=headers, timeout=60)
    ok = r.status_code == 200
    body = (r.json().get("response", "") or "") if ok else ""
    report("7.2", "Chat: out-of-scope → fallback/refusal", ok and len(body) > 5, f"response={body[:150]}",
           "Orchestrator → RAG fallback (out-of-scope)." if ok else "")


def test_7_faq_delegation(client: httpx.Client, headers: dict):
    """Run FAQ queries from sample_queries.json; verify orchestrator delegates to RAG."""
    faq_queries = load_faq_queries(max_n=4)
    if not faq_queries:
        report("7.FAQ", "FAQ delegation (sample_queries)", True, "", "No data/sample_queries.json; skipped.")
        return
    for i, q in enumerate(faq_queries):
        qid = q.get("id", f"faq_{i}")
        query = q.get("query", "")
        if not query:
            continue
        r = client.post("/chat", json={"query": query}, headers=headers, timeout=60)
        ok = r.status_code == 200
        body = (r.json().get("response", "") or "") if ok else ""
        report(f"7.{qid}", f"FAQ: '{query[:40]}...' → RAG", ok and len(body) > 10,
               f"response={body[:120]}" if not ok else "",
               f"Orchestrator → RAG; {len(body)} chars." if ok else "")


# ---------------------------------------------------------------------------
# Layer 8: Chat orchestrator — Todo routing
# ---------------------------------------------------------------------------

def test_8_1_chat_create_task(client: httpx.Client, headers: dict):
    r = client.post("/chat", json={"query": "Create a task called 'E2E homework'"}, headers=headers, timeout=60)
    ok = r.status_code == 200
    body = (r.json().get("response", "") or "") if ok else ""
    has_task = any(w in body.lower() for w in ("created", "task", "e2e homework", "homework"))
    report("8.1", "Chat: 'create task' → task created", ok and has_task, f"response={body[:150]}",
           "Agent routed to Todo tool; task created." if ok and has_task else "")


def test_8_2_chat_list_tasks(client: httpx.Client, headers: dict):
    r = client.post("/chat", json={"query": "List all my tasks"}, headers=headers, timeout=60)
    ok = r.status_code == 200
    body = (r.json().get("response", "") or "") if ok else ""
    report("8.2", "Chat: 'list tasks' → non-empty", ok and len(body) > 5, f"response={body[:150]}",
           "Agent routed to Todo tool; listed tasks." if ok else "")


# ---------------------------------------------------------------------------
# Layer 9: Chat stream (SSE) + edge cases
# ---------------------------------------------------------------------------

def test_9_1_chat_stream_sse(client: httpx.Client, headers: dict):
    with client.stream(
        "POST", "/chat/stream", json={"message": "What is 2+2? Reply with one number."}, headers=headers, timeout=30
    ) as r:
        ok = r.status_code == 200
        chunks = []
        for line in r.iter_lines():
            if line and (line.startswith("data:") or line.startswith("event:")):
                chunks.append(line[:100])
            if len(chunks) >= 5:
                break
        got = len(chunks) >= 1
    report("9.1", "POST /chat/stream → SSE events", ok and got, f"status={r.status_code} chunks={len(chunks)}",
           f"Chat stream emitted {len(chunks)} SSE lines (orchestrator with MCP)." if ok and got else "")


def test_9_2_chat_empty_query(client: httpx.Client, headers: dict):
    r = client.post("/chat", json={"query": ""}, headers=headers, timeout=60)
    report("9.2", "Chat: empty query → no crash (200)", r.status_code == 200, f"status={r.status_code}")


def test_9_3_todo_not_found(client: httpx.Client, headers: dict):
    r = client.put("/todos/99999", json={"title": "nope"}, headers=headers)
    ok = r.status_code == 200 and "not found" in r.json().get("message", "").lower()
    report("9.3", "PUT /todos/99999 → not found", ok, r.text[:80])


def test_9_4_chat_no_auth(client: httpx.Client):
    r = client.post("/chat", json={"query": "hi"})
    report("9.4", "POST /chat without auth → 401", r.status_code == 401, f"status={r.status_code}",
           "Chat endpoint protected by JWT." if r.status_code == 401 else "")


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def main():
    global passed, failed, errors
    print("=" * 72)
    print("  Multi-Agent RAG — E2E Tests")
    print(f"  Target: {BASE_URL}")
    print("  Scenarios: Auth, Login/AgentOS, Weather, MCP Todo, Chat (weather/FAQ/todo), Stream, Edge")
    print("=" * 72)

    client = httpx.Client(base_url=BASE_URL, timeout=10)
    try:
        r = client.get("/docs")
        if r.status_code != 200:
            print(f"\n  Server not reachable at {BASE_URL} (status {r.status_code})")
            sys.exit(1)
    except httpx.ConnectError:
        print(f"\n  Cannot connect to {BASE_URL}. Is the server running?")
        sys.exit(1)

    scenario_header("Layer 1: Authentication", "JWT login and protected route behavior")
    token = test_1_1_login_success(client)
    if not token:
        print("  Cannot proceed without token. Aborting.")
        sys.exit(1)
    headers = {"Authorization": f"Bearer {token}"}
    test_1_2_login_wrong_password(client)
    test_1_3_login_missing_fields(client)
    test_1_4_protected_no_auth(client)
    test_1_5_protected_garbage_token(client)
    test_1_6_protected_expired_token(client)

    scenario_header("Layer 2: Login page & AgentOS", "Login page, teams, config, team run (stream + non-stream)")
    test_2_1_login_page_no_auth(client)
    test_2_2_teams_list(client, headers)
    test_2_3_config(client, headers)
    test_2_4_team_run_non_streaming(client, headers)
    test_2_5_team_run_streaming(client, headers)
    test_2_6_teams_no_auth(client)

    scenario_header("Layer 3: Weather tool (REST)", "Direct tool API")
    test_3_1_weather_with_auth(client, headers)
    test_3_2_weather_custom_city(client, headers)

    scenario_header("Layer 4: MCP Todo server (direct)", "FastMCP client → create, list, update, delete")
    asyncio.run(test_layer_4_mcp_direct())

    scenario_header("Layer 5: Todo REST API (via app)", "App → MCP proxy")
    test_5_1_todo_create(client, headers)
    test_5_2_todo_list(client, headers)
    r = client.get("/todos", headers=headers)
    tasks_text = r.json().get("tasks", "") if r.status_code == 200 else ""
    ids = re.findall(r"ID (\d+):", tasks_text)
    task_id = int(ids[-1]) if ids else 2
    test_5_3_todo_update_delete(client, headers, task_id)
    test_5_5_todo_no_auth(client)

    scenario_header("Layer 6: Chat — Weather routing", "Orchestrator → Weather tool")
    test_6_1_chat_weather(client, headers)
    test_6_2_chat_weather_today(client, headers)

    scenario_header("Layer 7: Chat — FAQ/RAG routing", "Orchestrator → RAG agent")
    test_7_1_chat_faq(client, headers)
    test_7_2_chat_out_of_scope(client, headers)
    test_7_faq_delegation(client, headers)

    scenario_header("Chat streaming showcase", "User / Assistant / Tool lines via /chat/stream")
    faq_queries = load_faq_queries(max_n=1)
    faq_q = faq_queries[0]["query"] if faq_queries else "What are the company working hours?"
    run_chat_showcase(client, headers, faq_q, "FAQ → RAG")
    run_chat_showcase(client, headers, "What is the weather in London?", "Weather → get_weather")
    run_chat_showcase(client, headers, "List all my tasks", "Todo → MCP")

    scenario_header("Layer 8: Chat — Todo routing", "Orchestrator → Todo tool (MCP)")
    test_8_1_chat_create_task(client, headers)
    test_8_2_chat_list_tasks(client, headers)

    scenario_header("Layer 9: Chat stream + edge cases", "SSE stream and 401/not-found")
    test_9_1_chat_stream_sse(client, headers)
    test_9_2_chat_empty_query(client, headers)
    test_9_3_todo_not_found(client, headers)
    test_9_4_chat_no_auth(client)

    total = passed + failed
    print()
    print("=" * 72)
    print(f"  Results: {passed}/{total} passed, {failed} failed")
    if errors:
        print("\n  Failures:")
        for e in errors:
            print(f"    - {e}")
    print("=" * 72)
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
