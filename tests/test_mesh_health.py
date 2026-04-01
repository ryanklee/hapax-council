"""Test mesh-wide health aggregation."""

import json
import os
import time

import pytest


def test_aggregate_mesh_health(tmp_path):
    from shared.mesh_health import aggregate_mesh_health

    for component, error in [("ir_perception", 0.1), ("stimmung", 0.0), ("dmn", 0.3)]:
        d = tmp_path / f"hapax-{component}"
        d.mkdir()
        (d / "health.json").write_text(
            json.dumps(
                {
                    "component": component,
                    "error": error,
                    "timestamp": time.time(),
                }
            )
        )
    result = aggregate_mesh_health(shm_root=tmp_path)
    assert result["component_count"] == 3
    assert result["worst_component"] == "dmn"
    assert result["e_mesh"] == pytest.approx(0.4 / 3, abs=0.01)


def test_stale_health_excluded(tmp_path):
    from shared.mesh_health import aggregate_mesh_health

    d = tmp_path / "hapax-old"
    d.mkdir()
    health = d / "health.json"
    health.write_text(
        json.dumps(
            {
                "component": "old",
                "error": 0.9,
                "timestamp": time.time() - 300,
            }
        )
    )
    os.utime(health, (time.time() - 300, time.time() - 300))
    result = aggregate_mesh_health(shm_root=tmp_path, stale_s=120.0)
    assert result["component_count"] == 0


def test_empty_shm(tmp_path):
    from shared.mesh_health import aggregate_mesh_health

    result = aggregate_mesh_health(shm_root=tmp_path)
    assert result["e_mesh"] == 1.0
    assert result["component_count"] == 0
