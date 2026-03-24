"""Integration tests for query API — persistent insight queries."""

from __future__ import annotations

from unittest.mock import patch

from httpx import ASGITransport, AsyncClient

from logos.api.app import app


class TestQueryRunIntegration:
    @patch("logos.api.routes.query.start")
    @patch("logos.api.routes.query.active_count", return_value=0)
    async def test_run_returns_json_with_id(self, mock_count, mock_start):
        mock_start.return_value = {"id": "q-int-1", "status": "running"}
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/api/query/run", json={"query": "test query"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == "q-int-1"
        assert data["status"] == "running"

    async def test_empty_query_rejected(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/api/query/run", json={"query": "  "})
        assert resp.status_code == 422

    @patch("logos.api.routes.query.load_all", return_value=[])
    async def test_list_returns_queries(self, mock_load):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/query/list")
        assert resp.status_code == 200
        assert "queries" in resp.json()

    @patch("logos.api.routes.query.get")
    async def test_get_query_by_id(self, mock_get):
        mock_get.return_value = {
            "id": "q-1",
            "status": "complete",
            "query": "test",
            "result": "answer",
        }
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/query/q-1")
        assert resp.status_code == 200
        assert resp.json()["id"] == "q-1"

    @patch("logos.api.routes.query.get", return_value=None)
    async def test_get_missing_query_404(self, mock_get):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/query/nonexistent")
        assert resp.status_code == 404
