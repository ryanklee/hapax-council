"""Tests for watch wire protocol schemas."""

from __future__ import annotations

import json
import re
from pathlib import Path

SCHEMA_DIR = Path(__file__).resolve().parent.parent / "schemas" / "watch"

EXPECTED_SCHEMAS = [
    "SensorPayload.schema.json",
    "SensorReading.schema.json",
    "VoiceTriggerPayload.schema.json",
    "GesturePayload.schema.json",
    "HealthSummaryPayload.schema.json",
    "PhoneContextPayload.schema.json",
]


def test_schema_files_exist() -> None:
    """All 6 schema files and VERSION must exist."""
    for name in EXPECTED_SCHEMAS:
        assert (SCHEMA_DIR / name).exists(), f"Missing schema file: {name}"
    assert (SCHEMA_DIR / "VERSION").exists(), "Missing VERSION file"


def test_schemas_are_valid_json() -> None:
    """Every .schema.json file must parse as valid JSON."""
    for name in EXPECTED_SCHEMAS:
        path = SCHEMA_DIR / name
        text = path.read_text()
        parsed = json.loads(text)
        assert isinstance(parsed, dict), f"{name} root is not a JSON object"
        assert "properties" in parsed or "$defs" in parsed, f"{name} missing properties or $defs"


def test_voice_trigger_includes_ts() -> None:
    """Regression: VoiceTriggerPayload schema must include ts field."""
    schema = json.loads((SCHEMA_DIR / "VoiceTriggerPayload.schema.json").read_text())
    props = schema.get("properties", {})
    assert "ts" in props, "VoiceTriggerPayload schema missing 'ts' property"


def test_version_file() -> None:
    """VERSION must be semver (three dot-separated numeric parts)."""
    version = (SCHEMA_DIR / "VERSION").read_text().strip()
    assert re.match(r"^\d+\.\d+\.\d+$", version), f"VERSION not semver: {version!r}"
