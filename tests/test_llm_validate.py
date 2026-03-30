"""Tests for METADATA.yaml validator."""

from __future__ import annotations

from scripts.llm_validate import validate_metadata


def test_valid_metadata():
    metadata = {
        "module": "drift_detector",
        "purpose": "Compare live infrastructure state against declared manifest",
        "version": 1,
        "interface": {
            "inputs": [{"name": "manifest", "type": "InfrastructureManifest"}],
            "outputs": [{"name": "report", "type": "DriftReport"}],
            "side_effects": [{"target": "qdrant", "collection": "drift", "operation": "upsert"}],
        },
        "dependencies": {"runtime": ["pydantic", "litellm"], "internal": []},
        "execution": {"entry": "uv run python -m agents.drift_detector"},
        "token_budget": {"self": 1800},
    }
    result = validate_metadata(metadata)
    assert result.valid
    assert result.self_contained


def test_invalid_metadata_missing_purpose():
    metadata = {"module": "test", "version": 1}
    result = validate_metadata(metadata)
    assert not result.valid
    assert any("purpose" in e for e in result.errors)


def test_not_self_contained():
    metadata = {
        "module": "test",
        "purpose": "A test module that imports from shared",
        "version": 1,
        "interface": {},
        "dependencies": {"runtime": [], "internal": ["shared.config"]},
        "execution": {},
        "token_budget": {"self": 500},
    }
    result = validate_metadata(metadata)
    assert result.valid
    assert not result.self_contained


def test_purpose_too_short():
    metadata = {
        "module": "test",
        "purpose": "Short",
        "version": 1,
        "interface": {},
        "dependencies": {"internal": []},
        "execution": {},
        "token_budget": {"self": 100},
    }
    result = validate_metadata(metadata)
    assert not result.valid
    assert any("purpose" in e for e in result.errors)


def test_version_must_be_positive_integer():
    metadata = {
        "module": "test",
        "purpose": "A valid purpose with enough length",
        "version": 0,
        "interface": {},
        "dependencies": {"internal": []},
        "execution": {},
        "token_budget": {"self": 100},
    }
    result = validate_metadata(metadata)
    assert not result.valid
    assert any("version" in e for e in result.errors)


def test_token_budget_self_non_negative():
    metadata = {
        "module": "test",
        "purpose": "A valid purpose with enough length",
        "version": 1,
        "interface": {},
        "dependencies": {"internal": []},
        "execution": {},
        "token_budget": {"self": -1},
    }
    result = validate_metadata(metadata)
    assert not result.valid
    assert any("self" in e or "token_budget" in e for e in result.errors)


def test_side_effects_operation_enum():
    metadata = {
        "module": "test",
        "purpose": "A valid purpose with enough length",
        "version": 1,
        "interface": {
            "side_effects": [{"target": "db", "operation": "invalid_op"}],
        },
        "dependencies": {"internal": []},
        "execution": {},
        "token_budget": {"self": 100},
    }
    result = validate_metadata(metadata)
    assert not result.valid


def test_additional_properties_rejected():
    metadata = {
        "module": "test",
        "purpose": "A valid purpose with enough length",
        "version": 1,
        "interface": {},
        "dependencies": {"internal": []},
        "execution": {},
        "token_budget": {"self": 100},
        "unknown_field": "should be rejected",
    }
    result = validate_metadata(metadata)
    assert not result.valid


def test_frontend_interface_props_emits():
    metadata = {
        "module": "status_widget",
        "purpose": "React component displaying real-time system status",
        "version": 1,
        "interface": {
            "props": [{"name": "status", "type": "SystemStatus", "required": True}],
            "emits": [{"event": "on-refresh", "payload": "void"}],
        },
        "dependencies": {"internal": []},
        "execution": {},
        "token_budget": {"self": 400},
    }
    result = validate_metadata(metadata)
    assert result.valid
    assert result.self_contained


def test_validation_result_has_path():
    metadata = {
        "module": "mod",
        "purpose": "A valid purpose with enough length",
        "version": 1,
        "interface": {},
        "dependencies": {"internal": []},
        "execution": {},
        "token_budget": {"self": 0},
    }
    result = validate_metadata(metadata, path="agents/mod/METADATA.yaml")
    assert result.path == "agents/mod/METADATA.yaml"
