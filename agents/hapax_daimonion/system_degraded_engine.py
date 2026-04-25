"""SystemDegradedEngine — Phase 6d meta-claim Bayesian wrapper.

Per Universal Bayesian Claim-Confidence research (§Phase 6d, system/meta
claims): meta-claims about Hapax's own operational state benefit from
posterior framing — `P(system_is_degraded | observed_signals)` — rather
than ad-hoc threshold gates. This module ships the engine + signal
contract; consumers (DMN governor, narration cadence, recruitment
pipeline) wire in Phase 6d-i.B.

Mirrors the SpeakerIsOperatorEngine (#1355) and PresenceEngine pattern:
- ``ClaimEngine[bool]`` internal delegate
- Asymmetric ``TemporalProfile`` (fast-enter/slow-exit — degradation
  asserts on the first strong cue, retreats only after sustained
  recovery, so callers err toward conservative behavior under doubt)
- ``LRDerivation``-typed signal weights (HPX003 compliant)
- Prior provenance ref into ``shared/prior_provenance.yaml`` (HPX004)
- ``HAPAX_BAYESIAN_BYPASS=1`` flows through the engine automatically

Phase 6d-i.A scope (this PR): module + signal contract + tests + prior
provenance entry. Phase 6d-i.B (deferred): wire to actual signals
(engine queue depth, drift detector, GPU pressure) in a follow-up so
the wiring surface is reviewed independently from the engine math.
"""

from __future__ import annotations

import logging

from shared.claim import (
    ClaimEngine,
    ClaimState,
    LRDerivation,
    TemporalProfile,
)

log = logging.getLogger(__name__)


# Engine-state translation for callers reading state vocabulary directly.
# Mirrors PresenceEngine's PRESENT/UNCERTAIN/AWAY pattern but uses
# DEGRADED/UNCERTAIN/HEALTHY for system-level claim semantics.
_ENGINE_STATE_TO_DEGRADED_STATE: dict[ClaimState, str] = {
    "ASSERTED": "DEGRADED",
    "UNCERTAIN": "UNCERTAIN",
    "RETRACTED": "HEALTHY",
}


# Default LR weights per signal. Each (p_present, p_absent) tuple
# represents (P(signal | degraded), P(signal | healthy)). Tuned for
# fast-enter / slow-exit semantics: any single strong cue lifts the
# posterior over the enter threshold within 1-2 ticks; recovery
# requires sustained absence (k_exit=12 ticks).
DEFAULT_SIGNAL_WEIGHTS: dict[str, tuple[float, float]] = {
    # Reactive engine consumer queue depth above safe-watermark.
    # Strong signal — gmail-sync drains drove the original incident
    # (3499-004), so weight reflects post-3499-004 baseline.
    "engine_queue_depth_high": (0.85, 0.05),
    # Drift detector posterior threshold breach.
    "drift_significant": (0.75, 0.10),
    # GPU memory pressure within safety margin.
    "gpu_pressure_high": (0.70, 0.08),
    # Director cadence missed (>2 consecutive ticks without narration
    # emission when impingements are queued).
    "director_cadence_missed": (0.65, 0.12),
}


class SystemDegradedEngine:
    """Bayesian posterior over P(system_is_degraded).

    Provides the same surface other Phase 6 cluster engines do —
    ``contribute(observations)``, ``posterior``, ``state``, ``reset()``,
    ``_required_ticks_for_transition`` — so consumers can swap between
    engines uniformly. State vocabulary is DEGRADED/UNCERTAIN/HEALTHY
    rather than ASSERTED/UNCERTAIN/RETRACTED.

    Phase 6d-i.B will wire the four signal sources into this engine
    via a perception loop adapter; until then the engine is constructed
    + tested against synthetic observations only.
    """

    name: str = "system_degraded_engine"
    provides: tuple[str, ...] = ("system_degraded_probability", "system_degraded_state")

    def __init__(
        self,
        prior: float = 0.10,  # System healthy by default — bias toward HEALTHY
        enter_threshold: float = 0.65,
        exit_threshold: float = 0.30,
        enter_ticks: int = 2,
        exit_ticks: int = 12,
        signal_weights: dict[str, tuple[float, float]] | None = None,
    ) -> None:
        weights = signal_weights or DEFAULT_SIGNAL_WEIGHTS
        lr_records: dict[str, LRDerivation] = {
            name: LRDerivation(
                signal_name=name,
                claim_name="system_degraded",
                source_category="expert_elicitation_shelf",
                p_true_given_h1=p_degraded,
                p_true_given_h0=p_healthy,
                positive_only=False,
                estimation_reference=(
                    "DEFAULT_SIGNAL_WEIGHTS calibrated 2026-04-25 against "
                    "post-3499-004 baseline; refined in 6d-i.B wire-in"
                ),
            )
            for name, (p_degraded, p_healthy) in weights.items()
        }
        self._engine: ClaimEngine[bool] = ClaimEngine(
            name="system_degraded",
            prior=prior,
            temporal_profile=TemporalProfile(
                enter_threshold=enter_threshold,
                exit_threshold=exit_threshold,
                k_enter=enter_ticks,
                k_exit=exit_ticks,
                k_uncertain=4,
            ),
            signal_weights=lr_records,
        )

    def contribute(self, observations: dict[str, bool | None]) -> None:
        """Apply a single tick's worth of signal observations.

        Each key must match a ``LRDerivation.signal_name`` known to the
        engine; unknown keys are silently ignored by the engine's log-
        odds fusion so callers can pass extended-vocabulary dicts
        without breaking forward compatibility.
        """
        self._engine.tick(observations)

    @property
    def posterior(self) -> float:
        return self._engine.posterior

    @property
    def state(self) -> str:
        return _ENGINE_STATE_TO_DEGRADED_STATE[self._engine.state]

    def reset(self) -> None:
        self._engine.reset()

    def _required_ticks_for_transition(self, frm: str, to: str) -> int:
        """Test-introspection helper. Translates DEGRADED/HEALTHY back
        to the engine's ASSERTED/RETRACTED vocabulary then delegates."""
        translation: dict[str, ClaimState] = {
            "DEGRADED": "ASSERTED",
            "UNCERTAIN": "UNCERTAIN",
            "HEALTHY": "RETRACTED",
        }
        return self._engine._required_ticks_for_transition(translation[frm], translation[to])


__all__ = [
    "DEFAULT_SIGNAL_WEIGHTS",
    "SystemDegradedEngine",
]
