# The Foundry - Open Core LLM Training Ecosystem
# Copyright (c) 2026 Hermes Lekkas
# 
# This file is part of the open-core release (MIT License).
# See LICENSE file for full terms.

"""Tests for the FastAPI application and routes."""

import pytest
from contextlib import asynccontextmanager
from httpx import AsyncClient, ASGITransport
from foundry.orchestrator.app import create_app
from foundry.orchestrator.state import StateManager
from foundry.orchestrator.websocket import ConnectionManager


@pytest.fixture
async def app():
    """Create app with state initialized (lifespan won't run in test transport)."""
    application = create_app()
    # Manually init what lifespan would do
    state = StateManager(db_path=":memory:")
    await state.initialize()
    application.state.state_manager = state
    application.state.ws_manager = ConnectionManager()
    yield application
    await state.close()


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_health_endpoint(client):
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "version" in data
    assert "gpu" in data
    assert "tier" in data
    assert "platform" in data


@pytest.mark.asyncio
async def test_config_hardware(client):
    resp = await client.get("/api/config/hardware")
    assert resp.status_code == 200
    data = resp.json()
    assert "platform" in data
    assert "tier" in data
    assert "cpu_count" in data


@pytest.mark.asyncio
async def test_config_tiers(client):
    resp = await client.get("/api/config/tiers")
    assert resp.status_code == 200
    data = resp.json()
    assert "8gb" in data
    assert "24gb" in data


@pytest.mark.asyncio
async def test_config_settings(client):
    resp = await client.get("/api/config/settings")
    assert resp.status_code == 200
    data = resp.json()
    assert "device" in data
    assert "default_model" in data


@pytest.mark.asyncio
async def test_list_constitutions(client):
    resp = await client.get("/api/data/constitutions")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    names = [c["name"] for c in data]
    assert "agentic" in names


@pytest.mark.asyncio
async def test_list_datasets_empty(client):
    resp = await client.get("/api/data/datasets")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_list_training_jobs(client):
    resp = await client.get("/api/training/jobs")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_leaderboard(client):
    resp = await client.get("/api/eval/leaderboard")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
