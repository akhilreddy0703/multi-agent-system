"""
End-to-end tests — happy path only.
"""
import re
import sys

import httpx

BASE_URL = "http://localhost:8000"

passed = 0
failed = 0


def report(description: str, ok: bool, detail: str = ""):
    global passed, failed
    tag = "\033[92mPASS\033[0m" if ok else "\033[91mFAIL\033[0m"
    line = f"  [{tag}] {description}"
    if detail and not ok:
        line += f" — {detail}"
    print(line)
    if ok:
        passed += 1
    else:
        failed += 1


# ---------------------------------------------------------------------------
# Happy-path tests (pytest: use client=AsyncClient, auth_headers from conftest)
# ---------------------------------------------------------------------------

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    r = await client.post("/auth/login", data={"username": "demo", "password": "password"})
    ok = r.status_code == 200 and "access_token" in r.json()
    report("Login with valid credentials", ok, f"status={r.status_code}")
    assert ok


@pytest.mark.asyncio
async def test_teams_list(client: AsyncClient, auth_headers: dict):
    r = await client.get("/teams", headers=auth_headers)
    report("GET /teams → 200", r.status_code == 200, f"status={r.status_code}")
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_config(client: AsyncClient, auth_headers: dict):
    r = await client.get("/config", headers=auth_headers)
    report("GET /config → 200", r.status_code == 200, f"status={r.status_code}")
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_team_run_non_streaming(client: AsyncClient, auth_headers: dict):
    r = await client.post(
        "/teams/orchestrator/runs",
        data={"message": "Reply with exactly: 2+2=4", "stream": "false"},
        headers={**auth_headers, "Content-Type": "application/x-www-form-urlencoded"},
        timeout=60,
    )
    ok = r.status_code == 200
    report("POST /teams/orchestrator/runs (stream=false) → 200", ok, f"status={r.status_code}")
    assert ok


@pytest.mark.asyncio
async def test_team_run_streaming(client: AsyncClient, auth_headers: dict):
    async with client.stream(
        "POST",
        "/teams/orchestrator/runs",
        data={"message": "Say hello in one word.", "stream": "true"},
        headers={**auth_headers, "Content-Type": "application/x-www-form-urlencoded"},
        timeout=30,
    ) as r:
        ok = r.status_code == 200
        chunks = []
        async for line in r.aiter_lines():
            if line and line.startswith("data:"):
                chunks.append(line)
                if len(chunks) >= 3:
                    break
    report("POST /teams/orchestrator/runs (stream=true) → SSE", ok and len(chunks) >= 1, f"chunks={len(chunks)}")
    assert ok and len(chunks) >= 1


@pytest.mark.asyncio
async def test_weather_with_auth(client: AsyncClient, auth_headers: dict):
    r = await client.get("/weather", headers=auth_headers)
    ok = r.status_code == 200
    if ok:
        d = r.json()
        ok = all(k in d for k in ("city", "temperature_c", "condition", "source"))
    report("GET /weather with auth → 200, mock data", ok, f"status={r.status_code}")
    assert ok


@pytest.mark.asyncio
async def test_weather_custom_city(client: AsyncClient, auth_headers: dict):
    r = await client.get("/weather", params={"city": "Mumbai"}, headers=auth_headers)
    ok = r.status_code == 200 and r.json().get("city") == "Mumbai"
    report("GET /weather?city=Mumbai → city=Mumbai", ok, r.text[:80] if not ok else "")
    assert ok


@pytest.mark.asyncio
async def test_todo_create(client: AsyncClient, auth_headers: dict):
    r = await client.post("/todos", json={"title": "E2E happy path", "description": "test"}, headers=auth_headers)
    ok = r.status_code == 200 and "Created" in r.json().get("message", "")
    report("POST /todos → Created", ok, r.text[:80] if not ok else "")
    assert ok


@pytest.mark.asyncio
async def test_todo_list(client: AsyncClient, auth_headers: dict):
    r = await client.get("/todos", headers=auth_headers)
    ok = r.status_code == 200 and "E2E happy path" in r.json().get("tasks", "")
    report("GET /todos → contains created task", ok, r.text[:80] if not ok else "")
    assert ok


@pytest.mark.asyncio
async def test_todo_update_delete(client: AsyncClient, auth_headers: dict):
    r = await client.get("/todos", headers=auth_headers)
    assert r.status_code == 200
    tasks_text = r.json().get("tasks", "")
    ids = re.findall(r"ID (\d+):", tasks_text)
    task_id = int(ids[-1]) if ids else 1
    r = await client.put(f"/todos/{task_id}", json={"status": "done"}, headers=auth_headers)
    ok_put = r.status_code == 200 and "Updated" in r.json().get("message", "")
    r = await client.delete(f"/todos/{task_id}", headers=auth_headers)
    ok_del = r.status_code == 200 and "Deleted" in r.json().get("message", "")
    report("PUT/DELETE /todos/{id} → Updated, Deleted", ok_put and ok_del, "" if (ok_put and ok_del) else r.text[:80])
    assert ok_put and ok_del


@pytest.mark.asyncio
async def test_chat_weather(client: AsyncClient, auth_headers: dict):
    r = await client.post(
        "/chat", json={"query": "What is the weather in London?"}, headers=auth_headers, timeout=60
    )
    ok = r.status_code == 200
    body = (r.json().get("response", "") or "") if ok else ""
    report("Chat: weather in London → 200, response", ok, body[:120] if not ok else "")
    assert ok


@pytest.mark.asyncio
async def test_chat_faq(client: AsyncClient, auth_headers: dict):
    r = await client.post(
        "/chat", json={"query": "What are the company working hours?"}, headers=auth_headers, timeout=60
    )
    ok = r.status_code == 200
    body = (r.json().get("response", "") or "") if ok else ""
    report("Chat: FAQ → RAG answer", ok and len(body) > 10, body[:120] if not ok else "")
    assert ok and len(body) > 10


@pytest.mark.asyncio
async def test_chat_todo(client: AsyncClient, auth_headers: dict):
    r = await client.post("/chat", json={"query": "List all my tasks"}, headers=auth_headers, timeout=60)
    ok = r.status_code == 200
    body = (r.json().get("response", "") or "") if ok else ""
    report("Chat: list tasks → non-empty", ok and len(body) > 5, body[:120] if not ok else "")
    assert ok and len(body) > 5


@pytest.mark.asyncio
async def test_chat_stream_sse(client: AsyncClient, auth_headers: dict):
    async with client.stream(
        "POST",
        "/chat/stream",
        json={"message": "What is 2+2? Reply with one number."},
        headers=auth_headers,
        timeout=30,
    ) as r:
        ok = r.status_code == 200
        chunks = []
        async for line in r.aiter_lines():
            if line and (line.startswith("data:") or line.startswith("event:")):
                chunks.append(line)
                if len(chunks) >= 5:
                    break
    report("POST /chat/stream → SSE events", ok and len(chunks) >= 1, f"chunks={len(chunks)}" if not ok else "")
    assert ok and len(chunks) >= 1


# ---------------------------------------------------------------------------
# Script runner (optional: run against live server)
# ---------------------------------------------------------------------------

def main():
    global passed, failed
    print("=" * 60)
    print("  E2E — happy path only")
    print(f"  Target: {BASE_URL}")
    print("=" * 60)

    client = httpx.Client(base_url=BASE_URL, timeout=10)
    try:
        r = client.get("/docs")
        if r.status_code != 200:
            print(f"  Server not reachable (status {r.status_code})")
            sys.exit(1)
    except httpx.ConnectError:
        print("  Cannot connect. Is the server running?")
        sys.exit(1)

    r = client.post("/auth/login", data={"username": "demo", "password": "password"})
    if r.status_code != 200 or "access_token" not in r.json():
        report("Login", False, f"status={r.status_code}")
        sys.exit(1)
    report("Login", True)
    headers = {"Authorization": f"Bearer {r.json()['access_token']}"}

    report("GET /teams", client.get("/teams", headers=headers).status_code == 200)
    report("GET /config", client.get("/config", headers=headers).status_code == 200)
    report("GET /weather", client.get("/weather", headers=headers).status_code == 200)
    report(
        "POST /todos",
        "Created" in client.post("/todos", json={"title": "Script task"}, headers=headers).json().get("message", ""),
    )
    report("GET /todos", client.get("/todos", headers=headers).status_code == 200)
    r = client.post("/chat", json={"query": "What is the weather today?"}, headers=headers, timeout=60)
    report("POST /chat (weather)", r.status_code == 200 and len((r.json().get("response") or "")) > 10)
    r = client.post("/chat/stream", json={"message": "Say hi"}, headers=headers, timeout=30)
    report("POST /chat/stream", r.status_code == 200)

    print()
    print(f"  {passed} passed, {failed} failed")
    print("=" * 60)
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
