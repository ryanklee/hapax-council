"""Tests for logos API working-mode endpoints."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from logos.api.app import app


@pytest.fixture
def mode_file(tmp_path):
    f = tmp_path / "working-mode"
    f.write_text("rnd\n")
    return f


@pytest.mark.asyncio
async def test_get_working_mode_returns_current(mode_file):
    with patch("logos.api.routes.working_mode.WORKING_MODE_FILE", mode_file):
        with patch("logos.api.cache.start_refresh_loop", new_callable=AsyncMock):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/working-mode")
    assert resp.status_code == 200
    data = resp.json()
    assert data["mode"] == "rnd"
    assert "switched_at" in data


@pytest.mark.asyncio
async def test_put_working_mode_switches(mode_file):
    async def _fake_run(mode):
        mode_file.write_text(mode + "\n")
        return (0, f"Working mode -> {mode}\n")

    with patch("logos.api.routes.working_mode.WORKING_MODE_FILE", mode_file):
        with patch("logos.api.routes.working_mode._run_hapax_working_mode", side_effect=_fake_run):
            with patch("logos.api.cache.start_refresh_loop", new_callable=AsyncMock):
                transport = ASGITransport(app=app)
                async with AsyncClient(transport=transport, base_url="http://test") as client:
                    resp = await client.put("/api/working-mode", json={"mode": "research"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["mode"] == "research"


@pytest.mark.asyncio
async def test_put_working_mode_rejects_invalid(mode_file):
    with patch("logos.api.routes.working_mode.WORKING_MODE_FILE", mode_file):
        with patch("logos.api.cache.start_refresh_loop", new_callable=AsyncMock):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.put("/api/working-mode", json={"mode": "turbo"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_deprecated_cycle_mode_alias(mode_file):
    """The /api/cycle-mode endpoint still works as deprecated alias."""
    with patch("logos.api.routes.working_mode.WORKING_MODE_FILE", mode_file):
        with patch("logos.api.cache.start_refresh_loop", new_callable=AsyncMock):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/cycle-mode")
    assert resp.status_code == 200
    data = resp.json()
    assert data["mode"] == "rnd"
