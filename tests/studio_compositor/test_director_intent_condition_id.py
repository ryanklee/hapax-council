"""Phase C2 regression pin — director-intent records stamp the active condition_id.

Per the 2026-04-19 blinding-defaults audit: 994/994 of the most recent
director-intent records carried ``condition_id="none"`` because the
research-registry ``open`` command was never run for
``cond-phase-a-homage-active-001``. Phase C2 of the homage-completion
plan opens the condition and pins the director loop's stamping
behavior so future regressions are caught in CI.

This suite covers two layers:

1. ``_read_research_marker`` round-trip — given a marker file with a
   real ``condition_id``, the cached reader returns it. Given an
   absent/malformed file, the reader returns ``None``.
2. End-to-end stamping — invoking ``_emit_intent_artifacts`` with
   ``condition_id="cond-phase-a-homage-active-001"`` produces a JSONL
   line whose ``condition_id`` field matches.
3. Integration shape — a full director tick (simulated via the
   marker file + ``_emit_intent_artifacts`` invocation mirroring the
   production call path) writes the condition_id onto the JSONL
   record. Regression pin for the blinding-defaults fix.

Upstream writer path: ``scripts/research-registry.py open``.
Downstream consumer: ``agents.studio_compositor.director_loop``.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agents.studio_compositor import director_loop as dl
from shared.director_intent import CompositionalImpingement, DirectorIntent
from shared.stimmung import Stance

HOMAGE_CONDITION_ID = "cond-phase-a-homage-active-001"


def _stock_impingement() -> CompositionalImpingement:
    """CompositionalImpingement used to satisfy the operator invariant
    that every emitted DirectorIntent carries at least one."""
    return CompositionalImpingement(
        narrative="phase c2 wiring exercise",
        intent_family="overlay.emphasis",
    )


def _reset_marker_cache() -> None:
    """Blow away the marker cache so each test reads the file fresh."""
    dl._research_marker_cache["loaded_at"] = 0.0
    dl._research_marker_cache["condition_id"] = None


@pytest.fixture
def tmp_marker(tmp_path: Path, monkeypatch):
    """Point the director_loop marker path at a tmp file + reset cache."""
    marker_path = tmp_path / "research-marker.json"
    monkeypatch.setattr(dl, "_RESEARCH_MARKER_PATH", marker_path)
    _reset_marker_cache()
    yield marker_path
    _reset_marker_cache()


@pytest.fixture
def tmp_artifact_paths(tmp_path: Path, monkeypatch):
    """Route JSONL + narrative-state writes to tmp files."""
    jsonl = tmp_path / "director-intent.jsonl"
    narrative_state = tmp_path / "narrative-state.json"
    monkeypatch.setattr(dl, "_DIRECTOR_INTENT_JSONL", jsonl)
    monkeypatch.setattr(dl, "_NARRATIVE_STATE_PATH", narrative_state)
    return jsonl, narrative_state


class TestReadResearchMarker:
    def test_returns_condition_id_from_marker(self, tmp_marker: Path):
        tmp_marker.write_text(
            json.dumps({"condition_id": HOMAGE_CONDITION_ID, "written_at": "2026-04-19T06:00:00Z"})
        )
        assert dl._read_research_marker() == HOMAGE_CONDITION_ID

    def test_returns_none_when_marker_missing(self, tmp_marker: Path):
        # file not written; reader returns None
        assert not tmp_marker.exists()
        assert dl._read_research_marker() is None

    def test_returns_none_when_marker_malformed(self, tmp_marker: Path):
        tmp_marker.write_text("{not valid json")
        assert dl._read_research_marker() is None

    def test_cache_serves_repeat_reads_without_file_access(self, tmp_marker: Path):
        tmp_marker.write_text(
            json.dumps({"condition_id": HOMAGE_CONDITION_ID, "written_at": "2026-04-19T06:00:00Z"})
        )
        first = dl._read_research_marker()
        # Delete the file — cache should still return the prior value
        # within the 5 s TTL.
        tmp_marker.unlink()
        second = dl._read_research_marker()
        assert first == HOMAGE_CONDITION_ID
        assert second == HOMAGE_CONDITION_ID


class TestEmitIntentStampsCondition:
    def test_jsonl_record_carries_homage_condition_id(self, tmp_artifact_paths):
        jsonl, _ = tmp_artifact_paths
        intent = DirectorIntent(
            activity="react",
            stance=Stance.NOMINAL,
            narrative_text="testing phase c2 condition stamping",
            compositional_impingements=[_stock_impingement()],
        )
        dl._emit_intent_artifacts(intent, condition_id=HOMAGE_CONDITION_ID)
        assert jsonl.exists()
        line = jsonl.read_text().strip()
        payload = json.loads(line)
        assert payload["condition_id"] == HOMAGE_CONDITION_ID

    def test_narrative_state_carries_homage_condition_id(self, tmp_artifact_paths):
        _, narrative_state = tmp_artifact_paths
        intent = DirectorIntent(
            activity="silence",
            stance=Stance.CAUTIOUS,
            narrative_text="",
            compositional_impingements=[_stock_impingement()],
        )
        dl._emit_intent_artifacts(intent, condition_id=HOMAGE_CONDITION_ID)
        assert narrative_state.exists()
        state = json.loads(narrative_state.read_text())
        assert state["condition_id"] == HOMAGE_CONDITION_ID


class TestDirectorTickStampsConditionId:
    """Integration regression pin for the blinding-defaults fix.

    Before Phase C2, the research-registry ``open`` command was never run
    for ``cond-phase-a-homage-active-001``, so the director's marker read
    fell through to ``"none"`` on every tick. This test wires the marker
    file to carry the homage condition and asserts the resulting JSONL
    record stamps it correctly — matching the production
    ``_read_research_marker() or "none"`` fallback path in
    ``_run_tick`` / ``_run_structural_tick``.
    """

    def test_tick_simulation_writes_homage_condition_id(self, tmp_marker: Path, tmp_artifact_paths):
        jsonl, _ = tmp_artifact_paths
        # Marker file carries the homage condition (mirrors what
        # ``research-registry.py open cond-phase-a-homage-active-001``
        # produces in /dev/shm/hapax-compositor/research-marker.json).
        tmp_marker.write_text(
            json.dumps({"condition_id": HOMAGE_CONDITION_ID, "written_at": "2026-04-19T06:47:48Z"})
        )

        # Mirror the production tick path: read the marker, fall back to
        # "none" if unset, then emit.
        condition_id = dl._read_research_marker() or "none"
        assert condition_id == HOMAGE_CONDITION_ID, (
            "director tick would have stamped 'none' — blinding-defaults regression"
        )

        intent = DirectorIntent(
            activity="vinyl",
            stance=Stance.NOMINAL,
            narrative_text="record keeps going",
            compositional_impingements=[_stock_impingement()],
        )
        dl._emit_intent_artifacts(intent, condition_id=condition_id)

        line = jsonl.read_text().strip()
        payload = json.loads(line)
        assert payload["condition_id"] == HOMAGE_CONDITION_ID
        # Regression negative: explicitly NOT the "none" sentinel.
        assert payload["condition_id"] != "none"

    def test_tick_simulation_falls_through_to_none_when_marker_absent(
        self, tmp_marker: Path, tmp_artifact_paths
    ):
        """Opposite pin: when the research-registry hasn't opened any
        condition, the legacy ``"none"`` sentinel shows up on JSONL —
        which is exactly the bug Phase C2 corrects in production. This
        test ensures the fallback path itself still works so future
        registry-outage scenarios don't crash the director loop."""
        jsonl, _ = tmp_artifact_paths
        # Marker file absent — represents the pre-C2 production state.
        assert not tmp_marker.exists()

        condition_id = dl._read_research_marker() or "none"
        assert condition_id == "none"

        intent = DirectorIntent(
            activity="silence",
            stance=Stance.NOMINAL,
            narrative_text="",
            compositional_impingements=[_stock_impingement()],
        )
        dl._emit_intent_artifacts(intent, condition_id=condition_id)

        line = jsonl.read_text().strip()
        payload = json.loads(line)
        assert payload["condition_id"] == "none"
