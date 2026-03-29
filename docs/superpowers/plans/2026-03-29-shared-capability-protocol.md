# Phase 1: Shared Capability Protocol — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extract a shared Capability protocol, SystemContext, and CapabilityRegistry to `shared/` so all four capability types (perception backends, tools, speech, visual) conform to one interface.

**Architecture:** New `shared/capability.py` defines the protocol. Existing types get minimal additions (category, resource_tier, degrade) to conform. CapabilityRegistry provides unified query across all categories. ToolRegistry becomes a thin view over CapabilityRegistry. No behavioral changes — this is structural unification.

**Tech Stack:** Python 3.12, typing.Protocol, dataclasses

**Spec:** `docs/superpowers/specs/2026-03-29-capability-parity-design.md` (Phase 1)

---

## File Map

### New Files

| File | Responsibility |
|------|---------------|
| `shared/capability.py` | Capability protocol, CapabilityCategory, SystemContext, CapabilityRegistry |
| `tests/test_capability_protocol.py` | Protocol conformance, registry, filtering |

### Modified Files

| File | Change |
|------|--------|
| `agents/hapax_daimonion/tool_capability.py` | ToolCapability.category returns CapabilityCategory.TOOL; ToolContext → SystemContext; ToolRegistry delegates to CapabilityRegistry |
| `agents/hapax_daimonion/capability.py` | SpeechProductionCapability gains resource_tier, degrade(), category |
| `agents/effect_graph/capability.py` | ShaderGraphCapability gains available(), resource_tier, degrade(), category |
| `agents/hapax_daimonion/tool_definitions.py` | Import SystemContext instead of ToolContext |
| `agents/hapax_daimonion/__main__.py` | Import SystemContext instead of ToolContext |

---

## Task 1: Capability Protocol + SystemContext + CapabilityRegistry

**Files:**
- Create: `shared/capability.py`
- Test: `tests/test_capability_protocol.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_capability_protocol.py
"""Tests for shared capability protocol and registry."""

from __future__ import annotations

import unittest

from shared.capability import (
    Capability,
    CapabilityCategory,
    CapabilityRegistry,
    ResourceTier,
    SystemContext,
)


def _make_ctx(**overrides) -> SystemContext:
    defaults = {
        "stimmung_stance": "nominal",
        "consent_state": {},
        "guest_present": False,
        "active_backends": frozenset({"vision", "hyprland", "phone"}),
        "working_mode": "rnd",
        "experiment_flags": {},
        "tpn_active": False,
    }
    defaults.update(overrides)
    return SystemContext(**defaults)


class StubCapability:
    """Minimal Capability implementation for testing."""

    def __init__(
        self,
        name: str = "stub",
        category: CapabilityCategory = CapabilityCategory.TOOL,
        resource_tier: ResourceTier = ResourceTier.INSTANT,
        is_available: bool = True,
    ):
        self._name = name
        self._category = category
        self._resource_tier = resource_tier
        self._is_available = is_available

    @property
    def name(self) -> str:
        return self._name

    @property
    def category(self) -> CapabilityCategory:
        return self._category

    @property
    def resource_tier(self) -> ResourceTier:
        return self._resource_tier

    def available(self, ctx: SystemContext) -> bool:
        return self._is_available

    def degrade(self) -> str:
        return f"{self._name} is unavailable"


class TestSystemContext(unittest.TestCase):
    def test_frozen(self):
        ctx = _make_ctx()
        with self.assertRaises(AttributeError):
            ctx.stimmung_stance = "degraded"  # type: ignore[misc]

    def test_defaults(self):
        ctx = SystemContext()
        assert ctx.stimmung_stance == "nominal"
        assert ctx.working_mode == "rnd"
        assert ctx.tpn_active is False


class TestCapabilityProtocol(unittest.TestCase):
    def test_stub_is_capability(self):
        cap = StubCapability()
        assert isinstance(cap, Capability)

    def test_stub_properties(self):
        cap = StubCapability("test", CapabilityCategory.EXPRESSION, ResourceTier.HEAVY)
        assert cap.name == "test"
        assert cap.category == CapabilityCategory.EXPRESSION
        assert cap.resource_tier == ResourceTier.HEAVY

    def test_available_delegates(self):
        cap = StubCapability(is_available=False)
        assert cap.available(_make_ctx()) is False

    def test_degrade_returns_string(self):
        cap = StubCapability("my_tool")
        assert "my_tool" in cap.degrade()


class TestCapabilityRegistry(unittest.TestCase):
    def test_register_and_get(self):
        reg = CapabilityRegistry()
        cap = StubCapability("a")
        reg.register(cap)
        assert reg.get("a") is cap

    def test_register_duplicate_raises(self):
        reg = CapabilityRegistry()
        reg.register(StubCapability("a"))
        with self.assertRaises(ValueError):
            reg.register(StubCapability("a"))

    def test_all_returns_registered(self):
        reg = CapabilityRegistry()
        reg.register(StubCapability("a"))
        reg.register(StubCapability("b"))
        assert len(reg.all()) == 2

    def test_available_filters(self):
        reg = CapabilityRegistry()
        reg.register(StubCapability("on", is_available=True))
        reg.register(StubCapability("off", is_available=False))
        available = reg.available(_make_ctx())
        assert len(available) == 1
        assert available[0].name == "on"

    def test_available_filters_by_category(self):
        reg = CapabilityRegistry()
        reg.register(StubCapability("t", category=CapabilityCategory.TOOL))
        reg.register(StubCapability("e", category=CapabilityCategory.EXPRESSION))
        tools = reg.available(_make_ctx(), category=CapabilityCategory.TOOL)
        assert len(tools) == 1
        assert tools[0].name == "t"

    def test_get_missing_returns_none(self):
        reg = CapabilityRegistry()
        assert reg.get("nonexistent") is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_capability_protocol.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'shared.capability'`

- [ ] **Step 3: Implement shared/capability.py**

```python
# shared/capability.py
"""Shared capability protocol for all Hapax subsystems.

Every capability — perception backends, tools, expression (speech, visual),
modulation — conforms to this protocol. It declares what it provides, what
it requires, when it's available, and how it degrades.

Phase 1 of capability parity (queue #017).
"""

from __future__ import annotations

import enum
import logging
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

log = logging.getLogger(__name__)


class CapabilityCategory(enum.Enum):
    PERCEPTION = "perception"
    TOOL = "tool"
    EXPRESSION = "expression"
    MODULATION = "modulation"


class ResourceTier(enum.Enum):
    INSTANT = "instant"
    LIGHT = "light"
    HEAVY = "heavy"


@dataclass(frozen=True)
class SystemContext:
    """Snapshot of system state used for capability availability decisions.

    Replaces ToolContext with a universal context used by all capability types.
    """

    stimmung_stance: str = "nominal"
    consent_state: dict = field(default_factory=dict)
    guest_present: bool = False
    active_backends: frozenset[str] = field(default_factory=frozenset)
    working_mode: str = "rnd"
    experiment_flags: dict = field(default_factory=dict)
    tpn_active: bool = False


@runtime_checkable
class Capability(Protocol):
    """Universal interface for all Hapax capabilities."""

    @property
    def name(self) -> str: ...

    @property
    def category(self) -> CapabilityCategory: ...

    @property
    def resource_tier(self) -> ResourceTier: ...

    def available(self, ctx: SystemContext) -> bool: ...

    def degrade(self) -> str: ...


class CapabilityRegistry:
    """Unified registry for all capabilities across all categories."""

    def __init__(self) -> None:
        self._capabilities: dict[str, Capability] = {}

    def register(self, cap: Capability) -> None:
        if cap.name in self._capabilities:
            raise ValueError(
                f"Capability {cap.name!r} already registered"
            )
        self._capabilities[cap.name] = cap
        log.debug("Registered capability: %s (%s)", cap.name, cap.category.value)

    def get(self, name: str) -> Capability | None:
        return self._capabilities.get(name)

    def all(self) -> list[Capability]:
        return list(self._capabilities.values())

    def available(
        self,
        ctx: SystemContext,
        category: CapabilityCategory | None = None,
    ) -> list[Capability]:
        caps = self._capabilities.values()
        if category is not None:
            caps = [c for c in caps if c.category == category]
        return [c for c in caps if c.available(ctx)]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_capability_protocol.py -v`
Expected: All 11 tests PASS

- [ ] **Step 5: Commit**

```bash
git add shared/capability.py tests/test_capability_protocol.py
git commit -m "feat: shared Capability protocol + SystemContext + CapabilityRegistry"
```

---

## Task 2: Migrate ToolCapability to Shared Protocol

**Files:**
- Modify: `agents/hapax_daimonion/tool_capability.py`
- Modify: `agents/hapax_daimonion/tool_definitions.py`
- Modify: `agents/hapax_daimonion/__main__.py`
- Test: `tests/hapax_daimonion/test_tool_capability.py` (update imports)
- Test: `tests/hapax_daimonion/test_tool_definitions.py` (update imports)

- [ ] **Step 1: Update tool_capability.py**

Replace the module-level `ToolCategory`, `ResourceTier`, and `ToolContext` with imports from `shared.capability`, and add `category` property:

In tool_capability.py, replace:

```python
class ToolCategory(enum.Enum):
    INFORMATION = "information"
    ACTION = "action"
    CONTROL = "control"


class ResourceTier(enum.Enum):
    INSTANT = "instant"
    LIGHT = "light"
    HEAVY = "heavy"


@dataclass(frozen=True)
class ToolContext:
    """Snapshot of system state used for tool availability decisions."""

    stimmung_stance: str = "nominal"
    consent_state: dict = field(default_factory=dict)
    guest_present: bool = False
    active_backends: frozenset[str] = field(default_factory=frozenset)
    working_mode: str = "rnd"
    experiment_tools_enabled: bool = False
```

With:

```python
from shared.capability import (
    CapabilityCategory,
    ResourceTier,
    SystemContext,
)

# Backward compatibility aliases
ToolContext = SystemContext


class ToolCategory(enum.Enum):
    """Tool-specific sub-categories within CapabilityCategory.TOOL."""

    INFORMATION = "information"
    ACTION = "action"
    CONTROL = "control"
```

Add `category` property to `ToolCapability`:

```python
    @property
    def category_cap(self) -> CapabilityCategory:
        """Capability protocol conformance."""
        return CapabilityCategory.TOOL
```

Wait — the protocol expects `category` as a property name, but `ToolCapability` has a `category` field of type `ToolCategory`. We need to reconcile. The cleanest approach: rename the existing field to `tool_category` and add a `category` property that returns `CapabilityCategory.TOOL`.

Actually, simpler: the Capability protocol's `category` returns `CapabilityCategory`. ToolCapability's existing `category` field returns `ToolCategory`. These are different types. The protocol check will fail. Fix: add a property that shadows the dataclass field is messy. Instead, keep the existing `category` field as `tool_category` and add `category` as a property.

Change in ToolCapability dataclass:

```python
@dataclass
class ToolCapability:
    name: str
    description: str
    schema: dict
    handler: Callable

    tool_category: ToolCategory    # was: category
    resource_tier: ResourceTier
    requires_consent: list[str] = field(default_factory=list)
    requires_backends: list[str] = field(default_factory=list)
    requires_confirmation: bool = False
    timeout_s: float = 3.0

    @property
    def category(self) -> CapabilityCategory:
        return CapabilityCategory.TOOL
```

Update `available()` to accept `SystemContext` (backward compatible — has all the same fields plus `experiment_flags` and `tpn_active`). The `experiment_tools_enabled` check reads from `experiment_flags`:

```python
    def available(self, ctx: SystemContext) -> bool:
        if ctx.working_mode == "research" and not ctx.experiment_flags.get(
            "tools_enabled", False
        ):
            return False
        # ... rest unchanged
```

- [ ] **Step 2: Update tool_definitions.py**

Change `category=ToolCategory.INFORMATION` → `tool_category=ToolCategory.INFORMATION` in the `_META` dict and the `_cap()` helper. Change `ToolContext` → `SystemContext` import.

- [ ] **Step 3: Update __main__.py**

Change `from agents.hapax_daimonion.tool_capability import ToolContext` → `from shared.capability import SystemContext`. Update the `tool_ctx = ToolContext(...)` call to `tool_ctx = SystemContext(...)` and change `experiment_tools_enabled=...` to `experiment_flags={"tools_enabled": ...}`.

- [ ] **Step 4: Update test imports**

In `test_tool_capability.py`: import `ResourceTier` and `SystemContext` from `shared.capability`. Update `_make_ctx` to use `SystemContext` with `experiment_flags` dict instead of `experiment_tools_enabled`. Update `ToolCategory` import from `tool_capability`.

In `test_tool_definitions.py`: same import updates.

- [ ] **Step 5: Run tests**

Run: `uv run pytest tests/hapax_daimonion/test_tool_capability.py tests/hapax_daimonion/test_tool_definitions.py tests/test_capability_protocol.py -v`
Expected: All pass

- [ ] **Step 6: Verify protocol conformance**

Add a test in `test_capability_protocol.py`:

```python
class TestToolCapabilityConformance(unittest.TestCase):
    def test_tool_capability_is_capability(self):
        from agents.hapax_daimonion.tool_capability import ToolCapability, ToolCategory

        async def noop(args):
            return "ok"

        tool = ToolCapability(
            name="test",
            description="test",
            schema={"type": "function", "function": {"name": "test", "description": "", "parameters": {"type": "object", "properties": {}, "required": []}}},
            handler=noop,
            tool_category=ToolCategory.INFORMATION,
            resource_tier=ResourceTier.INSTANT,
        )
        assert isinstance(tool, Capability)
        assert tool.category == CapabilityCategory.TOOL
```

- [ ] **Step 7: Run all tests**

Run: `uv run pytest tests/hapax_daimonion/test_tool_capability.py tests/hapax_daimonion/test_tool_definitions.py tests/test_capability_protocol.py -v`
Expected: All pass

- [ ] **Step 8: Commit**

```bash
git add shared/capability.py agents/hapax_daimonion/tool_capability.py agents/hapax_daimonion/tool_definitions.py agents/hapax_daimonion/__main__.py tests/hapax_daimonion/test_tool_capability.py tests/hapax_daimonion/test_tool_definitions.py tests/test_capability_protocol.py
git commit -m "refactor: ToolCapability conforms to shared Capability protocol"
```

---

## Task 3: Migrate SpeechProductionCapability

**Files:**
- Modify: `agents/hapax_daimonion/capability.py`
- Test: `tests/test_capability_protocol.py` (add conformance test)

- [ ] **Step 1: Add protocol properties to SpeechProductionCapability**

In `agents/hapax_daimonion/capability.py`, add imports and properties:

```python
from shared.capability import CapabilityCategory, ResourceTier, SystemContext
```

Add to the class:

```python
    @property
    def category(self) -> CapabilityCategory:
        return CapabilityCategory.EXPRESSION

    @property
    def resource_tier(self) -> ResourceTier:
        return ResourceTier.HEAVY  # GPU for TTS

    def available(self, ctx: SystemContext) -> bool:
        return True  # always available when daemon is running

    def degrade(self) -> str:
        return "Speech production is unavailable — voice daemon not active."
```

Note: `name` property already exists. `available()` is new (speech is always available when the daemon runs — gating happens in the VetoChain, not at the capability level).

- [ ] **Step 2: Add conformance test**

In `tests/test_capability_protocol.py`:

```python
class TestSpeechCapabilityConformance(unittest.TestCase):
    def test_speech_capability_is_capability(self):
        from agents.hapax_daimonion.capability import SpeechProductionCapability

        cap = SpeechProductionCapability()
        assert isinstance(cap, Capability)
        assert cap.category == CapabilityCategory.EXPRESSION
        assert cap.resource_tier == ResourceTier.HEAVY
        assert cap.name == "speech_production"
        assert "unavailable" in cap.degrade().lower() or "speech" in cap.degrade().lower()
```

- [ ] **Step 3: Run tests**

Run: `uv run pytest tests/test_capability_protocol.py -v`
Expected: All pass

- [ ] **Step 4: Commit**

```bash
git add agents/hapax_daimonion/capability.py tests/test_capability_protocol.py
git commit -m "refactor: SpeechProductionCapability conforms to shared Capability protocol"
```

---

## Task 4: Migrate ShaderGraphCapability

**Files:**
- Modify: `agents/effect_graph/capability.py`
- Test: `tests/test_capability_protocol.py` (add conformance test)

- [ ] **Step 1: Add protocol properties to ShaderGraphCapability**

In `agents/effect_graph/capability.py`, add imports and properties:

```python
from shared.capability import CapabilityCategory, ResourceTier, SystemContext
```

Add to the class:

```python
    @property
    def category(self) -> CapabilityCategory:
        return CapabilityCategory.EXPRESSION

    @property
    def resource_tier(self) -> ResourceTier:
        return ResourceTier.HEAVY  # GPU for shader rendering

    def available(self, ctx: SystemContext) -> bool:
        """Available when the imagination pipeline directory exists."""
        from pathlib import Path

        return Path("/dev/shm/hapax-imagination/pipeline").exists()

    def degrade(self) -> str:
        return "Visual expression is unavailable — imagination pipeline not running."
```

- [ ] **Step 2: Add conformance test**

In `tests/test_capability_protocol.py`:

```python
class TestShaderGraphConformance(unittest.TestCase):
    def test_shader_graph_is_capability(self):
        from agents.effect_graph.capability import ShaderGraphCapability

        cap = ShaderGraphCapability()
        assert isinstance(cap, Capability)
        assert cap.category == CapabilityCategory.EXPRESSION
        assert cap.resource_tier == ResourceTier.HEAVY
        assert cap.name == "shader_graph"

    def test_shader_graph_degrade(self):
        from agents.effect_graph.capability import ShaderGraphCapability

        cap = ShaderGraphCapability()
        msg = cap.degrade()
        assert "visual" in msg.lower() or "unavailable" in msg.lower()
```

- [ ] **Step 3: Run tests**

Run: `uv run pytest tests/test_capability_protocol.py -v`
Expected: All pass

- [ ] **Step 4: Commit**

```bash
git add agents/effect_graph/capability.py tests/test_capability_protocol.py
git commit -m "refactor: ShaderGraphCapability conforms to shared Capability protocol"
```

---

## Task 5: PerceptionBackend Adapter

**Files:**
- Create: `shared/capability_adapters.py`
- Test: `tests/test_capability_protocol.py` (add adapter test)

- [ ] **Step 1: Create adapter that wraps PerceptionBackend as Capability**

```python
# shared/capability_adapters.py
"""Adapters that wrap existing types as Capability protocol instances.

PerceptionBackend has available() with no args (checks hardware).
This adapter wraps it to conform to the Capability protocol.
"""

from __future__ import annotations

from shared.capability import CapabilityCategory, ResourceTier, SystemContext


class PerceptionBackendAdapter:
    """Wraps a PerceptionBackend as a Capability for registry purposes."""

    def __init__(self, backend) -> None:
        self._backend = backend

    @property
    def name(self) -> str:
        return self._backend.name

    @property
    def category(self) -> CapabilityCategory:
        return CapabilityCategory.PERCEPTION

    @property
    def resource_tier(self) -> ResourceTier:
        tier = self._backend.tier
        if tier.value == "fast":
            return ResourceTier.INSTANT
        if tier.value == "slow":
            return ResourceTier.LIGHT
        return ResourceTier.INSTANT  # EVENT → INSTANT

    def available(self, ctx: SystemContext) -> bool:
        return self._backend.available()

    def degrade(self) -> str:
        return f"Perception backend {self._backend.name} is unavailable."

    @property
    def backend(self):
        """Access the wrapped backend for medium-specific operations."""
        return self._backend
```

- [ ] **Step 2: Add adapter test**

In `tests/test_capability_protocol.py`:

```python
class TestPerceptionBackendAdapter(unittest.TestCase):
    def test_adapter_is_capability(self):
        from unittest.mock import MagicMock

        from shared.capability_adapters import PerceptionBackendAdapter

        mock_backend = MagicMock()
        mock_backend.name = "test_backend"
        mock_backend.tier.value = "fast"
        mock_backend.available.return_value = True

        adapter = PerceptionBackendAdapter(mock_backend)
        assert isinstance(adapter, Capability)
        assert adapter.category == CapabilityCategory.PERCEPTION
        assert adapter.resource_tier == ResourceTier.INSTANT
        assert adapter.available(_make_ctx()) is True

    def test_adapter_slow_tier(self):
        from unittest.mock import MagicMock

        from shared.capability_adapters import PerceptionBackendAdapter

        mock_backend = MagicMock()
        mock_backend.name = "slow_backend"
        mock_backend.tier.value = "slow"
        mock_backend.available.return_value = True

        adapter = PerceptionBackendAdapter(mock_backend)
        assert adapter.resource_tier == ResourceTier.LIGHT

    def test_adapter_unavailable(self):
        from unittest.mock import MagicMock

        from shared.capability_adapters import PerceptionBackendAdapter

        mock_backend = MagicMock()
        mock_backend.name = "broken"
        mock_backend.available.return_value = False

        adapter = PerceptionBackendAdapter(mock_backend)
        assert adapter.available(_make_ctx()) is False
```

- [ ] **Step 3: Run tests**

Run: `uv run pytest tests/test_capability_protocol.py -v`
Expected: All pass

- [ ] **Step 4: Commit**

```bash
git add shared/capability_adapters.py tests/test_capability_protocol.py
git commit -m "feat: PerceptionBackendAdapter wraps backends as Capability"
```

---

## Task 6: ToolRegistry Delegates to CapabilityRegistry

**Files:**
- Modify: `agents/hapax_daimonion/tool_capability.py`
- Modify: `agents/hapax_daimonion/tool_definitions.py`
- Test: `tests/test_capability_protocol.py` (add integration test)

- [ ] **Step 1: Update ToolRegistry to wrap CapabilityRegistry**

Replace the standalone `ToolRegistry` class with one that delegates to `CapabilityRegistry`:

```python
class ToolRegistry:
    """Tool-specific view over CapabilityRegistry.

    Provides tool-specific methods (schemas_for_llm, handler_map) while
    delegating storage and name-uniqueness to the shared registry.
    """

    def __init__(self, registry: CapabilityRegistry | None = None) -> None:
        self._registry = registry or CapabilityRegistry()

    @property
    def capability_registry(self) -> CapabilityRegistry:
        return self._registry

    def register(self, tool: ToolCapability) -> None:
        try:
            self._registry.register(tool)
        except ValueError:
            log.warning("Tool %s already registered, skipping", tool.name)

    def get(self, name: str) -> ToolCapability | None:
        cap = self._registry.get(name)
        return cap if isinstance(cap, ToolCapability) else None

    def available_tools(self, ctx: SystemContext) -> list[ToolCapability]:
        return [
            c
            for c in self._registry.available(ctx, category=CapabilityCategory.TOOL)
            if isinstance(c, ToolCapability)
        ]

    def schemas_for_llm(self, ctx: SystemContext) -> list[dict]:
        return [t.schema for t in self.available_tools(ctx)]

    def handler_map(self, ctx: SystemContext) -> dict[str, Callable]:
        return {t.name: t.handler for t in self.available_tools(ctx)}

    def all_tools(self) -> list[ToolCapability]:
        return [
            c for c in self._registry.all() if isinstance(c, ToolCapability)
        ]
```

Add import at top:

```python
from shared.capability import CapabilityCategory, CapabilityRegistry, SystemContext
```

- [ ] **Step 2: Update build_registry in tool_definitions.py**

Change `build_registry()` to accept an optional `CapabilityRegistry` and pass it to `ToolRegistry`:

```python
def build_registry(
    guest_mode: bool = False,
    config=None,
    webcam_capturer=None,
    screen_capturer=None,
    capability_registry: CapabilityRegistry | None = None,
) -> ToolRegistry:
    if guest_mode:
        return ToolRegistry(capability_registry)

    # ... rest unchanged, but construct ToolRegistry with:
    registry = ToolRegistry(capability_registry)
    # ... register tools as before
```

- [ ] **Step 3: Add integration test**

In `tests/test_capability_protocol.py`:

```python
class TestToolRegistryDelegation(unittest.TestCase):
    def test_tool_registry_delegates_to_capability_registry(self):
        from agents.hapax_daimonion.tool_capability import ToolCapability, ToolCategory, ToolRegistry

        cap_reg = CapabilityRegistry()
        tool_reg = ToolRegistry(cap_reg)

        async def noop(args):
            return "ok"

        tool = ToolCapability(
            name="test_tool",
            description="test",
            schema={"type": "function", "function": {"name": "test_tool", "description": "", "parameters": {"type": "object", "properties": {}, "required": []}}},
            handler=noop,
            tool_category=ToolCategory.INFORMATION,
            resource_tier=ResourceTier.INSTANT,
        )
        tool_reg.register(tool)

        # Visible in both registries
        assert cap_reg.get("test_tool") is tool
        assert tool_reg.get("test_tool") is tool

        # Available filtered by category
        ctx = _make_ctx()
        assert len(cap_reg.available(ctx, category=CapabilityCategory.TOOL)) == 1
        assert len(tool_reg.available_tools(ctx)) == 1

    def test_cross_category_name_conflict(self):
        from agents.hapax_daimonion.tool_capability import ToolCapability, ToolCategory, ToolRegistry

        cap_reg = CapabilityRegistry()
        tool_reg = ToolRegistry(cap_reg)

        # Register a non-tool capability with same name
        cap_reg.register(StubCapability("conflict", category=CapabilityCategory.EXPRESSION))

        async def noop(args):
            return "ok"

        tool = ToolCapability(
            name="conflict",
            description="test",
            schema={"type": "function", "function": {"name": "conflict", "description": "", "parameters": {"type": "object", "properties": {}, "required": []}}},
            handler=noop,
            tool_category=ToolCategory.INFORMATION,
            resource_tier=ResourceTier.INSTANT,
        )
        # Should warn and skip (not crash)
        tool_reg.register(tool)
        # Original stays
        assert cap_reg.get("conflict").category == CapabilityCategory.EXPRESSION
```

- [ ] **Step 4: Run all tests**

Run: `uv run pytest tests/test_capability_protocol.py tests/hapax_daimonion/test_tool_capability.py tests/hapax_daimonion/test_tool_definitions.py -v`
Expected: All pass

- [ ] **Step 5: Commit**

```bash
git add agents/hapax_daimonion/tool_capability.py agents/hapax_daimonion/tool_definitions.py tests/test_capability_protocol.py
git commit -m "refactor: ToolRegistry delegates to shared CapabilityRegistry"
```

---

## Task 7: Full Test Suite + PR

- [ ] **Step 1: Run full daimonion test suite**

Run: `uv run pytest tests/hapax_daimonion/ -q --ignore=tests/hapax_daimonion/test_tracing.py --ignore=tests/hapax_daimonion/test_tracing_flush_timeout.py --ignore=tests/hapax_daimonion/test_tracing_robustness.py`
Expected: 0 new failures (same pass count as before)

- [ ] **Step 2: Run shared tests**

Run: `uv run pytest tests/test_capability_protocol.py -v`
Expected: All pass

- [ ] **Step 3: Lint**

Run: `uv run ruff check . && uv run ruff format --check .`
Expected: Clean

- [ ] **Step 4: Push and create PR**

```bash
git push -u origin HEAD
gh pr create --title "feat: shared Capability protocol — unified registration for all capabilities" --body "..."
```

- [ ] **Step 5: Monitor CI, fix failures, merge when green**
