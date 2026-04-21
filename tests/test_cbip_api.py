"""Tests for /api/cbip endpoints — operator intensity-override surface."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from logos.api.routes.cbip import router as cbip_router


@pytest.fixture
def client(tmp_path: Path):
    """Isolate the override file to tmp_path and build a minimal FastAPI app."""
    import agents.studio_compositor.cbip.override as ov

    original = ov.DEFAULT_OVERRIDE_PATH
    ov.DEFAULT_OVERRIDE_PATH = tmp_path / "intensity-override.json"
    try:
        app = FastAPI()
        app.include_router(cbip_router)
        yield TestClient(app)
    finally:
        ov.DEFAULT_OVERRIDE_PATH = original


def test_get_default_is_auto(client: TestClient) -> None:
    """No file present → value is None ('auto')."""
    response = client.get("/api/cbip/intensity-override")
    assert response.status_code == 200
    assert response.json() == {"value": None}


def test_put_numeric_then_get(client: TestClient) -> None:
    response = client.put("/api/cbip/intensity-override", json={"value": 0.62})
    assert response.status_code == 200
    assert response.json() == {"value": 0.62}

    follow_up = client.get("/api/cbip/intensity-override")
    assert follow_up.json() == {"value": 0.62}


def test_put_auto_string_then_get(client: TestClient) -> None:
    """First set numeric, then revert to 'auto'."""
    client.put("/api/cbip/intensity-override", json={"value": 0.5})
    response = client.put("/api/cbip/intensity-override", json={"value": "auto"})
    assert response.status_code == 200
    assert response.json() == {"value": None}

    follow_up = client.get("/api/cbip/intensity-override")
    assert follow_up.json() == {"value": None}


def test_put_above_one_clamps(client: TestClient) -> None:
    response = client.put("/api/cbip/intensity-override", json={"value": 2.0})
    assert response.status_code == 200
    assert response.json() == {"value": 1.0}


def test_put_below_zero_clamps(client: TestClient) -> None:
    response = client.put("/api/cbip/intensity-override", json={"value": -0.5})
    assert response.status_code == 200
    assert response.json() == {"value": 0.0}


def test_put_arbitrary_string_treated_as_auto(client: TestClient) -> None:
    """Non-'auto' strings still revert to auto — Pydantic accepts the union."""
    response = client.put("/api/cbip/intensity-override", json={"value": "loud"})
    assert response.status_code == 200
    assert response.json() == {"value": None}
