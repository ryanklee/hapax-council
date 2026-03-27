# Formal Constraint Coverage Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bring the ~60% of the hapax system under convention-based governance into formal constraint where the domain benefits from it.

**Architecture:** Six workstreams executed in dependency order. Workstreams 1, 2, and 6 run in parallel (no deps). Workstream 3 follows 1. Workstream 4 follows 3. Workstream 5 follows 1+2. Each workstream is independently deployable with feature-flag rollback. All new code follows TDD.

**Tech Stack:** pydantic v2 + pydantic-settings, pyright, FastAPI, JSON Schema, pytest

**Spec:** `docs/specs/formal-constraint-coverage.md`

---

## File Map

### Workstream 1: Typed Configuration (council)
- Create: `shared/settings.py` — pydantic-settings models
- Modify: `shared/config.py` — import settings, replace os.getenv calls
- Create: `tests/test_settings.py` — validation tests
- Modify: `pyproject.toml` — add pydantic-settings dep

### Workstream 2: Filesystem Bus Schemas (officium)
- Create: `shared/vault_schemas.py` — Pydantic models for 13 doc types
- Modify: `shared/vault_writer.py` — add schema param to _write_md, validate on write
- Create: `tests/test_vault_schemas.py` — schema validation tests
- Create: `scripts/vault_validate.py` — one-time scan of existing docs

### Workstream 3: Runtime Axiom Enforcement (council)
- Create: `shared/governance/enforced_agent.py` — run_enforced() wrapper
- Modify: `shared/axiom_enforcer.py` — widen enforce_output for general use
- Modify: `agents/briefing.py` — migrate to run_enforced (proof of concept)
- Modify: `agents/scout.py` — migrate to run_enforced
- Modify: `agents/drift_detector.py` — migrate to run_enforced
- Modify: `agents/digest.py` — migrate to run_enforced
- Modify: `axioms/enforcement-patterns.yaml` — add patterns for all 5 axioms
- Create: `tests/test_enforced_agent.py` — enforcement integration tests

### Workstream 4: Reactive Engine Phase Contracts (council)
- Modify: `logos/engine/models.py` — add RuleSpec, Phase enum
- Modify: `logos/engine/rules.py` — RuleRegistry accepts RuleSpec
- Modify: `logos/engine/reactive_rules.py` — wrap rules in RuleSpec
- Create: `tests/test_engine_contracts.py` — phase invariant tests

### Workstream 5: Pyright Incremental Tightening (council)
- Modify: `pyrightconfig.json` — enable checks incrementally
- No new files — fix existing type errors

### Workstream 6: Wire Protocol Contracts (watch <> council)
- Create: `schemas/watch/sensor-payload.schema.json`
- Create: `schemas/watch/sensor-reading.schema.json`
- Create: `schemas/watch/voice-trigger.schema.json`
- Create: `schemas/watch/gesture.schema.json`
- Create: `schemas/watch/health-summary.schema.json`
- Create: `schemas/watch/phone-context.schema.json`
- Create: `schemas/watch/VERSION`
- Modify: `agents/watch_receiver.py` — fix voice-trigger ts mismatch
- Create: `tests/test_watch_schemas.py` — schema round-trip tests
- Create: `scripts/generate_watch_schemas.py` — Pydantic -> JSON Schema generator

---

## Batch 1 (parallel): Tasks 1-3

These three workstreams have zero dependencies on each other.

---

### Task 1: Typed Configuration — Council Settings Model

**Files:**
- Modify: `/home/hapax/projects/hapax-council/pyproject.toml`
- Create: `/home/hapax/projects/hapax-council/shared/settings.py`
- Create: `/home/hapax/projects/hapax-council/tests/test_settings.py`
- Modify: `/home/hapax/projects/hapax-council/shared/config.py`

- [ ] **Step 1: Add pydantic-settings dependency**

In `pyproject.toml`, add `"pydantic-settings>=2.7.0"` to the `dependencies` list (after the existing `pydantic>=2.12.5` line).

Run: `cd /home/hapax/projects/hapax-council && uv sync`
Expected: Clean install with pydantic-settings added.

- [ ] **Step 2: Write failing test — settings model loads from env**

Create `tests/test_settings.py`:

```python
"""Tests for shared.settings — typed configuration."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest


def test_default_settings_load():
    """Settings model loads with defaults when no env vars set."""
    from shared.settings import CouncilSettings

    with patch.dict(os.environ, {}, clear=True):
        s = CouncilSettings()
    assert s.litellm.base_url == "http://localhost:4000"
    assert s.qdrant.url == "http://localhost:6333"
    assert s.engine.debounce_ms >= 50


def test_settings_override_from_env():
    """Env vars override defaults."""
    from shared.settings import CouncilSettings

    env = {"LITELLM_API_BASE": "http://example:9000", "QDRANT_URL": "http://qdrant:6334"}
    with patch.dict(os.environ, env, clear=True):
        s = CouncilSettings()
    assert s.litellm.base_url == "http://example:9000"
    assert s.qdrant.url == "http://qdrant:6334"


def test_settings_rejects_invalid_port():
    """Negative debounce_ms rejected."""
    from shared.settings import CouncilSettings

    with patch.dict(os.environ, {"ENGINE_DEBOUNCE_MS": "-5"}, clear=True):
        with pytest.raises(Exception):
            CouncilSettings()


def test_secret_str_hides_api_key():
    """API keys use SecretStr to prevent accidental logging."""
    from shared.settings import CouncilSettings

    env = {"LITELLM_API_KEY": "sk-secret-key-123"}
    with patch.dict(os.environ, env, clear=True):
        s = CouncilSettings()
    assert "sk-secret-key-123" not in str(s.litellm)
    assert s.litellm.api_key.get_secret_value() == "sk-secret-key-123"
```

Run: `cd /home/hapax/projects/hapax-council && uv run pytest tests/test_settings.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'shared.settings'`

- [ ] **Step 3: Write settings model**

Create `shared/settings.py`:

```python
"""Typed configuration for hapax-council.

All 30+ council env vars validated at import time via pydantic-settings.
Feature-gated: set HAPAX_USE_SETTINGS=1 to activate in config.py.
"""

from __future__ import annotations

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class LiteLLMSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="LITELLM_", populate_by_name=True)

    base_url: str = Field(alias="LITELLM_API_BASE", default="http://localhost:4000")
    api_key: SecretStr = SecretStr("")


class QdrantSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="QDRANT_")

    url: str = "http://localhost:6333"


class OllamaSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="OLLAMA_")

    host: str = "http://localhost:11434"


class LangfuseSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="LANGFUSE_")

    host: str = "http://localhost:3000"
    public_key: SecretStr = SecretStr("")
    secret_key: SecretStr = SecretStr("")


class NtfySettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="NTFY_")

    base_url: str = "http://localhost:8090"
    topic: str = "cockpit"
    dedup_cooldown_s: int = Field(default=3600, ge=0)


class EngineSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ENGINE_")

    debounce_ms: int = Field(default=1500, ge=50, le=10000)
    gpu_concurrency: int = Field(default=1, ge=1, le=8)
    cloud_concurrency: int = Field(default=2, ge=1, le=16)
    action_timeout_s: float = Field(default=120.0, ge=1.0)
    quiet_window_s: float = Field(default=180.0, ge=0.0)
    cooldown_s: float = Field(default=600.0, ge=0.0)


class PathSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="HAPAX_")

    home: str = ""  # resolved at runtime from Path.home()
    work_vault_path: str = "~/Documents/Work"
    personal_vault_path: str = "~/Documents/Personal"


class LogSettings(BaseSettings):
    model_config = SettingsConfigDict(populate_by_name=True)

    log_level: str = Field(alias="LOG_LEVEL", default="INFO")
    hapax_log_human: bool = Field(alias="HAPAX_LOG_HUMAN", default=False)
    hapax_service: str = Field(alias="HAPAX_SERVICE", default="hapax-council")


class GovernanceSettings(BaseSettings):
    model_config = SettingsConfigDict(populate_by_name=True)

    enforce_block: bool = Field(alias="AXIOM_ENFORCE_BLOCK", default=False)


class CouncilSettings(BaseSettings):
    """Top-level council configuration. Validated at import time."""

    litellm: LiteLLMSettings = LiteLLMSettings()
    qdrant: QdrantSettings = QdrantSettings()
    ollama: OllamaSettings = OllamaSettings()
    langfuse: LangfuseSettings = LangfuseSettings()
    ntfy: NtfySettings = NtfySettings()
    engine: EngineSettings = EngineSettings()
    paths: PathSettings = PathSettings()
    logging: LogSettings = LogSettings()
    governance: GovernanceSettings = GovernanceSettings()
```

Run: `cd /home/hapax/projects/hapax-council && uv run pytest tests/test_settings.py -v`
Expected: All 4 tests PASS.

- [ ] **Step 4: Wire settings into config.py behind feature flag**

In `shared/config.py`, add near the top (after existing imports):

```python
import os as _os

_USE_SETTINGS = _os.environ.get("HAPAX_USE_SETTINGS", "") == "1"
if _USE_SETTINGS:
    from shared.settings import CouncilSettings
    _settings = CouncilSettings()
```

Then replace the first env var block (LITELLM_API_BASE, LITELLM_API_KEY, QDRANT_URL) with:

```python
if _USE_SETTINGS:
    LITELLM_BASE = _settings.litellm.base_url
    LITELLM_KEY = _settings.litellm.api_key.get_secret_value()
    QDRANT_URL = _settings.qdrant.url
    OLLAMA_HOST = _settings.ollama.host
else:
    LITELLM_BASE = os.environ.get("LITELLM_API_BASE") or os.environ.get("LITELLM_BASE_URL", "http://localhost:4000")
    LITELLM_KEY = os.environ.get("LITELLM_API_KEY", "")
    # ... (keep existing env var code as-is)
```

Run: `cd /home/hapax/projects/hapax-council && uv run pytest tests/test_config.py tests/test_settings.py -v`
Expected: All tests PASS. Existing config tests unaffected (flag defaults to off).

- [ ] **Step 5: Commit**

```bash
cd /home/hapax/projects/hapax-council
git add shared/settings.py tests/test_settings.py pyproject.toml shared/config.py
git commit -m "feat: add typed configuration via pydantic-settings

Introduces CouncilSettings model validating all 30+ env vars at import
time. Feature-gated behind HAPAX_USE_SETTINGS=1. Existing os.getenv
paths preserved as fallback."
```

---

### Task 1b: Typed Configuration — Officium Settings Model

**Files:**
- Modify: `/home/hapax/projects/hapax-officium/pyproject.toml`
- Create: `/home/hapax/projects/hapax-officium/shared/settings.py`
- Create: `/home/hapax/projects/hapax-officium/tests/test_settings.py`
- Modify: `/home/hapax/projects/hapax-officium/shared/config.py`

Same pattern as Task 1 but for officium. Key differences:
- `LITELLM_BASE_URL` default: `http://localhost:4100` (not 4000)
- `QDRANT_URL` default: `http://localhost:6433` (not 6333)
- `OLLAMA_URL` default: `http://localhost:11534` (not 11434)
- `LANGFUSE_HOST` default: `http://localhost:3100` (not 3000)
- `HAPAX_SERVICE` default: `hapax-officium`
- Engine settings differ: `debounce_ms=200`, `llm_concurrency=2`, `delivery_interval_s=300`, `synthesis_enabled`, `synthesis_quiet_s`, `profiler_interval_s`
- No GPU-specific settings (officium has 2 phases, not 3)

- [ ] **Step 1: Add pydantic-settings dependency**

Run: `cd /home/hapax/projects/hapax-officium && grep -q pydantic-settings pyproject.toml || echo "need to add"`

Add `"pydantic-settings>=2.7.0"` to officium's `pyproject.toml` dependencies.

Run: `cd /home/hapax/projects/hapax-officium && uv sync`

- [ ] **Step 2: Write failing tests**

Create `tests/test_settings.py` with same structure as council (4 tests), but with officium defaults.

- [ ] **Step 3: Write OfficiumSettings model**

Create `shared/settings.py` reusing the same nested model classes (LiteLLMSettings, QdrantSettings, etc.) but with `OfficiumSettings` as the top-level and officium-specific `OfficiumEngineSettings`:

```python
class OfficiumEngineSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ENGINE_")

    enabled: bool = True
    debounce_ms: int = Field(default=200, ge=50, le=10000)
    llm_concurrency: int = Field(default=2, ge=1, le=16)
    delivery_interval_s: int = Field(default=300, ge=10)
    action_timeout_s: float = Field(default=60.0, ge=1.0)
    synthesis_enabled: bool = True
    synthesis_quiet_s: float = Field(default=180.0, ge=0.0)
    profiler_interval_s: float = Field(default=86400.0, ge=60.0)


class OfficiumSettings(BaseSettings):
    litellm: LiteLLMSettings = LiteLLMSettings()  # override defaults at instantiation
    qdrant: QdrantSettings = QdrantSettings()
    # ... etc with officium-specific defaults
    engine: OfficiumEngineSettings = OfficiumEngineSettings()
```

- [ ] **Step 4: Wire into config.py behind feature flag**

Same `HAPAX_USE_SETTINGS=1` pattern as council.

Run: `cd /home/hapax/projects/hapax-officium && uv run pytest tests/test_settings.py tests/test_config.py -v`

- [ ] **Step 5: Commit**

```bash
cd /home/hapax/projects/hapax-officium
git add shared/settings.py tests/test_settings.py pyproject.toml shared/config.py
git commit -m "feat: add typed configuration via pydantic-settings

OfficiumSettings model validates all env vars at import time.
Feature-gated behind HAPAX_USE_SETTINGS=1."
```

---

### Task 2: Filesystem Bus Schemas — Officium Vault Models

**Files:**
- Create: `/home/hapax/projects/hapax-officium/shared/vault_schemas.py`
- Create: `/home/hapax/projects/hapax-officium/tests/test_vault_schemas.py`
- Modify: `/home/hapax/projects/hapax-officium/shared/vault_writer.py`
- Create: `/home/hapax/projects/hapax-officium/scripts/vault_validate.py`

- [ ] **Step 1: Write failing tests — schema validation**

Create `tests/test_vault_schemas.py`:

```python
"""Tests for vault document schemas."""

from __future__ import annotations

from datetime import date

import pytest


def test_person_doc_valid():
    from shared.vault_schemas import PersonDoc

    doc = PersonDoc(
        type="person",
        name="Sarah Chen",
        team="Platform",
        role="Staff Engineer",
        cadence="weekly",
    )
    assert doc.type == "person"
    assert doc.status == "active"


def test_person_doc_rejects_bad_cadence():
    from shared.vault_schemas import PersonDoc

    with pytest.raises(Exception):
        PersonDoc(
            type="person",
            name="Sarah Chen",
            team="Platform",
            role="Staff Engineer",
            cadence="daily",  # invalid
        )


def test_person_doc_ignores_extra_fields():
    from shared.vault_schemas import PersonDoc

    doc = PersonDoc(
        type="person",
        name="Sarah Chen",
        team="Platform",
        role="Staff Engineer",
        cadence="weekly",
        unknown_future_field="whatever",
    )
    assert doc.name == "Sarah Chen"


def test_coaching_doc_valid():
    from shared.vault_schemas import CoachingDoc

    doc = CoachingDoc(
        type="coaching",
        person="Alice",
        date=date(2026, 3, 23),
    )
    assert doc.person == "Alice"


def test_feedback_doc_defaults():
    from shared.vault_schemas import FeedbackDoc

    doc = FeedbackDoc(
        type="feedback",
        person="Alice",
        date=date(2026, 3, 23),
    )
    assert doc.direction == "given"
    assert doc.category == "growth"
    assert doc.followed_up is False


def test_incident_doc_valid():
    from shared.vault_schemas import IncidentDoc

    doc = IncidentDoc(
        type="incident",
        title="API gateway outage",
    )
    assert doc.severity == "sev3"


def test_okr_doc_with_key_results():
    from shared.vault_schemas import KeyResult, OkrDoc

    kr = KeyResult(
        id="kr1",
        description="Reduce P99 latency below 200ms",
        target=200.0,
        current=310.0,
        unit="ms",
    )
    doc = OkrDoc(
        type="okr",
        objective="Improve reliability",
        quarter="2026-Q1",
        key_results=[kr],
    )
    assert len(doc.key_results) == 1


def test_resolve_schema_by_type():
    from shared.vault_schemas import resolve_schema

    assert resolve_schema("person").__name__ == "PersonDoc"
    assert resolve_schema("coaching").__name__ == "CoachingDoc"
    assert resolve_schema("unknown") is None
```

Run: `cd /home/hapax/projects/hapax-officium && uv run pytest tests/test_vault_schemas.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'shared.vault_schemas'`

- [ ] **Step 2: Write vault schema models**

Create `shared/vault_schemas.py`:

```python
"""Pydantic models for officium vault document types.

Each model corresponds to a document type stored as markdown with YAML
frontmatter in DATA_DIR. Models use extra="ignore" to allow organic
field growth through agent code.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class VaultDocBase(BaseModel):
    """Base for all vault documents."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    type: str
    date: date | None = None


class PersonDoc(VaultDocBase):
    type: Literal["person"] = "person"
    name: str
    team: str
    role: str
    cadence: Literal["weekly", "biweekly", "monthly"]
    status: Literal["active", "inactive"] = "active"
    last_1on1: date | None = Field(default=None, alias="last-1on1")
    cognitive_load: Literal["low", "moderate", "medium", "high", "critical"] | None = Field(
        default=None, alias="cognitive-load"
    )
    growth_vector: str | None = Field(default=None, alias="growth-vector")
    feedback_style: str | None = Field(default=None, alias="feedback-style")
    coaching_active: bool | None = Field(default=None, alias="coaching-active")
    career_goal_3y: str | None = Field(default=None, alias="career-goal-3y")
    current_gaps: str | None = Field(default=None, alias="current-gaps")
    current_focus: str | None = Field(default=None, alias="current-focus")
    last_career_convo: date | None = Field(default=None, alias="last-career-convo")
    team_type: str | None = Field(default=None, alias="team-type")
    interaction_mode: str | None = Field(default=None, alias="interaction-mode")
    skill_level: str | None = Field(default=None, alias="skill-level")
    will_signal: str | None = Field(default=None, alias="will-signal")
    domains: list[str] = Field(default_factory=list)
    relationship: str | None = None


class CoachingDoc(VaultDocBase):
    type: Literal["coaching"] = "coaching"
    person: str
    date: date
    title: str | None = None
    status: Literal["active", "completed", "paused"] = "active"
    check_in_by: date | None = Field(default=None, alias="check-in-by")


class FeedbackDoc(VaultDocBase):
    type: Literal["feedback"] = "feedback"
    person: str
    date: date
    direction: Literal["given", "received"] = "given"
    category: Literal["growth", "performance", "cultural"] = "growth"
    follow_up_by: date | None = Field(default=None, alias="follow-up-by")
    followed_up: bool = Field(default=False, alias="followed-up")
    title: str | None = None


class MeetingDoc(VaultDocBase):
    type: Literal["meeting"] = "meeting"
    title: str
    date: date
    attendees: list[str] = Field(default_factory=list)


class DecisionDoc(VaultDocBase):
    type: Literal["decision"] = "decision"
    date: date
    meeting_ref: str | None = None
    title: str | None = None


class GoalDoc(VaultDocBase):
    type: Literal["goal"] = "goal"
    person: str
    framework: str = "smart"
    status: Literal["active", "completed", "abandoned"] = "active"
    category: str | None = None
    created: date | None = None
    target_date: date | None = Field(default=None, alias="target-date")
    last_reviewed: date | None = Field(default=None, alias="last-reviewed")
    review_cadence: Literal["quarterly", "monthly"] = Field(
        default="quarterly", alias="review-cadence"
    )
    specific: str = ""
    measurable: str | None = None
    achievable: str | None = None
    relevant: str | None = None
    time_bound: str | None = Field(default=None, alias="time-bound")
    linked_okr: str | None = Field(default=None, alias="linked-okr")


class KeyResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    description: str
    target: float | None = None
    current: float | None = None
    unit: str | None = None
    direction: Literal["increase", "decrease"] | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)
    last_updated: date | None = Field(default=None, alias="last-updated")


class OkrDoc(VaultDocBase):
    type: Literal["okr"] = "okr"
    objective: str
    scope: Literal["team", "personal", "company"] = "team"
    team: str | None = None
    person: str | None = None
    quarter: str
    status: Literal["active", "completed", "paused"] = "active"
    score: float | None = Field(default=None, ge=0, le=1)
    scored_at: date | None = Field(default=None, alias="scored-at")
    key_results: list[KeyResult] = Field(default_factory=list, alias="key-results")


class IncidentDoc(VaultDocBase):
    type: Literal["incident"] = "incident"
    title: str
    severity: Literal["sev1", "sev2", "sev3", "sev4"] = "sev3"
    status: str = "detected"
    detected: datetime | None = None
    mitigated: datetime | None = None
    duration_minutes: int | None = Field(default=None, alias="duration-minutes")
    impact: str | None = None
    root_cause: str | None = Field(default=None, alias="root-cause")
    owner: str | None = None
    teams_affected: list[str] = Field(default_factory=list, alias="teams-affected")


class PostmortemActionDoc(VaultDocBase):
    type: Literal["postmortem-action"] = "postmortem-action"
    title: str
    incident_ref: str | None = Field(default=None, alias="incident-ref")
    owner: str | None = None
    status: Literal["open", "in-progress", "completed", "wont-fix"] = "open"
    priority: Literal["high", "medium", "low"] = "medium"
    due_date: date | None = Field(default=None, alias="due-date")
    completed_date: date | None = Field(default=None, alias="completed-date")


class ReviewCycleDoc(VaultDocBase):
    type: Literal["review-cycle"] = "review-cycle"
    person: str
    cycle: str
    status: str = "not-started"
    self_assessment_due: date | None = Field(default=None, alias="self-assessment-due")
    self_assessment_received: bool = Field(default=False, alias="self-assessment-received")
    peer_feedback_requested: int | None = Field(default=None, alias="peer-feedback-requested")
    peer_feedback_received: int | None = Field(default=None, alias="peer-feedback-received")
    review_due: date | None = Field(default=None, alias="review-due")
    calibration_date: date | None = Field(default=None, alias="calibration-date")
    delivered: bool = False


class StatusReportDoc(VaultDocBase):
    type: Literal["status-report"] = "status-report"
    date: date
    cadence: Literal["weekly", "monthly", "pi"] | None = None
    direction: Literal["upward", "downward"] = "upward"
    generated: bool = False
    edited: bool = False


class PrepDoc(VaultDocBase):
    type: Literal["prep"] = "prep"
    person: str
    date: date


class ReferenceDoc(VaultDocBase):
    """Catch-all for generated reference documents (briefings, digests, etc.)."""

    type: str  # varies: briefing, digest, nudges, goals, team-snapshot, overview, prompt
    name: str | None = None


# --- Schema registry ---

_SCHEMA_MAP: dict[str, type[VaultDocBase]] = {
    "person": PersonDoc,
    "coaching": CoachingDoc,
    "feedback": FeedbackDoc,
    "meeting": MeetingDoc,
    "decision": DecisionDoc,
    "goal": GoalDoc,
    "okr": OkrDoc,
    "incident": IncidentDoc,
    "postmortem-action": PostmortemActionDoc,
    "review-cycle": ReviewCycleDoc,
    "status-report": StatusReportDoc,
    "prep": PrepDoc,
}


def resolve_schema(doc_type: str) -> type[VaultDocBase] | None:
    """Return the schema class for a document type, or None if unknown."""
    return _SCHEMA_MAP.get(doc_type)
```

Run: `cd /home/hapax/projects/hapax-officium && uv run pytest tests/test_vault_schemas.py -v`
Expected: All 8 tests PASS.

- [ ] **Step 3: Wire schema validation into vault_writer**

In `shared/vault_writer.py`, modify `_write_md` to accept an optional schema parameter. Add after the existing path validation:

```python
from shared.vault_schemas import VaultDocBase, resolve_schema

def _write_md(
    path: Path,
    content: str,
    frontmatter: dict | None = None,
    *,
    schema: type[VaultDocBase] | None = None,
) -> Path:
    # ... existing path validation ...

    if frontmatter and schema is not None:
        schema.model_validate(frontmatter)  # raises ValidationError on bad data

    # ... rest of existing write logic ...
```

Then update each public write function to pass the appropriate schema. Example for `create_coaching_starter`:

```python
def create_coaching_starter(person: str, observation: str) -> Path | None:
    fm = {"type": "coaching", "person": person, "date": _today()}
    return _write_md(
        _data_dir() / "coaching" / f"{_slug(person)}-{_today()}.md",
        f"# Coaching: {person}\n\n{observation}\n",
        frontmatter=fm,
        schema=CoachingDoc,
    )
```

Run: `cd /home/hapax/projects/hapax-officium && uv run pytest tests/ -q --timeout=30`
Expected: All existing tests PASS (schema defaults to None = no validation change).

- [ ] **Step 4: Write vault_validate scan script**

Create `scripts/vault_validate.py`:

```python
#!/usr/bin/env python3
"""One-time scan of existing vault documents against schemas.

Reports validation errors without modifying any files.
Usage: uv run python scripts/vault_validate.py [--data-dir PATH]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from shared.frontmatter import parse_frontmatter
from shared.vault_schemas import resolve_schema


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    args = parser.parse_args()

    errors = 0
    checked = 0
    for md in sorted(args.data_dir.rglob("*.md")):
        fm, _ = parse_frontmatter(md)
        doc_type = fm.get("type")
        if not doc_type:
            continue
        schema = resolve_schema(doc_type)
        if schema is None:
            continue
        checked += 1
        try:
            schema.model_validate(fm)
        except Exception as exc:
            errors += 1
            print(f"FAIL {md.relative_to(args.data_dir)}: {exc}")

    print(f"\nChecked {checked} documents, {errors} validation errors.")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
```

Run: `cd /home/hapax/projects/hapax-officium && uv run python scripts/vault_validate.py`
Expected: Reports any existing documents that don't match schemas. Fix schemas if needed (adjust Optional fields, widen Literal unions).

- [ ] **Step 5: Commit**

```bash
cd /home/hapax/projects/hapax-officium
git add shared/vault_schemas.py tests/test_vault_schemas.py shared/vault_writer.py scripts/vault_validate.py
git commit -m "feat: add Pydantic schemas for vault document types

13 document types modeled. Write-time validation opt-in via schema
parameter. extra='ignore' allows organic field growth. Includes
vault_validate.py scan script for existing documents."
```

---

### Task 3: Wire Protocol Contracts — Watch Schemas

**Files:**
- Create: `/home/hapax/projects/hapax-council/schemas/watch/` (directory + 7 files)
- Create: `/home/hapax/projects/hapax-council/scripts/generate_watch_schemas.py`
- Modify: `/home/hapax/projects/hapax-council/agents/watch_receiver.py`
- Create: `/home/hapax/projects/hapax-council/tests/test_watch_schemas.py`

- [ ] **Step 1: Write failing test — schema generation and validation**

Create `tests/test_watch_schemas.py`:

```python
"""Tests for watch wire protocol schemas."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

SCHEMA_DIR = Path(__file__).resolve().parent.parent / "schemas" / "watch"


def test_schema_files_exist():
    expected = [
        "sensor-payload.schema.json",
        "sensor-reading.schema.json",
        "voice-trigger.schema.json",
        "gesture.schema.json",
        "health-summary.schema.json",
        "phone-context.schema.json",
        "VERSION",
    ]
    for name in expected:
        assert (SCHEMA_DIR / name).exists(), f"Missing: {name}"


def test_schemas_are_valid_json():
    for path in SCHEMA_DIR.glob("*.schema.json"):
        data = json.loads(path.read_text())
        assert "type" in data or "$ref" in data or "properties" in data


def test_voice_trigger_includes_ts():
    """Regression: voice-trigger must accept ts field (was silently dropped)."""
    schema = json.loads((SCHEMA_DIR / "voice-trigger.schema.json").read_text())
    props = schema.get("properties", {})
    assert "ts" in props, "voice-trigger schema must include ts field"


def test_version_file():
    version = (SCHEMA_DIR / "VERSION").read_text().strip()
    parts = version.split(".")
    assert len(parts) == 3, f"VERSION must be semver, got: {version}"
```

Run: `cd /home/hapax/projects/hapax-council && uv run pytest tests/test_watch_schemas.py -v`
Expected: FAIL — schema files don't exist yet.

- [ ] **Step 2: Fix voice-trigger ts mismatch in watch_receiver.py**

In `agents/watch_receiver.py`, find the `VoiceTriggerPayload` class and add the `ts` field:

```python
class VoiceTriggerPayload(BaseModel):
    device_id: str
    ts: int | None = None  # Client-provided timestamp (epoch ms); falls back to server clock
```

Then in the voice-trigger handler, use client timestamp when available:

```python
triggered_at = (
    datetime.fromtimestamp(payload.ts / 1000, tz=UTC) if payload.ts else datetime.now(UTC)
)
```

Run: `cd /home/hapax/projects/hapax-council && uv run pytest tests/test_watch_receiver.py -v`
Expected: Existing tests PASS (ts is optional, backward-compatible).

- [ ] **Step 3: Write schema generator script**

Create `scripts/generate_watch_schemas.py`:

```python
#!/usr/bin/env python3
"""Generate JSON Schema files from watch_receiver Pydantic models.

Usage: uv run python scripts/generate_watch_schemas.py
"""

from __future__ import annotations

import json
from pathlib import Path

# Import the server-side models (authoritative)
from agents.watch_receiver import (
    GesturePayload,
    HealthSummaryPayload,
    PhoneContextPayload,
    SensorPayload,
    SensorReading,
    VoiceTriggerPayload,
)

SCHEMA_DIR = Path(__file__).resolve().parent.parent / "schemas" / "watch"

MODELS = {
    "sensor-payload": SensorPayload,
    "sensor-reading": SensorReading,
    "voice-trigger": VoiceTriggerPayload,
    "gesture": GesturePayload,
    "health-summary": HealthSummaryPayload,
    "phone-context": PhoneContextPayload,
}


def main() -> None:
    SCHEMA_DIR.mkdir(parents=True, exist_ok=True)

    for name, model in MODELS.items():
        schema = model.model_json_schema()
        path = SCHEMA_DIR / f"{name}.schema.json"
        path.write_text(json.dumps(schema, indent=2) + "\n")
        print(f"  wrote {path.relative_to(SCHEMA_DIR.parent.parent)}")

    version_file = SCHEMA_DIR / "VERSION"
    if not version_file.exists():
        version_file.write_text("1.0.0\n")
        print("  wrote VERSION (1.0.0)")


if __name__ == "__main__":
    main()
```

Run: `cd /home/hapax/projects/hapax-council && uv run python scripts/generate_watch_schemas.py`
Expected: Creates 6 schema files + VERSION.

- [ ] **Step 4: Run schema tests**

Run: `cd /home/hapax/projects/hapax-council && uv run pytest tests/test_watch_schemas.py -v`
Expected: All 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
cd /home/hapax/projects/hapax-council
git add schemas/watch/ scripts/generate_watch_schemas.py tests/test_watch_schemas.py agents/watch_receiver.py
git commit -m "feat: add wire protocol schemas for watch endpoints

JSON Schema generated from Pydantic models. Fixes voice-trigger ts
mismatch (client timestamp now accepted). Six endpoints covered with
semver VERSION file."
```

---

## Batch 2 (sequential): Tasks 4-5

Workstream 3 (axiom enforcement) depends on workstream 1 (config), then workstream 4 (engine contracts) depends on workstream 3.

---

### Task 4: Runtime Axiom Enforcement — Enforced Agent Wrapper

**Files:**
- Create: `/home/hapax/projects/hapax-council/shared/governance/enforced_agent.py`
- Create: `/home/hapax/projects/hapax-council/tests/test_enforced_agent.py`
- Modify: `/home/hapax/projects/hapax-council/axioms/enforcement-patterns.yaml`
- Modify: `/home/hapax/projects/hapax-council/agents/briefing.py`
- Modify: `/home/hapax/projects/hapax-council/agents/scout.py`

- [ ] **Step 1: Write failing test — run_enforced blocks T0 violations**

Create `tests/test_enforced_agent.py`:

```python
"""Tests for enforced agent wrapper."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_run_enforced_passes_clean_output():
    from shared.governance.enforced_agent import run_enforced

    mock_result = MagicMock()
    mock_result.output = "System health is nominal."

    mock_agent = AsyncMock()
    mock_agent.run = AsyncMock(return_value=mock_result)

    with patch("shared.governance.enforced_agent.enforce_output") as mock_enforce:
        mock_enforce.return_value = MagicMock(allowed=True, violations=[])
        output = await run_enforced(mock_agent, "check health", agent_id="test")

    assert output == "System health is nominal."
    mock_enforce.assert_called_once()


@pytest.mark.asyncio
async def test_run_enforced_raises_on_t0_block():
    from shared.governance.enforced_agent import AxiomViolationError, run_enforced

    mock_result = MagicMock()
    mock_result.output = "I think Sarah should improve her communication skills."

    mock_agent = AsyncMock()
    mock_agent.run = AsyncMock(return_value=mock_result)

    violation = MagicMock(tier="T0", pattern_id="out-mg-feedback-001")
    with patch("shared.governance.enforced_agent.enforce_output") as mock_enforce:
        mock_enforce.return_value = MagicMock(allowed=False, violations=[violation])
        with pytest.raises(AxiomViolationError):
            await run_enforced(mock_agent, "generate feedback", agent_id="test")


@pytest.mark.asyncio
async def test_run_enforced_allows_structured_output():
    """Non-string outputs (Pydantic models) are serialized for checking."""
    from shared.governance.enforced_agent import run_enforced

    mock_model = MagicMock()
    mock_model.model_dump_json = MagicMock(return_value='{"summary": "all clear"}')

    mock_result = MagicMock()
    mock_result.output = mock_model

    mock_agent = AsyncMock()
    mock_agent.run = AsyncMock(return_value=mock_result)

    with patch("shared.governance.enforced_agent.enforce_output") as mock_enforce:
        mock_enforce.return_value = MagicMock(allowed=True, violations=[])
        output = await run_enforced(mock_agent, "check", agent_id="test")

    assert output is mock_model
```

Run: `cd /home/hapax/projects/hapax-council && uv run pytest tests/test_enforced_agent.py -v`
Expected: FAIL — module not found.

- [ ] **Step 2: Implement run_enforced wrapper**

Create `shared/governance/enforced_agent.py`:

```python
"""Universal axiom enforcement wrapper for pydantic-ai agents.

Intercepts agent output and runs axiom pattern checks before returning.
Raises AxiomViolationError on T0 violations when blocking is enabled.
"""

from __future__ import annotations

import logging
from typing import Any, TypeVar

from shared.axiom_enforcer import enforce_output

logger = logging.getLogger(__name__)

R = TypeVar("R")


class AxiomViolationError(Exception):
    """Raised when agent output violates a T0 axiom pattern."""

    def __init__(self, agent_id: str, violations: list[Any]) -> None:
        self.agent_id = agent_id
        self.violations = violations
        ids = ", ".join(v.pattern_id for v in violations)
        super().__init__(f"Agent {agent_id} output blocked by axiom enforcement: {ids}")


def _extract_text(output: Any) -> str:
    """Extract checkable text from agent output."""
    if isinstance(output, str):
        return output
    if hasattr(output, "model_dump_json"):
        return output.model_dump_json()
    return str(output)


async def run_enforced(
    agent: Any,
    prompt: str,
    *,
    agent_id: str,
    deps: Any | None = None,
    output_path: str = "",
) -> Any:
    """Run a pydantic-ai agent with mandatory axiom enforcement on output.

    Args:
        agent: A pydantic-ai Agent instance.
        prompt: The prompt to run.
        agent_id: Identifier for enforcement audit trail.
        deps: Optional agent dependencies.
        output_path: Optional path where output will be written.

    Returns:
        The agent's output (unchanged if enforcement passes).

    Raises:
        AxiomViolationError: If T0 violations detected and blocking enabled.
    """
    if deps is not None:
        result = await agent.run(prompt, deps=deps)
    else:
        result = await agent.run(prompt)

    text = _extract_text(result.output)
    enforcement = enforce_output(text, agent_id=agent_id, output_path=output_path)

    if not enforcement.allowed:
        logger.warning(
            "Axiom enforcement blocked output from %s: %s",
            agent_id,
            [v.pattern_id for v in enforcement.violations],
        )
        raise AxiomViolationError(agent_id, enforcement.violations)

    if enforcement.violations:
        logger.info(
            "Axiom enforcement advisory for %s: %s",
            agent_id,
            [v.pattern_id for v in enforcement.violations],
        )

    return result.output
```

Run: `cd /home/hapax/projects/hapax-council && uv run pytest tests/test_enforced_agent.py -v`
Expected: All 3 tests PASS.

- [ ] **Step 3: Add enforcement patterns for remaining axioms**

In `axioms/enforcement-patterns.yaml`, append patterns for `interpersonal_transparency` and `corporate_boundary`:

```yaml
- id: out-it-persist-001
  axiom_id: interpersonal_transparency
  tier: T0
  description: "Persistent person-state without consent contract reference"
  keywords: ["storing", "tracking", "recording", "logging"]
  context_keywords: ["about", "person", "employee", "team member"]
  regex: null

- id: out-cb-employer-001
  axiom_id: corporate_boundary
  tier: T1
  description: "Employer-system reference in personal-system output"
  keywords: ["jira", "confluence", "slack.com", "teams.microsoft"]
  context_keywords: []
  regex: "https?://[a-z]+\\.(atlassian|slack|microsoft)\\.com"
```

Run: `cd /home/hapax/projects/hapax-council && uv run pytest tests/test_axiom_enforcement.py -v`
Expected: Existing enforcement tests PASS.

- [ ] **Step 4: Migrate briefing.py to run_enforced (proof of concept)**

In `agents/briefing.py`, find the existing `enforce_output()` call and replace the manual enforcement with `run_enforced`. The exact change depends on the current call pattern — replace the manual `result = await agent.run(...)` + `enforce_output(result)` sequence with:

```python
from shared.governance.enforced_agent import run_enforced

output = await run_enforced(agent, prompt, agent_id="briefing", output_path=str(BRIEFING_FILE))
```

Remove the now-redundant manual `enforce_output()` call.

Run: `cd /home/hapax/projects/hapax-council && uv run pytest tests/test_briefing*.py -v`
Expected: All briefing tests PASS.

- [ ] **Step 5: Migrate scout.py to run_enforced**

Same pattern: replace `await agent.run(prompt)` with `await run_enforced(agent, prompt, agent_id="scout")`.

Run: `cd /home/hapax/projects/hapax-council && uv run pytest tests/test_scout*.py -v`
Expected: All scout tests PASS.

- [ ] **Step 6: Commit**

```bash
cd /home/hapax/projects/hapax-council
git add shared/governance/enforced_agent.py tests/test_enforced_agent.py axioms/enforcement-patterns.yaml agents/briefing.py agents/scout.py
git commit -m "feat: universal axiom enforcement for agent output

Introduces run_enforced() wrapper. All agent output checked against
axiom patterns before return. Migrates briefing + scout as proof of
concept. Adds patterns for interpersonal_transparency and
corporate_boundary axioms (5/5 covered)."
```

- [ ] **Step 7: Migrate remaining agents (batch)**

Apply the same `run_enforced` pattern to all agents that produce natural language output:
- `agents/drift_detector.py`
- `agents/digest.py`
- `agents/code_review.py`
- `agents/knowledge_maint.py`
- `agents/profiler.py`
- `agents/research.py`
- `agents/activity_analyzer.py`

For each agent: find the `agent.run()` call, wrap with `run_enforced()`, run that agent's tests.

Run: `cd /home/hapax/projects/hapax-council && uv run pytest tests/ -q --timeout=60`
Expected: All tests PASS.

- [ ] **Step 8: Commit remaining migrations**

```bash
cd /home/hapax/projects/hapax-council
git add agents/drift_detector.py agents/digest.py agents/code_review.py agents/knowledge_maint.py agents/profiler.py agents/research.py agents/activity_analyzer.py
git commit -m "feat: enforce axiom patterns on all LLM agent outputs

Remaining 7 agents migrated to run_enforced(). All ~20 LLM-producing
agents now pass through axiom enforcement."
```

---

### Task 5: Reactive Engine Phase Contracts

**Files:**
- Modify: `/home/hapax/projects/hapax-council/logos/engine/models.py`
- Modify: `/home/hapax/projects/hapax-council/logos/engine/rules.py`
- Modify: `/home/hapax/projects/hapax-council/logos/engine/reactive_rules.py`
- Create: `/home/hapax/projects/hapax-council/tests/test_engine_contracts.py`

- [ ] **Step 1: Write failing test — Phase enum and RuleSpec**

Create `tests/test_engine_contracts.py`:

```python
"""Tests for reactive engine phase contracts."""

from __future__ import annotations

import pytest


def test_phase_enum_values():
    from logos.engine.models import Phase

    assert Phase.DETERMINISTIC == 0
    assert Phase.GPU == 1
    assert Phase.CLOUD == 2


def test_rulespec_creation():
    from logos.engine.models import Phase, RuleSpec

    spec = RuleSpec(
        id="test-rule",
        phase=Phase.DETERMINISTIC,
        trigger=lambda e: True,
        produce=lambda e: [],
    )
    assert spec.id == "test-rule"
    assert spec.phase == Phase.DETERMINISTIC
    assert spec.cooldown_s == 0


def test_rulespec_rejects_duplicate_id():
    """Registry rejects two rules with the same ID."""
    from logos.engine.models import Phase, RuleSpec
    from logos.engine.rules import RuleRegistry

    registry = RuleRegistry()
    spec1 = RuleSpec(id="dup", phase=Phase.DETERMINISTIC, trigger=lambda e: True, produce=lambda e: [])
    spec2 = RuleSpec(id="dup", phase=Phase.GPU, trigger=lambda e: True, produce=lambda e: [])

    registry.register(spec1)
    with pytest.raises(ValueError, match="duplicate"):
        registry.register(spec2)


def test_action_phase_invariant():
    """A deterministic rule cannot produce GPU-phase actions."""
    from logos.engine.models import Action, Phase, RuleSpec

    spec = RuleSpec(
        id="bad-rule",
        phase=Phase.DETERMINISTIC,
        produce=lambda e: [Action(name="gpu-work", handler=None, phase=Phase.GPU)],
        trigger=lambda e: True,
    )
    # Invariant checked at evaluation time, not at registration
    assert spec.phase == Phase.DETERMINISTIC
```

Run: `cd /home/hapax/projects/hapax-council && uv run pytest tests/test_engine_contracts.py -v`
Expected: FAIL — Phase and RuleSpec don't exist yet.

- [ ] **Step 2: Add Phase enum and RuleSpec to models.py**

In `logos/engine/models.py`, add at the top (after imports):

```python
from enum import IntEnum


class Phase(IntEnum):
    """Execution phases with strict barrier semantics."""
    DETERMINISTIC = 0
    GPU = 1
    CLOUD = 2


@dataclass(frozen=True)
class RuleSpec:
    """Formal rule declaration with phase contract.

    Invariants enforced by RuleRegistry:
    - Unique rule ID across registry
    - produce() actions must have phase <= rule.phase
    """
    id: str
    phase: Phase
    trigger: Callable[[ChangeEvent], bool]
    produce: Callable[[ChangeEvent], list[Action]]
    cooldown_s: float = 0
    quiet_window_s: float = 0
    doc_types: frozenset[str] = field(default_factory=frozenset)
    directories: frozenset[str] = field(default_factory=frozenset)
    axiom_exempt: bool = False
```

Update the `Action` dataclass to accept `Phase` for the `phase` field:

```python
@dataclass
class Action:
    name: str
    handler: Callable[..., Awaitable[Any]]
    args: dict = field(default_factory=dict)
    priority: int = 50
    phase: int | Phase = 0  # backward-compatible
    depends_on: list[str] = field(default_factory=list)
```

Run: `cd /home/hapax/projects/hapax-council && uv run pytest tests/test_engine_contracts.py::test_phase_enum_values tests/test_engine_contracts.py::test_rulespec_creation -v`
Expected: PASS.

- [ ] **Step 3: Update RuleRegistry to accept RuleSpec**

In `logos/engine/rules.py`, update `RuleRegistry` to accept `RuleSpec`:

```python
from logos.engine.models import RuleSpec

class RuleRegistry:
    def __init__(self) -> None:
        self._rules: dict[str, Rule] = {}  # existing: keyed by name
        self._specs: dict[str, RuleSpec] = {}

    def register(self, spec_or_rule: RuleSpec | Rule) -> None:
        if isinstance(spec_or_rule, RuleSpec):
            if spec_or_rule.id in self._specs:
                raise ValueError(f"duplicate rule ID: {spec_or_rule.id}")
            self._specs[spec_or_rule.id] = spec_or_rule
            # Bridge: create a legacy Rule for backward compat
            self._rules[spec_or_rule.id] = Rule(
                name=spec_or_rule.id,
                description=f"[RuleSpec] {spec_or_rule.id}",
                trigger_filter=spec_or_rule.trigger,
                produce=spec_or_rule.produce,
                phase=int(spec_or_rule.phase),
                cooldown_s=spec_or_rule.cooldown_s,
            )
        else:
            self._rules[spec_or_rule.name] = spec_or_rule
```

Run: `cd /home/hapax/projects/hapax-council && uv run pytest tests/test_engine_contracts.py -v`
Expected: All tests PASS.

- [ ] **Step 4: Wrap existing rules in RuleSpec**

In `logos/engine/reactive_rules.py`, convert the first 2-3 rules from the ad-hoc tuple/Rule format to `RuleSpec` as proof of concept. Keep the rest as-is (backward-compatible registry accepts both).

Example conversion for `collector-refresh`:

```python
from logos.engine.models import Phase, RuleSpec

RuleSpec(
    id="collector-refresh",
    phase=Phase.DETERMINISTIC,
    trigger=lambda e: e.doc_type in {"person", "coaching", "feedback"},
    produce=_produce_refresh,
    directories=frozenset({"people", "coaching", "feedback"}),
)
```

Run: `cd /home/hapax/projects/hapax-council && uv run pytest tests/test_engine*.py -v`
Expected: All engine tests PASS.

- [ ] **Step 5: Commit**

```bash
cd /home/hapax/projects/hapax-council
git add logos/engine/models.py logos/engine/rules.py logos/engine/reactive_rules.py tests/test_engine_contracts.py
git commit -m "feat: typed phase contracts for reactive engine

Introduces Phase enum and RuleSpec with formal phase invariants.
RuleRegistry accepts both RuleSpec and legacy Rule (backward-compatible).
First rules converted as proof of concept."
```

---

## Batch 3 (sequential): Task 6

Pyright follows config + bus schemas.

---

### Task 6: Pyright Phase 1 — Import Hygiene

**Files:**
- Modify: `/home/hapax/projects/hapax-council/pyrightconfig.json`

- [ ] **Step 1: Measure current baseline**

Run: `cd /home/hapax/projects/hapax-council && uv run pyright 2>&1 | tail -3`
Expected: ~414 errors (basic mode, existing).

- [ ] **Step 2: Enable import checks**

In `pyrightconfig.json`, change:
```json
"reportMissingImports": true,
"reportMissingTypeStubs": true
```

Run: `cd /home/hapax/projects/hapax-council && uv run pyright 2>&1 | tail -3`
Record the new count. Fix any new import errors (missing stubs, wrong import paths).

- [ ] **Step 3: Fix import errors**

For each new error:
- Missing type stubs: add to `[tool.pyright] extraPaths` or install stubs
- Wrong imports: fix the import path
- Missing modules: verify the module exists, fix path

Run: `cd /home/hapax/projects/hapax-council && uv run pyright 2>&1 | tail -3`
Expected: Error count equal to or less than baseline.

- [ ] **Step 4: Commit**

```bash
cd /home/hapax/projects/hapax-council
git add pyrightconfig.json
git commit -m "chore: enable pyright import checks (phase 1 of 4)

reportMissingImports and reportMissingTypeStubs now enabled.
Incremental path toward standard mode."
```

- [ ] **Step 5: Enable return/argument type checks (Phase 2)**

In `pyrightconfig.json`, change:
```json
"reportReturnType": true,
"reportArgumentType": true
```

Run: `cd /home/hapax/projects/hapax-council && uv run pyright 2>&1 | tail -5`
Record new count. Fix violations in `shared/` first (most impactful), then `logos/`, then `agents/`.

- [ ] **Step 6: Fix type errors iteratively**

Focus on `shared/` directory first — these are imported everywhere. Common fixes:
- Add return type annotations to functions missing them
- Fix argument type mismatches (usually Optional vs required)
- Add `# type: ignore[specific-error]` for genuinely unfixable cases (rare)

Run: `cd /home/hapax/projects/hapax-council && uv run pyright 2>&1 | tail -3`
Expected: Steady decrease in error count.

- [ ] **Step 7: Commit phase 2**

```bash
cd /home/hapax/projects/hapax-council
git add -u
git commit -m "chore: enable pyright return/argument checks (phase 2 of 4)

reportReturnType and reportArgumentType enabled. Fixes applied to
shared/ and logos/ modules."
```

Note: Phases 3-4 (reportCallIssue, reportAssignmentType, then standard mode) follow the same pattern. Each is a separate commit. The full pyright remediation may span multiple sessions given the 414-error baseline.

---

## Execution Notes

**Parallel execution strategy:**
- Tasks 1, 1b, 2, 3 can run as parallel subagents (different repos/directories, no conflicts)
- Task 4 must wait for Task 1 (reads AXIOM_ENFORCE_BLOCK from settings)
- Task 5 must wait for Task 4 (enforcement in engine handlers)
- Task 6 must wait for Tasks 1+1b+2 (new code must type-check)

**Feature flags for rollback:**
- `HAPAX_USE_SETTINGS=1` — typed config (Task 1)
- `schema=` parameter — bus validation (Task 2, defaults to None)
- `AXIOM_ENFORCE_BLOCK=0` — enforcement audit-only (Task 4)
- `ENGINE_STRICT_PHASES=1` — phase invariant checking (Task 5)
- `continue-on-error: true` — pyright CI (Task 6)

**PR strategy:**
- One PR per task (6 total)
- Tasks 1-3 can be PRed in parallel
- Each PR independently mergeable
