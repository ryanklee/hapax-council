"""Vinyl-source chain — Mode D (granular wash) capability, DMCA-defeat vector.

Sibling of ``vocal_chain.py`` but targeting Evil Pet + Torso S-4 granular
engagement parameters for vinyl source. Where voice-chain KEEPS granular
OFF (CC 11 grains = 0, mix = 50%), Mode D INVERTS the base: grains ON,
mix fully wet, shimmer on, bit-crush allowed. The output is a re-emission
of the vinyl source from re-windowed micro-segments whose spectral-peak
constellation is distinct from the source — the empirical Content-ID
defeat vector per Smitelli 2020 (grain size ≤30 ms, spray ≥40%).

Nine vinyl-source dimensions mirror the vocal-chain architecture but
describe granular-specific behaviour: position_drift, spray, grain_size,
density, pitch_displacement, harmonic_richness, spectral_skew,
stereo_width, decay_tail. See docs/research/2026-04-20-vinyl-broadcast-
mode-d-granular-instrument.md §7 for the full design.

Governance:
- Mode D is a ``medium``-risk capability in the MonetizationRiskGate
  taxonomy. Activation requires an active Programme whose
  monetization_opt_ins contains ``mode_d_granular_wash``.
- The research gate in ``docs/research/2026-04-20-vinyl-collection-
  livestream-broadcast-safety.md`` is authoritative; if Mode D is
  invoked without programme opt-in, the pipeline filter drops it
  silently — no dry vinyl ever reaches the broadcast sink.

CC uncertainties (§7.3): Position, Spread, Size, Cloud CC numbers are
marked "verify" in the research doc. Placeholders below use educated
guesses from typical Endorphin.es conventions. Operator should confirm
against https://midi.guide/d/endorphines/evil-pet/ and patch the
_TBD_* constants. Dimensions that touch ONLY _TBD_ CCs log a warning
and no-op at send time until resolved.
"""

from __future__ import annotations

import logging
from typing import Any

from agents._affordance import CapabilityRecord, OperationalProperties
from agents._impingement import Impingement
from agents.hapax_daimonion.vocal_chain import (
    CCMapping,
    Dimension,
    _centered,
    _inverted,
    _ranged,
    cc_value_from_level,
)

log = logging.getLogger(__name__)


# CCs marked "verify" in the research doc. Placeholder values based on
# Endorphin.es family conventions; operator-verify against midi.guide.
# Setting a CC to None disables writes on that dim until resolved.
_TBD_POSITION_CC: int | None = 73  # educated guess (some EPs: 73 = pos)
_TBD_SPRAY_CC: int | None = 74  # educated guess
_TBD_GRAIN_SIZE_CC: int | None = 75  # educated guess
_TBD_CLOUD_CC: int | None = 76  # educated guess
_TBD_STEREO_WIDTH_CC: int | None = 10  # CC 10 = pan (standard MIDI); Evil Pet may use 77
_TBD_MOSAIC_POS_CC: int | None = 20  # S-4 Mosaic params (verify)
_TBD_MOSAIC_SPRAY_CC: int | None = 21
_TBD_MOSAIC_SIZE_CC: int | None = 22
_TBD_MOSAIC_RATE_CC: int | None = 23


def _optional(device: str, cc: int | None, breakpoints: list) -> CCMapping | None:
    return CCMapping(device, cc, breakpoints) if cc is not None else None


# Mode D base-scene CCs. Invert the voice-chain starting point to engage
# the granular engine. Sent once on Mode D entry via ``activate_mode_d``.
MODE_D_SCENE: list[tuple[int, int, str]] = [
    (11, 120, "Grains volume → ~94% (Mode D: granular engine DOMINANT)"),
    (40, 127, "Mix → 100% fully wet (kill dry to defeat fingerprint)"),
    (7, 127, "Volume → max (L6 handles downstream gain staging)"),
    (80, 64, "Filter type → bandpass (spectral motion)"),
    (70, 76, "Filter freq → 1 o'clock (mid spectrum)"),
    (71, 60, "Filter resonance → 70% (Mode D embraces resonance)"),
    (96, 50, "Env→filter mod → 40% (granular-following motion)"),
    (84, 40, "Saturator type → bit-crush region (Mode D allowed)"),
    (39, 50, "Saturator amount → 40% (moderate bit-crush)"),
    (95, 64, "Reverb type → room"),
    (91, 70, "Reverb amount → ~55% (deep wash)"),
    (92, 64, "Reverb tone → 12 o'clock"),
    (93, 80, "Reverb tail → 63% (long tail, cathedral territory)"),
    (94, 60, "Reverb shimmer → 47% (Mode D embraces shimmer; voice forbids)"),
]


# Build DIMENSIONS by composing optional CC mappings so TBD CCs no-op cleanly.
def _build_dimensions() -> dict[str, Dimension]:
    def _mappings_for(*pairs: CCMapping | None) -> list[CCMapping]:
        return [m for m in pairs if m is not None]

    # Inverted curve for grain_size: dim=0 → long grain (CC=127),
    # dim=1 → short grain (CC=0). Shortest grains = best defeat.
    _inverted_grain = _inverted(cc_high=127, cc_low=0)
    # Log-ish density curve — fast rise at low levels, plateau at top.
    _log_dense = [(0.0, 0), (0.3, 40), (0.7, 90), (1.0, 120)]

    return {
        "vinyl_source.position_drift": Dimension(
            name="vinyl_source.position_drift",
            description="Where in the granular buffer the read-head sits. Low = real-time vinyl follow; high = temporal drift into buffer memory. Operator's primary 'how far back' control.",
            cc_mappings=_mappings_for(
                _optional("evil_pet", _TBD_POSITION_CC, _ranged(20, 110)),
                _optional("s4", _TBD_MOSAIC_POS_CC, _ranged(20, 110)),
            ),
        ),
        "vinyl_source.spray": Dimension(
            name="vinyl_source.spray",
            description="Position randomisation per grain. PRIMARY Content-ID defeat axis — scrambles which source moment each grain comes from.",
            cc_mappings=_mappings_for(
                _optional("evil_pet", _TBD_SPRAY_CC, _ranged(0, 127)),
                _optional("s4", _TBD_MOSAIC_SPRAY_CC, _ranged(0, 127)),
            ),
        ),
        "vinyl_source.grain_size": Dimension(
            name="vinyl_source.grain_size",
            description="Length of each grain. Inverted: dim=0 → long grain (source-recognisable); dim=1 → short grain (~10 ms, microsound — defeat region).",
            cc_mappings=_mappings_for(
                _optional("evil_pet", _TBD_GRAIN_SIZE_CC, _inverted_grain),
                _optional("s4", _TBD_MOSAIC_SIZE_CC, _inverted_grain),
            ),
        ),
        "vinyl_source.density": Dimension(
            name="vinyl_source.density",
            description="Grains per second. Low = sparse stutter; high = continuous wash. Pair with small grain_size for defeat, large grain_size for aesthetic stutter.",
            cc_mappings=_mappings_for(
                _optional("evil_pet", _TBD_CLOUD_CC, _log_dense),
                _optional("s4", _TBD_MOSAIC_RATE_CC, _log_dense),
            ),
        ),
        "vinyl_source.pitch_displacement": Dimension(
            name="vinyl_source.pitch_displacement",
            description="Per-grain pitch jitter / detune. Even small jitter (±2%) defeats per-grain fingerprint match.",
            cc_mappings=[
                # CC 44 = /Detune on Evil Pet (voice-chain shares this)
                CCMapping("evil_pet", 44, _centered(64, 40)),
                CCMapping("s4", 82, _centered(64, 30)),  # Ring pitch
            ],
        ),
        "vinyl_source.harmonic_richness": Dimension(
            name="vinyl_source.harmonic_richness",
            description="Saturation + bit-crush on post-granular signal. Mode D has no intelligibility constraint (not voice) so bit-crush is allowed.",
            cc_mappings=[
                CCMapping("evil_pet", 39, _ranged(0, 110)),  # saturator amount
                CCMapping("s4", 95, _ranged(20, 80)),  # deform drive
                CCMapping("s4", 98, [(0.0, 0), (0.7, 0), (0.71, 60), (1.0, 110)]),  # crush step
            ],
        ),
        "vinyl_source.spectral_skew": Dimension(
            name="vinyl_source.spectral_skew",
            description="Filter sweep + ring resonator pitch. Shifts spectral center and adds resonant artefacts that scramble Content-ID fingerprint constellation.",
            cc_mappings=[
                CCMapping("evil_pet", 70, _ranged(20, 120)),  # filter freq
                CCMapping("s4", 79, _ranged(20, 120)),  # ring cutoff
                CCMapping("s4", 80, _ranged(15, 80)),  # ring resonance
            ],
        ),
        "vinyl_source.stereo_width": Dimension(
            name="vinyl_source.stereo_width",
            description="Spread + delay-spread. Stereo phase scrambling defeats Smitelli's mono-collapsing fingerprint.",
            cc_mappings=_mappings_for(
                _optional("evil_pet", _TBD_STEREO_WIDTH_CC, _ranged(0, 127)),
                CCMapping("s4", 117, _ranged(30, 110)),  # delay spread
            ),
        ),
        "vinyl_source.decay_tail": Dimension(
            name="vinyl_source.decay_tail",
            description="Reverb composite: amount + tail + size. Long tails place the granular wash in deep reverberant space.",
            cc_mappings=[
                CCMapping("evil_pet", 91, _ranged(30, 120)),  # reverb amount
                CCMapping("evil_pet", 93, _ranged(30, 120)),  # reverb tail
                CCMapping("s4", 114, _ranged(30, 100)),  # reverb amount
                CCMapping("s4", 115, _ranged(40, 110)),  # reverb size
                CCMapping("s4", 119, _ranged(30, 100)),  # reverb decay
            ],
        ),
    }


DIMENSIONS: dict[str, Dimension] = _build_dimensions()


VINYL_CHAIN_RECORDS = [
    CapabilityRecord(
        name=dim.name,
        description=dim.description,
        daemon="hapax_daimonion",
        operational=OperationalProperties(
            latency_class="fast",
            medium="auditory",
            # Mode D is a medium-risk capability per the broadcast-safety
            # research. MonetizationRiskGate filters it out unless an
            # active Programme opts it in via monetization_opt_ins.
            monetization_risk="medium",
            risk_reason="Mode D granular wash on vinyl source — DMCA-defeat vector; requires explicit programme opt-in for broadcast",
        ),
    )
    for dim in DIMENSIONS.values()
]


VINYL_CHAIN_AFFORDANCES = {
    "vinyl_modulation",
    "granular_wash",
    "content_id_defeat",
    "mode_d_granular_wash",
    "vinyl_transform",
}


class VinylChainCapability:
    """Mode D granular engagement on the vinyl-source chain.

    Activation semantics differ from vocal_chain:

    1. ``activate_mode_d()`` writes the Mode D base-scene CCs (grains ON,
       mix fully wet, shimmer on) — must be invoked before dimension
       modulation takes effect as Mode D.
    2. ``activate_dimension()`` updates one of the 9 vinyl-source dims,
       writing its per-device CCs.
    3. ``deactivate_mode_d()`` restores the voice-safe base (grains=0,
       mix=50, shimmer=0) — back to voice-chain territory for TTS.
    """

    def __init__(
        self,
        midi_output: Any,
        evil_pet_channel: int = 0,
        s4_channel: int = 1,
        decay_rate: float = 0.02,
    ) -> None:
        self._midi = midi_output
        self._evil_pet_ch = evil_pet_channel
        self._s4_ch = s4_channel
        self._decay_rate = decay_rate
        self._levels: dict[str, float] = {name: 0.0 for name in DIMENSIONS}
        self._activation_level = 0.0
        self._mode_d_active = False

    @property
    def name(self) -> str:
        return "vinyl_chain"

    @property
    def mode_d_active(self) -> bool:
        return self._mode_d_active

    @property
    def affordance_signature(self) -> set[str]:
        return VINYL_CHAIN_AFFORDANCES

    @property
    def activation_cost(self) -> float:
        return 0.05

    @property
    def activation_level(self) -> float:
        return self._activation_level

    @property
    def consent_required(self) -> bool:
        return False

    @property
    def priority_floor(self) -> bool:
        return False

    def activate_mode_d(self) -> None:
        """Write Mode D base-scene CCs to Evil Pet. Must be called before
        dimension modulation takes effect as granular wash."""
        for cc, value, note in MODE_D_SCENE:
            try:
                self._midi.send_cc(channel=self._evil_pet_ch, cc=cc, value=value)
            except Exception:
                log.warning("Mode D scene CC failed: CC%d=%d (%s)", cc, value, note, exc_info=True)
        self._mode_d_active = True
        log.info("Vinyl chain: Mode D scene written (granular wash engaged)")

    def deactivate_mode_d(self) -> None:
        """Restore voice-safe base: grains=0, mix=50, shimmer=0."""
        revert = [
            (11, 0, "Grains → 0"),
            (40, 64, "Mix → 50%"),
            (94, 0, "Shimmer → 0"),
            (84, 10, "Saturator type → distortion (voice-safe)"),
        ]
        for cc, value, _note in revert:
            try:
                self._midi.send_cc(channel=self._evil_pet_ch, cc=cc, value=value)
            except Exception:
                log.warning("Mode D deactivate CC failed: CC%d=%d", cc, value, exc_info=True)
        for name in self._levels:
            self._levels[name] = 0.0
        self._activation_level = 0.0
        self._mode_d_active = False
        log.info("Vinyl chain: Mode D deactivated, voice-safe base restored")

    def activate_dimension(
        self, dimension_name: str, impingement: Impingement, level: float
    ) -> None:
        if dimension_name not in DIMENSIONS:
            log.debug("Unknown vinyl dimension: %s", dimension_name)
            return
        if not self._mode_d_active:
            log.debug("activate_dimension on %s ignored — Mode D not active", dimension_name)
            return
        self._levels[dimension_name] = max(0.0, min(1.0, level))
        self._activation_level = max(self._levels.values())
        self._send_dimension_cc(dimension_name)

    def get_dimension_level(self, dimension_name: str) -> float:
        key = dimension_name if dimension_name in self._levels else f"vinyl_source.{dimension_name}"
        return self._levels.get(key, 0.0)

    def decay(self, elapsed_s: float) -> None:
        if not self._mode_d_active:
            return
        amount = self._decay_rate * elapsed_s
        any_active = False
        for name in list(self._levels):
            if self._levels[name] > 0.0:
                self._levels[name] = max(0.0, self._levels[name] - amount)
                if self._levels[name] > 0.0:
                    any_active = True
                self._send_dimension_cc(name)
        self._activation_level = max(self._levels.values()) if any_active else 0.0

    def _send_dimension_cc(self, dimension_name: str) -> None:
        dim = DIMENSIONS[dimension_name]
        level = self._levels[dimension_name]
        for mapping in dim.cc_mappings:
            value = cc_value_from_level(level, mapping.breakpoints)
            channel = self._evil_pet_ch if mapping.device == "evil_pet" else self._s4_ch
            try:
                self._midi.send_cc(channel=channel, cc=mapping.cc, value=value)
            except Exception:
                log.debug("CC send failed: %s", dimension_name, exc_info=True)
