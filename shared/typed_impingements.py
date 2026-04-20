"""Typed impingement payload schemas — director-loop cross-zone glue.

Per alpha handoff §7.1 + §7.2 (docs/research/2026-04-20-delta-queue-flow-
organization.md). The existing ``shared/impingement.Impingement`` uses a
generic ``content: dict`` payload; director-loop consumers want to type-
check that dict without duplicating validation. This module is the
typed surface: each class models one impingement's payload shape +
embeds/extracts cleanly through ``Impingement``.

Two shipped here:

- ``VoiceTierImpingement`` — director announces a tier transition
  (Phase 3b of the voice-tier spectrum integration).
- ``EngineAcquireImpingement`` — engine-ownership state change
  emitted alongside the Mode D × voice-tier mutex (Phase 3).

Pattern:

    # Producer:
    imp = VoiceTierImpingement(
        tier=VoiceTier.MEMORY, programme_band=(1, 3),
        voice_path=VoicePath.EVIL_PET, monetization_risk="none",
        since=time.time(),
    ).to_impingement()
    # Consumer (director_loop):
    payload = VoiceTierImpingement.try_from(imp)
    if payload is not None:
        director.apply_tier(payload.tier, payload.voice_path)

Scope:

- Payload-only. The outer Impingement's id/source/type/strength stays
  the generic BaseModel's concern.
- No runtime dispatch: consumers `try_from(imp)` and branch on None.
- No cross-imports from compositor; director_loop does the dispatch
  with these as a shared surface.

Reference:
    - docs/research/2026-04-20-delta-queue-flow-organization.md §7
    - docs/research/2026-04-20-voice-tier-director-integration.md §4
    - docs/research/2026-04-20-mode-d-voice-tier-mutex.md §3
"""

from __future__ import annotations

import time
from typing import Literal

from pydantic import BaseModel, Field

from shared.evil_pet_state import EvilPetMode
from shared.impingement import Impingement, ImpingementType
from shared.voice_tier import VoiceTier

MonetizationRiskLevel = Literal["none", "low", "medium", "high"]

# Source strings the director_loop matches on to dispatch. Kept as
# constants so producer/consumer pairs agree without a string-typo risk.
VOICE_TIER_IMPINGEMENT_SOURCE = "voice_tier.transition"
ENGINE_ACQUIRE_IMPINGEMENT_SOURCE = "evil_pet.engine_acquire"


class VoiceTierImpingement(BaseModel, frozen=True):
    """Payload emitted when the director picks a new voice tier.

    Five load-bearing fields named in alpha §7.1: tier, programme_band,
    voice_path, monetization_risk, since. Plus an optional
    ``excursion`` marker indicating the tier is a §4.2 excursion pick
    (bypasses structural band clamp for a single tick).
    """

    tier: VoiceTier
    programme_band: tuple[int, int]
    voice_path: str  # VoicePath value (kept as str so this module stays
    # zone-neutral — no import from agents.hapax_daimonion.voice_path)
    monetization_risk: MonetizationRiskLevel
    since: float = Field(default_factory=time.time)
    excursion: bool = False
    # Budget clamp provenance: when IntelligibilityBudget downshifted
    # the director's requested tier, record the original pick so the
    # director can log the clamp reason.
    clamped_from: VoiceTier | None = None

    def to_impingement(self, strength: float = 1.0) -> Impingement:
        """Wrap this payload in an Impingement the consumer loop reads."""
        return Impingement(
            timestamp=self.since,
            source=VOICE_TIER_IMPINGEMENT_SOURCE,
            type=ImpingementType.SALIENCE_INTEGRATION,
            strength=strength,
            content=self.model_dump(mode="json"),
            intent_family="voice.register_shift",
        )

    @classmethod
    def try_from(cls, imp: Impingement) -> VoiceTierImpingement | None:
        """Return typed view or None if this impingement isn't a tier transition."""
        if imp.source != VOICE_TIER_IMPINGEMENT_SOURCE:
            return None
        try:
            return cls.model_validate(imp.content)
        except Exception:
            return None


class EngineAcquireImpingement(BaseModel, frozen=True):
    """Payload emitted when Evil Pet engine ownership changes.

    Sent by the delta-side mutex layer (``shared.evil_pet_state.
    acquire_engine``) so the director_loop can observe ownership
    transitions without polling the SHM flag. ``accepted`` mirrors
    ``ArbitrationResult.accepted``; on reject, ``reason`` carries the
    ``blocked_by_*`` / ``debounce_*`` diagnostic.
    """

    consumer: str  # "operator", "programme", "director", "governance"
    target_mode: EvilPetMode
    accepted: bool
    reason: str
    since: float = Field(default_factory=time.time)

    def to_impingement(self, strength: float = 0.5) -> Impingement:
        return Impingement(
            timestamp=self.since,
            source=ENGINE_ACQUIRE_IMPINGEMENT_SOURCE,
            type=ImpingementType.PATTERN_MATCH,
            strength=strength,
            content=self.model_dump(mode="json"),
        )

    @classmethod
    def try_from(cls, imp: Impingement) -> EngineAcquireImpingement | None:
        if imp.source != ENGINE_ACQUIRE_IMPINGEMENT_SOURCE:
            return None
        try:
            return cls.model_validate(imp.content)
        except Exception:
            return None
