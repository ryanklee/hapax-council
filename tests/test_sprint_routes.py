"""Tests for logos API sprint endpoints."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from logos.api.app import app

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SAMPLE_STATE = {
    "sprint_id": "sprint-7",
    "active": True,
    "start_date": "2026-03-01",
    "end_date": "2026-03-29",
    "measures": [],
    "gates": [],
}

_MEASURE_FRONTMATTER = """---
id: "7.1"
title: Phenomenological scaffold
model: Phenomenological Mapping
status: completed
---
Body text here.
"""

_MEASURE_FRONTMATTER_2 = """---
id: "7.2"
title: DMN substrate probe
model: DMN Continuous Substrate
status: in_progress
---
Body text here.
"""

_GATE_FRONTMATTER = """---
id: G1
title: Sprint gate 1
status: open
---
Gate body.
"""


def _make_md_file(tmp_path: Path, name: str, content: str) -> Path:
    f = tmp_path / name
    f.write_text(content, encoding="utf-8")
    return f


# ---------------------------------------------------------------------------
# GET /api/sprint
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_sprint_state_with_shm(tmp_path: Path) -> None:
    """Returns shm state enriched with models field."""
    state_file = tmp_path / "state.json"
    state_file.write_text(json.dumps(_SAMPLE_STATE), encoding="utf-8")

    measures_dir = tmp_path / "measures"
    measures_dir.mkdir()

    with (
        patch("logos.api.routes.sprint._SHM_STATE", state_file),
        patch("logos.api.routes.sprint._VAULT_MEASURES_DIR", measures_dir),
        patch("logos.api.cache.start_refresh_loop", new_callable=AsyncMock),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/sprint")

    assert resp.status_code == 200
    data = resp.json()
    assert data["sprint_id"] == "sprint-7"
    assert data["active"] is True
    assert "models" in data
    # All 6 model baselines should be present
    assert len(data["models"]) == 6
    assert "Phenomenological Mapping" in data["models"]


@pytest.mark.asyncio
async def test_get_sprint_state_missing_shm(tmp_path: Path) -> None:
    """Returns zeroed state when shm file is absent."""
    missing = tmp_path / "nonexistent.json"
    measures_dir = tmp_path / "measures"
    measures_dir.mkdir()

    with (
        patch("logos.api.routes.sprint._SHM_STATE", missing),
        patch("logos.api.routes.sprint._VAULT_MEASURES_DIR", measures_dir),
        patch("logos.api.cache.start_refresh_loop", new_callable=AsyncMock),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/sprint")

    assert resp.status_code == 200
    data = resp.json()
    assert data["active"] is False
    assert data["sprint_id"] is None
    assert "models" in data


@pytest.mark.asyncio
async def test_get_sprint_state_model_posteriors(tmp_path: Path) -> None:
    """Model posteriors reflect completed measures in vault."""
    state_file = tmp_path / "state.json"
    state_file.write_text(json.dumps(_SAMPLE_STATE), encoding="utf-8")

    measures_dir = tmp_path / "measures"
    measures_dir.mkdir()
    _make_md_file(measures_dir, "7.1.md", _MEASURE_FRONTMATTER)
    _make_md_file(measures_dir, "7.2.md", _MEASURE_FRONTMATTER_2)

    with (
        patch("logos.api.routes.sprint._SHM_STATE", state_file),
        patch("logos.api.routes.sprint._VAULT_MEASURES_DIR", measures_dir),
        patch("logos.api.cache.start_refresh_loop", new_callable=AsyncMock),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/sprint")

    data = resp.json()
    phenom = data["models"]["Phenomenological Mapping"]
    assert phenom["measures_total"] == 1
    assert phenom["measures_completed"] == 1
    # posterior should be higher than baseline when all measures completed
    assert phenom["posterior"] > phenom["baseline"] * 0.5

    dmn = data["models"]["DMN Continuous Substrate"]
    assert dmn["measures_total"] == 1
    assert dmn["measures_completed"] == 0


# ---------------------------------------------------------------------------
# GET /api/sprint/measures
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_measures_returns_list(tmp_path: Path) -> None:
    """Returns all measures from vault directory."""
    measures_dir = tmp_path / "measures"
    measures_dir.mkdir()
    _make_md_file(measures_dir, "7.1.md", _MEASURE_FRONTMATTER)
    _make_md_file(measures_dir, "7.2.md", _MEASURE_FRONTMATTER_2)

    with (
        patch("logos.api.routes.sprint._VAULT_MEASURES_DIR", measures_dir),
        patch("logos.api.cache.start_refresh_loop", new_callable=AsyncMock),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/sprint/measures")

    assert resp.status_code == 200
    data = resp.json()
    assert "measures" in data
    assert len(data["measures"]) == 2


@pytest.mark.asyncio
async def test_get_measures_missing_vault_dir(tmp_path: Path) -> None:
    """Returns empty list when vault directory does not exist."""
    missing_dir = tmp_path / "nonexistent"

    with (
        patch("logos.api.routes.sprint._VAULT_MEASURES_DIR", missing_dir),
        patch("logos.api.cache.start_refresh_loop", new_callable=AsyncMock),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/sprint/measures")

    assert resp.status_code == 200
    assert resp.json() == {"measures": []}


# ---------------------------------------------------------------------------
# GET /api/sprint/measures/{id}
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_measure_by_id_found(tmp_path: Path) -> None:
    """Returns single measure matching the given ID."""
    measures_dir = tmp_path / "measures"
    measures_dir.mkdir()
    _make_md_file(measures_dir, "7.1.md", _MEASURE_FRONTMATTER)

    with (
        patch("logos.api.routes.sprint._VAULT_MEASURES_DIR", measures_dir),
        patch("logos.api.cache.start_refresh_loop", new_callable=AsyncMock),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/sprint/measures/7.1")

    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == "7.1"
    assert data["status"] == "completed"


@pytest.mark.asyncio
async def test_get_measure_by_id_not_found(tmp_path: Path) -> None:
    """Returns 404 when measure ID does not exist."""
    measures_dir = tmp_path / "measures"
    measures_dir.mkdir()
    _make_md_file(measures_dir, "7.1.md", _MEASURE_FRONTMATTER)

    with (
        patch("logos.api.routes.sprint._VAULT_MEASURES_DIR", measures_dir),
        patch("logos.api.cache.start_refresh_loop", new_callable=AsyncMock),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/sprint/measures/99.9")

    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /api/sprint/gates
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_gates_returns_list(tmp_path: Path) -> None:
    """Returns all gates from vault directory."""
    gates_dir = tmp_path / "gates"
    gates_dir.mkdir()
    _make_md_file(gates_dir, "G1.md", _GATE_FRONTMATTER)

    with (
        patch("logos.api.routes.sprint._VAULT_GATES_DIR", gates_dir),
        patch("logos.api.cache.start_refresh_loop", new_callable=AsyncMock),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/sprint/gates")

    assert resp.status_code == 200
    data = resp.json()
    assert "gates" in data
    assert len(data["gates"]) == 1
    assert data["gates"][0]["id"] == "G1"


@pytest.mark.asyncio
async def test_get_gates_missing_vault_dir(tmp_path: Path) -> None:
    """Returns empty list when gates directory does not exist."""
    missing_dir = tmp_path / "nonexistent"

    with (
        patch("logos.api.routes.sprint._VAULT_GATES_DIR", missing_dir),
        patch("logos.api.cache.start_refresh_loop", new_callable=AsyncMock),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/sprint/gates")

    assert resp.status_code == 200
    assert resp.json() == {"gates": []}


# ---------------------------------------------------------------------------
# GET /api/sprint/gates/{id}
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_gate_by_id_found(tmp_path: Path) -> None:
    """Returns single gate matching the given ID."""
    gates_dir = tmp_path / "gates"
    gates_dir.mkdir()
    _make_md_file(gates_dir, "G1.md", _GATE_FRONTMATTER)

    with (
        patch("logos.api.routes.sprint._VAULT_GATES_DIR", gates_dir),
        patch("logos.api.cache.start_refresh_loop", new_callable=AsyncMock),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/sprint/gates/G1")

    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == "G1"


@pytest.mark.asyncio
async def test_get_gate_by_id_not_found(tmp_path: Path) -> None:
    """Returns 404 when gate ID does not exist."""
    gates_dir = tmp_path / "gates"
    gates_dir.mkdir()
    _make_md_file(gates_dir, "G1.md", _GATE_FRONTMATTER)

    with (
        patch("logos.api.routes.sprint._VAULT_GATES_DIR", gates_dir),
        patch("logos.api.cache.start_refresh_loop", new_callable=AsyncMock),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/sprint/gates/G999")

    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /api/sprint/measures/{id}/transition
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_post_transition_completed(tmp_path: Path) -> None:
    """Writes completion signal and returns ok response."""
    completed_file = tmp_path / "completed.jsonl"

    with (
        patch("logos.api.routes.sprint._SHM_COMPLETED", completed_file),
        patch("logos.api.cache.start_refresh_loop", new_callable=AsyncMock),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/sprint/measures/7.1/transition",
                json={"status": "completed", "result_summary": "All probes passed"},
            )

    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["measure_id"] == "7.1"
    assert data["new_status"] == "completed"

    # Verify signal was written
    lines = completed_file.read_text().strip().splitlines()
    assert len(lines) == 1
    signal = json.loads(lines[0])
    assert signal["measure_id"] == "7.1"
    assert signal["trigger"] == "obsidian-plugin"
    assert signal["status"] == "completed"
    assert signal["result_summary"] == "All probes passed"


@pytest.mark.asyncio
async def test_post_transition_in_progress(tmp_path: Path) -> None:
    """Writes in_progress signal correctly."""
    completed_file = tmp_path / "completed.jsonl"

    with (
        patch("logos.api.routes.sprint._SHM_COMPLETED", completed_file),
        patch("logos.api.cache.start_refresh_loop", new_callable=AsyncMock),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/sprint/measures/7.2/transition",
                json={"status": "in_progress"},
            )

    assert resp.status_code == 200
    data = resp.json()
    assert data["new_status"] == "in_progress"


@pytest.mark.asyncio
async def test_post_transition_invalid_status(tmp_path: Path) -> None:
    """Rejects invalid status values with 422."""
    completed_file = tmp_path / "completed.jsonl"

    with (
        patch("logos.api.routes.sprint._SHM_COMPLETED", completed_file),
        patch("logos.api.cache.start_refresh_loop", new_callable=AsyncMock),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/sprint/measures/7.1/transition",
                json={"status": "invalid_value"},
            )

    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_post_transition_appends_multiple(tmp_path: Path) -> None:
    """Multiple transitions append to the same jsonl file."""
    completed_file = tmp_path / "completed.jsonl"

    with (
        patch("logos.api.routes.sprint._SHM_COMPLETED", completed_file),
        patch("logos.api.cache.start_refresh_loop", new_callable=AsyncMock),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            await client.post(
                "/api/sprint/measures/7.1/transition",
                json={"status": "in_progress"},
            )
            await client.post(
                "/api/sprint/measures/7.1/transition",
                json={"status": "completed"},
            )

    lines = completed_file.read_text().strip().splitlines()
    assert len(lines) == 2


# ---------------------------------------------------------------------------
# POST /api/sprint/gates/{id}/acknowledge
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_post_acknowledge_gate_found(tmp_path: Path) -> None:
    """Acknowledges gate nudge and writes back atomically."""
    nudge_file = tmp_path / "nudge.json"
    nudge_file.write_text(
        json.dumps({"gate_id": "G1", "acknowledged": False, "message": "Gate pending"}),
        encoding="utf-8",
    )

    with (
        patch("logos.api.routes.sprint._SHM_NUDGE", nudge_file),
        patch("logos.api.cache.start_refresh_loop", new_callable=AsyncMock),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/api/sprint/gates/G1/acknowledge")

    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["gate_id"] == "G1"

    # Verify nudge file was updated
    nudge = json.loads(nudge_file.read_text())
    assert nudge["acknowledged"] is True
    assert nudge["message"] == "Gate pending"  # other fields preserved


@pytest.mark.asyncio
async def test_post_acknowledge_gate_missing_nudge(tmp_path: Path) -> None:
    """Returns 404 when nudge.json does not exist."""
    missing_nudge = tmp_path / "nonexistent.json"

    with (
        patch("logos.api.routes.sprint._SHM_NUDGE", missing_nudge),
        patch("logos.api.cache.start_refresh_loop", new_callable=AsyncMock),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/api/sprint/gates/G1/acknowledge")

    assert resp.status_code == 404
