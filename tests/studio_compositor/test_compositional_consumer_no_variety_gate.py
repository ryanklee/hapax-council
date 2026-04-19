"""Regression pin for HOMAGE Phase F1 — camera.hero variety-gate retired.

Per ``docs/research/2026-04-19-expert-system-blinding-audit.md`` §A1, the
variety-gate at ``compositional_consumer.py:198-206`` silently dropped
6,358/45,178 (14%) of all camera.hero dispatches over 12h by rejecting
any role present in the last N picks. The recruitment pipeline had
already scored those dispatches; the gate threw the answer away.

These tests pin the retirement: a camera.hero dispatch MUST succeed
even when the same camera role was recently hero'd — the only remaining
temporal gate is the ~12s dwell window, and it applies only to the most
recent pick, not the last N.
"""

from __future__ import annotations

import json
import time

import pytest

from agents.studio_compositor import compositional_consumer as cc


@pytest.fixture
def tmp_shm(monkeypatch, tmp_path):
    monkeypatch.setattr(cc, "_HERO_CAMERA_OVERRIDE", tmp_path / "hero-camera-override.json")
    monkeypatch.setattr(cc, "_OVERLAY_ALPHA_OVERRIDES", tmp_path / "overlay-alpha-overrides.json")
    monkeypatch.setattr(cc, "_RECENT_RECRUITMENT", tmp_path / "recent-recruitment.json")
    monkeypatch.setattr(cc, "_YOUTUBE_DIRECTION", tmp_path / "youtube-direction.json")
    monkeypatch.setattr(cc, "_STREAM_MODE_INTENT", tmp_path / "stream-mode-intent.json")
    monkeypatch.setattr(cc, "_CAMERA_ROLE_HISTORY", [])
    return tmp_path


class TestNoVarietyGate:
    """Phase F1 retirement: same role dispatched N+ times still wins."""

    def test_same_role_outside_dwell_window_succeeds(self, tmp_shm):
        """A role hero'd 15s ago (past _CAMERA_MIN_DWELL_S=12.0s) must be
        dispatchable again even though the variety-gate would previously
        have rejected it for being 'in recent picks'.
        """
        past = time.time() - 15.0
        cc._CAMERA_ROLE_HISTORY.extend(
            [
                (past - 2.0, "c920-desk"),
                (past - 1.0, "c920-desk"),
                (past, "c920-desk"),
            ]
        )
        # With the variety-gate retired, the pipeline's choice of
        # c920-desk goes through; dwell gate is passed (15s >= 12s).
        assert cc.dispatch_camera_hero("cam.hero.desk-c920.deep-work", 30.0)
        data = json.loads((tmp_shm / "hero-camera-override.json").read_text())
        assert data["camera_role"] == "c920-desk"

    def test_role_present_in_last_three_picks_still_dispatches(self, tmp_shm):
        """The retired variety-gate rejected any role appearing in the
        last ``_CAMERA_VARIETY_WINDOW=3`` picks. Post-retirement a role
        that was the most-recent pick AND appeared in two of the prior
        picks must still dispatch, as long as the dwell window has
        elapsed.
        """
        past = time.time() - 30.0
        cc._CAMERA_ROLE_HISTORY.extend(
            [
                (past - 20.0, "c920-desk"),
                (past - 10.0, "brio-operator"),
                (past, "c920-desk"),
            ]
        )
        # c920-desk appears in the 3-slot history window. Under the old
        # rule this would log "variety-gate: ... in recent ..., skipping"
        # and return False. Under the new rule the pipeline's choice is
        # honored.
        assert cc.dispatch_camera_hero("cam.hero.desk-c920.track-spinning", 30.0)
        data = json.loads((tmp_shm / "hero-camera-override.json").read_text())
        assert data["camera_role"] == "c920-desk"

    def test_dwell_gate_still_blocks_rapid_reswap(self, tmp_shm):
        """Retirement is scoped: the ~12s min-dwell gate is preserved
        (it prevents frenetic cuts within a cinematic minimum). A swap
        within the dwell window to the same role still fails.
        """
        cc._CAMERA_ROLE_HISTORY.append((time.time() - 2.0, "c920-desk"))
        assert not cc.dispatch_camera_hero("cam.hero.desk-c920.deep-work", 30.0)
        # No file written because the dispatch was rejected.
        assert not (tmp_shm / "hero-camera-override.json").exists()

    def test_dispatch_writes_role_to_shm_and_records_history(self, tmp_shm):
        """End-to-end: the dispatch writes the hero-camera-override file
        and updates the history list, proving the code path that was
        previously short-circuited by the variety-gate now runs.
        """
        # Seed history so a variety-gate would reject; dwell gate clears.
        past = time.time() - 20.0
        cc._CAMERA_ROLE_HISTORY.extend(
            [
                (past - 5.0, "c920-desk"),
                (past, "c920-desk"),
            ]
        )
        before_len = len(cc._CAMERA_ROLE_HISTORY)
        assert cc.dispatch_camera_hero("cam.hero.desk-c920.deep-work", 45.0)
        # Role was recorded (proving we didn't exit early).
        assert len(cc._CAMERA_ROLE_HISTORY) == before_len + 1
        assert cc._CAMERA_ROLE_HISTORY[-1][1] == "c920-desk"
        # Write landed.
        data = json.loads((tmp_shm / "hero-camera-override.json").read_text())
        assert data["camera_role"] == "c920-desk"
        assert data["ttl_s"] == 45.0
        assert data["source_capability"] == "cam.hero.desk-c920.deep-work"
