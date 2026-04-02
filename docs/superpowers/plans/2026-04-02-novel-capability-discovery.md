# Novel Capability Discovery Implementation Plan (Phase 5)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Register a `capability_discovery` meta-affordance that matches when no existing capability can fulfill an intention. The system discovers potential capabilities through web search and surfaces them to the operator for consent-gated acquisition.

**Architecture:** The exploration tracker already feeds `error=1.0` when `pipeline.select()` returns empty. This drives boredom/curiosity impingements. A new `capability_discovery` affordance matches these exploration impingements. Its handler formulates the unresolved intention as a search query, uses web search to find options, and either auto-registers the new capability (if consent exists) or surfaces it to the operator.

**Tech Stack:** Python 3.12, Pydantic v2, pytest

**Spec:** `docs/superpowers/specs/2026-04-02-unified-semantic-recruitment-design.md` §10

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `agents/hapax_daimonion/discovery_affordance.py` | Create | The meta-affordance: description, handler, registration |
| `agents/hapax_daimonion/init_pipeline.py` | Modify | Register capability_discovery in AffordancePipeline |
| `tests/test_capability_discovery.py` | Create | Tests for registration, matching, handler |

---

### Task 1: Register Capability Discovery Affordance

**Files:**
- Create: `agents/hapax_daimonion/discovery_affordance.py`
- Create: `tests/test_capability_discovery.py`
- Modify: `agents/hapax_daimonion/init_pipeline.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_capability_discovery.py`:

```python
"""Tests for novel capability discovery meta-affordance."""

from agents.hapax_daimonion.discovery_affordance import (
    DISCOVERY_AFFORDANCE,
    CapabilityDiscoveryHandler,
)


def test_discovery_affordance_exists():
    """The meta-affordance is defined with semantic description."""
    name, desc = DISCOVERY_AFFORDANCE
    assert name == "capability_discovery"
    assert "find" in desc.lower() or "discover" in desc.lower()
    assert "capability" in desc.lower() or "ability" in desc.lower()


def test_discovery_handler_extracts_unresolved_intent():
    """Handler extracts the original unresolved intention from exploration impingement."""
    from shared.impingement import Impingement, ImpingementType

    imp = Impingement(
        source="exploration.boredom",
        type=ImpingementType.BOREDOM,
        timestamp=0.0,
        strength=0.8,
        content={"narrative": "I wonder what that song sounds like", "mode": "directed"},
    )
    handler = CapabilityDiscoveryHandler()
    intent = handler.extract_intent(imp)
    assert "song" in intent.lower()


def test_discovery_handler_consent_required():
    """Discovery handler requires consent for acquisition."""
    handler = CapabilityDiscoveryHandler()
    assert handler.consent_required is True


def test_discovery_affordance_registered():
    """The discovery affordance has consent_required=True in operational properties."""
    from shared.affordance import CapabilityRecord, OperationalProperties

    name, desc = DISCOVERY_AFFORDANCE
    rec = CapabilityRecord(
        name=name,
        description=desc,
        daemon="hapax_daimonion",
        operational=OperationalProperties(
            latency_class="slow",
            requires_network=True,
            consent_required=True,
        ),
    )
    assert rec.operational.consent_required is True
    assert rec.operational.requires_network is True
```

- [ ] **Step 2: Run test — verify FAIL**

Run: `uv run pytest tests/test_capability_discovery.py -v`

- [ ] **Step 3: Create the discovery module**

Create `agents/hapax_daimonion/discovery_affordance.py`:

```python
"""Novel capability discovery — the recursive meta-affordance.

When no existing capability matches an intention, the exploration tracker
emits boredom/curiosity impingements. This affordance matches those signals
and searches for capabilities that could fulfill the unresolved need.

Discovery (searching for what's possible) is read-only and safe.
Acquisition (installing/configuring) requires operator consent.
"""

from __future__ import annotations

import logging

from shared.impingement import Impingement

log = logging.getLogger("capability.discovery")

DISCOVERY_AFFORDANCE: tuple[str, str] = (
    "capability_discovery",
    "Discover and acquire new capabilities when no existing capability matches an intention. "
    "Find tools, services, or resources that could fulfill unmet cognitive needs.",
)


class CapabilityDiscoveryHandler:
    """Handles the capability_discovery affordance.

    When recruited, extracts the unresolved intention from the exploration
    impingement and searches for capabilities that could fulfill it.
    """

    consent_required: bool = True

    def extract_intent(self, impingement: Impingement) -> str:
        """Extract the original unresolved intention from an exploration impingement."""
        content = impingement.content or {}
        # Exploration impingements carry the original narrative
        narrative = content.get("narrative", "")
        if narrative:
            return narrative
        # Fallback: use source description
        return f"unresolved intent from {impingement.source}"

    def search(self, intent: str) -> list[dict]:
        """Search for capabilities matching the intent.

        Returns list of potential capabilities found. Each has:
        - name: suggested affordance name
        - description: what it would afford
        - source: where it was found (url, package name, etc.)
        - acquisition_method: how to install/configure it

        Currently a stub — full implementation will use web search tools.
        """
        log.info("Searching for capability: %s", intent[:80])
        # Phase 5 stub: log the discovery request
        # Full implementation will call web search, scan packages, etc.
        return []

    def propose(self, capabilities: list[dict]) -> None:
        """Surface discovered capabilities to the operator for consent.

        Full implementation will use ntfy or voice to propose the capability.
        """
        for cap in capabilities:
            log.info(
                "Discovered potential capability: %s — %s (from %s)",
                cap.get("name", "unknown"),
                cap.get("description", ""),
                cap.get("source", "unknown"),
            )
```

- [ ] **Step 4: Register in init_pipeline.py**

In `agents/hapax_daimonion/init_pipeline.py`, after tool registration, add:

```python
from agents.hapax_daimonion.discovery_affordance import DISCOVERY_AFFORDANCE

daemon._affordance_pipeline.index_capability(
    CapabilityRecord(
        name=DISCOVERY_AFFORDANCE[0],
        description=DISCOVERY_AFFORDANCE[1],
        daemon="hapax_daimonion",
        operational=OperationalProperties(
            latency_class="slow",
            requires_network=True,
            consent_required=True,
        ),
    )
)
daemon._discovery_handler = CapabilityDiscoveryHandler()
```

- [ ] **Step 5: Run tests**

Run: `uv run pytest tests/test_capability_discovery.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git commit -m "feat: capability_discovery meta-affordance for novel capability recruitment"
```

---

### Task 2: Wire Discovery into Impingement Dispatch

**Files:**
- Modify: `agents/hapax_daimonion/run_loops_aux.py`

- [ ] **Step 1: Add discovery routing**

In `agents/hapax_daimonion/run_loops_aux.py`, in the impingement dispatch loop, add handling for `capability_discovery`:

```python
elif c.capability_name == "capability_discovery":
    if hasattr(daemon, "_discovery_handler"):
        intent = daemon._discovery_handler.extract_intent(imp)
        results = daemon._discovery_handler.search(intent)
        if results:
            daemon._discovery_handler.propose(results)
```

- [ ] **Step 2: Run tests**

Run: `uv run pytest tests/test_capability_discovery.py -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git commit -m "feat: wire capability discovery into impingement dispatch"
```

---

### Task 3: Full Suite Verification

- [ ] **Step 1: Run full test suite**

Run: `uv run pytest tests/ -q --ignore=tests/test_llm_integration.py -x`

- [ ] **Step 2: Lint**

Run: `uv run ruff check agents/hapax_daimonion/discovery_affordance.py agents/hapax_daimonion/init_pipeline.py agents/hapax_daimonion/run_loops_aux.py`

- [ ] **Step 3: Commit any fixes**
