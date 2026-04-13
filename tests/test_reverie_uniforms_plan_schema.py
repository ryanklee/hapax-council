"""Tests for `_uniforms._iter_passes` and `_load_plan_defaults` schema handling.

Regression coverage for the v1 → v2 plan schema drift that silently starved
the visual chain → GPU bridge. See
`docs/superpowers/specs/2026-04-12-reverie-bridge-repair-design.md`.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest import mock

import pytest

from agents.reverie import _uniforms


@pytest.fixture(autouse=True)
def _reset_cache():
    """Clear the module-level plan-defaults cache between tests."""
    _uniforms._plan_defaults_cache = None
    _uniforms._plan_defaults_mtime = 0.0
    yield
    _uniforms._plan_defaults_cache = None
    _uniforms._plan_defaults_mtime = 0.0


# -- _iter_passes ------------------------------------------------------------


def test_iter_passes_v1_flat():
    plan = {
        "passes": [
            {"node_id": "noise", "uniforms": {"amplitude": 0.7}},
            {"node_id": "rd", "uniforms": {"feed_rate": 0.055}},
        ]
    }
    result = list(_uniforms._iter_passes(plan))
    assert len(result) == 2
    assert result[0]["node_id"] == "noise"
    assert result[1]["node_id"] == "rd"


def test_iter_passes_v2_single_target():
    plan = {
        "version": 2,
        "targets": {
            "main": {
                "passes": [
                    {"node_id": "noise", "uniforms": {"amplitude": 0.7}},
                    {"node_id": "rd", "uniforms": {"feed_rate": 0.055}},
                    {"node_id": "color", "uniforms": {"saturation": 1.0}},
                ]
            }
        },
    }
    result = list(_uniforms._iter_passes(plan))
    assert len(result) == 3
    assert [p["node_id"] for p in result] == ["noise", "rd", "color"]


def test_iter_passes_v2_multi_target_merges():
    plan = {
        "version": 2,
        "targets": {
            "main": {"passes": [{"node_id": "noise", "uniforms": {"amplitude": 0.7}}]},
            "aux": {"passes": [{"node_id": "post", "uniforms": {"vignette_strength": 0.4}}]},
        },
    }
    result = list(_uniforms._iter_passes(plan))
    assert len(result) == 2
    node_ids = {p["node_id"] for p in result}
    assert node_ids == {"noise", "post"}


def test_iter_passes_empty_and_malformed():
    assert list(_uniforms._iter_passes({})) == []
    assert list(_uniforms._iter_passes({"version": 2})) == []
    assert list(_uniforms._iter_passes({"passes": []})) == []
    assert list(_uniforms._iter_passes({"targets": {}})) == []
    assert list(_uniforms._iter_passes({"targets": "not-a-dict"})) == []


# -- _load_plan_defaults -----------------------------------------------------


def _write_plan(tmp_path: Path, plan: dict) -> Path:
    plan_file = tmp_path / "plan.json"
    plan_file.write_text(json.dumps(plan))
    return plan_file


def test_load_plan_defaults_v2_live_shape(tmp_path: Path):
    """Mirrors the shape actually emitted by the Rust DynamicPipeline."""
    plan = {
        "version": 2,
        "targets": {
            "main": {
                "passes": [
                    {
                        "node_id": "noise",
                        "shader": "noise_gen.wgsl",
                        "type": "render",
                        "backend": "wgsl_render",
                        "inputs": [],
                        "output": "layer_0",
                        "uniforms": {
                            "frequency_x": 1.5,
                            "frequency_y": 1.0,
                            "octaves": 3.0,
                            "amplitude": 0.7,
                            "speed": 0.08,
                        },
                        "param_order": [
                            "frequency_x",
                            "frequency_y",
                            "octaves",
                            "amplitude",
                            "speed",
                        ],
                    },
                    {
                        "node_id": "color",
                        "uniforms": {
                            "saturation": 1.0,
                            "brightness": 1.0,
                            "contrast": 0.8,
                            "sepia": 0.0,
                            "hue_rotate": 0.0,
                        },
                        "param_order": [
                            "saturation",
                            "brightness",
                            "contrast",
                            "sepia",
                            "hue_rotate",
                        ],
                    },
                ]
            }
        },
    }
    plan_file = _write_plan(tmp_path, plan)

    with mock.patch.object(_uniforms, "PLAN_FILE", plan_file):
        defaults = _uniforms._load_plan_defaults()

    # All numeric uniforms land keyed as {node_id}.{param_name}.
    assert defaults["noise.amplitude"] == 0.7
    assert defaults["noise.frequency_x"] == 1.5
    assert defaults["noise.octaves"] == 3.0
    assert defaults["color.saturation"] == 1.0
    assert defaults["color.brightness"] == 1.0
    assert defaults["color.contrast"] == 0.8
    # Total count: 5 noise + 5 color.
    assert len(defaults) == 10


def test_load_plan_defaults_v1_still_supported(tmp_path: Path):
    plan = {
        "passes": [
            {"node_id": "noise", "uniforms": {"amplitude": 0.7}},
        ]
    }
    plan_file = _write_plan(tmp_path, plan)

    with mock.patch.object(_uniforms, "PLAN_FILE", plan_file):
        defaults = _uniforms._load_plan_defaults()

    assert defaults == {"noise.amplitude": 0.7}


def test_load_plan_defaults_missing_file_returns_empty(tmp_path: Path):
    missing = tmp_path / "does-not-exist.json"
    with mock.patch.object(_uniforms, "PLAN_FILE", missing):
        defaults = _uniforms._load_plan_defaults()
    assert defaults == {}


def test_load_plan_defaults_malformed_json_returns_empty(tmp_path: Path):
    bad = tmp_path / "bad.json"
    bad.write_text("{not valid json")
    with mock.patch.object(_uniforms, "PLAN_FILE", bad):
        defaults = _uniforms._load_plan_defaults()
    assert defaults == {}


def test_load_plan_defaults_v2_empty_target_returns_empty(tmp_path: Path):
    plan = {"version": 2, "targets": {"main": {"passes": []}}}
    plan_file = _write_plan(tmp_path, plan)
    with mock.patch.object(_uniforms, "PLAN_FILE", plan_file):
        defaults = _uniforms._load_plan_defaults()
    assert defaults == {}


def test_load_plan_defaults_skips_non_numeric_uniforms(tmp_path: Path):
    plan = {
        "version": 2,
        "targets": {
            "main": {
                "passes": [
                    {
                        "node_id": "noise",
                        "uniforms": {
                            "amplitude": 0.7,
                            "tag": "not-a-number",
                            "slot_opacities": [0.0, 0.0, 0.0, 0.0],
                        },
                    }
                ]
            }
        },
    }
    plan_file = _write_plan(tmp_path, plan)
    with mock.patch.object(_uniforms, "PLAN_FILE", plan_file):
        defaults = _uniforms._load_plan_defaults()
    assert defaults == {"noise.amplitude": 0.7}


def test_load_plan_defaults_caches_until_mtime_changes(tmp_path: Path):
    plan_a = {
        "version": 2,
        "targets": {"main": {"passes": [{"node_id": "noise", "uniforms": {"amplitude": 0.7}}]}},
    }
    plan_b = {
        "version": 2,
        "targets": {"main": {"passes": [{"node_id": "noise", "uniforms": {"amplitude": 0.9}}]}},
    }
    plan_file = _write_plan(tmp_path, plan_a)

    with mock.patch.object(_uniforms, "PLAN_FILE", plan_file):
        first = _uniforms._load_plan_defaults()
        assert first["noise.amplitude"] == 0.7

        # Rewrite with a newer mtime.
        plan_file.write_text(json.dumps(plan_b))
        newer_mtime = plan_file.stat().st_mtime + 1.0
        import os

        os.utime(plan_file, (newer_mtime, newer_mtime))

        second = _uniforms._load_plan_defaults()
        assert second["noise.amplitude"] == 0.9
