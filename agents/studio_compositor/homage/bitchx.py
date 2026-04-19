"""BitchX HomagePackage — first concrete member.

HOMAGE spec §5. Load-bearing authenticity distilled from the BitchX 1.3
source distribution (``github.com/BitchX/BitchX1.3``), the mIRC-16
colour contract, the CP437 raster convention, and the 16colo.rs ANSI
pack archive. Shunted through the NUANCED HOMAGE FRAMEWORK — the
grammar transfers; the substrate (IRC-messages) is replaced by the
livestream event stream.

Refuses, via the framework's validators, every anti-pattern catalogued
in spec §5.5: emoji, anti-aliased text, proportional fonts, flat-UI
chrome, ISO-8601 timestamps, rounded corners, right-aligned
timestamps, fade transitions, Swiss-grid MOTDs, box-draw inline rules.

The package's ``signature_artefacts`` seed corpus lives in
``assets/homage/bitchx/artefacts.yaml`` and is loaded at import time.

Spec: ``docs/superpowers/specs/2026-04-18-homage-framework-design.md``.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from shared.homage_package import (
    CouplingRules,
    GrammarRules,
    HomagePackage,
    HomagePalette,
    SignatureArtefact,
    SignatureRules,
    TransitionVocab,
    TypographyStack,
)
from shared.voice_register import VoiceRegister

_ARTEFACTS_PATH = (
    Path(__file__).resolve().parent.parent.parent.parent
    / "assets"
    / "homage"
    / "bitchx"
    / "artefacts.yaml"
)


def _load_artefacts() -> tuple[SignatureArtefact, ...]:
    """Load the BitchX seed corpus from YAML.

    Fatal at import time if the file is missing or malformed — the
    corpus is load-bearing for the package; the operator needs to know
    immediately, not at render time.
    """
    with _ARTEFACTS_PATH.open(encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    records = data.get("artefacts") or []
    if not isinstance(records, list):
        raise ValueError(
            f"{_ARTEFACTS_PATH}: 'artefacts' must be a list, got {type(records).__name__}"
        )
    artefacts: list[SignatureArtefact] = []
    for record in records:
        if not isinstance(record, dict):
            continue
        artefacts.append(SignatureArtefact(**record))
    return tuple(artefacts)


_BITCHX_PALETTE = HomagePalette(
    # Grey punctuation skeleton — the composition's structural rule.
    muted=(0.39, 0.39, 0.39, 1.00),
    # Bright identity — mIRC 15 (bright white); nicks, channels, stance.
    bright=(0.90, 0.90, 0.90, 1.00),
    # mIRC 11 — bright cyan; status bar fg, accent.
    accent_cyan=(0.00, 0.78, 0.78, 1.00),
    # mIRC 6 — magenta; own-message distinction.
    accent_magenta=(0.78, 0.00, 0.78, 1.00),
    # mIRC 9 — bright green; op indicator.
    accent_green=(0.20, 0.78, 0.20, 1.00),
    # mIRC 8 — yellow; highlight / warning.
    accent_yellow=(0.90, 0.90, 0.00, 1.00),
    # mIRC 4 — bright red; critical / error.
    accent_red=(0.78, 0.00, 0.00, 1.00),
    # mIRC 2 — blue; status-bar background accent.
    accent_blue=(0.20, 0.20, 0.78, 1.00),
    # Content body — dim white, default terminal.
    terminal_default=(0.80, 0.80, 0.80, 1.00),
    # Composite background; near-black with alpha so the shader surface
    # shows through.
    background=(0.04, 0.04, 0.04, 0.90),
)


_BITCHX_TYPOGRAPHY = TypographyStack(
    primary_font_family="Px437 IBM VGA 8x16",
    fallback_families=(
        "Terminus",
        "Unscii",
        "DejaVu Sans Mono",
    ),
    size_classes={
        "compact": 10,
        "normal": 14,
        "large": 18,
        "banner": 24,
    },
    weight="single",
    monospaced=True,
)


_BITCHX_GRAMMAR = GrammarRules(
    punctuation_colour_role="muted",
    identity_colour_role="bright",
    content_colour_role="terminal_default",
    line_start_marker="»»»",
    container_shape="angle-bracket",
    raster_cell_required=True,
    transition_frame_count=0,  # zero-frame instant-cut
    event_rhythm_as_texture=True,
    signed_artefacts_required=True,
)


_BITCHX_TRANSITIONS = TransitionVocab(
    supported=frozenset(
        [
            "zero-cut-in",
            "zero-cut-out",
            "join-message",
            "part-message",
            "topic-change",
            "netsplit-burst",
            "mode-change",
            "ticker-scroll-in",
            "ticker-scroll-out",
        ]
    ),
    default_entry="ticker-scroll-in",
    default_exit="ticker-scroll-out",
    max_simultaneous_entries=2,
    max_simultaneous_exits=2,
    netsplit_burst_min_interval_s=120.0,
)


_BITCHX_COUPLING = CouplingRules(
    custom_slot_index=4,
    payload_channels=(
        "active_transition_energy",
        "palette_accent_hue_deg",
        "signature_artefact_intensity",
        "rotation_phase",
    ),
    shader_feedback_enabled=True,
    shader_feedback_key="shader_energy",
)


_BITCHX_SIGNATURE = SignatureRules(
    author_tag="by Hapax/bitchx",
    attribution_inline=True,
    generated_content_only=True,
    rotation_cadence_s_steady=90.0,
    rotation_cadence_s_deliberate=180.0,
    rotation_cadence_s_rapid=30.0,
    netsplit_burst_cadence_s=120.0,
)


BITCHX_PACKAGE = HomagePackage(
    name="bitchx",
    version="1.0.0",
    description=(
        "BitchX-grammar homage: grey-punctuation skeleton, bright-identity "
        "coloring, CP437 raster, angle-bracket container, zero-frame "
        "transitions, event-rhythm as texture, signed artefacts."
    ),
    grammar=_BITCHX_GRAMMAR,
    typography=_BITCHX_TYPOGRAPHY,
    palette=_BITCHX_PALETTE,
    transition_vocabulary=_BITCHX_TRANSITIONS,
    coupling_rules=_BITCHX_COUPLING,
    signature_conventions=_BITCHX_SIGNATURE,
    voice_register_default=VoiceRegister.TEXTMODE,
    signature_artefacts=_load_artefacts(),
    refuses_anti_patterns=frozenset(
        [
            "emoji",
            "anti-aliased",
            "proportional-font",
            "flat-ui-chrome",
            "iso-8601-timestamp",
            "rounded-corners",
            "right-aligned-timestamp",
            "fade-transition",
            "swiss-grid-motd",
            "box-draw-inline-rule",
        ]
    ),
)


# ── Consent-safe variant ──────────────────────────────────────────────────
# Phase 12 / task #120. Applied when ``consent_live_egress`` flips the
# compositor into ``consent-safe`` layout (guest detected, no active
# contract). All identity accent colours collapse to muted grey, all
# signature artefacts are stripped, and the author tag is neutralised.
# This is the axiom ``it-irreversible-broadcast`` safety posture —
# HOMAGE may continue running structurally (so the compositor doesn't
# re-architect mid-stream) but emits nothing that could carry operator
# identity into the broadcast.

_BITCHX_CONSENT_SAFE_PALETTE = _BITCHX_PALETTE.model_copy(
    update={
        # Every accent role collapses to the same muted grey as the
        # punctuation skeleton. No bright identity, no coloured accents.
        "bright": _BITCHX_PALETTE.muted,
        "accent_cyan": _BITCHX_PALETTE.muted,
        "accent_magenta": _BITCHX_PALETTE.muted,
        "accent_green": _BITCHX_PALETTE.muted,
        "accent_yellow": _BITCHX_PALETTE.muted,
        "accent_red": _BITCHX_PALETTE.muted,
        "accent_blue": _BITCHX_PALETTE.muted,
        # Content body also drops to muted — no mIRC-contract foreground.
        "terminal_default": _BITCHX_PALETTE.muted,
    }
)


_BITCHX_CONSENT_SAFE_SIGNATURE = _BITCHX_SIGNATURE.model_copy(
    update={
        "author_tag": "by Hapax/bitchx-consent-safe",
        # Stretch cadences: with zero artefacts in the corpus this is
        # mostly cosmetic, but if downstream rotation timers read the
        # cadence they land on the longest interval.
        "rotation_cadence_s_steady": 180.0,
        "rotation_cadence_s_deliberate": 360.0,
        "rotation_cadence_s_rapid": 60.0,
    }
)


BITCHX_CONSENT_SAFE_PACKAGE = HomagePackage(
    name="bitchx_consent_safe",
    version="1.0.0",
    description=(
        "BitchX consent-safe variant — grammar/typography/transitions "
        "preserved; palette collapsed to a pure-grey skeleton; signature "
        "artefact corpus stripped. Engaged when the consent gate flips "
        "the compositor into consent-safe layout (axiom "
        "it-irreversible-broadcast)."
    ),
    grammar=_BITCHX_GRAMMAR,
    typography=_BITCHX_TYPOGRAPHY,
    palette=_BITCHX_CONSENT_SAFE_PALETTE,
    transition_vocabulary=_BITCHX_TRANSITIONS,
    coupling_rules=_BITCHX_COUPLING,
    signature_conventions=_BITCHX_CONSENT_SAFE_SIGNATURE,
    voice_register_default=VoiceRegister.TEXTMODE,
    signature_artefacts=(),
    refuses_anti_patterns=frozenset(
        [
            "emoji",
            "anti-aliased",
            "proportional-font",
            "flat-ui-chrome",
            "iso-8601-timestamp",
            "rounded-corners",
            "right-aligned-timestamp",
            "fade-transition",
            "swiss-grid-motd",
            "box-draw-inline-rule",
        ]
    ),
)


__all__ = ["BITCHX_CONSENT_SAFE_PACKAGE", "BITCHX_PACKAGE"]
