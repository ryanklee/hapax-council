"""Tests for the reverie pool_metrics SHM bridge.

Exercises ``_mirror_reverie_pool_metrics`` against synthetic JSON
documents at a monkey-patched SHM path. The Rust-side publisher is
not in scope here — these tests pin the consumer side so a future
schema bump in either direction surfaces as a test failure.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

prometheus_client = pytest.importorskip("prometheus_client")

from agents.studio_compositor import metrics  # noqa: E402


def _gauge_value(gauge: object) -> float | None:
    """Return the scalar value of an unlabeled Prometheus gauge."""
    for sample_set in gauge.collect():
        for sample in sample_set.samples:
            if sample.name.startswith("reverie_pool_"):
                return sample.value
    return None


def _write_pool_metrics(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload))


def test_mirror_happy_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Happy path: all six fields propagate onto the matching gauges."""
    shm = tmp_path / "pool_metrics.json"
    _write_pool_metrics(
        shm,
        {
            "bucket_count": 3,
            "total_textures": 12,
            "total_acquires": 480,
            "total_allocations": 12,
            "reuse_ratio": 0.975,
            "slot_count": 7,
        },
    )
    monkeypatch.setattr(metrics, "_POOL_METRICS_SHM_PATH", shm)

    metrics._mirror_reverie_pool_metrics()

    assert _gauge_value(metrics.REVERIE_POOL_BUCKET_COUNT) == 3.0
    assert _gauge_value(metrics.REVERIE_POOL_TOTAL_TEXTURES) == 12.0
    assert _gauge_value(metrics.REVERIE_POOL_TOTAL_ACQUIRES) == 480.0
    assert _gauge_value(metrics.REVERIE_POOL_TOTAL_ALLOCATIONS) == 12.0
    assert _gauge_value(metrics.REVERIE_POOL_REUSE_RATIO) == pytest.approx(0.975)
    assert _gauge_value(metrics.REVERIE_POOL_SLOT_COUNT) == 7.0


def test_mirror_missing_file_is_noop(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """No SHM file → no exception, gauges are not clobbered to zero."""
    monkeypatch.setattr(metrics, "_POOL_METRICS_SHM_PATH", tmp_path / "does-not-exist.json")

    # Prime the gauges with a recognizable sentinel, then run the mirror.
    metrics.REVERIE_POOL_BUCKET_COUNT.set(42.0)

    metrics._mirror_reverie_pool_metrics()  # must not raise

    assert _gauge_value(metrics.REVERIE_POOL_BUCKET_COUNT) == 42.0


def test_mirror_malformed_json_is_noop(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Malformed JSON → logged at debug, gauges retain prior values."""
    shm = tmp_path / "pool_metrics.json"
    shm.parent.mkdir(parents=True, exist_ok=True)
    shm.write_text("{not valid json")
    monkeypatch.setattr(metrics, "_POOL_METRICS_SHM_PATH", shm)

    metrics.REVERIE_POOL_TOTAL_TEXTURES.set(99.0)
    metrics._mirror_reverie_pool_metrics()
    assert _gauge_value(metrics.REVERIE_POOL_TOTAL_TEXTURES) == 99.0


def test_mirror_partial_payload_uses_defaults(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Missing keys default to zero (except reuse_ratio which defaults 0.0)."""
    shm = tmp_path / "pool_metrics.json"
    _write_pool_metrics(shm, {"bucket_count": 1})
    monkeypatch.setattr(metrics, "_POOL_METRICS_SHM_PATH", shm)

    metrics._mirror_reverie_pool_metrics()

    assert _gauge_value(metrics.REVERIE_POOL_BUCKET_COUNT) == 1.0
    assert _gauge_value(metrics.REVERIE_POOL_TOTAL_TEXTURES) == 0.0
    assert _gauge_value(metrics.REVERIE_POOL_REUSE_RATIO) == 0.0


def test_mirror_non_dict_payload_is_ignored(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A valid JSON list at the SHM path must not crash the mirror."""
    shm = tmp_path / "pool_metrics.json"
    shm.parent.mkdir(parents=True, exist_ok=True)
    shm.write_text(json.dumps([1, 2, 3]))
    monkeypatch.setattr(metrics, "_POOL_METRICS_SHM_PATH", shm)

    metrics.REVERIE_POOL_BUCKET_COUNT.set(77.0)
    metrics._mirror_reverie_pool_metrics()
    assert _gauge_value(metrics.REVERIE_POOL_BUCKET_COUNT) == 77.0


def test_gauges_registered_on_custom_registry() -> None:
    """The new gauges land on the compositor's custom REGISTRY so the
    :9482 exporter exposes them (companion to PR #755's fix for the
    default-vs-custom registry split)."""
    assert metrics.REVERIE_POOL_BUCKET_COUNT is not None
    series_names = {
        sample.name for sample_set in metrics.REGISTRY.collect() for sample in sample_set.samples
    }
    assert "reverie_pool_bucket_count" in series_names
    assert "reverie_pool_reuse_ratio" in series_names
    assert "reverie_pool_slot_count" in series_names
