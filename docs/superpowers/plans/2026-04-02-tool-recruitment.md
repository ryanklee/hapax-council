# Tool Recruitment Implementation Plan (Phase 3)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Route tool selection through the AffordancePipeline with learning (Thompson sampling + Hebbian associations). The LLM executes only recruited tools — it never sees unrecruited tools. Pipeline learns from success/failure across sessions.

**Architecture:** Each tool registers as an affordance in Qdrant with a Gibson-verb description. On each conversational turn, the utterance becomes an impingement, the pipeline scores all tool affordances, and only tools above threshold are given to the LLM as function-calling schemas. After execution, `record_success()` or `record_failure()` updates Thompson sampling. Hebbian associations learn utterance-context → tool mappings. The LLM still handles argument parsing and execution orchestration.

**Tech Stack:** Python 3.12, Pydantic v2, pydantic-ai, pytest

**Spec:** `docs/superpowers/specs/2026-04-02-unified-semantic-recruitment-design.md` §11

**Depends on:** Phase 1 (PR #554), Phase 2 (PR #556)

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `agents/hapax_daimonion/tool_affordances.py` | Create | Gibson-verb descriptions for all 26 tools, registration in Qdrant |
| `agents/hapax_daimonion/tool_recruitment.py` | Create | Utterance→impingement conversion, pipeline selection, outcome recording |
| `agents/hapax_daimonion/pipeline_start.py` | Modify | Replace `schemas_for_llm()` with pipeline-recruited tool set |
| `agents/hapax_daimonion/conversation_pipeline.py` | Modify | Record tool success/failure back to pipeline |
| `tests/test_tool_recruitment.py` | Create | Tests for affordance registration, recruitment, learning |

---

### Task 1: Tool Affordance Descriptions

**Files:**
- Create: `agents/hapax_daimonion/tool_affordances.py`
- Create: `tests/test_tool_recruitment.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_tool_recruitment.py`:

```python
"""Tests for tool recruitment via AffordancePipeline."""

from agents.hapax_daimonion.tool_affordances import TOOL_AFFORDANCES


def test_all_tools_have_affordance_descriptions():
    """Every registered tool has a Gibson-verb affordance description."""
    assert len(TOOL_AFFORDANCES) >= 20  # at least 20 tools described


def test_descriptions_are_semantic_not_implementation():
    """Tool descriptions use cognitive verbs, not API/function names."""
    for name, desc in TOOL_AFFORDANCES:
        assert "function" not in desc.lower(), f"{name}: mentions 'function'"
        assert "api" not in desc.lower(), f"{name}: mentions 'api'"
        assert "endpoint" not in desc.lower(), f"{name}: mentions 'endpoint'"
        assert "json" not in desc.lower(), f"{name}: mentions 'json'"
        # Should be 15-30 words
        word_count = len(desc.split())
        assert 8 <= word_count <= 40, f"{name}: description has {word_count} words (want 8-40)"


def test_descriptions_use_gibson_verbs():
    """At least half of descriptions start with a Gibson verb."""
    gibson_verbs = {"retrieve", "search", "find", "check", "observe", "detect", "send",
                    "generate", "display", "notify", "open", "switch", "control", "assess",
                    "describe", "query", "highlight", "set", "confirm", "focus", "get"}
    verb_count = 0
    for _name, desc in TOOL_AFFORDANCES:
        first_word = desc.split()[0].lower().rstrip(",.")
        if first_word in gibson_verbs:
            verb_count += 1
    assert verb_count >= len(TOOL_AFFORDANCES) * 0.5, (
        f"Only {verb_count}/{len(TOOL_AFFORDANCES)} descriptions start with Gibson verbs"
    )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_tool_recruitment.py -v`
Expected: FAIL — module doesn't exist

- [ ] **Step 3: Create tool affordance descriptions**

Create `agents/hapax_daimonion/tool_affordances.py`:

```python
"""Tool affordance descriptions — semantic, not implementation.

Each tool is described in terms of what it AFFORDS to the system's
cognitive state, not how it works technically. These descriptions are
embedded in Qdrant for semantic matching against operator utterances.
"""

from __future__ import annotations

TOOL_AFFORDANCES: list[tuple[str, str]] = [
    # Information retrieval
    ("get_current_time", "Retrieve the current date and time for temporal awareness"),
    ("get_weather", "Retrieve current weather conditions and forecast for environmental context"),
    ("get_briefing", "Retrieve a comprehensive system briefing summarizing health, tasks, and status"),
    ("get_system_status", "Assess current system health including services, GPU, memory, and network"),
    ("get_calendar_today", "Retrieve upcoming calendar events and schedule for temporal planning"),
    ("get_desktop_state", "Observe the current desktop environment — active windows, workspaces, applications"),
    ("search_documents", "Search ingested knowledge for information relevant to a question or topic"),
    ("search_drive", "Search cloud documents for files and content matching a query"),
    ("search_emails", "Search email messages for correspondence matching a topic or person"),
    # Governance awareness
    ("check_consent_status", "Assess the current consent state for a person — what data flows are permitted"),
    ("describe_consent_flow", "Describe how consent detection and negotiation works in this system"),
    ("check_governance_health", "Assess governance system integrity — consent coverage, authority heartbeat"),
    # Scene perception
    ("query_scene_inventory", "Observe detected objects in camera feeds — what is present, where, how confident"),
    ("query_person_details", "Observe enriched person data — gaze direction, emotion, posture, gesture, depth"),
    ("query_object_motion", "Observe object movement — velocity, direction, temporal sighting history"),
    ("query_scene_state", "Observe scene classification — inferred activity, flow state, spatial arrangement"),
    ("highlight_detection", "Highlight a detected object with a visual indicator for operator attention"),
    ("set_detection_layers", "Control detection overlay visibility and detail level"),
    # Image generation
    ("generate_image", "Generate a visual image from a description or transform a captured scene"),
    ("analyze_scene", "Observe and analyze camera or screen content through vision reasoning"),
    # Communication
    ("send_sms", "Compose a text message for the operator to review before sending"),
    ("confirm_send_sms", "Confirm and send a previously composed text message"),
    # Desktop control
    ("open_app", "Open an application by name, optionally on a specific workspace"),
    ("confirm_open_app", "Confirm launching a previously requested application"),
    ("focus_window", "Bring a specific window to the foreground for operator attention"),
    ("switch_workspace", "Switch the active desktop workspace to a different number"),
]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_tool_recruitment.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add agents/hapax_daimonion/tool_affordances.py tests/test_tool_recruitment.py
git commit -m "feat(tools): Gibson-verb affordance descriptions for all tools"
```

---

### Task 2: Tool Recruitment Module

**Files:**
- Create: `agents/hapax_daimonion/tool_recruitment.py`
- Modify: `tests/test_tool_recruitment.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_tool_recruitment.py`:

```python
from agents.hapax_daimonion.tool_recruitment import ToolRecruitmentGate


def test_utterance_to_impingement():
    """Operator utterance is converted to an impingement for pipeline matching."""
    gate = ToolRecruitmentGate.__new__(ToolRecruitmentGate)
    gate._pipeline = None  # won't use pipeline in this test
    imp = gate._utterance_to_impingement("what's the weather like today?")
    assert imp.source == "operator.utterance"
    assert "weather" in imp.content.get("narrative", "")
    assert imp.strength == 1.0


def test_recruit_returns_tool_names():
    """recruit() returns a list of tool names that passed the pipeline threshold."""
    from unittest.mock import MagicMock

    gate = ToolRecruitmentGate.__new__(ToolRecruitmentGate)
    mock_pipeline = MagicMock()
    # Simulate pipeline returning two candidates
    from shared.affordance import SelectionCandidate
    mock_pipeline.select.return_value = [
        SelectionCandidate(capability_name="get_weather", combined=0.7),
        SelectionCandidate(capability_name="get_current_time", combined=0.3),
    ]
    gate._pipeline = mock_pipeline
    gate._tool_names = {"get_weather", "get_current_time", "search_documents"}

    recruited = gate.recruit("what's the weather?")
    assert "get_weather" in recruited
    assert "get_current_time" in recruited


def test_record_outcome_calls_pipeline():
    """Recording success/failure updates the pipeline's Thompson sampling."""
    from unittest.mock import MagicMock

    gate = ToolRecruitmentGate.__new__(ToolRecruitmentGate)
    gate._pipeline = MagicMock()
    gate.record_outcome("get_weather", success=True)
    gate._pipeline.record_outcome.assert_called_once_with("get_weather", success=True)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_tool_recruitment.py::test_utterance_to_impingement -v`
Expected: FAIL — module doesn't exist

- [ ] **Step 3: Create tool recruitment gate**

Create `agents/hapax_daimonion/tool_recruitment.py`:

```python
"""Tool recruitment gate — AffordancePipeline selects tools for each utterance.

Converts operator utterances to impingements, runs pipeline.select(),
and returns only recruited tool names. Records success/failure for
Thompson sampling learning.
"""

from __future__ import annotations

import logging
import time

from shared.affordance import CapabilityRecord, OperationalProperties, SelectionCandidate
from shared.impingement import Impingement, ImpingementType

log = logging.getLogger("tool.recruitment")


class ToolRecruitmentGate:
    """Gates tool availability through AffordancePipeline selection."""

    def __init__(self, pipeline, tool_names: set[str]) -> None:
        """Initialize with a shared AffordancePipeline and set of known tool names."""
        self._pipeline = pipeline
        self._tool_names = tool_names

    def recruit(self, utterance: str) -> list[str]:
        """Recruit tools for an operator utterance.

        Returns list of tool names that the pipeline selected above threshold.
        The LLM should only see schemas for these tools.
        """
        imp = self._utterance_to_impingement(utterance)
        candidates: list[SelectionCandidate] = self._pipeline.select(imp)
        recruited = [
            c.capability_name
            for c in candidates
            if c.capability_name in self._tool_names
        ]
        if recruited:
            log.info("Recruited tools for '%s': %s", utterance[:50], recruited)
        return recruited

    def record_outcome(self, tool_name: str, success: bool) -> None:
        """Record tool execution outcome for Thompson sampling learning."""
        self._pipeline.record_outcome(tool_name, success=success)
        log.debug("Recorded %s for %s", "success" if success else "failure", tool_name)

    @staticmethod
    def _utterance_to_impingement(utterance: str) -> Impingement:
        """Convert an operator utterance to an impingement for pipeline matching."""
        return Impingement(
            source="operator.utterance",
            type=ImpingementType.SALIENCE_INTEGRATION,
            timestamp=time.time(),
            strength=1.0,
            content={"narrative": utterance},
        )

    @staticmethod
    def register_tools(pipeline, affordances: list[tuple[str, str]]) -> int:
        """Register tool affordances in the pipeline's Qdrant index.

        Returns number successfully registered.
        """
        registered = 0
        for name, desc in affordances:
            ok = pipeline.index_capability(
                CapabilityRecord(
                    name=name,
                    description=desc,
                    daemon="hapax_daimonion",
                    operational=OperationalProperties(latency_class="fast"),
                )
            )
            if ok:
                registered += 1
        log.info("Registered %d/%d tool affordances", registered, len(affordances))
        return registered
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/test_tool_recruitment.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add agents/hapax_daimonion/tool_recruitment.py tests/test_tool_recruitment.py
git commit -m "feat(tools): tool recruitment gate with pipeline selection and learning"
```

---

### Task 3: Wire Pipeline Start to Use Tool Recruitment

**Files:**
- Modify: `agents/hapax_daimonion/pipeline_start.py`
- Modify: `agents/hapax_daimonion/init_pipeline.py`

- [ ] **Step 1: Register tool affordances at daemon startup**

In `agents/hapax_daimonion/init_pipeline.py`, in `precompute_pipeline_deps()`, after the speech_production registration, add tool registration:

```python
from agents.hapax_daimonion.tool_affordances import TOOL_AFFORDANCES
from agents.hapax_daimonion.tool_recruitment import ToolRecruitmentGate

ToolRecruitmentGate.register_tools(daemon._affordance_pipeline, TOOL_AFFORDANCES)
tool_names = {name for name, _ in TOOL_AFFORDANCES}
daemon._tool_recruitment_gate = ToolRecruitmentGate(daemon._affordance_pipeline, tool_names)
```

- [ ] **Step 2: Update `_resolve_tools()` to use recruitment gate**

In `agents/hapax_daimonion/pipeline_start.py`, modify `_resolve_tools()`. Currently it calls `daemon._tool_registry.schemas_for_llm(ctx)` to get ALL available tools. Change it to:

1. Get the full available tool list from `schemas_for_llm(ctx)` (availability filtering stays)
2. Store the gate reference on the pipeline context so the conversation pipeline can use it

The key change: don't filter schemas here. Instead, pass the recruitment gate to the ConversationPipeline, which will call `gate.recruit(utterance)` per turn.

Add to the pipeline start:

```python
# Pass recruitment gate to conversation pipeline for per-turn filtering
tool_recruitment_gate = getattr(daemon, "_tool_recruitment_gate", None)
```

Pass it to `ConversationPipeline.__init__()`:

```python
pipeline = ConversationPipeline(
    ...,
    tool_recruitment_gate=tool_recruitment_gate,
)
```

- [ ] **Step 3: Update ConversationPipeline to recruit per-turn**

In `agents/hapax_daimonion/conversation_pipeline.py`, add `tool_recruitment_gate` parameter to `__init__`:

```python
def __init__(self, ..., tool_recruitment_gate=None):
    ...
    self._tool_recruitment_gate = tool_recruitment_gate
```

In `_generate_response()`, before injecting tools into the LLM kwargs, add recruitment filtering:

```python
if self.tools and self._tool_recruitment_gate:
    recruited_names = self._tool_recruitment_gate.recruit(utterance)
    if recruited_names:
        kwargs["tools"] = [t for t in self.tools if t["function"]["name"] in recruited_names]
    else:
        # No tools recruited — LLM sees no tools
        pass
elif self.tools:
    # Fallback: no recruitment gate, use all available tools (backward compat)
    kwargs["tools"] = self.tools
```

- [ ] **Step 4: Record tool outcomes**

In `_handle_tool_calls()`, after tool execution, record success/failure:

```python
if self._tool_recruitment_gate:
    success = "error" not in str(result).lower()
    self._tool_recruitment_gate.record_outcome(tc["name"], success=success)
```

- [ ] **Step 5: Run tests**

Run: `uv run pytest tests/test_tool_recruitment.py tests/test_reverie_mixer.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add agents/hapax_daimonion/pipeline_start.py agents/hapax_daimonion/init_pipeline.py agents/hapax_daimonion/conversation_pipeline.py
git commit -m "feat(tools): wire tool recruitment gate into conversation pipeline"
```

---

### Task 4: Run Full Test Suite and Verify

**Files:** None (verification only)

- [ ] **Step 1: Run full test suite**

Run: `uv run pytest tests/ -q --ignore=tests/test_llm_integration.py -x`
Expected: All pass (pre-existing failures only)

- [ ] **Step 2: Lint**

Run: `uv run ruff check agents/hapax_daimonion/tool_affordances.py agents/hapax_daimonion/tool_recruitment.py agents/hapax_daimonion/pipeline_start.py agents/hapax_daimonion/conversation_pipeline.py agents/hapax_daimonion/init_pipeline.py`
Expected: All checks passed

- [ ] **Step 3: Restart voice daemon and verify**

```bash
systemctl --user restart hapax-daimonion.service
sleep 30
journalctl --user -u hapax-daimonion.service --since "30 sec ago" --no-pager 2>&1 | grep -i "tool\|afford\|recruit" | head -5
```

Expected: Log entries showing tool affordances registered in Qdrant.

- [ ] **Step 4: Commit any fixes**

```bash
git add -A && git commit -m "chore: Phase 3 verification fixes"
```
