"""Tests for audio-pathways Phase 2 — echo-cancel virtual source consumer.

Spec: docs/superpowers/specs/2026-04-18-audio-pathways-audit-design.md §3.1.
Plan: docs/superpowers/plans/2026-04-20-audio-pathways-audit-plan.md Phase 2.

Verifies:
  - resolve_source picks the first present candidate
  - resolve_source falls back when no candidate is present
  - resolve_source falls back when pw-cli output is empty (degraded)
  - DEFAULT_SOURCE_PRIORITY lists echo_cancel_capture ahead of Yeti
  - DaimonionConfig accepts a list[str] for audio_input_source
  - DaimonionConfig.audio_input_source legacy-string path warns +
    auto-wraps to a 1-element list (backward compat)
  - The PipeWire conf file at config/pipewire/hapax-echo-cancel.conf
    declares the echo_cancel_capture virtual source (regression pin)
"""

from __future__ import annotations

import logging
from pathlib import Path

import pytest  # noqa: TC002

from agents.hapax_daimonion.audio_input import (
    _AEC_SOURCE_NAME,
    _RAW_YETI_PATTERN,
    DEFAULT_SOURCE_PRIORITY,
    resolve_source,
)
from agents.hapax_daimonion.config import DaimonionConfig

# ── Resolver ───────────────────────────────────────────────────────────


class TestResolveSource:
    def test_first_present_candidate_wins(self) -> None:
        nodes = (
            "id 12, type PipeWire:Interface:Node\n"
            "  node.name = echo_cancel_capture\n"
            "id 13, type PipeWire:Interface:Node\n"
            "  node.name = alsa_input.usb-Blue_Microphones_Yeti_xx\n"
        )
        chosen = resolve_source(
            ["echo_cancel_capture", _RAW_YETI_PATTERN],
            pw_cli=lambda: nodes,
        )
        assert chosen == "echo_cancel_capture"

    def test_falls_through_to_second_when_first_absent(self) -> None:
        nodes = "id 12\n  node.name = alsa_input.usb-Blue_Microphones_Yeti_xx\n"
        chosen = resolve_source(
            ["echo_cancel_capture", _RAW_YETI_PATTERN],
            pw_cli=lambda: nodes,
        )
        assert chosen == _RAW_YETI_PATTERN

    def test_falls_back_when_no_candidate_present(self) -> None:
        nodes = "id 7\n  node.name = some_other_source\n"
        chosen = resolve_source(
            ["echo_cancel_capture", _RAW_YETI_PATTERN],
            pw_cli=lambda: nodes,
            fallback="emergency_fallback",
        )
        assert chosen == "emergency_fallback"

    def test_empty_pw_cli_output_falls_back(self) -> None:
        chosen = resolve_source(
            ["echo_cancel_capture"],
            pw_cli=lambda: "",
            fallback="degraded_default",
        )
        assert chosen == "degraded_default"

    def test_empty_candidate_list_returns_fallback(self) -> None:
        chosen = resolve_source([], pw_cli=lambda: "anything", fallback="bare_fallback")
        assert chosen == "bare_fallback"

    def test_default_priority_lists_aec_first(self) -> None:
        assert DEFAULT_SOURCE_PRIORITY[0] == _AEC_SOURCE_NAME
        assert _RAW_YETI_PATTERN in DEFAULT_SOURCE_PRIORITY


# ── Config ─────────────────────────────────────────────────────────────


class TestDaimonionConfigAudioSource:
    def test_default_is_priority_list(self) -> None:
        cfg = DaimonionConfig()
        assert isinstance(cfg.audio_input_source, list)
        assert cfg.audio_input_source[0] == "echo_cancel_capture"
        assert any("Yeti" in s for s in cfg.audio_input_source)

    def test_explicit_list_accepted(self) -> None:
        cfg = DaimonionConfig(audio_input_source=["src_a", "src_b"])
        assert cfg.audio_input_source == ["src_a", "src_b"]

    def test_legacy_string_auto_wraps_with_warning(self, caplog: pytest.LogCaptureFixture) -> None:
        """Backward compat: a single str is auto-wrapped to a 1-element
        list. The deprecation warning must fire so operator's old YAML
        configs surface in logs.
        """
        with caplog.at_level(logging.WARNING):
            cfg = DaimonionConfig(audio_input_source="legacy_single_source")  # type: ignore[arg-type]
        assert cfg.audio_input_source == ["legacy_single_source"]
        assert any("deprecated" in rec.getMessage() for rec in caplog.records)


# ── PipeWire conf regression pin ───────────────────────────────────────


class TestEchoCancelConf:
    def test_conf_file_exists(self) -> None:
        path = (
            Path(__file__).resolve().parents[2] / "config" / "pipewire" / "hapax-echo-cancel.conf"
        )
        assert path.exists(), f"missing conf file at {path}"

    def test_conf_declares_virtual_source(self) -> None:
        path = (
            Path(__file__).resolve().parents[2] / "config" / "pipewire" / "hapax-echo-cancel.conf"
        )
        text = path.read_text()
        # The capture node name daimonion looks for.
        assert "echo_cancel_capture" in text
        # WebRTC AEC backend per spec §7 Q2 default.
        assert "webrtc" in text.lower()

    def test_conf_targets_yeti_source(self) -> None:
        path = (
            Path(__file__).resolve().parents[2] / "config" / "pipewire" / "hapax-echo-cancel.conf"
        )
        text = path.read_text()
        # The mic the AEC reads from. Substring match — the device-id
        # suffix may rotate per kernel boot but "Yeti" stays stable.
        assert "Yeti" in text
