"""Tests for query API route — persistent insight queries."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from logos.query_dispatch import QueryAgentInfo


@pytest.fixture
async def client():
    from logos.api.app import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


class TestQueryRun:
    @patch("logos.api.routes.query.start")
    @patch("logos.api.routes.query.active_count", return_value=0)
    async def test_run_returns_id_and_status(self, mock_count, mock_start, client):
        mock_start.return_value = {"id": "q-123", "status": "running"}
        resp = await client.post("/api/query/run", json={"query": "what changed today"})
        assert resp.status_code == 200
        data = resp.json()
        assert "id" in data
        assert data["status"] == "running"

    async def test_run_empty_query_rejected(self, client):
        resp = await client.post("/api/query/run", json={"query": ""})
        assert resp.status_code == 422

    @patch("logos.api.routes.query.active_count", return_value=3)
    async def test_run_rejects_when_at_capacity(self, mock_count, client):
        resp = await client.post("/api/query/run", json={"query": "test"})
        assert resp.status_code == 429


class TestQueryRefine:
    @patch("logos.api.routes.query.start")
    @patch("logos.api.routes.query.active_count", return_value=0)
    @patch("logos.api.routes.query.get_agent_list")
    async def test_refine_starts_query(self, mock_agents, mock_count, mock_start, client):
        mock_agents.return_value = [
            QueryAgentInfo(agent_type="dev_story", name="Dev Story", description="")
        ]
        mock_start.return_value = {"id": "q-456", "status": "running"}
        resp = await client.post(
            "/api/query/refine",
            json={
                "query": "expand on that",
                "parent_id": "q-123",
                "prior_result": "## Prior\nSome text",
                "agent_type": "dev_story",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == "q-456"


class TestQueryAgentList:
    @patch("logos.api.routes.query.get_agent_list")
    async def test_list_agents(self, mock_list, client):
        mock_list.return_value = [
            QueryAgentInfo(
                agent_type="dev_story", name="Dev Story", description="Search dev history"
            )
        ]
        resp = await client.get("/api/query/agents")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["agent_type"] == "dev_story"
