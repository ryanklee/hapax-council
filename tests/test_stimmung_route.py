"""Tests for logos API stimmung endpoint."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from logos.api.app import app

_SAMPLE_STATE = {
    "overall_stance": "cautious",
    "timestamp": 1743300000,
    "health": 0.072,
    "health_trend": "declining",
    "resource_pressure": 0.45,
    "resource_pressure_trend": "stable",
    "error_rate": 0.12,
    "processing_throughput": 0.88,
    "perception_confidence": 0.71,
    "llm_cost_pressure": 0.30,
    "grounding_quality": 0.65,
    "operator_stress": 0.55,
    "operator_energy": 0.60,
    "physiological_coherence": 0.78,
}


@pytest.mark.asyncio
async def test_get_stimmung_with_shm(tmp_path: Path) -> None:
    """Returns structured stimmung state from shm file."""
    state_file = tmp_path / "state.json"
    state_file.write_text(json.dumps(_SAMPLE_STATE), encoding="utf-8")

    with (
        patch("logos.api.routes.stimmung._SHM_STATE", state_file),
        patch("logos.api.cache.start_refresh_loop", new_callable=AsyncMock),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/stimmung")

    assert resp.status_code == 200
    data = resp.json()

    assert data["overall_stance"] == "cautious"
    assert data["timestamp"] == 1743300000
    assert "dimensions" in data

    dims = data["dimensions"]
    assert "health" in dims
    assert dims["health"]["value"] == pytest.approx(0.072)
    assert dims["health"]["trend"] == "declining"

    assert "resource_pressure" in dims
    assert dims["resource_pressure"]["value"] == pytest.approx(0.45)
    assert dims["resource_pressure"]["trend"] == "stable"

    # Verify all 10 dimension keys present
    expected_keys = [
        "health",
        "resource_pressure",
        "error_rate",
        "processing_throughput",
        "perception_confidence",
        "llm_cost_pressure",
        "grounding_quality",
        "operator_stress",
        "operator_energy",
        "physiological_coherence",
    ]
    for key in expected_keys:
        assert key in dims, f"Missing dimension: {key}"


@pytest.mark.asyncio
async def test_get_stimmung_missing_shm(tmp_path: Path) -> None:
    """Returns unknown state when shm file is absent."""
    missing_file = tmp_path / "nonexistent.json"

    with (
        patch("logos.api.routes.stimmung._SHM_STATE", missing_file),
        patch("logos.api.cache.start_refresh_loop", new_callable=AsyncMock),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/stimmung")

    assert resp.status_code == 200
    data = resp.json()
    assert data["overall_stance"] == "unknown"
    assert data["dimensions"] == {}
    assert data["timestamp"] == 0


@pytest.mark.asyncio
async def test_get_stimmung_trend_defaults_to_stable(tmp_path: Path) -> None:
    """Dimensions without a _trend key default to 'stable'."""
    # State without any trend keys
    state = {
        "overall_stance": "nominal",
        "timestamp": 999,
        "health": 0.9,
        "resource_pressure": 0.1,
        "error_rate": 0.0,
        "processing_throughput": 0.95,
        "perception_confidence": 0.8,
        "llm_cost_pressure": 0.2,
        "grounding_quality": 0.7,
        "operator_stress": 0.3,
        "operator_energy": 0.85,
        "physiological_coherence": 0.9,
    }
    state_file = tmp_path / "state.json"
    state_file.write_text(json.dumps(state), encoding="utf-8")

    with (
        patch("logos.api.routes.stimmung._SHM_STATE", state_file),
        patch("logos.api.cache.start_refresh_loop", new_callable=AsyncMock),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/stimmung")

    data = resp.json()
    for dim in data["dimensions"].values():
        assert dim["trend"] == "stable"


@pytest.mark.asyncio
async def test_get_stimmung_missing_dimension_values_default_to_zero(tmp_path: Path) -> None:
    """Dimensions not present in shm state default to 0.0."""
    # Minimal state — only overall_stance and timestamp
    state = {"overall_stance": "recovering", "timestamp": 1234}
    state_file = tmp_path / "state.json"
    state_file.write_text(json.dumps(state), encoding="utf-8")

    with (
        patch("logos.api.routes.stimmung._SHM_STATE", state_file),
        patch("logos.api.cache.start_refresh_loop", new_callable=AsyncMock),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/stimmung")

    data = resp.json()
    assert data["overall_stance"] == "recovering"
    dims = data["dimensions"]
    assert dims["health"]["value"] == 0.0
    assert dims["operator_energy"]["value"] == 0.0
