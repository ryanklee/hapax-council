"""Epic pipeline rule — detects and drives the multi-phase epic workflow."""

from __future__ import annotations

import logging
import re

from agents.session_conductor.rules import HookEvent, HookResponse, RuleBase
from agents.session_conductor.state import (
    EPIC_PHASE_ORDER,
    MAX_GAP_ROUNDS,
    EpicPhase,
    SessionState,
)
from agents.session_conductor.topology import TopologyConfig

log = logging.getLogger(__name__)

_EPIC_PATTERNS = [
    re.compile(r"\bresearch\s+(any|all)\s+loose\s+ends\b", re.IGNORECASE),
    re.compile(r"\bformal\s+design\s+doc\b", re.IGNORECASE),
    re.compile(r"\bbatched\s+planning\b", re.IGNORECASE),
]

# Filenames that indicate a design doc write
_DESIGN_DOC_RE = re.compile(r"(DESIGN|design[_-]doc|design\.md)", re.IGNORECASE)
# Filenames that indicate a plan doc write
_PLAN_DOC_RE = re.compile(r"(PLAN|plan[_-]doc|plan\.md|implementation[_-]plan)", re.IGNORECASE)

# Internal attribute name used to track gap rounds on SessionState at runtime
_GAP_ROUNDS_ATTR = "_gap_rounds"


def is_epic_trigger(text: str) -> bool:
    """Return True if the text matches any epic entry pattern."""
    return any(p.search(text) for p in _EPIC_PATTERNS)


class EpicRule(RuleBase):
    """Detect epic entry and drive phase transitions through the pipeline."""

    def __init__(self, topology: TopologyConfig, state: SessionState) -> None:
        super().__init__(topology)
        self._state = state

    def on_pre_tool_use(self, event: HookEvent) -> HookResponse | None:
        return None

    def on_post_tool_use(self, event: HookEvent) -> HookResponse | None:
        state = self._state

        # Detect epic entry via Agent tool prompts
        if event.tool_name == "Agent":
            prompt = event.tool_input.get("prompt", "")
            if state.epic_phase is None and is_epic_trigger(prompt):
                log.info("EpicRule: epic entry detected — entering RESEARCH phase")
                state.epic_phase = EpicPhase.RESEARCH
                return None

        # Detect design/plan doc writes for phase transitions
        if event.tool_name in ("Write", "Edit"):
            file_path: str = event.tool_input.get("file_path", "")
            if state.epic_phase == EpicPhase.DESIGN and _DESIGN_DOC_RE.search(file_path):
                log.info("EpicRule: design doc written — transitioning to DESIGN_GAPS")
                state.epic_phase = EpicPhase.DESIGN_GAPS
                setattr(state, _GAP_ROUNDS_ATTR, 0)
                return None
            if state.epic_phase == EpicPhase.PLANNING and _PLAN_DOC_RE.search(file_path):
                log.info("EpicRule: plan doc written — transitioning to PLANNING_GAPS")
                state.epic_phase = EpicPhase.PLANNING_GAPS
                setattr(state, _GAP_ROUNDS_ATTR, 0)
                return None

        # After post-tool-use, check if a phase transition is needed
        self.check_phase_transition(state)
        return None

    def check_phase_transition(self, state: SessionState) -> None:
        """Advance phase when research converges, or gap rounds are capped."""
        if state.epic_phase is None:
            return

        current_idx = EPIC_PHASE_ORDER.index(state.epic_phase)

        # Research phase: advance to DESIGN when all active topics are converging or capped
        if state.epic_phase == EpicPhase.RESEARCH:
            if state.active_topics and all(
                t.is_converging() or t.is_capped() for t in state.active_topics.values()
            ):
                log.info("EpicRule: all topics converged — transitioning to DESIGN")
                state.epic_phase = EpicPhase.DESIGN

        # Gap phases: advance when gap rounds are at MAX_GAP_ROUNDS
        elif state.epic_phase in (EpicPhase.DESIGN_GAPS, EpicPhase.PLANNING_GAPS):
            gap_rounds = getattr(state, _GAP_ROUNDS_ATTR, 0)
            if gap_rounds >= MAX_GAP_ROUNDS:
                next_phase = EPIC_PHASE_ORDER[current_idx + 1]
                log.info(
                    "EpicRule: gap rounds capped — transitioning from %s to %s",
                    state.epic_phase.value,
                    next_phase.value,
                )
                state.epic_phase = next_phase
                setattr(state, _GAP_ROUNDS_ATTR, 0)
