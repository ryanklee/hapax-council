"""Tests for D-27: MonetizationRiskGate.assess() egress audit wire.

Covers the wire from `_record_and_return()` → `default_writer().record()`
with sampling per plan §Phase 6 lines 393-395:

  - blocks (allowed=False) and high-risk decisions: SAMPLE_HIGH (default 1.0)
  - low/none-risk allowed decisions:                 SAMPLE_LOW (default 0.1)
  - HAPAX_DEMONET_AUDIT=0:                           disabled entirely

The wire passes capability_name + programme_id + surface through to the
audit JSONL, so the audit trail is complete enough for D-17's downstream
quiet_frame subscriber (Option 2) to operate on it once that ships.
"""

from __future__ import annotations

import importlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

import shared.governance.monetization_egress_audit as audit_mod
import shared.governance.monetization_safety as safety_mod
from shared.governance.monetization_safety import (
    MonetizationRiskGate,
    RiskAssessment,
    SurfaceKind,
)


@dataclass
class _FakeCandidate:
    capability_name: str
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class _FakeProgramme:
    programme_id: str
    monetization_opt_ins: set[str] = field(default_factory=set)


@pytest.fixture
def isolated_writer(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Replace the default audit writer with one writing to tmp_path so
    each test gets its own JSONL and the production ~/hapax-state path is
    never touched.
    """
    writer = audit_mod.MonetizationEgressAudit(path=tmp_path / "audit.jsonl")
    monkeypatch.setattr(audit_mod, "_DEFAULT_WRITER", writer)
    monkeypatch.setattr(audit_mod, "default_writer", lambda: writer)
    return writer


def _force_sample_yes(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make _should_sample_audit() always return True for deterministic tests
    of the wire (sampling itself is tested separately)."""
    monkeypatch.setattr(safety_mod, "_should_sample_audit", lambda _: True)


def _force_sample_no(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(safety_mod, "_should_sample_audit", lambda _: False)


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


class TestEgressAuditWire:
    def test_high_risk_block_writes_audit_record(
        self, isolated_writer, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _force_sample_yes(monkeypatch)
        cand = _FakeCandidate("mouth.broadcast", {"monetization_risk": "high"})
        gate = MonetizationRiskGate()
        r = gate.assess(cand, programme=None, surface=SurfaceKind.TTS)
        assert r.allowed is False
        records = _read_jsonl(isolated_writer.path)
        assert len(records) == 1
        rec = records[0]
        assert rec["capability_name"] == "mouth.broadcast"
        assert rec["allowed"] is False
        assert rec["risk"] == "high"
        assert rec["surface"] == "tts"
        assert rec["programme_id"] is None

    def test_low_risk_allow_writes_audit_record_when_sampled(
        self, isolated_writer, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _force_sample_yes(monkeypatch)
        cand = _FakeCandidate("knowledge.web_search", {"monetization_risk": "low"})
        gate = MonetizationRiskGate()
        r = gate.assess(cand, programme=None)
        assert r.allowed is True
        records = _read_jsonl(isolated_writer.path)
        assert len(records) == 1
        assert records[0]["risk"] == "low"
        assert records[0]["allowed"] is True

    def test_low_risk_allow_skips_audit_when_not_sampled(
        self, isolated_writer, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _force_sample_no(monkeypatch)
        cand = _FakeCandidate("knowledge.web_search", {"monetization_risk": "low"})
        gate = MonetizationRiskGate()
        gate.assess(cand, programme=None)
        assert _read_jsonl(isolated_writer.path) == []

    def test_audit_disabled_env_skips_writes(
        self, isolated_writer, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Reload module so the env-var-derived constant picks up the override.
        monkeypatch.setenv("HAPAX_DEMONET_AUDIT", "0")
        importlib.reload(safety_mod)
        try:
            cand = _FakeCandidate("mouth.broadcast", {"monetization_risk": "high"})
            gate = safety_mod.MonetizationRiskGate()
            gate.assess(cand, programme=None)
            assert _read_jsonl(isolated_writer.path) == []
        finally:
            # Restore default for downstream tests.
            monkeypatch.delenv("HAPAX_DEMONET_AUDIT", raising=False)
            importlib.reload(safety_mod)

    def test_programme_id_propagates_to_audit(
        self, isolated_writer, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _force_sample_yes(monkeypatch)
        cand = _FakeCandidate("mouth.curated", {"monetization_risk": "medium"})
        prog = _FakeProgramme(programme_id="vinyl-sunday-001")
        gate = MonetizationRiskGate()
        gate.assess(cand, programme=prog, surface=SurfaceKind.TTS)
        records = _read_jsonl(isolated_writer.path)
        assert len(records) == 1
        assert records[0]["programme_id"] == "vinyl-sunday-001"

    def test_audit_failure_does_not_break_gate(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _force_sample_yes(monkeypatch)
        # Force the writer's record() to raise — gate must still return
        # the assessment unchanged (audit failure ≠ gate failure).
        broken_writer = audit_mod.MonetizationEgressAudit(
            path=Path("/dev/null/cannot-write-here.jsonl")
        )

        def _broken_record(*args, **kwargs):
            raise RuntimeError("simulated audit-disk failure")

        monkeypatch.setattr(broken_writer, "record", _broken_record)
        monkeypatch.setattr(audit_mod, "default_writer", lambda: broken_writer)
        cand = _FakeCandidate("mouth.broadcast", {"monetization_risk": "high"})
        gate = MonetizationRiskGate()
        r = gate.assess(cand, programme=None)
        assert r.allowed is False
        assert r.risk == "high"


class TestSamplingDecisions:
    def test_blocks_always_sampled(self) -> None:
        # SAMPLE_HIGH defaults to 1.0; verify decision logic rather than
        # randomness.
        assess = RiskAssessment(allowed=False, risk="medium", reason="test")
        with patch.object(safety_mod, "_SAMPLE_HIGH", 1.0):
            assert safety_mod._should_sample_audit(assess) is True

    def test_high_risk_always_sampled_even_when_allowed(self) -> None:
        assess = RiskAssessment(allowed=True, risk="high", reason="test")
        with patch.object(safety_mod, "_SAMPLE_HIGH", 1.0):
            assert safety_mod._should_sample_audit(assess) is True

    def test_low_risk_allow_uses_sample_low(self) -> None:
        assess = RiskAssessment(allowed=True, risk="low", reason="test")
        # Force sample_low=0 → never sample (low/none allowed).
        with patch.object(safety_mod, "_SAMPLE_LOW", 0.0):
            assert safety_mod._should_sample_audit(assess) is False
        with patch.object(safety_mod, "_SAMPLE_LOW", 1.0):
            assert safety_mod._should_sample_audit(assess) is True

    def test_audit_disabled_overrides_all_sampling(self) -> None:
        assess_block = RiskAssessment(allowed=False, risk="high", reason="test")
        assess_low = RiskAssessment(allowed=True, risk="low", reason="test")
        with patch.object(safety_mod, "_AUDIT_ENABLED", False):
            assert safety_mod._should_sample_audit(assess_block) is False
            assert safety_mod._should_sample_audit(assess_low) is False
