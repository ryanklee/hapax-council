"""Tests for logos.api.deps.consent_gate — API egress label checking."""

from __future__ import annotations

from shared.governance.consent_label import ConsentLabel


def test_gate_passes_public_data():
    from logos.api.deps.consent_gate import gate_response

    data = {"value": 42, "_consent": None}
    result = gate_response(data)
    assert result["value"] == 42
    assert "_consent" not in result


def test_gate_passes_when_label_flows():
    from logos.api.deps.consent_gate import gate_response

    data = {"value": 42, "_consent": {"label": [], "provenance": [], "labeled_at": 0}}
    result = gate_response(data)
    assert result["value"] == 42


def test_gate_redacts_when_flow_denied():
    from logos.api.deps.consent_gate import gate_response

    data = {
        "value": 42,
        "_consent": {
            "label": [{"owner": "alice", "readers": []}],
            "provenance": [],
            "labeled_at": 0,
        },
    }
    # Target is bottom (no readers) — alice's data with no readers can't flow to empty
    restricted_target = ConsentLabel(frozenset({("system", frozenset({"nobody"}))}))
    result = gate_response(data, target_label=restricted_target)
    assert result.get("_redacted") is True
