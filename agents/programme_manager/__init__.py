"""ProgrammeManager — Phase 7 of the programme-layer plan.

Lifecycle loop + boundary choreographer for the meso-tier content
programming layer. The transition module never invokes capabilities
directly: every boundary emits ritual-scope impingements that the
affordance pipeline recruits against. Rituals are recruited, not
scripted (per `project_programmes_enable_grounding` and
`feedback_no_expert_system_rules`).

References:
- docs/superpowers/plans/2026-04-20-programme-layer-plan.md §Phase 7
- docs/research/2026-04-19-content-programming-layer-design.md §6
"""

from agents.programme_manager.manager import (
    BoundaryDecision,
    BoundaryTrigger,
    ProgrammeManager,
)
from agents.programme_manager.transition import (
    DEFAULT_RITUAL_STRENGTH,
    RITUAL_INTENT_FAMILIES,
    TransitionChoreographer,
    TransitionImpingements,
)

__all__ = [
    "DEFAULT_RITUAL_STRENGTH",
    "RITUAL_INTENT_FAMILIES",
    "BoundaryDecision",
    "BoundaryTrigger",
    "ProgrammeManager",
    "TransitionChoreographer",
    "TransitionImpingements",
]
