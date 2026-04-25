"""Tests for DURF (Display Under Reflective Frame) ward — Phase 2.

Phase 2 replaces Phase 1's text-classification + redaction approach with
literal Hyprland window pixel capture (per operator directive 2026-04-24
"BE my term content AS it IS"). Token classification, redaction regex,
and ring buffer tests from Phase 1 are removed because the underlying
``_classify_line_role`` / ``_PaneRing`` / ``_redact`` primitives no
longer exist on ``DURFCairoSource``.

AUDIT-01 (2026-04-25) reintroduces redaction at the pixel layer via
``durf_redaction.redact_terminal_capture`` invoked inside
``_grim_capture`` after grim writes the tmp PNG and before the atomic
``os.replace`` into the published path. Per-capture wiring is tested
here; the redaction primitive itself is covered by
``test_durf_redaction.py``.

What this file pins now:
- Source registration in the cairo_sources registry
- Construction with explicit + missing config
- Gate behavior (off when desk inactive)
- ``state()`` shape (alpha, now)
- Layout integration (default.json includes durf surface + assignment)
- AUDIT-01 wiring: SUPPRESS / UNAVAILABLE drops capture; CLEAN passes
  through; consent-safe short-circuits the poll iteration.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from agents.studio_compositor import durf_source as _durf_module
from agents.studio_compositor.cairo_sources import get_cairo_source_class
from agents.studio_compositor.durf_redaction import (
    RedactionAction,
    RedactionResult,
)
from agents.studio_compositor.durf_source import DURFCairoSource, _grim_capture

# ── Source instantiation + registration ──────────────────────────────


@pytest.fixture
def minimal_config(tmp_path):
    """Phase 2 config — same yaml shape as Phase 1, but only the
    ``panes`` block carries forward as the discovery hint list."""
    cfg = {
        "panes": [
            {"role": "alpha", "tmux_target": "nowhere:0.0", "glyph": "A-//"},
            {"role": "beta", "tmux_target": "nowhere:0.1", "glyph": "B-|/"},
        ]
    }
    path = tmp_path / "durf-panes.yaml"
    path.write_text(yaml.dump(cfg))
    return path


class TestDURFSource:
    def test_registered_in_cairo_sources(self):
        cls = get_cairo_source_class("DURFCairoSource")
        assert cls is DURFCairoSource

    def test_instantiates_with_config(self, minimal_config):
        src = DURFCairoSource(config_path=minimal_config)
        try:
            assert src.source_id == "durf"
            assert src._config_path == minimal_config
        finally:
            src.stop()

    def test_gate_false_without_desk_active(self, minimal_config):
        src = DURFCairoSource(config_path=minimal_config)
        try:
            assert src._gate_active() is False
        finally:
            src.stop()

    def test_state_returns_alpha_and_now(self, minimal_config):
        src = DURFCairoSource(config_path=minimal_config)
        try:
            state = src.state()
            assert "alpha" in state
            assert "now" in state
            assert 0.0 <= state["alpha"] <= 1.0
        finally:
            src.stop()

    def test_missing_config_handles_gracefully(self, tmp_path):
        """No yaml file at config_path: source still constructs and
        gates off — the discovery thread starts with no hints, finds
        no sessions, and reports alpha=0.0."""
        src = DURFCairoSource(config_path=tmp_path / "nonexistent.yaml")
        try:
            state = src.state()
            assert state["alpha"] == 0.0
        finally:
            src.stop()


# ── Layout parse ─────────────────────────────────────────────────────


class TestLayoutIntegration:
    def test_default_layout_includes_durf(self):
        import json

        from shared.compositor_model import Layout

        path = (
            Path(__file__).resolve().parent.parent.parent
            / "config"
            / "compositor-layouts"
            / "default.json"
        )
        d = json.loads(path.read_text())
        layout = Layout.model_validate(d)
        assert any(s.id == "durf" for s in layout.sources)
        assert any(s.id == "durf-fullframe" for s in layout.surfaces)
        assert any(a.source == "durf" for a in layout.assignments)

    def test_durf_source_full_frame_geometry(self):
        import json

        path = (
            Path(__file__).resolve().parent.parent.parent
            / "config"
            / "compositor-layouts"
            / "default.json"
        )
        d = json.loads(path.read_text())
        surf = next(s for s in d["surfaces"] if s["id"] == "durf-fullframe")
        assert surf["geometry"]["w"] == 1920
        assert surf["geometry"]["h"] == 1080
        assert surf["z_order"] == 5


# ── AUDIT-01: redaction wiring ───────────────────────────────────────


def _fake_grim_run(returncode: int = 0):
    """Build a MagicMock simulating ``subprocess.run(['grim', ...])``."""
    fake = MagicMock()
    fake.returncode = returncode
    fake.stdout = ""
    fake.stderr = ""
    return fake


class TestGrimCaptureRedactionWiring:
    """Pin: ``_grim_capture`` runs the AUDIT-01 redaction primitive
    between grim's tmp-write and the atomic ``os.replace`` into the
    published path."""

    def _patch_grim_success(self, tmp_path: Path):
        """Helper: subprocess.run(grim) succeeds + writes a tmp file."""

        # tmp_path within _grim_capture is `output_path.with_suffix(... + ".tmp")`
        def fake_run(cmd, *args, **kwargs):
            tmp = Path(cmd[-1])  # last arg is the tmp output path
            tmp.write_bytes(b"\x89PNG\r\n\x1a\nfake")
            return _fake_grim_run(0)

        return fake_run

    def test_clean_capture_publishes_png(self, tmp_path: Path) -> None:
        out = tmp_path / "alpha.png"
        with (
            patch.object(
                _durf_module.subprocess,
                "run",
                side_effect=self._patch_grim_success(tmp_path),
            ),
            patch.object(
                _durf_module,
                "redact_terminal_capture",
                return_value=RedactionResult(RedactionAction.CLEAN),
            ) as fake_redact,
        ):
            ok = _grim_capture({"x": 0, "y": 0, "w": 100, "h": 100}, out)
        assert ok is True
        assert out.exists()
        # Redaction was invoked exactly once
        assert fake_redact.call_count == 1

    def test_suppress_drops_tmp_and_published(self, tmp_path: Path) -> None:
        out = tmp_path / "alpha.png"
        # Pre-existing clean snapshot must ALSO be cleared
        out.write_bytes(b"prev clean")
        with (
            patch.object(
                _durf_module.subprocess,
                "run",
                side_effect=self._patch_grim_success(tmp_path),
            ),
            patch.object(
                _durf_module,
                "redact_terminal_capture",
                return_value=RedactionResult(
                    RedactionAction.SUPPRESS,
                    matched_pattern="anthropic_api_key",
                    detail="matched 'anthropic_api_key'",
                ),
            ),
        ):
            ok = _grim_capture({"x": 0, "y": 0, "w": 100, "h": 100}, out)
        assert ok is False
        # Both the tmp AND the previously-published path are gone
        assert not out.exists()
        assert not out.with_suffix(".png.tmp").exists()

    def test_unavailable_drops_tmp_and_published(self, tmp_path: Path) -> None:
        """OCR-unavailable is fail-closed — same outcome as SUPPRESS."""
        out = tmp_path / "alpha.png"
        out.write_bytes(b"prev clean")
        with (
            patch.object(
                _durf_module.subprocess,
                "run",
                side_effect=self._patch_grim_success(tmp_path),
            ),
            patch.object(
                _durf_module,
                "redact_terminal_capture",
                return_value=RedactionResult(
                    RedactionAction.UNAVAILABLE,
                    detail="ocr failed",
                ),
            ),
        ):
            ok = _grim_capture({"x": 0, "y": 0, "w": 100, "h": 100}, out)
        assert ok is False
        assert not out.exists()


class _StopAfterFirstWait:
    """Stand-in for :class:`threading.Event` that exits a poll loop
    after exactly one iteration: ``is_set()`` is False initially so the
    while-condition lets the body run, then ``wait()`` flips the flag
    so the next while-check exits."""

    def __init__(self) -> None:
        self._stopped = False

    def is_set(self) -> bool:
        return self._stopped

    def set(self) -> None:
        self._stopped = True

    def clear(self) -> None:
        self._stopped = False

    def wait(self, timeout: float | None = None) -> bool:
        self._stopped = True
        return True


class TestPollLoopConsentSafe:
    """Pin: when ``consent-state.txt = safe`` the poll loop refuses to
    call ``_grim_capture`` at all (defense in depth — the render gate
    already suppresses, but this prevents pixel bytes from ever
    landing in /dev/shm)."""

    def test_consent_safe_skips_capture_and_clears_state(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Stand up a source but stop its real discovery thread first.
        src = DURFCairoSource(config_path=tmp_path / "nonexistent.yaml")
        src.stop()
        # Manually populate "discovered" state to verify it gets cleared.
        src._discovered = [{"role": "alpha"}]
        src._capture_paths = {"alpha": tmp_path / "alpha.png"}

        monkeypatch.setattr(_durf_module, "_consent_safe_active", lambda: True)
        # Discovery + capture must NOT be called
        discover_spy = MagicMock(return_value=[])
        capture_spy = MagicMock(return_value=False)
        monkeypatch.setattr(_durf_module, "_discover_session_windows", discover_spy)
        monkeypatch.setattr(_durf_module, "_grim_capture", capture_spy)

        # Swap the stop event for the one-iteration stub so the loop
        # exits cleanly after running its body exactly once.
        src._stop_event = _StopAfterFirstWait()
        src._poll_loop()

        assert discover_spy.call_count == 0
        assert capture_spy.call_count == 0
        # State cleared so the render path has nothing to render
        assert src._discovered == []
        assert src._capture_paths == {}
