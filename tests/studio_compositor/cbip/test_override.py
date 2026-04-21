"""Tests for cbip.override (operator manual intensity override)."""

from __future__ import annotations

import json
from pathlib import Path

from agents.studio_compositor.cbip.override import (
    OverrideValue,
    read_override,
    write_override,
)

# ── read_override ────────────────────────────────────────────────────────


def test_missing_file_reads_as_auto(tmp_path: Path) -> None:
    assert read_override(tmp_path / "absent.json") == OverrideValue(value=None)


def test_malformed_json_reads_as_auto(tmp_path: Path) -> None:
    path = tmp_path / "override.json"
    path.write_text("{ not valid json", encoding="utf-8")
    assert read_override(path) == OverrideValue(value=None)


def test_non_dict_payload_reads_as_auto(tmp_path: Path) -> None:
    path = tmp_path / "override.json"
    path.write_text(json.dumps([1, 2, 3]), encoding="utf-8")
    assert read_override(path) == OverrideValue(value=None)


def test_value_auto_string_yields_none(tmp_path: Path) -> None:
    path = tmp_path / "override.json"
    path.write_text(json.dumps({"value": "auto"}), encoding="utf-8")
    assert read_override(path) == OverrideValue(value=None)


def test_value_null_yields_none(tmp_path: Path) -> None:
    path = tmp_path / "override.json"
    path.write_text(json.dumps({"value": None}), encoding="utf-8")
    assert read_override(path) == OverrideValue(value=None)


def test_missing_value_key_yields_none(tmp_path: Path) -> None:
    path = tmp_path / "override.json"
    path.write_text(json.dumps({"other": "field"}), encoding="utf-8")
    assert read_override(path) == OverrideValue(value=None)


def test_numeric_value_roundtrips(tmp_path: Path) -> None:
    path = tmp_path / "override.json"
    path.write_text(json.dumps({"value": 0.62}), encoding="utf-8")
    assert read_override(path) == OverrideValue(value=0.62)


def test_non_numeric_value_falls_back_to_auto(tmp_path: Path) -> None:
    path = tmp_path / "override.json"
    path.write_text(json.dumps({"value": "loud"}), encoding="utf-8")
    assert read_override(path) == OverrideValue(value=None)


def test_value_above_one_clamps_on_read(tmp_path: Path) -> None:
    path = tmp_path / "override.json"
    path.write_text(json.dumps({"value": 1.5}), encoding="utf-8")
    assert read_override(path) == OverrideValue(value=1.0)


def test_value_below_zero_clamps_on_read(tmp_path: Path) -> None:
    path = tmp_path / "override.json"
    path.write_text(json.dumps({"value": -0.5}), encoding="utf-8")
    assert read_override(path) == OverrideValue(value=0.0)


# ── write_override ───────────────────────────────────────────────────────


def test_write_none_serializes_auto(tmp_path: Path) -> None:
    path = tmp_path / "override.json"
    write_override(None, path)
    assert json.loads(path.read_text(encoding="utf-8")) == {"value": "auto"}


def test_write_numeric_serializes_clamped(tmp_path: Path) -> None:
    path = tmp_path / "override.json"
    write_override(0.42, path)
    assert json.loads(path.read_text(encoding="utf-8")) == {"value": 0.42}


def test_write_above_one_clamps(tmp_path: Path) -> None:
    path = tmp_path / "override.json"
    write_override(2.5, path)
    assert json.loads(path.read_text(encoding="utf-8")) == {"value": 1.0}


def test_write_below_zero_clamps(tmp_path: Path) -> None:
    path = tmp_path / "override.json"
    write_override(-0.5, path)
    assert json.loads(path.read_text(encoding="utf-8")) == {"value": 0.0}


def test_write_creates_parent_dir(tmp_path: Path) -> None:
    path = tmp_path / "deep" / "nested" / "override.json"
    write_override(0.5, path)
    assert path.exists()


def test_write_no_partial_files_on_success(tmp_path: Path) -> None:
    path = tmp_path / "override.json"
    write_override(0.5, path)
    leftovers = [p.name for p in tmp_path.iterdir() if p.name.endswith(".tmp")]
    assert leftovers == []


# ── roundtrip ────────────────────────────────────────────────────────────


def test_roundtrip_numeric(tmp_path: Path) -> None:
    path = tmp_path / "override.json"
    write_override(0.7, path)
    assert read_override(path) == OverrideValue(value=0.7)


def test_roundtrip_auto(tmp_path: Path) -> None:
    path = tmp_path / "override.json"
    write_override(None, path)
    assert read_override(path) == OverrideValue(value=None)
