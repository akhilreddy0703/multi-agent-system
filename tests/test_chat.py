"""Happy-path tests for POST /chat."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_chat_returns_response(client: AsyncClient, auth_headers: dict):
    r = await client.post(
        "/chat",
        json={"query": "What is the weather today?"},
        headers=auth_headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert "response" in data
    assert isinstance(data["response"], str)


@pytest.mark.asyncio
async def test_chat_requires_auth(client: AsyncClient):
    r = await client.post("/chat", json={"query": "Hello"})
    assert r.status_code in (401, 403)
