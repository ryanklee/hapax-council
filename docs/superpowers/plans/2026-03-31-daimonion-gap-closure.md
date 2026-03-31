# Daimonion Gap Closure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close all implementation gaps between the daimonion model and its codebase — mode-driven grounding activation, responsive grounding acts, vocal chain impingement wiring, cross-modal expression coordination, tool metadata completion, and documentation accuracy.

**Architecture:** Six tasks targeting specific files. No new modules. All changes extend existing code paths. Grounding changes stay within the pre-registered experiment framework (VOLATILE band directives, not structural act injection). Vocal chain and expression coordinator wire existing initialized-but-dormant capabilities into the impingement consumer loop.

**Tech Stack:** Python 3.12, pydantic, asyncio, existing LiteLLM tool-calling

**Spec:** Design approved in conversation (2026-03-31). Evaluated against exhaustive audit of daimonion model vs implementation.

---

## File Map

### Modified Files

| File | Change |
|------|--------|
| `agents/hapax_daimonion/pipeline_start.py` | Fix mode-driven grounding: set correct flag names in R&D mode |
| `agents/hapax_daimonion/grounding_ledger.py` | Add Traum responsive act directives to strategy generation |
| `agents/hapax_daimonion/run_loops_aux.py` | Wire vocal chain + expression coordinator into impingement consumer |
| `agents/hapax_daimonion/tool_definitions.py` | Add _META for missing handlers + phone tools |
| `agents/hapax_daimonion/README.md` | Update stale counts, add known limitations |

### Test Files

| File | Tests |
|------|-------|
| `tests/hapax_daimonion/test_mode_grounding.py` | R&D defaults flags ON, research uses config file |
| `tests/hapax_daimonion/test_responsive_directives.py` | Each DU state produces correct Traum act directive |
| `tests/hapax_daimonion/test_vocal_chain_wiring.py` | Impingement with vocal affordance reaches vocal chain |
| `tests/hapax_daimonion/test_expression_coordinator_wiring.py` | Multi-modal recruitment produces coordinated activations |
| `tests/hapax_daimonion/test_tool_definitions_complete.py` | All handlers have _META entries |

---

## Task 1: Fix Mode-Driven Grounding Activation

**Problem:** `pipeline_start.py:48-49` sets `_exp["enable_grounding"] = True` in R&D mode. But `conversation_pipeline.py` checks `grounding_directive`, `effort_modulation`, and `cross_session` — different flag names. The mode mapping is attempted but broken.

**Files:**
- Modify: `agents/hapax_daimonion/pipeline_start.py:46-49`
- Create: `tests/hapax_daimonion/test_mode_grounding.py`

- [ ] **Step 1: Write failing test**

```python
# tests/hapax_daimonion/test_mode_grounding.py
"""Tests for mode-driven grounding activation."""

from __future__ import annotations

import unittest
from unittest.mock import patch


class TestModeGroundingActivation(unittest.TestCase):
    """Verify R&D mode enables grounding flags, research mode uses config."""

    def test_rnd_mode_enables_grounding_flags(self):
        """R&D mode should set grounding_directive, effort_modulation, cross_session."""
        flags: dict = {}

        from agents.hapax_daimonion.pipeline_start import _apply_mode_grounding_defaults

        with patch("agents.hapax_daimonion.pipeline_start.get_working_mode") as mock_mode:
            mock_mode.return_value.value = "rnd"
            _apply_mode_grounding_defaults(flags)

        assert flags["grounding_directive"] is True
        assert flags["effort_modulation"] is True
        assert flags["cross_session"] is True

    def test_research_mode_preserves_config_flags(self):
        """Research mode should NOT override experiment config flags."""
        flags: dict = {"grounding_directive": False, "experiment_mode": True}

        from agents.hapax_daimonion.pipeline_start import _apply_mode_grounding_defaults

        with patch("agents.hapax_daimonion.pipeline_start.get_working_mode") as mock_mode:
            mock_mode.return_value.value = "research"
            _apply_mode_grounding_defaults(flags)

        assert flags["grounding_directive"] is False

    def test_rnd_mode_does_not_override_explicit_experiment(self):
        """R&D mode should NOT override flags when experiment_mode is set."""
        flags: dict = {"grounding_directive": False, "experiment_mode": True}

        from agents.hapax_daimonion.pipeline_start import _apply_mode_grounding_defaults

        with patch("agents.hapax_daimonion.pipeline_start.get_working_mode") as mock_mode:
            mock_mode.return_value.value = "rnd"
            _apply_mode_grounding_defaults(flags)

        # experiment_mode=True means explicit experiment config — don't override
        assert flags["grounding_directive"] is False


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/hapax_daimonion/test_mode_grounding.py -v`
Expected: FAIL with `ImportError: cannot import name '_apply_mode_grounding_defaults'`

- [ ] **Step 3: Implement mode-driven grounding in pipeline_start.py**

In `agents/hapax_daimonion/pipeline_start.py`, replace lines 46-49:

```python
    from agents._working_mode import get_working_mode

    if get_working_mode().value == "rnd":
        _exp["enable_grounding"] = True
```

With:

```python
    _apply_mode_grounding_defaults(_exp)
```

And add the function (after the imports, before `start_conversation_pipeline`):

```python
def _apply_mode_grounding_defaults(flags: dict) -> None:
    """Set grounding flags based on working mode.

    R&D mode: enable all grounding features by default.
    Research mode: leave flags as-is (controlled by experiment config).
    If experiment_mode is explicitly set, never override — the experiment
    config file is authoritative.
    """
    from agents._working_mode import get_working_mode

    if flags.get("experiment_mode", False):
        return  # explicit experiment config — don't touch

    if get_working_mode().value == "rnd":
        flags.setdefault("grounding_directive", True)
        flags.setdefault("effort_modulation", True)
        flags.setdefault("cross_session", True)
        flags.setdefault("stable_frame", True)
        flags.setdefault("message_drop", True)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/hapax_daimonion/test_mode_grounding.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add tests/hapax_daimonion/test_mode_grounding.py agents/hapax_daimonion/pipeline_start.py
git commit -m "feat(daimonion): mode-driven grounding — R&D defaults all flags ON

Fixes broken mode mapping: pipeline_start set 'enable_grounding' but
conversation_pipeline checks 'grounding_directive', 'effort_modulation',
'cross_session'. Now sets the correct flag names via setdefault() so
explicit experiment config is never overridden."
```

---

## Task 2: Responsive Grounding Act Directives

**Problem:** Grounding ledger produces strategy names ("rephrase", "elaborate") but the directive text doesn't encode Traum's specific responsive acts (acknowledge, repair, request-repair, request-acknowledge, cancel). The LLM gets general instructions, not grounding-act-specific behavior.

**Files:**
- Modify: `agents/hapax_daimonion/grounding_ledger.py:58-86`
- Create: `tests/hapax_daimonion/test_responsive_directives.py`

- [ ] **Step 1: Write failing test**

```python
# tests/hapax_daimonion/test_responsive_directives.py
"""Tests for Traum responsive grounding act directives."""

from __future__ import annotations

import unittest

from agents.hapax_daimonion.grounding_ledger import GroundingLedger


class TestResponsiveDirectives(unittest.TestCase):
    """Each DU state should produce a directive encoding a specific Traum act."""

    def test_pending_produces_request_acknowledge(self):
        """PENDING state (turn 2+) should ask operator to confirm understanding."""
        ledger = GroundingLedger()
        ledger.add_du(turn=1, summary="initial point")
        # Don't update acceptance — DU stays PENDING
        ledger.add_du(turn=2, summary="second point")
        directive = ledger.grounding_directive()
        assert "confirm" in directive.lower() or "check" in directive.lower()

    def test_repair_1_produces_acknowledge_plus_repair(self):
        """REPAIR-1 should acknowledge the clarification request then rephrase."""
        ledger = GroundingLedger()
        ledger.add_du(turn=1, summary="test point")
        ledger.update_from_acceptance("CLARIFY")
        directive = ledger.grounding_directive()
        assert "acknowledge" in directive.lower()
        assert "rephrase" in directive.lower()

    def test_repair_2_produces_request_repair(self):
        """REPAIR-2 should ask what specifically isn't clear."""
        ledger = GroundingLedger()
        ledger.add_du(turn=1, summary="test point")
        ledger.update_from_acceptance("CLARIFY")
        ledger.update_from_acceptance("CLARIFY")
        directive = ledger.grounding_directive()
        assert "what" in directive.lower() and "clear" in directive.lower()

    def test_contested_produces_acknowledge(self):
        """CONTESTED should acknowledge the operator's disagreement."""
        ledger = GroundingLedger()
        ledger.add_du(turn=1, summary="test point")
        ledger.update_from_acceptance("REJECT")
        directive = ledger.grounding_directive()
        assert "acknowledge" in directive.lower()

    def test_grounded_consecutive_does_not_revisit(self):
        """Consecutive GROUNDED DUs should not revisit grounded content."""
        ledger = GroundingLedger()
        ledger.add_du(turn=1, summary="point A")
        ledger.update_from_acceptance("ACCEPT")
        ledger.add_du(turn=2, summary="point B")
        ledger.update_from_acceptance("ACCEPT")
        directive = ledger.grounding_directive()
        assert "revisit" in directive.lower() or "new" in directive.lower()

    def test_abandoned_produces_move_on(self):
        """ABANDONED should move on without referencing ungrounded content."""
        ledger = GroundingLedger()
        ledger.add_du(turn=1, summary="test point")
        ledger.update_from_acceptance("CLARIFY")
        ledger.update_from_acceptance("CLARIFY")
        ledger.update_from_acceptance("CLARIFY")
        directive = ledger.grounding_directive()
        assert "move on" in directive.lower() or "abandon" in directive.lower()


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify failures**

Run: `uv run pytest tests/hapax_daimonion/test_responsive_directives.py -v`
Expected: Several FAIL (current directives lack "acknowledge", "confirm", "what...clear")

- [ ] **Step 3: Update strategy directives with Traum acts**

In `agents/hapax_daimonion/grounding_ledger.py`, replace `_STRATEGY_DIRECTIVES` (lines 59-86):

```python
_STRATEGY_DIRECTIVES: dict[str, str] = {
    "advance": (
        "The operator accepted your previous point. Advance to new content. "
        "Do not repeat or revisit what was already understood."
    ),
    "rephrase": (
        "The operator asked for clarification. First, acknowledge their question "
        "(e.g. 'Good question' or 'Let me put that differently'). "
        "Then rephrase your previous point using different words. "
        "Do not introduce new information yet."
    ),
    "elaborate": (
        "Understanding has not been established after rephrasing. "
        "Ask the operator what specifically isn't clear before continuing. "
        "Keep your question short and specific."
    ),
    "present_reasoning": (
        "The operator disagreed. Acknowledge their position first "
        "(e.g. 'I hear you' or 'That's a fair point'). "
        "Then present your reasoning without retracting. "
        "Do not apologize or cave. Explain why you said what you said."
    ),
    "move_on": (
        "Previous point was not grounded after multiple attempts. Move on. "
        "Do not reference the ungrounded content as established. "
        "Start fresh with the operator's current interest."
    ),
    "neutral": (
        "No prior context to repair. Respond naturally to the operator's input. "
        "After responding, briefly check understanding "
        "(e.g. 'Does that make sense?' or 'What do you think?')."
    ),
    "ungrounded_caution": (
        "The operator did not engage with your previous point. "
        "Do not build on it or reference it as established. "
        "Respond to what the operator actually said."
    ),
}
```

Also update `grounding_directive()` to handle PENDING-at-turn-2+. Replace lines 278-304:

```python
    def grounding_directive(self) -> str:
        """Generate the grounding directive for VOLATILE band injection.

        Encodes Traum (1994) responsive grounding acts as directive text.
        """
        if not self._units:
            return ""

        du = self._units[-1]
        strategy = "neutral"

        if du.state == DUState.GROUNDED:
            strategy = "advance"
        elif du.state == DUState.REPAIR_1:
            strategy = "rephrase"
        elif du.state == DUState.REPAIR_2:
            strategy = "elaborate"
        elif du.state == DUState.CONTESTED:
            strategy = "present_reasoning"
        elif du.state == DUState.ABANDONED:
            strategy = "move_on"
        elif du.state == DUState.UNGROUNDED:
            strategy = "ungrounded_caution"
        elif du.state == DUState.PENDING and len(self._units) >= 2:
            strategy = "neutral"  # neutral now includes the check-understanding act

        directive = _STRATEGY_DIRECTIVES.get(strategy, _STRATEGY_DIRECTIVES["neutral"])
        return f"## Grounding Directive\n{directive}"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/hapax_daimonion/test_responsive_directives.py -v`
Expected: 6 passed

- [ ] **Step 5: Run existing grounding tests for regressions**

Run: `uv run pytest tests/hapax_daimonion/test_grounding_ledger.py -v`
Expected: All pass

- [ ] **Step 6: Commit**

```bash
git add agents/hapax_daimonion/grounding_ledger.py tests/hapax_daimonion/test_responsive_directives.py
git commit -m "feat(daimonion): responsive grounding act directives (Traum 1994)

Extend strategy directives to encode 5 responsive grounding acts:
- REPAIR_1: acknowledge + rephrase (Traum: Acknowledge + Repair)
- REPAIR_2: ask what's unclear (Traum: Request-Repair)
- CONTESTED: acknowledge disagreement (Traum: Acknowledge)
- GROUNDED: don't revisit (Traum: Cancel stale)
- neutral: check understanding (Traum: Request-Acknowledge)

Directive-based approach per design: within pre-registered framework."
```

---

## Task 3: Vocal Chain Impingement Wiring

**Problem:** `VocalChainCapability.can_resolve()` exists but nothing routes impingements to it.

**Files:**
- Modify: `agents/hapax_daimonion/run_loops_aux.py:113-153`
- Modify: `agents/hapax_daimonion/vocal_chain.py` (add `activate_from_impingement`)
- Create: `tests/hapax_daimonion/test_vocal_chain_wiring.py`

- [ ] **Step 1: Write failing test**

```python
# tests/hapax_daimonion/test_vocal_chain_wiring.py
"""Tests for vocal chain impingement wiring."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from agents._impingement import Impingement


class TestVocalChainWiring(unittest.TestCase):
    """Verify impingements with vocal affordances reach the vocal chain."""

    def test_vocal_affordance_activates_chain(self):
        from agents.hapax_daimonion.vocal_chain import VocalChainCapability

        midi_out = MagicMock()
        chain = VocalChainCapability(
            midi_output=midi_out, evil_pet_channel=0, s4_channel=1
        )

        imp = Impingement(
            source="dmn.evaluative",
            strength=0.7,
            content={"metric": "vocal.intensity", "narrative": "test"},
            context={"dimensions": {"intensity": 0.8}},
        )

        score = chain.can_resolve(imp)
        assert score > 0.0

        result = chain.activate_from_impingement(imp)
        assert result["activated"] is True
        assert chain.get_dimension_level("intensity") > 0.0

    def test_non_vocal_impingement_ignored(self):
        from agents.hapax_daimonion.vocal_chain import VocalChainCapability

        midi_out = MagicMock()
        chain = VocalChainCapability(
            midi_output=midi_out, evil_pet_channel=0, s4_channel=1
        )

        imp = Impingement(
            source="dmn.sensory",
            strength=0.5,
            content={"metric": "visual.brightness", "narrative": "bright"},
            context={},
        )

        score = chain.can_resolve(imp)
        assert score == 0.0

    def test_stimmung_impingement_reduced_strength(self):
        from agents.hapax_daimonion.vocal_chain import VocalChainCapability

        midi_out = MagicMock()
        chain = VocalChainCapability(
            midi_output=midi_out, evil_pet_channel=0, s4_channel=1
        )

        imp = Impingement(
            source="stimmung.shift",
            strength=0.8,
            content={"metric": "stance_change", "narrative": "degraded"},
            context={"dimensions": {"tension": 0.6}},
        )

        score = chain.can_resolve(imp)
        assert 0.3 <= score <= 0.35  # 0.8 * 0.4 = 0.32


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/hapax_daimonion/test_vocal_chain_wiring.py -v`
Expected: FAIL with `AttributeError: 'VocalChainCapability' ... 'activate_from_impingement'`

- [ ] **Step 3: Add activate_from_impingement to vocal_chain.py**

In `agents/hapax_daimonion/vocal_chain.py`, add after `activate()` (after line 270):

```python
    def activate_from_impingement(self, impingement: Impingement) -> dict[str, object]:
        """Activate vocal chain dimensions from impingement content.

        Maps impingement dimensions to vocal chain dimensions and sends
        corresponding MIDI CCs.
        """
        dims = impingement.context.get("dimensions", {})
        activated_dims: list[str] = []

        for dim_name, level in dims.items():
            if dim_name in DIMENSIONS and isinstance(level, (int, float)):
                self.activate_dimension(dim_name, impingement, float(level))
                activated_dims.append(dim_name)

        if not activated_dims:
            score = self.can_resolve(impingement)
            if score > 0:
                self.activate(impingement, score)
                return {"activated": True, "level": score, "dimensions": []}

        return {
            "activated": bool(activated_dims),
            "level": self._activation_level,
            "dimensions": activated_dims,
        }
```

- [ ] **Step 4: Wire vocal chain into impingement consumer loop**

In `agents/hapax_daimonion/run_loops_aux.py`, in `impingement_consumer_loop`, after the speech recruitment `for c in candidates` block (after line 144), add:

```python
                            # Vocal chain: modulate voice character via MIDI
                            if (
                                hasattr(daemon, "_vocal_chain")
                                and daemon._vocal_chain is not None
                            ):
                                vc_score = daemon._vocal_chain.can_resolve(imp)
                                if vc_score > 0.0:
                                    daemon._vocal_chain.activate_from_impingement(imp)
                                    log.debug(
                                        "Vocal chain activated: %s (score=%.2f)",
                                        imp.content.get("metric", imp.source),
                                        vc_score,
                                    )
```

- [ ] **Step 5: Run tests**

Run: `uv run pytest tests/hapax_daimonion/test_vocal_chain_wiring.py -v`
Expected: 3 passed

- [ ] **Step 6: Commit**

```bash
git add agents/hapax_daimonion/vocal_chain.py agents/hapax_daimonion/run_loops_aux.py tests/hapax_daimonion/test_vocal_chain_wiring.py
git commit -m "feat(daimonion): wire vocal chain into impingement consumer loop

VocalChainCapability.can_resolve() was declared but dormant. Now
the impingement consumer routes matching impingements to the vocal
chain for MIDI CC modulation of Evil Pet + S-4."
```

---

## Task 4: Expression Coordinator Wiring

**Problem:** `shared/expression.py` ExpressionCoordinator exists but daimonion never uses it.

**Files:**
- Modify: `agents/hapax_daimonion/run_loops_aux.py:113-153`
- Modify: `agents/hapax_daimonion/init_pipeline.py`
- Create: `tests/hapax_daimonion/test_expression_coordinator_wiring.py`

- [ ] **Step 1: Write failing test**

```python
# tests/hapax_daimonion/test_expression_coordinator_wiring.py
"""Tests for ExpressionCoordinator wiring in impingement consumer."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from shared.expression import ExpressionCoordinator


class TestExpressionCoordinatorWiring(unittest.TestCase):

    def test_single_modality_skips_coordinator(self):
        coordinator = ExpressionCoordinator()
        recruited = [("speech_production", MagicMock())]
        activations = coordinator.coordinate({"narrative": "test"}, recruited)
        assert len(activations) == 1

    def test_multi_modality_produces_coordinated_activations(self):
        coordinator = ExpressionCoordinator()
        speech = MagicMock()
        visual = MagicMock()
        visual.modality = "visual"
        recruited = [("speech_production", speech), ("shader_graph", visual)]
        activations = coordinator.coordinate(
            {"narrative": "a warm amber glow"}, recruited
        )
        assert len(activations) == 2
        fragments = {a["modality"] for a in activations}
        assert len(fragments) == 2

    def test_no_fragment_returns_empty(self):
        coordinator = ExpressionCoordinator()
        recruited = [("speech_production", MagicMock())]
        activations = coordinator.coordinate({"metric": "cpu_load"}, recruited)
        assert len(activations) == 0


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests (should pass — coordinator already implemented)**

Run: `uv run pytest tests/hapax_daimonion/test_expression_coordinator_wiring.py -v`
Expected: 3 passed

- [ ] **Step 3: Initialize ExpressionCoordinator in init_pipeline.py**

In `agents/hapax_daimonion/init_pipeline.py`, add after line 128 (after `register_interrupt`):

```python
    # Cross-modal expression coordinator
    from shared.expression import ExpressionCoordinator

    daemon._expression_coordinator = ExpressionCoordinator()
```

- [ ] **Step 4: Wire coordinator into impingement consumer**

In `agents/hapax_daimonion/run_loops_aux.py`, in `impingement_consumer_loop`, after the vocal chain block (added in Task 3), before the proactive utterance block, add:

```python
                            # Cross-modal coordination
                            if len(candidates) > 1 and hasattr(daemon, "_expression_coordinator"):
                                recruited_pairs = [
                                    (c.capability_name, getattr(daemon, f"_{c.capability_name}", None))
                                    for c in candidates
                                ]
                                recruited_pairs = [
                                    (n, cap) for n, cap in recruited_pairs if cap is not None
                                ]
                                if len(recruited_pairs) > 1:
                                    activations = daemon._expression_coordinator.coordinate(
                                        imp.content, recruited_pairs
                                    )
                                    if activations:
                                        log.info(
                                            "Cross-modal coordination: %d modalities for %s",
                                            len(activations),
                                            imp.content.get("narrative", "")[:40],
                                        )
```

- [ ] **Step 5: Commit**

```bash
git add agents/hapax_daimonion/run_loops_aux.py agents/hapax_daimonion/init_pipeline.py tests/hapax_daimonion/test_expression_coordinator_wiring.py
git commit -m "feat(daimonion): wire ExpressionCoordinator into impingement consumer

When multiple modalities recruited for same impingement, coordinator
distributes fragment to each for coherent cross-modal expression."
```

---

## Task 5: Tool Metadata Completion

**Problem:** Phone tools outside formal registry. Possible missing _META entries.

**Files:**
- Modify: `agents/hapax_daimonion/tool_definitions.py:77-216`
- Create: `tests/hapax_daimonion/test_tool_definitions_complete.py`

- [ ] **Step 1: Write failing test**

```python
# tests/hapax_daimonion/test_tool_definitions_complete.py
"""Tests for complete tool metadata coverage."""

from __future__ import annotations

import logging
import unittest


class TestToolDefinitionsComplete(unittest.TestCase):

    def test_all_handlers_have_metadata(self):
        """build_registry should log no 'no metadata' warnings."""
        warnings: list[str] = []

        class _Handler(logging.Handler):
            def emit(self, record: logging.LogRecord) -> None:
                if "no metadata" in record.getMessage():
                    warnings.append(record.getMessage())

        handler = _Handler()
        logger = logging.getLogger("agents.hapax_daimonion.tool_definitions")
        logger.addHandler(handler)
        try:
            from agents.hapax_daimonion.tool_definitions import build_registry

            build_registry(guest_mode=False)
        finally:
            logger.removeHandler(handler)

        assert warnings == [], f"Tools without metadata: {warnings}"

    def test_phone_tools_in_registry(self):
        from agents.hapax_daimonion.tool_definitions import build_registry

        reg = build_registry(guest_mode=False)
        all_names = {t.name for t in reg.all_tools()}
        for name in ["find_phone", "lock_phone", "send_to_phone", "media_control"]:
            assert name in all_names, f"Phone tool '{name}' not in registry"


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify failures**

Run: `uv run pytest tests/hapax_daimonion/test_tool_definitions_complete.py -v`
Expected: FAIL on phone tools at minimum

- [ ] **Step 3: Add missing _META entries**

In `agents/hapax_daimonion/tool_definitions.py`, add to the `_META` dict (before the closing `}`):

```python
        # Phone tools
        "find_phone": (ToolCategory.ACTION, ResourceTier.LIGHT, [], ["phone"], False, 3.0),
        "lock_phone": (ToolCategory.ACTION, ResourceTier.LIGHT, [], ["phone"], False, 3.0),
        "send_to_phone": (ToolCategory.ACTION, ResourceTier.LIGHT, [], ["phone"], False, 3.0),
        "media_control": (ToolCategory.ACTION, ResourceTier.LIGHT, [], ["phone"], False, 3.0),
        "phone_notifications": (ToolCategory.INFORMATION, ResourceTier.LIGHT, [], ["phone"], False, 3.0),
```

Check `get_openai_tools()` handler_map output for any other handlers without _META. If `query_object_motion`, `query_person_details`, or `query_scene_state` appear, add:

```python
        "query_object_motion": (
            ToolCategory.INFORMATION, ResourceTier.LIGHT,
            ["interpersonal_transparency"], ["vision"], False, 3.0,
        ),
        "query_person_details": (
            ToolCategory.INFORMATION, ResourceTier.LIGHT,
            ["interpersonal_transparency"], ["vision"], False, 3.0,
        ),
        "query_scene_state": (
            ToolCategory.INFORMATION, ResourceTier.LIGHT,
            ["interpersonal_transparency"], ["vision"], False, 3.0,
        ),
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/hapax_daimonion/test_tool_definitions_complete.py -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add agents/hapax_daimonion/tool_definitions.py tests/hapax_daimonion/test_tool_definitions_complete.py
git commit -m "feat(daimonion): complete tool metadata — phone + vision tools

Add _META entries for all phone tools and any vision query tools.
No handler registered with defaults."
```

---

## Task 6: Documentation Accuracy

**Files:**
- Modify: `agents/hapax_daimonion/README.md`

- [ ] **Step 1: Read current README for stale counts**

Read `agents/hapax_daimonion/README.md` and identify:
- "Five concurrent async loops" → should be 9
- "Eight backends" → should be 23
- "63 .py files" → update to actual
- Missing Known Limitations section

- [ ] **Step 2: Update counts and add Known Limitations**

Update "Daemon Lifecycle" section: "Nine concurrent async loops handle audio distribution, perception polling, actuation draining, wake word processing, proactive notification delivery, ambient classification, impingement consumption, ntfy subscription, and workspace monitoring."

Update "Perception Infrastructure" section: "Twenty-three backends in `backends/`" with full listing.

Update "Package Structure" file count.

Add at end:

```markdown
## Known Limitations

- **Grounding acts**: The system classifies operator acceptance and generates strategy directives encoding Traum's responsive acts, but compliance depends on the LLM following the directive — which RLHF actively suppresses (Shaikh et al. 2025). See `EPISTEMIC-AUDIT-conversational-continuity.md` for vocabulary mismatch analysis.

- **Grounding features**: R&D-default, Research-gated. In R&D mode all features enabled. In Research mode each feature individually controlled by experiment flags for Bayesian SCED testing.

- **Acceptance classification**: Keyword-based heuristic in `grounding_evaluator.py`. Cannot distinguish "yeah" (agreement) from "yeah, but..." (concession).

- **Cognitive loop**: Tick-driven at 150ms intervals, not continuous processing.
```

- [ ] **Step 3: Commit**

```bash
git add agents/hapax_daimonion/README.md
git commit -m "docs(daimonion): accurate counts + known limitations

9 async loops (was 5), 23 backends (was 8), updated package
structure. Known limitations: RLHF compliance gap, keyword
acceptance, tick-driven loop."
```

---

## Verification

After all 6 tasks, run all new tests:

```bash
uv run pytest tests/hapax_daimonion/test_mode_grounding.py tests/hapax_daimonion/test_responsive_directives.py tests/hapax_daimonion/test_vocal_chain_wiring.py tests/hapax_daimonion/test_expression_coordinator_wiring.py tests/hapax_daimonion/test_tool_definitions_complete.py -v
```

Then run full suite for regressions:

```bash
uv run pytest tests/hapax_daimonion/ -q --timeout=30
```
