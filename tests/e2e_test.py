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
import sys
import time
from datetime import UTC, datetime, timedelta

import httpx
import jwt

BASE_URL = "http://localhost:8000"
MCP_URL = "http://localhost:8001/mcp"
JWT_SECRET = "a-secure-random-string-at-least-256-bits-long-for-hs256"

passed = 0
failed = 0
errors: list[str] = []


def report(test_id: str, description: str, ok: bool, detail: str = ""):
    global passed, failed
    tag = "\033[92m[PASS]\033[0m" if ok else "\033[91m[FAIL]\033[0m"
    line = f"{tag} {test_id} {description}"
    if detail and not ok:
        line += f"  -- {detail}"
    print(line)
    if ok:
        passed += 1
    else:
        failed += 1
        errors.append(f"{test_id} {description}: {detail}")


# ---------------------------------------------------------------------------
# Layer 1: Auth
# ---------------------------------------------------------------------------

def test_1_1_login_success(client: httpx.Client) -> str:
    """Login with valid credentials -> 200 + access_token."""
    r = client.post(
        "/auth/login",
        data={"username": "demo", "password": "password"},
    )
    ok = r.status_code == 200 and "access_token" in r.json()
    report("1.1", "Login with valid credentials", ok, f"status={r.status_code}")
    if ok:
        return r.json()["access_token"]
    return ""


def test_1_2_login_wrong_password(client: httpx.Client):
    r = client.post(
        "/auth/login",
        data={"username": "demo", "password": "WRONG"},
    )
    report("1.2", "Login with wrong password -> 401", r.status_code == 401, f"status={r.status_code}")


def test_1_3_login_missing_fields(client: httpx.Client):
    r = client.post("/auth/login", data={})
    report("1.3", "Login with missing fields -> 422", r.status_code == 422, f"status={r.status_code}")


def test_1_4_weather_no_auth(client: httpx.Client):
    r = client.get("/weather")
    report("1.4", "GET /weather without token -> 401", r.status_code == 401, f"status={r.status_code}")


def test_1_5_weather_garbage_token(client: httpx.Client):
    r = client.get("/weather", headers={"Authorization": "Bearer garbage.not.valid"})
    report("1.5", "GET /weather with garbage token -> 401", r.status_code == 401, f"status={r.status_code}")


def test_1_6_weather_expired_token(client: httpx.Client):
    payload = {
        "sub": "user_123",
        "username": "demo",
        "exp": datetime.now(UTC) - timedelta(hours=1),
        "iat": datetime.now(UTC) - timedelta(hours=2),
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")
    r = client.get("/weather", headers={"Authorization": f"Bearer {token}"})
    report("1.6", "GET /weather with expired token -> 401", r.status_code == 401, f"status={r.status_code}")


# ---------------------------------------------------------------------------
# Layer 2: Weather Tool (direct REST)
# ---------------------------------------------------------------------------

def test_2_1_weather_with_auth(client: httpx.Client, headers: dict):
    r = client.get("/weather", headers=headers)
    ok = r.status_code == 200
    if ok:
        d = r.json()
        ok = all(k in d for k in ("city", "temperature_c", "condition", "source"))
        ok = ok and d["source"] == "mock"
    report("2.1", "GET /weather with auth -> structured mock data", ok, f"status={r.status_code} body={r.text[:120]}")


def test_2_2_weather_custom_city(client: httpx.Client, headers: dict):
    r = client.get("/weather", params={"city": "Mumbai"}, headers=headers)
    ok = r.status_code == 200 and r.json().get("city") == "Mumbai"
    report("2.2", "GET /weather?city=Mumbai -> city=Mumbai", ok, f"body={r.text[:120]}")


def test_2_3_weather_default_city(client: httpx.Client, headers: dict):
    r = client.get("/weather", headers=headers)
    ok = r.status_code == 200 and r.json().get("city") == "London"
    report("2.3", "GET /weather (no city) -> default London", ok, f"city={r.json().get('city')}")


# ---------------------------------------------------------------------------
# Layer 3: MCP Todo Server (direct FastMCP client)
# ---------------------------------------------------------------------------

async def test_layer_3_mcp_direct():
    """Test the MCP server directly via fastmcp.Client."""
    try:
        from fastmcp import Client
    except ImportError:
        report("3.x", "fastmcp import", False, "fastmcp not installed")
        return

    try:
        client = Client(MCP_URL)
        async with client:
            def _text(result) -> str:
                """Extract text from CallToolResult (fastmcp 3.x)."""
                if hasattr(result, "data"):
                    return str(result.data)
                return str(result)

            # 3.1 create
            result = await client.call_tool("create_task", {"title": "Buy milk", "description": "Grocery shopping"})
            text = _text(result)
            report("3.1", "MCP create_task -> Created", "Created" in text, text[:80])

            # 3.2 list all
            result = await client.call_tool("list_tasks", {"status_filter": "all"})
            text = _text(result)
            report("3.2", "MCP list_tasks(all) -> contains Buy milk", "Buy milk" in text, text[:80])

            # 3.3 update -- find the task id from the create output
            import re as _re
            ids = _re.findall(r"ID (\d+):", text)
            tid = int(ids[-1]) if ids else 1
            result = await client.call_tool("update_task", {"task_id": tid, "status": "done"})
            text = _text(result)
            report("3.3", f"MCP update_task({tid}, done) -> Updated", "Updated" in text, text[:80])

            # 3.4 list done
            result = await client.call_tool("list_tasks", {"status_filter": "done"})
            text = _text(result)
            report("3.4", "MCP list_tasks(done) -> Buy milk [done]", "Buy milk" in text and "done" in text, text[:80])

            # 3.5 delete
            result = await client.call_tool("delete_task", {"task_id": tid})
            text = _text(result)
            report("3.5", f"MCP delete_task({tid}) -> Deleted", "Deleted" in text, text[:80])

            # 3.6 verify deleted task is gone (other tasks from prior runs may remain)
            result = await client.call_tool("list_tasks", {"status_filter": "all"})
            text = _text(result)
            task_gone = f"ID {tid}:" not in text
            report("3.6", f"MCP list_tasks -> task {tid} removed", task_gone, text[:80])
    except Exception as e:
        report("3.x", "MCP direct connection", False, str(e)[:120])


# ---------------------------------------------------------------------------
# Layer 4: Todo REST API (via app)
# ---------------------------------------------------------------------------

def test_4_1_todo_create(client: httpx.Client, headers: dict):
    r = client.post("/todos", json={"title": "Write report", "description": "Q1 report"}, headers=headers)
    ok = r.status_code == 200 and "Created" in r.json().get("message", "")
    report("4.1", "POST /todos -> Created", ok, f"status={r.status_code} body={r.text[:120]}")


def test_4_2_todo_list(client: httpx.Client, headers: dict):
    r = client.get("/todos", headers=headers)
    ok = r.status_code == 200 and "Write report" in r.json().get("tasks", "")
    report("4.2", "GET /todos -> contains Write report", ok, f"body={r.text[:120]}")


def test_4_3_todo_update(client: httpx.Client, headers: dict, task_id: int):
    r = client.put(f"/todos/{task_id}", json={"status": "done"}, headers=headers)
    ok = r.status_code == 200 and "Updated" in r.json().get("message", "")
    report("4.3", f"PUT /todos/{task_id} done -> Updated", ok, f"body={r.text[:120]}")


def test_4_4_todo_list_done(client: httpx.Client, headers: dict):
    r = client.get("/todos", params={"status": "done"}, headers=headers)
    ok = r.status_code == 200 and "Write report" in r.json().get("tasks", "")
    report("4.4", "GET /todos?status=done -> Write report", ok, f"body={r.text[:120]}")


def test_4_5_todo_delete(client: httpx.Client, headers: dict, task_id: int):
    r = client.delete(f"/todos/{task_id}", headers=headers)
    ok = r.status_code == 200 and "Deleted" in r.json().get("message", "")
    report("4.5", f"DELETE /todos/{task_id} -> Deleted", ok, f"body={r.text[:120]}")


def test_4_6_todo_no_auth(client: httpx.Client):
    r = client.post("/todos", json={"title": "Fail"})
    report("4.6", "POST /todos without auth -> 401", r.status_code == 401, f"status={r.status_code}")


# ---------------------------------------------------------------------------
# Layer 5: Chat Orchestrator - Weather routing
# ---------------------------------------------------------------------------

def test_5_1_chat_weather(client: httpx.Client, headers: dict):
    r = client.post("/chat", json={"query": "What is the weather in London?"}, headers=headers, timeout=60)
    ok = r.status_code == 200
    body = r.json().get("response", "") if ok else ""
    has_weather = any(w in body.lower() for w in ("weather", "temperature", "london", "cloudy", "72", "22"))
    report("5.1", "Chat: weather in London -> mentions weather data", ok and has_weather,
           f"status={r.status_code} response={body[:150]}")


def test_5_2_chat_weather_generic(client: httpx.Client, headers: dict):
    r = client.post("/chat", json={"query": "How is the weather today?"}, headers=headers, timeout=60)
    ok = r.status_code == 200
    body = r.json().get("response", "") if ok else ""
    has_weather = any(w in body.lower() for w in ("weather", "temperature", "cloudy", "mock", "humidity"))
    report("5.2", "Chat: weather today -> mentions weather", ok and has_weather,
           f"status={r.status_code} response={body[:150]}")


# ---------------------------------------------------------------------------
# Layer 6: Chat Orchestrator - FAQ/RAG routing
# ---------------------------------------------------------------------------

def test_6_1_chat_faq(client: httpx.Client, headers: dict):
    r = client.post(
        "/chat",
        json={"query": "What are the company working hours?"},
        headers=headers,
        timeout=60,
    )
    ok = r.status_code == 200
    body = r.json().get("response", "") if ok else ""
    report("6.1", "Chat: FAQ question -> non-empty response", ok and len(body) > 10,
           f"status={r.status_code} response={body[:150]}")


def test_6_2_chat_faq_fallback(client: httpx.Client, headers: dict):
    r = client.post(
        "/chat",
        json={"query": "Explain the theory of quantum entanglement in detail"},
        headers=headers,
        timeout=60,
    )
    ok = r.status_code == 200
    body = r.json().get("response", "") if ok else ""
    report("6.2", "Chat: out-of-scope question -> fallback or polite refusal",
           ok and len(body) > 5, f"status={r.status_code} response={body[:150]}")


# ---------------------------------------------------------------------------
# Layer 7: Chat Orchestrator - Todo routing
# ---------------------------------------------------------------------------

def test_7_1_chat_create_task(client: httpx.Client, headers: dict):
    r = client.post(
        "/chat",
        json={"query": "Create a task called 'Finish homework'"},
        headers=headers,
        timeout=60,
    )
    ok = r.status_code == 200
    body = r.json().get("response", "") if ok else ""
    has_task = any(w in body.lower() for w in ("created", "task", "finish homework"))
    report("7.1", "Chat: create task -> mentions task created", ok and has_task,
           f"status={r.status_code} response={body[:150]}")


def test_7_2_chat_list_tasks(client: httpx.Client, headers: dict):
    r = client.post(
        "/chat",
        json={"query": "List all my tasks"},
        headers=headers,
        timeout=60,
    )
    ok = r.status_code == 200
    body = r.json().get("response", "") if ok else ""
    report("7.2", "Chat: list tasks -> non-empty response", ok and len(body) > 5,
           f"status={r.status_code} response={body[:150]}")


# ---------------------------------------------------------------------------
# Layer 8: Negative / edge cases
# ---------------------------------------------------------------------------

def test_8_1_chat_empty_query(client: httpx.Client, headers: dict):
    r = client.post("/chat", json={"query": ""}, headers=headers, timeout=60)
    report("8.1", "Chat: empty query -> doesn't crash (200)", r.status_code == 200,
           f"status={r.status_code}")


def test_8_2_todo_update_nonexistent(client: httpx.Client, headers: dict):
    r = client.put("/todos/999", json={"title": "nope"}, headers=headers)
    ok = r.status_code == 200 and "not found" in r.json().get("message", "").lower()
    report("8.2", "PUT /todos/999 -> not found", ok, f"body={r.text[:120]}")


def test_8_3_todo_delete_nonexistent(client: httpx.Client, headers: dict):
    r = client.delete("/todos/999", headers=headers)
    ok = r.status_code == 200 and "not found" in r.json().get("message", "").lower()
    report("8.3", "DELETE /todos/999 -> not found", ok, f"body={r.text[:120]}")


def test_8_4_chat_no_auth(client: httpx.Client):
    r = client.post("/chat", json={"query": "hello"})
    report("8.4", "POST /chat without auth -> 401", r.status_code == 401, f"status={r.status_code}")


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def main():
    global passed, failed, errors
    print("=" * 70)
    print("  Multi-Agent RAG System -- E2E Tests")
    print(f"  Target: {BASE_URL}")
    print("=" * 70)

    # Verify server is up
    client = httpx.Client(base_url=BASE_URL, timeout=10)
    try:
        r = client.get("/docs")
        if r.status_code != 200:
            print(f"\n  Server not reachable at {BASE_URL} (status {r.status_code})")
            sys.exit(1)
    except httpx.ConnectError:
        print(f"\n  Cannot connect to {BASE_URL}. Is the server running?")
        sys.exit(1)

    print()

    # --- Layer 1: Auth ---
    print("--- Layer 1: Authentication ---")
    token = test_1_1_login_success(client)
    if not token:
        print("  Cannot proceed without a token. Aborting.")
        sys.exit(1)
    headers = {"Authorization": f"Bearer {token}"}
    test_1_2_login_wrong_password(client)
    test_1_3_login_missing_fields(client)
    test_1_4_weather_no_auth(client)
    test_1_5_weather_garbage_token(client)
    test_1_6_weather_expired_token(client)
    print()

    # --- Layer 2: Weather REST ---
    print("--- Layer 2: Weather Tool (REST) ---")
    test_2_1_weather_with_auth(client, headers)
    test_2_2_weather_custom_city(client, headers)
    test_2_3_weather_default_city(client, headers)
    print()

    # --- Layer 3: MCP direct ---
    print("--- Layer 3: MCP Todo Server (direct) ---")
    asyncio.run(test_layer_3_mcp_direct())
    print()

    # --- Layer 4: Todo REST API ---
    print("--- Layer 4: Todo REST API ---")
    test_4_1_todo_create(client, headers)
    test_4_2_todo_list(client, headers)
    # The task id depends on MCP server state; the REST API creates via MCP
    # so we need to figure out the id. We'll use the latest created id.
    # Since Layer 3 deleted all tasks, the next id from the MCP server is incremented.
    # We try to parse the id from the create response, or guess common ids.
    r = client.get("/todos", headers=headers)
    tasks_text = r.json().get("tasks", "") if r.status_code == 200 else ""
    # Parse task id from "ID X: ..." pattern
    import re
    ids = re.findall(r"ID (\d+):", tasks_text)
    task_id = int(ids[-1]) if ids else 2
    test_4_3_todo_update(client, headers, task_id)
    test_4_4_todo_list_done(client, headers)
    test_4_5_todo_delete(client, headers, task_id)
    test_4_6_todo_no_auth(client)
    print()

    # --- Layer 5: Chat - Weather ---
    print("--- Layer 5: Chat Orchestrator - Weather ---")
    test_5_1_chat_weather(client, headers)
    test_5_2_chat_weather_generic(client, headers)
    print()

    # --- Layer 6: Chat - RAG ---
    print("--- Layer 6: Chat Orchestrator - FAQ/RAG ---")
    test_6_1_chat_faq(client, headers)
    test_6_2_chat_faq_fallback(client, headers)
    print()

    # --- Layer 7: Chat - Todo ---
    print("--- Layer 7: Chat Orchestrator - Todo ---")
    test_7_1_chat_create_task(client, headers)
    test_7_2_chat_list_tasks(client, headers)
    print()

    # --- Layer 8: Negative ---
    print("--- Layer 8: Negative / Edge Cases ---")
    test_8_1_chat_empty_query(client, headers)
    test_8_2_todo_update_nonexistent(client, headers)
    test_8_3_todo_delete_nonexistent(client, headers)
    test_8_4_chat_no_auth(client)
    print()

    # --- Summary ---
    total = passed + failed
    print("=" * 70)
    print(f"  Results: {passed}/{total} passed, {failed} failed")
    if errors:
        print("\n  Failures:")
        for e in errors:
            print(f"    - {e}")
    print("=" * 70)
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
