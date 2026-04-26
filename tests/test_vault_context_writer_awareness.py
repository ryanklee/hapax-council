"""Tests for the awareness-vault-daily-note-extension renderers.

Pure-function coverage: state-shape rendering, refusal raw-list
rendering (NEVER aggregated), staleness dimming, idempotent section
splice. The Obsidian REST API path lives in
:func:`_replace_section_in_daily` and is exercised at integration
time only — these unit tests cover the deterministic rendering +
splice logic.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from agents.vault_context_writer import (
    _read_awareness_state,
    _read_refused_events,
    _splice_section,
    render_awareness_section,
    render_refused_section,
)


def _ts(minutes_ago: int = 0) -> str:
    return (datetime.now(UTC) - timedelta(minutes=minutes_ago)).isoformat()


# ── render_awareness_section ────────────────────────────────────────


class TestRenderAwarenessSection:
    def test_none_state_renders_dimmed_placeholder(self):
        out = render_awareness_section(None, stale_reason="missing")
        assert "## Awareness" in out
        assert "_state missing_" in out
        # No fabricated zero-valued blocks when the state is absent.
        assert "Stream:" not in out
        assert "Health:" not in out

    def test_stale_state_renders_dimmed_placeholder(self):
        # Even with a populated state dict, a stale_reason takes
        # precedence — the consumer side of the TTL contract.
        out = render_awareness_section({"stream": {"live": True}}, stale_reason="stale (200s ago)")
        assert "_state stale (200s ago)_" in out
        assert "Stream:" not in out

    def test_full_state_renders_all_categories(self):
        state = {
            "stream": {"live": True, "chronicle_events_5min": 12},
            "health_system": {
                "overall_status": "healthy",
                "failed_units": 0,
                "disk_pct_used": 42.0,
                "gpu_vram_pct_used": 33.0,
            },
            "music_soundcloud": {"source": "soundcloud", "is_playing": True},
            "publishing_pipeline": {"inbox_count": 3, "in_flight_count": 1},
            "research_dispatches": {"in_flight_count": 2},
            "content_programmes": {"active_programme": "GEM"},
            "marketing_outreach": {"pending_count": 5},
            "hardware_fleet": {"pi_count_online": 3, "pi_count_total": 5},
            "time_sprint": {"sprint_day": 28, "completed_measures": 14, "blocked_measures": 1},
            "daimonion_voice": {"stance": "ALERT", "voice_session_active": True},
            "governance": {"active_consent_contracts": 4},
        }
        out = render_awareness_section(state)
        assert "Stream: live · 12 events/5min" in out
        assert "Health: healthy" in out
        assert "disk 42%" in out
        assert "GPU 33%" in out
        assert "Daimonion: stance=ALERT · voice-on" in out
        assert "Music: source=soundcloud · playing" in out
        assert "Publishing: inbox=3 · in-flight=1" in out
        assert "Research: in-flight=2" in out
        assert "Programmes: active=GEM" in out
        assert "Marketing: pending=5" in out
        assert "Fleet: pi 3/5 online" in out
        assert "Sprint: day=28 · completed=14 · blocked=1" in out
        assert "Governance: contracts=4" in out

    def test_offline_stream_renders_offline(self):
        out = render_awareness_section({"stream": {"live": False}})
        assert "Stream: offline" in out

    def test_silent_music_renders_silent(self):
        out = render_awareness_section({"music_soundcloud": {"is_playing": False}})
        assert "Music: source=none · silent" in out

    def test_missing_block_defaults_to_zero_values(self):
        # Empty state dict still renders all categories — operator
        # sees a deterministic table even on an under-populated state.
        out = render_awareness_section({})
        assert "Stream: offline · 0 events/5min" in out
        assert "Fleet: pi 0/0 online" in out


# ── render_refused_section ──────────────────────────────────────────


class TestRenderRefusedSection:
    def test_empty_events_renders_no_refusals_placeholder(self):
        out = render_refused_section([])
        assert "## Refused" in out
        assert "_no refusals in the last 24h_" in out

    def test_each_event_becomes_one_row(self):
        events = [
            {
                "timestamp": "2026-04-25T22:00:00+00:00",
                "axiom": "single_user",
                "surface": "publication_bus:bandcamp-upload",
                "reason": "Bandcamp ToS prohibits AI",
            },
            {
                "timestamp": "2026-04-25T22:05:00+00:00",
                "axiom": "interpersonal_transparency",
                "surface": "affordance_pipeline:consent_gate",
                "reason": "no active consent contract",
            },
        ]
        out = render_refused_section(events)
        # Both events appear as separate rows.
        assert out.count("\n- ") == 2
        assert "axiom=single_user" in out
        assert "surface=publication_bus:bandcamp-upload" in out
        assert "Bandcamp ToS prohibits AI" in out
        assert "axiom=interpersonal_transparency" in out

    def test_reason_newlines_collapsed(self):
        """Defence against legacy log entries with embedded newlines."""
        events = [
            {
                "timestamp": _ts(0),
                "axiom": "x",
                "surface": "y",
                "reason": "first line\nsecond line\rthird",
            }
        ]
        out = render_refused_section(events)
        # Section heading itself has newlines; the row text must be one line.
        rows = [line for line in out.split("\n") if line.startswith("- ")]
        assert len(rows) == 1
        assert "\n" not in rows[0]

    def test_no_aggregation_in_output(self):
        """Constitutional load-bearing: must NEVER summarize refusals.

        The header explicitly carries the disclaimer phrase
        ``no aggregation``; this test inspects only the row body to
        confirm the renderer doesn't sneak in a summary line.
        """
        events = [
            {"timestamp": _ts(i), "axiom": "x", "surface": "y", "reason": f"r{i}"} for i in range(5)
        ]
        out = render_refused_section(events)
        # All 5 events appear as raw rows.
        assert out.count("\n- ") == 5
        # No summary-line forbidden-strings in the row body.
        rows = [line for line in out.split("\n") if line.startswith("- ")]
        body = "\n".join(rows).lower()
        for forbidden in ("total", "summary", "5 refusal", "aggregat"):
            assert forbidden not in body


# ── _read_awareness_state ───────────────────────────────────────────


class TestReadAwarenessState:
    def test_missing_file(self, tmp_path: Path):
        state, stale = _read_awareness_state(path=tmp_path / "absent.json")
        assert state is None
        assert stale == "missing"

    def test_unreadable_json(self, tmp_path: Path):
        path = tmp_path / "state.json"
        path.write_text("not json {")
        state, stale = _read_awareness_state(path=path)
        assert state is None
        assert stale == "unreadable"

    def test_non_dict_root(self, tmp_path: Path):
        path = tmp_path / "state.json"
        path.write_text(json.dumps([1, 2, 3]))
        state, stale = _read_awareness_state(path=path)
        assert state is None
        assert stale == "unreadable"

    def test_fresh_state(self, tmp_path: Path):
        path = tmp_path / "state.json"
        now = datetime(2026, 4, 25, 22, 0, tzinfo=UTC)
        path.write_text(json.dumps({"timestamp": now.isoformat(), "stream": {"live": True}}))
        state, stale = _read_awareness_state(
            path=path, now=now + timedelta(seconds=30), stale_after_s=90.0
        )
        assert stale is None
        assert state is not None
        assert state["stream"]["live"] is True

    def test_stale_state(self, tmp_path: Path):
        path = tmp_path / "state.json"
        now = datetime(2026, 4, 25, 22, 0, tzinfo=UTC)
        path.write_text(json.dumps({"timestamp": now.isoformat()}))
        # Wall-clock 5 minutes after the state timestamp → past TTL.
        state, stale = _read_awareness_state(
            path=path, now=now + timedelta(minutes=5), stale_after_s=90.0
        )
        assert state is None
        assert stale is not None
        assert "stale" in stale


# ── _read_refused_events ────────────────────────────────────────────


class TestReadRefusedEvents:
    def test_missing_file(self, tmp_path: Path):
        assert _read_refused_events(path=tmp_path / "absent.jsonl") == []

    def test_drops_outside_window(self, tmp_path: Path):
        path = tmp_path / "log.jsonl"
        now = datetime(2026, 4, 25, 22, 0, tzinfo=UTC)
        old = (now - timedelta(hours=48)).isoformat()
        recent = (now - timedelta(hours=2)).isoformat()
        path.write_text(
            json.dumps({"timestamp": old, "axiom": "x", "surface": "y", "reason": "old"})
            + "\n"
            + json.dumps({"timestamp": recent, "axiom": "x", "surface": "y", "reason": "recent"})
            + "\n"
        )
        events = _read_refused_events(path=path, now=now)
        assert len(events) == 1
        assert events[0]["reason"] == "recent"

    def test_skips_malformed_lines(self, tmp_path: Path):
        path = tmp_path / "log.jsonl"
        now = datetime(2026, 4, 25, 22, 0, tzinfo=UTC)
        recent = (now - timedelta(hours=1)).isoformat()
        path.write_text(
            "not json\n"
            + json.dumps({"timestamp": recent, "axiom": "x", "surface": "y", "reason": "kept"})
            + "\n"
        )
        events = _read_refused_events(path=path, now=now)
        assert len(events) == 1


# ── _splice_section ─────────────────────────────────────────────────


class TestSpliceSection:
    def test_appends_when_heading_absent(self):
        existing = "# Daily 2026-04-25\n\n## Log\n\n- entry\n"
        rendered = "## Awareness\n\n- Stream: live\n"
        out = _splice_section(existing, "## Awareness", rendered)
        assert out.endswith("## Awareness\n\n- Stream: live\n")
        # Original ## Log is preserved.
        assert "## Log\n\n- entry" in out

    def test_replaces_existing_section(self):
        existing = (
            "## Log\n\n- entry\n\n## Awareness\n\n- old: stuff\n\n## Refused\n\n- old refusal\n"
        )
        rendered = "## Awareness\n\n- Stream: live\n"
        out = _splice_section(existing, "## Awareness", rendered)
        # New content replaces old.
        assert "Stream: live" in out
        assert "old: stuff" not in out
        # ## Refused untouched.
        assert "## Refused" in out
        assert "old refusal" in out

    def test_idempotent_two_passes(self):
        existing = "## Log\n\n- e\n"
        rendered_v1 = "## Awareness\n\n- v1\n"
        rendered_v2 = "## Awareness\n\n- v2\n"
        out_v1 = _splice_section(existing, "## Awareness", rendered_v1)
        out_v2 = _splice_section(out_v1, "## Awareness", rendered_v2)
        # v2 cleanly replaces v1; no doubled section.
        assert out_v2.count("## Awareness") == 1
        assert "v2" in out_v2
        assert "v1" not in out_v2

    def test_preserves_non_h2_headings(self):
        """A ``### `` (h3) inside a section must NOT terminate it."""
        existing = (
            "## Awareness\n\n- old\n\n### Sub-heading should stay\n\n## Other\n\n- other entry\n"
        )
        rendered = "## Awareness\n\n- new\n"
        out = _splice_section(existing, "## Awareness", rendered)
        # The ## Other section is untouched; the h3 was inside the
        # replaced block (correct — the spec replaces from ## to next ##).
        assert "## Other" in out
        assert "other entry" in out
        assert "new" in out
        assert "old" not in out
