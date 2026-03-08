"""Pytest fixtures: test client, JWT token."""

import os

import pytest
from httpx import ASGITransport, AsyncClient

# Ensure test env doesn't hit real services
os.environ.setdefault("MILVUS_URI", "http://localhost:19530")
os.environ.setdefault("JWT_SECRET", "test-secret-at-least-256-bits-long-for-hs256")
os.environ.setdefault("OPENAI_API_KEY", "sk-test")

from src.main import app


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def token(client: AsyncClient):
    """Obtain a JWT token via login (happy path)."""
    r = await client.post(
        "/auth/login",
        data={"username": "demo", "password": "password"},
    )
    assert r.status_code == 200
    data = r.json()
    return data["access_token"]


@pytest.fixture
def auth_headers(token: str):
    """Authorization header with Bearer token."""
    return {"Authorization": f"Bearer {token}"}
