"""Happy-path tests for auth (login)."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    r = await client.post(
        "/auth/login",
        data={"username": "demo", "password": "password"},
    )
    assert r.status_code == 200
    data = r.json()
    assert "access_token" in data
    assert data.get("token_type") == "bearer"


@pytest.mark.asyncio
async def test_login_invalid_credentials(client: AsyncClient):
    r = await client.post(
        "/auth/login",
        data={"username": "demo", "password": "wrong"},
    )
    assert r.status_code == 401
