"""Transition choreographer — emits ritual-scope impingements at programme boundaries.

The choreographer NEVER invokes capabilities directly. Instead, every
boundary fires four ritual-scope impingements that the affordance
pipeline recruits against:

    1. ``programme.exit_ritual.<from_role>``  — high-salience exit rite
    2. ``programme.boundary.freeze``          — biases cadence priors low
    3. ``programme.palette.shift.<to_role>``  — biases Reverie palette
    4. ``programme.entry_ritual.<to_role>``   — high-salience entry rite

Which ward lights up, which signature artefact rotates, which
choreography emits — all chosen by the affordance pipeline against the
ritual narrative. There is no choreographer-internal list of "the exit
moves are X, Y, Z."

This is the concrete encoding of `project_programmes_enable_grounding`:
ritual-scope impingements EXPAND grounding opportunities; they never
pre-determine moves.

Per plan §Phase 7, lines 749-769.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from shared.impingement import Impingement, ImpingementType
from shared.sensor_protocol import IMPINGEMENTS_FILE

if TYPE_CHECKING:
    from shared.programme import Programme

log = logging.getLogger(__name__)

DEFAULT_RITUAL_STRENGTH: float = 0.85
"""Ritual-scope impingements are intentionally high-salience.

Programme transitions are the meso-tier's highest-information moments;
the affordance pipeline must see them as strong activations or the
pipeline's normal ambient impingements will out-score them and the
ritual will be silently swallowed.
"""

# Family prefix vocabulary the affordance pipeline filters on. The
# pipeline restricts capability candidates to those whose name starts
# with the family prefix; ward-choreography capabilities are expected to
# register names like ``ward.choreography.boundary_pulse`` etc.
RITUAL_INTENT_FAMILIES: tuple[str, str, str, str] = (
    "programme.exit_ritual",
    "programme.boundary.freeze",
    "programme.palette.shift",
    "programme.entry_ritual",
)


@dataclass(frozen=True)
class TransitionImpingements:
    """The four ritual-scope impingements emitted at one boundary.

    Returned by ``TransitionChoreographer.transition`` so the manager
    (and tests) can assert on the emission sequence without reading
    back from the JSONL transport.
    """

    exit_ritual: Impingement | None
    boundary_freeze: Impingement
    palette_shift: Impingement | None
    entry_ritual: Impingement | None

    def as_list(self) -> list[Impingement]:
        return [
            imp
            for imp in (
                self.exit_ritual,
                self.boundary_freeze,
                self.palette_shift,
                self.entry_ritual,
            )
            if imp is not None
        ]


class TransitionChoreographer:
    """Emits the four ritual-scope impingements at a programme boundary.

    Stateless aside from configuration. The manager owns lifecycle
    state; this class only knows how to render a boundary as a sequence
    of impingements.
    """

    def __init__(
        self,
        *,
        impingements_file: Path = IMPINGEMENTS_FILE,
        ritual_strength: float = DEFAULT_RITUAL_STRENGTH,
        now_fn: Callable[[], float] = time.time,
        embed_fn: Callable[[str], list[float] | None] | None = None,
    ) -> None:
        self.impingements_file = impingements_file
        self.ritual_strength = ritual_strength
        self.now_fn = now_fn
        self.embed_fn = embed_fn

    def transition(
        self,
        *,
        from_programme: Programme | None,
        to_programme: Programme | None,
    ) -> TransitionImpingements:
        """Emit the four ritual-scope impingements for one boundary.

        Either side may be ``None`` (start-of-stream when there is no
        prior programme; end-of-stream when there is no successor).
        ``boundary_freeze`` always fires — even a one-sided transition
        is a boundary the affordance pipeline should recognise.
        """
        ts = self.now_fn()

        exit_ritual = self._build_exit_ritual(from_programme, to_programme, ts)
        boundary_freeze = self._build_boundary_freeze(from_programme, to_programme, ts)
        palette_shift = self._build_palette_shift(from_programme, to_programme, ts)
        entry_ritual = self._build_entry_ritual(from_programme, to_programme, ts)

        for imp in (exit_ritual, boundary_freeze, palette_shift, entry_ritual):
            if imp is not None:
                self._write(imp)

        return TransitionImpingements(
            exit_ritual=exit_ritual,
            boundary_freeze=boundary_freeze,
            palette_shift=palette_shift,
            entry_ritual=entry_ritual,
        )

    # --- impingement builders --------------------------------------

    def _build_exit_ritual(
        self,
        from_programme: Programme | None,
        to_programme: Programme | None,
        ts: float,
    ) -> Impingement | None:
        if from_programme is None:
            return None
        from_role = str(from_programme.role.value)
        to_role = str(to_programme.role.value) if to_programme is not None else None
        narrative = (
            f"closing the {from_role} programme — recruit the exit ritual "
            f"that releases this segment toward "
            f"{to_role + ' next' if to_role else 'the boundary silence'}"
        )
        return self._make_impingement(
            family=f"{RITUAL_INTENT_FAMILIES[0]}.{from_role}",
            source="programme.choreographer.exit",
            narrative=narrative,
            ts=ts,
            content_extra={
                "from_programme_id": from_programme.programme_id,
                "from_role": from_role,
                "to_role": to_role,
                "ritual_artefact_hint": from_programme.ritual.exit_signature_artefact,
                "ward_choreography_hint": list(from_programme.ritual.exit_ward_choreography),
            },
        )

    def _build_boundary_freeze(
        self,
        from_programme: Programme | None,
        to_programme: Programme | None,
        ts: float,
    ) -> Impingement:
        # Use either side's freeze duration (operator-tunable); default
        # to the from-side, fall through to to-side, fall through to the
        # ritual default of 4.0 s.
        freeze_s: float = 4.0
        if from_programme is not None:
            freeze_s = float(from_programme.ritual.boundary_freeze_s)
        elif to_programme is not None:
            freeze_s = float(to_programme.ritual.boundary_freeze_s)
        narrative = (
            f"programme boundary — settle for {freeze_s:.1f}s; "
            "bias toward stillness so the next programme has space to land"
        )
        return self._make_impingement(
            family=RITUAL_INTENT_FAMILIES[1],
            source="programme.choreographer.boundary",
            narrative=narrative,
            ts=ts,
            content_extra={
                "freeze_s": freeze_s,
                "from_programme_id": (
                    from_programme.programme_id if from_programme is not None else None
                ),
                "to_programme_id": (
                    to_programme.programme_id if to_programme is not None else None
                ),
            },
        )

    def _build_palette_shift(
        self,
        from_programme: Programme | None,
        to_programme: Programme | None,
        ts: float,
    ) -> Impingement | None:
        if to_programme is None:
            return None
        to_role = str(to_programme.role.value)
        target_saturation = to_programme.constraints.reverie_saturation_target
        narrative = (
            f"shift Reverie palette toward {to_role} — recruit the palette "
            "shaping that opens the next programme"
        )
        return self._make_impingement(
            family=f"{RITUAL_INTENT_FAMILIES[2]}.{to_role}",
            source="programme.choreographer.palette",
            narrative=narrative,
            ts=ts,
            content_extra={
                "to_programme_id": to_programme.programme_id,
                "to_role": to_role,
                "saturation_target": target_saturation,
                "preset_family_priors": list(to_programme.constraints.preset_family_priors),
            },
        )

    def _build_entry_ritual(
        self,
        from_programme: Programme | None,
        to_programme: Programme | None,
        ts: float,
    ) -> Impingement | None:
        if to_programme is None:
            return None
        to_role = str(to_programme.role.value)
        from_role = str(from_programme.role.value) if from_programme is not None else None
        narrative = (
            f"opening the {to_role} programme — recruit the entry ritual that "
            f"announces the shift "
            f"{'from ' + from_role if from_role else 'into being'}"
        )
        return self._make_impingement(
            family=f"{RITUAL_INTENT_FAMILIES[3]}.{to_role}",
            source="programme.choreographer.entry",
            narrative=narrative,
            ts=ts,
            content_extra={
                "to_programme_id": to_programme.programme_id,
                "to_role": to_role,
                "from_role": from_role,
                "ritual_artefact_hint": to_programme.ritual.entry_signature_artefact,
                "ward_choreography_hint": list(to_programme.ritual.entry_ward_choreography),
            },
        )

    # --- helpers ----------------------------------------------------

    def _make_impingement(
        self,
        *,
        family: str,
        source: str,
        narrative: str,
        ts: float,
        content_extra: dict,
    ) -> Impingement:
        content = {"narrative": narrative, **content_extra}
        embedding: list[float] | None = None
        if self.embed_fn is not None:
            try:
                embedding = self.embed_fn(narrative)
            except Exception:
                log.debug("embed_fn raised on ritual narrative", exc_info=True)
        return Impingement(
            timestamp=ts,
            source=source,
            type=ImpingementType.PATTERN_MATCH,
            strength=self.ritual_strength,
            content=content,
            interrupt_token="programme_boundary",
            intent_family=family,
            embedding=embedding,
        )

    def _write(self, imp: Impingement) -> None:
        try:
            self.impingements_file.parent.mkdir(parents=True, exist_ok=True)
            with self.impingements_file.open("a", encoding="utf-8") as f:
                f.write(imp.model_dump_json() + "\n")
        except OSError:
            log.warning(
                "transition: failed to write ritual impingement to %s",
                self.impingements_file,
                exc_info=True,
            )
