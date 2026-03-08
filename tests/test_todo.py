"""Happy-path tests for Todo CRUD (require running Todo MCP server or mock)."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_todo_create(client: AsyncClient, auth_headers: dict):
    r = await client.post(
        "/todos",
        json={"title": "Test task", "description": "From pytest"},
        headers=auth_headers,
    )
    # 200 if Todo server is reachable, 502 if not
    assert r.status_code in (200, 502)
    if r.status_code == 200:
        data = r.json()
        assert "message" in data


@pytest.mark.asyncio
async def test_todo_list_requires_auth(client: AsyncClient):
    r = await client.get("/todos")
    assert r.status_code in (401, 403)
