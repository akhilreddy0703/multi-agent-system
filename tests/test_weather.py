"""Happy-path tests for GET /weather."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_weather_returns_structured_data(client: AsyncClient, auth_headers: dict):
    r = await client.get("/weather", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert "city" in data
    assert "temperature_c" in data
    assert "condition" in data
    assert data["source"] == "mock"


@pytest.mark.asyncio
async def test_weather_requires_auth(client: AsyncClient):
    r = await client.get("/weather")
    assert r.status_code in (401, 403)
