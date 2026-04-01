# Orientation Panel — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the disconnected Goals + Briefing sidebar widgets with a unified orientation panel that reads goals from the Obsidian vault, infers session context from telemetry, and produces a domain-aware orientation surface with conditional LLM narrative.

**Architecture:** Vault-native goal notes (YAML frontmatter, one per goal) replace `operator.json` goals. A domain registry (`config/domains.yaml`) maps life domains to data sources. A telemetry inference engine reads git, Langfuse, IR, stimmung, and sprint signals to compute session context. An orientation collector assembles per-domain state deterministically, with a conditional LLM narrative that fires only at context boundaries (session resumption, morning, domain transitions). The frontend `OrientationPanel` replaces `GoalsPanel` + `BriefingPanel` with stimmung-responsive density modulation.

**Tech Stack:** Python 3.12, FastAPI, pydantic-ai (for LLM narrative), Tauri 2 (Rust), React + TanStack Query, Obsidian vault (YAML frontmatter)

**Spec:** `docs/superpowers/specs/2026-04-01-orientation-panel-design.md`

---

### File Map

| Action | File | Responsibility |
|--------|------|---------------|
| Create | `config/domains.yaml` | Domain registry: sources, staleness, telemetry per domain |
| Create | `logos/data/vault_goals.py` | Scan Obsidian vault for `type: goal` notes, compute staleness + sprint progress |
| Create | `logos/data/session_inference.py` | Infer session context from telemetry (git, Langfuse, IR, stimmung, sprint) |
| Create | `logos/data/orientation.py` | Assemble per-domain state + conditional LLM narrative |
| Create | `logos/api/routes/orientation.py` | `GET /api/orientation` endpoint |
| Create | `tests/test_vault_goals.py` | Unit tests for vault goal collector |
| Create | `tests/test_session_inference.py` | Unit tests for session inference |
| Create | `tests/test_orientation.py` | Unit tests for orientation collector |
| Create | `hapax-logos/src/components/sidebar/OrientationPanel.tsx` | Unified orientation UI component |
| Modify | `logos/api/cache.py` | Add `orientation` field to DataCache slow refresh |
| Modify | `logos/api/routes/data.py` | Add `/api/orientation` route |
| Modify | `hapax-logos/src/api/types.ts` | Add OrientationState, DomainState, SessionContext types |
| Modify | `hapax-logos/src/api/client.ts` | Add `orientation` invoke |
| Modify | `hapax-logos/src/api/hooks.ts` | Add `useOrientation()` hook |
| Modify | `hapax-logos/src-tauri/src/commands/state.rs` | Add `get_orientation()` Tauri command |
| Modify | `hapax-logos/src/components/Sidebar.tsx` | Replace goals+briefing panels with orientation panel |
| Delete | `logos/data/goals.py` | Replaced by vault_goals.py |
| Delete | `hapax-logos/src/components/sidebar/GoalsPanel.tsx` | Replaced by OrientationPanel |
| Delete | `hapax-logos/src/components/sidebar/BriefingPanel.tsx` | Merged into OrientationPanel |

---

### Task 1: Domain Registry

**Files:**
- Create: `config/domains.yaml`

- [ ] **Step 1: Create config directory**

```bash
mkdir -p config
```

- [ ] **Step 2: Write domains.yaml**

```yaml
# Domain registry — maps life domains to data sources for orientation panel.
# Adding a domain: add an entry here. No code changes needed.

domains:
  research:
    staleness_days: 7
    vault_goal_filter: "domain: research"
    apis:
      sprint: "/api/sprint"
    telemetry:
      git_repos: [hapax-council, hapax-constitution]
      langfuse_tags: [research, bayesian, sprint]
      vault_paths: []

  management:
    staleness_days: 14
    vault_goal_filter: "domain: management"
    apis:
      officium_nudges: "http://localhost:8050/api/nudges"
      officium_briefing: "http://localhost:8050/api/briefing"
    telemetry:
      git_repos: []
      langfuse_tags: []
      vault_paths: ["30 Areas/management/"]

  studio:
    staleness_days: 14
    vault_goal_filter: "domain: studio"
    apis: {}
    telemetry:
      git_repos: []
      langfuse_tags: []
      vault_paths: ["20 Projects/studio/", "30 Areas/music/"]

  personal:
    staleness_days: 30
    vault_goal_filter: "domain: personal"
    apis: {}
    telemetry:
      git_repos: []
      langfuse_tags: []
      vault_paths: ["30 Areas/", "20-personal/"]

  health:
    staleness_days: 7
    vault_goal_filter: "domain: health"
    apis:
      watch: "/api/biometrics"
    telemetry:
      git_repos: []
      langfuse_tags: []
      vault_paths: []
```

- [ ] **Step 3: Commit**

```bash
git add config/domains.yaml
git commit -m "feat: add domain registry for orientation panel"
```

---

### Task 2: Vault Goal Collector — Tests

**Files:**
- Create: `tests/test_vault_goals.py`

- [ ] **Step 1: Write failing tests**

```python
"""Tests for vault goal collector."""

from __future__ import annotations

import os
import time
from pathlib import Path

import yaml

from logos.data.vault_goals import VaultGoal, collect_vault_goals


def _write_goal(tmp_path: Path, name: str, **overrides: object) -> Path:
    """Write a minimal goal note with frontmatter."""
    fm = {
        "type": "goal",
        "title": overrides.get("title", name),
        "domain": overrides.get("domain", "research"),
        "status": overrides.get("status", "active"),
        "priority": overrides.get("priority", "P1"),
    }
    for key in ("started_at", "target_date", "sprint_measures", "depends_on", "tags"):
        if key in overrides:
            fm[key] = overrides[key]

    yaml_str = yaml.dump(fm, default_flow_style=False)
    content = f"---\n{yaml_str}---\n\nGoal body for {name}.\n"
    p = tmp_path / f"{name}.md"
    p.write_text(content, encoding="utf-8")
    return p


def test_empty_dir_returns_empty(tmp_path: Path) -> None:
    goals = collect_vault_goals(vault_base=tmp_path)
    assert goals == []


def test_non_goal_note_ignored(tmp_path: Path) -> None:
    p = tmp_path / "not-a-goal.md"
    p.write_text("---\ntype: note\ntitle: Just a note\n---\nBody.\n")
    goals = collect_vault_goals(vault_base=tmp_path)
    assert goals == []


def test_single_goal_parsed(tmp_path: Path) -> None:
    _write_goal(tmp_path, "validate-dmn", title="Validate DMN model", domain="research")
    goals = collect_vault_goals(vault_base=tmp_path)
    assert len(goals) == 1
    g = goals[0]
    assert g.id == "validate-dmn"
    assert g.title == "Validate DMN model"
    assert g.domain == "research"
    assert g.status == "active"
    assert g.priority == "P1"


def test_domain_filter(tmp_path: Path) -> None:
    _write_goal(tmp_path, "g-research", domain="research")
    _write_goal(tmp_path, "g-studio", domain="studio")
    research = collect_vault_goals(vault_base=tmp_path, domain_filter="research")
    assert len(research) == 1
    assert research[0].domain == "research"


def test_staleness_fresh(tmp_path: Path) -> None:
    _write_goal(tmp_path, "fresh-goal", domain="research")
    goals = collect_vault_goals(vault_base=tmp_path, staleness_days={"research": 7})
    assert len(goals) == 1
    assert goals[0].stale is False


def test_staleness_stale(tmp_path: Path) -> None:
    p = _write_goal(tmp_path, "stale-goal", domain="research")
    old_time = time.time() - (8 * 86400)
    os.utime(p, (old_time, old_time))
    goals = collect_vault_goals(vault_base=tmp_path, staleness_days={"research": 7})
    assert len(goals) == 1
    assert goals[0].stale is True


def test_completed_goals_included(tmp_path: Path) -> None:
    _write_goal(tmp_path, "done", status="completed")
    _write_goal(tmp_path, "active-one", status="active")
    goals = collect_vault_goals(vault_base=tmp_path)
    assert len(goals) == 2


def test_sprint_progress_computed(tmp_path: Path) -> None:
    _write_goal(tmp_path, "with-sprint", sprint_measures=["4.1", "4.2", "4.3"])
    sprint_state = {"4.1": "completed", "4.2": "completed", "4.3": "in_progress"}
    goals = collect_vault_goals(vault_base=tmp_path, sprint_measure_statuses=sprint_state)
    assert goals[0].progress is not None
    assert abs(goals[0].progress - 2 / 3) < 0.01


def test_malformed_frontmatter_skipped(tmp_path: Path) -> None:
    p = tmp_path / "bad.md"
    p.write_text("---\n{invalid yaml\n---\nBody.\n")
    goals = collect_vault_goals(vault_base=tmp_path)
    assert goals == []


def test_subdirectory_scanning(tmp_path: Path) -> None:
    sub = tmp_path / "20 Projects" / "research"
    sub.mkdir(parents=True)
    _write_goal(sub, "nested-goal", domain="research")
    goals = collect_vault_goals(vault_base=tmp_path)
    assert len(goals) == 1
    assert goals[0].id == "nested-goal"


def test_obsidian_uri_generated(tmp_path: Path) -> None:
    _write_goal(tmp_path, "uri-test", domain="research")
    goals = collect_vault_goals(vault_base=tmp_path, vault_name="Personal")
    assert goals[0].obsidian_uri.startswith("obsidian://open?vault=Personal&file=")
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_vault_goals.py -v
```

Expected: ImportError — `logos.data.vault_goals` does not exist yet.

- [ ] **Step 3: Commit test file**

```bash
git add tests/test_vault_goals.py
git commit -m "test: add vault goal collector tests (red)"
```

---

### Task 3: Vault Goal Collector — Implementation

**Files:**
- Create: `logos/data/vault_goals.py`

- [ ] **Step 1: Write implementation**

```python
"""Vault-native goal collector.

Scans the Obsidian vault for markdown notes with `type: goal` frontmatter.
Computes staleness from file modification time and sprint progress from linked measures.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

from shared.frontmatter import parse_frontmatter

log = logging.getLogger(__name__)

VAULT_BASE = Path.home() / "Documents" / "Personal"
VAULT_NAME = "Personal"

DEFAULT_STALENESS_DAYS: dict[str, int] = {
    "research": 7,
    "management": 14,
    "studio": 14,
    "personal": 30,
    "health": 7,
}


@dataclass
class VaultGoal:
    id: str
    title: str
    domain: str
    status: str
    priority: str
    started_at: str | None
    target_date: str | None
    sprint_measures: list[str]
    depends_on: list[str]
    tags: list[str]
    file_path: str
    last_modified: float
    stale: bool
    progress: float | None
    obsidian_uri: str


def _build_obsidian_uri(vault_name: str, file_path: Path, vault_base: Path) -> str:
    relative = file_path.relative_to(vault_base)
    encoded = quote(str(relative).removesuffix(".md"), safe="/")
    return f"obsidian://open?vault={quote(vault_name)}&file={encoded}"


def _compute_progress(
    measures: list[str],
    sprint_measure_statuses: dict[str, str] | None,
) -> float | None:
    if not measures or sprint_measure_statuses is None:
        return None
    completed = sum(
        1 for m in measures if sprint_measure_statuses.get(m) == "completed"
    )
    return completed / len(measures)


def _is_stale(mtime: float, domain: str, staleness_days: dict[str, int]) -> bool:
    threshold = staleness_days.get(domain, 30)
    age_days = (time.time() - mtime) / 86400
    return age_days > threshold


def collect_vault_goals(
    *,
    vault_base: Path | None = None,
    vault_name: str | None = None,
    domain_filter: str | None = None,
    staleness_days: dict[str, int] | None = None,
    sprint_measure_statuses: dict[str, str] | None = None,
) -> list[VaultGoal]:
    """Scan vault for type: goal notes, compute staleness and progress."""
    base = vault_base or VAULT_BASE
    name = vault_name or VAULT_NAME
    thresholds = staleness_days or DEFAULT_STALENESS_DAYS

    if not base.is_dir():
        log.warning("Vault base not found: %s", base)
        return []

    goals: list[VaultGoal] = []
    for md_file in base.rglob("*.md"):
        try:
            fm, _body = parse_frontmatter(md_file)
        except Exception:
            log.debug("Failed to parse: %s", md_file)
            continue

        if fm.get("type") != "goal":
            continue

        domain = fm.get("domain", "personal")
        if domain_filter and domain != domain_filter:
            continue

        mtime = md_file.stat().st_mtime
        measures = fm.get("sprint_measures", []) or []
        status = fm.get("status", "active")

        goals.append(
            VaultGoal(
                id=md_file.stem,
                title=fm.get("title", md_file.stem),
                domain=domain,
                status=status,
                priority=fm.get("priority", "P2"),
                started_at=fm.get("started_at"),
                target_date=fm.get("target_date"),
                sprint_measures=measures,
                depends_on=fm.get("depends_on", []) or [],
                tags=fm.get("tags", []) or [],
                file_path=str(md_file),
                last_modified=mtime,
                stale=_is_stale(mtime, domain, thresholds) if status == "active" else False,
                progress=_compute_progress(measures, sprint_measure_statuses),
                obsidian_uri=_build_obsidian_uri(name, md_file, base),
            )
        )

    goals.sort(key=lambda g: ({"P0": 0, "P1": 1, "P2": 2}.get(g.priority, 9), -g.last_modified))
    return goals
```

- [ ] **Step 2: Run tests**

```bash
uv run pytest tests/test_vault_goals.py -v
```

Expected: All tests PASS.

- [ ] **Step 3: Lint**

```bash
uv run ruff check logos/data/vault_goals.py && uv run ruff format logos/data/vault_goals.py
```

- [ ] **Step 4: Commit**

```bash
git add logos/data/vault_goals.py
git commit -m "feat: vault goal collector — reads Obsidian goal notes"
```

---

### Task 4: Session Inference — Tests

**Files:**
- Create: `tests/test_session_inference.py`

- [ ] **Step 1: Write failing tests**

```python
"""Tests for session inference engine."""

from __future__ import annotations

import time
from unittest.mock import patch

from logos.data.session_inference import SessionContext, infer_session


def test_empty_signals_returns_defaults() -> None:
    with (
        patch("logos.data.session_inference._read_stimmung", return_value={}),
        patch("logos.data.session_inference._read_sprint_state", return_value={}),
        patch("logos.data.session_inference._git_recency", return_value={}),
        patch("logos.data.session_inference._vault_recency", return_value=float("inf")),
    ):
        ctx = infer_session(domains={})
    assert ctx.last_active_domain == ""
    assert ctx.absence_hours >= 0
    assert ctx.session_boundary is False
    assert ctx.domain_recency == {}


@patch("logos.data.session_inference._read_sprint_state", return_value={})
@patch("logos.data.session_inference._git_recency", return_value={})
@patch("logos.data.session_inference._vault_recency", return_value=float("inf"))
@patch("logos.data.session_inference._read_stimmung")
def test_absence_from_ir(mock_stimmung, _v, _g, _s) -> None:
    mock_stimmung.return_value = {
        "last_person_detected_at": time.time() - 3 * 3600,
    }
    ctx = infer_session(domains={})
    assert ctx.absence_hours >= 2.9
    assert ctx.session_boundary is True


@patch("logos.data.session_inference._read_sprint_state", return_value={})
@patch("logos.data.session_inference._git_recency", return_value={})
@patch("logos.data.session_inference._vault_recency", return_value=float("inf"))
@patch("logos.data.session_inference._read_stimmung")
def test_no_boundary_when_present(mock_stimmung, _v, _g, _s) -> None:
    mock_stimmung.return_value = {
        "last_person_detected_at": time.time() - 60,
    }
    ctx = infer_session(domains={})
    assert ctx.absence_hours < 1
    assert ctx.session_boundary is False


@patch("logos.data.session_inference._read_sprint_state", return_value={})
@patch("logos.data.session_inference._read_stimmung", return_value={})
@patch("logos.data.session_inference._vault_recency", return_value=float("inf"))
@patch("logos.data.session_inference._git_recency")
def test_domain_recency_from_git(mock_git, _v, _st, _sp) -> None:
    mock_git.return_value = {"hapax-council": 1.5}
    domains = {"research": {"telemetry": {"git_repos": ["hapax-council"], "vault_paths": []}}}
    ctx = infer_session(domains=domains)
    assert "research" in ctx.domain_recency
    assert ctx.domain_recency["research"] <= 1.5


@patch("logos.data.session_inference._read_sprint_state", return_value={})
@patch("logos.data.session_inference._read_stimmung", return_value={})
@patch("logos.data.session_inference._git_recency", return_value={})
@patch("logos.data.session_inference._vault_recency")
def test_domain_recency_from_vault_mtime(mock_vault, _g, _st, _sp) -> None:
    mock_vault.return_value = 0.5
    domains = {"studio": {"telemetry": {"git_repos": [], "vault_paths": ["20 Projects/studio/"]}}}
    ctx = infer_session(domains=domains)
    assert "studio" in ctx.domain_recency
    assert ctx.domain_recency["studio"] <= 0.5


@patch("logos.data.session_inference._vault_recency", return_value=float("inf"))
@patch("logos.data.session_inference._read_stimmung", return_value={})
@patch("logos.data.session_inference._read_sprint_state", return_value={})
@patch("logos.data.session_inference._git_recency")
def test_most_recent_domain_wins(mock_git, _sp, _st, _v) -> None:
    mock_git.return_value = {"hapax-council": 5.0}
    with patch("logos.data.session_inference._vault_recency", return_value=0.5):
        domains = {
            "research": {"telemetry": {"git_repos": ["hapax-council"], "vault_paths": []}},
            "studio": {"telemetry": {"git_repos": [], "vault_paths": ["20 Projects/studio/"]}},
        }
        ctx = infer_session(domains=domains)
    assert ctx.last_active_domain == "studio"
```

- [ ] **Step 2: Run to verify failure**

```bash
uv run pytest tests/test_session_inference.py -v
```

Expected: ImportError.

- [ ] **Step 3: Commit**

```bash
git add tests/test_session_inference.py
git commit -m "test: add session inference tests (red)"
```

---

### Task 5: Session Inference — Implementation

**Files:**
- Create: `logos/data/session_inference.py`

- [ ] **Step 1: Write implementation**

```python
"""Session inference engine.

Infers operator session context from telemetry signals (git, IR, stimmung, sprint,
vault file timestamps). Zero LLM calls — purely deterministic.
"""

from __future__ import annotations

import json
import logging
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path

log = logging.getLogger(__name__)

STIMMUNG_STATE = Path("/dev/shm/hapax-stimmung/state.json")
SPRINT_STATE = Path("/dev/shm/hapax-sprint/state.json")
SESSION_BOUNDARY_HOURS = 2.0
PROJECTS_DIR = Path.home() / "projects"
VAULT_BASE = Path.home() / "Documents" / "Personal"


@dataclass
class SessionContext:
    last_active_domain: str = ""
    last_active_goal: str | None = None
    last_active_measure: str | None = None
    absence_hours: float = 0.0
    session_boundary: bool = False
    domain_recency: dict[str, float] = field(default_factory=dict)
    active_signals: list[str] = field(default_factory=list)


def _read_stimmung() -> dict:
    try:
        return json.loads(STIMMUNG_STATE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _read_sprint_state() -> dict:
    try:
        return json.loads(SPRINT_STATE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _git_recency(repos: list[str] | None = None) -> dict[str, float]:
    if not repos:
        return {}
    result: dict[str, float] = {}
    for repo in repos:
        repo_path = PROJECTS_DIR / repo
        if not repo_path.is_dir():
            continue
        try:
            out = subprocess.run(
                ["git", "-C", str(repo_path), "log", "-1", "--format=%ct"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if out.returncode == 0 and out.stdout.strip():
                epoch = int(out.stdout.strip())
                result[repo] = (time.time() - epoch) / 3600
        except Exception:
            log.debug("Git recency failed for %s", repo)
    return result


def _vault_recency(vault_paths: list[str] | None = None) -> float:
    if not vault_paths:
        return float("inf")
    newest_mtime = 0.0
    for vp in vault_paths:
        full = VAULT_BASE / vp
        if not full.is_dir():
            continue
        for md in full.rglob("*.md"):
            try:
                mt = md.stat().st_mtime
                if mt > newest_mtime:
                    newest_mtime = mt
            except Exception:
                continue
    if newest_mtime == 0.0:
        return float("inf")
    return (time.time() - newest_mtime) / 3600


def infer_session(
    *,
    domains: dict[str, dict] | None = None,
) -> SessionContext:
    """Infer session context from available telemetry."""
    domains = domains or {}
    ctx = SessionContext()

    # IR presence / absence
    stimmung = _read_stimmung()
    last_seen = stimmung.get("last_person_detected_at")
    if last_seen:
        ctx.absence_hours = (time.time() - float(last_seen)) / 3600
        ctx.session_boundary = ctx.absence_hours >= SESSION_BOUNDARY_HOURS

    # Sprint state
    sprint = _read_sprint_state()
    next_block = sprint.get("next_block")
    if isinstance(next_block, dict):
        ctx.last_active_measure = next_block.get("measure")

    # Per-domain recency — batch all git repos into one call
    all_repos = list({
        r
        for d in domains.values()
        for r in (d.get("telemetry", {}).get("git_repos") or [])
    })
    all_git = _git_recency(all_repos)

    for domain_name, domain_cfg in domains.items():
        telemetry = domain_cfg.get("telemetry", {})
        best_hours = float("inf")

        for repo in telemetry.get("git_repos") or []:
            if repo in all_git:
                best_hours = min(best_hours, all_git[repo])

        vault_paths = telemetry.get("vault_paths") or []
        if vault_paths:
            vault_h = _vault_recency(vault_paths)
            best_hours = min(best_hours, vault_h)

        if best_hours < float("inf"):
            ctx.domain_recency[domain_name] = best_hours

    if ctx.domain_recency:
        ctx.last_active_domain = min(ctx.domain_recency, key=ctx.domain_recency.get)

    return ctx
```

- [ ] **Step 2: Run tests**

```bash
uv run pytest tests/test_session_inference.py -v
```

Expected: All PASS.

- [ ] **Step 3: Lint**

```bash
uv run ruff check logos/data/session_inference.py && uv run ruff format logos/data/session_inference.py
```

- [ ] **Step 4: Commit**

```bash
git add logos/data/session_inference.py
git commit -m "feat: session inference engine — telemetry-based context detection"
```

---

### Task 6: Orientation Collector — Tests

**Files:**
- Create: `tests/test_orientation.py`

- [ ] **Step 1: Write failing tests**

```python
"""Tests for orientation collector."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from logos.data.orientation import (
    DomainState,
    OrientationState,
    collect_orientation,
)
from logos.data.session_inference import SessionContext
from logos.data.vault_goals import VaultGoal


def _goal(
    id: str = "g1",
    domain: str = "research",
    status: str = "active",
    priority: str = "P1",
    stale: bool = False,
    progress: float | None = None,
) -> VaultGoal:
    return VaultGoal(
        id=id,
        title=f"Goal {id}",
        domain=domain,
        status=status,
        priority=priority,
        started_at=None,
        target_date=None,
        sprint_measures=[],
        depends_on=[],
        tags=[],
        file_path=f"/vault/{id}.md",
        last_modified=0.0,
        stale=stale,
        progress=progress,
        obsidian_uri=f"obsidian://open?vault=Personal&file={id}",
    )


def _session(
    last_domain: str = "",
    absence: float = 0.0,
    boundary: bool = False,
) -> SessionContext:
    return SessionContext(
        last_active_domain=last_domain,
        absence_hours=absence,
        session_boundary=boundary,
        domain_recency={last_domain: 1.0} if last_domain else {},
    )


@patch("logos.data.orientation._get_health_summary", return_value=("healthy", 0))
@patch("logos.data.orientation._get_briefing", return_value=(None, None))
@patch("logos.data.orientation._get_stimmung_stance", return_value="nominal")
@patch("logos.data.orientation._get_sprint_summary", return_value=None)
@patch("logos.data.orientation._sprint_measure_statuses", return_value=None)
@patch("logos.data.orientation.infer_session")
@patch("logos.data.orientation.collect_vault_goals")
@patch("logos.data.orientation._load_domain_registry")
def test_basic_assembly(mock_reg, mock_goals, mock_session, *_mocks) -> None:
    mock_reg.return_value = {"research": {"staleness_days": 7, "apis": {}, "telemetry": {}}}
    mock_goals.return_value = [_goal()]
    mock_session.return_value = _session(last_domain="research")
    state = collect_orientation()
    assert isinstance(state, OrientationState)
    assert len(state.domains) == 1
    assert state.domains[0].domain == "research"
    assert state.domains[0].goal_count == 1


@patch("logos.data.orientation._get_health_summary", return_value=("healthy", 0))
@patch("logos.data.orientation._get_briefing", return_value=(None, None))
@patch("logos.data.orientation._get_stimmung_stance", return_value="nominal")
@patch("logos.data.orientation._get_sprint_summary", return_value=None)
@patch("logos.data.orientation._sprint_measure_statuses", return_value=None)
@patch("logos.data.orientation.infer_session")
@patch("logos.data.orientation.collect_vault_goals")
@patch("logos.data.orientation._load_domain_registry")
def test_domains_sorted_by_recency(mock_reg, mock_goals, mock_session, *_mocks) -> None:
    mock_reg.return_value = {
        "research": {"staleness_days": 7, "apis": {}, "telemetry": {}},
        "studio": {"staleness_days": 14, "apis": {}, "telemetry": {}},
    }
    mock_goals.return_value = [_goal(domain="research"), _goal(id="g2", domain="studio")]
    mock_session.return_value = SessionContext(
        last_active_domain="studio",
        domain_recency={"studio": 0.5, "research": 3.0},
    )
    state = collect_orientation()
    assert state.domains[0].domain == "studio"


@patch("logos.data.orientation._get_health_summary", return_value=("healthy", 0))
@patch("logos.data.orientation._get_briefing", return_value=(None, None))
@patch("logos.data.orientation._get_stimmung_stance", return_value="nominal")
@patch("logos.data.orientation._sprint_measure_statuses", return_value=None)
@patch("logos.data.orientation.infer_session")
@patch("logos.data.orientation.collect_vault_goals")
@patch("logos.data.orientation._load_domain_registry")
@patch("logos.data.orientation._get_sprint_summary")
def test_blocked_domain_ranks_highest(mock_sprint, mock_reg, mock_goals, mock_session, *_mocks) -> None:
    mock_reg.return_value = {
        "research": {"staleness_days": 7, "apis": {"sprint": "/api/sprint"}, "telemetry": {}},
        "studio": {"staleness_days": 14, "apis": {}, "telemetry": {}},
    }
    mock_goals.return_value = [_goal(domain="research"), _goal(id="g2", domain="studio")]
    mock_session.return_value = SessionContext(
        last_active_domain="studio",
        domain_recency={"studio": 0.5, "research": 3.0},
    )
    mock_sprint.return_value = MagicMock(blocking_gate="G1")
    state = collect_orientation()
    assert state.domains[0].domain == "research"


@patch("logos.data.orientation._get_health_summary", return_value=("healthy", 0))
@patch("logos.data.orientation._get_briefing", return_value=(None, None))
@patch("logos.data.orientation._get_stimmung_stance", return_value="nominal")
@patch("logos.data.orientation._get_sprint_summary", return_value=None)
@patch("logos.data.orientation._sprint_measure_statuses", return_value=None)
@patch("logos.data.orientation.infer_session")
@patch("logos.data.orientation.collect_vault_goals")
@patch("logos.data.orientation._load_domain_registry")
def test_no_narrative_during_steady_state(mock_reg, mock_goals, mock_session, *_mocks) -> None:
    mock_reg.return_value = {"research": {"staleness_days": 7, "apis": {}, "telemetry": {}}}
    mock_goals.return_value = [_goal()]
    mock_session.return_value = _session(last_domain="research", boundary=False)
    state = collect_orientation()
    assert state.narrative is None


@patch("logos.data.orientation._get_health_summary", return_value=("healthy", 0))
@patch("logos.data.orientation._get_briefing", return_value=(None, None))
@patch("logos.data.orientation._get_stimmung_stance", return_value="nominal")
@patch("logos.data.orientation._get_sprint_summary", return_value=None)
@patch("logos.data.orientation._sprint_measure_statuses", return_value=None)
@patch("logos.data.orientation.infer_session")
@patch("logos.data.orientation.collect_vault_goals")
@patch("logos.data.orientation._load_domain_registry")
def test_empty_registry_returns_empty_domains(mock_reg, mock_goals, mock_session, *_mocks) -> None:
    mock_reg.return_value = {}
    mock_goals.return_value = []
    mock_session.return_value = _session()
    state = collect_orientation()
    assert state.domains == []
```

- [ ] **Step 2: Run to verify failure**

```bash
uv run pytest tests/test_orientation.py -v
```

Expected: ImportError.

- [ ] **Step 3: Commit**

```bash
git add tests/test_orientation.py
git commit -m "test: add orientation collector tests (red)"
```

---

### Task 7: Orientation Collector — Implementation

**Files:**
- Create: `logos/data/orientation.py`

- [ ] **Step 1: Write implementation**

```python
"""Orientation collector.

Assembles per-domain state from vault goals, sprint data, briefing, and session
telemetry. Deterministic assembly phase always runs. Conditional LLM narrative
fires only at context boundaries.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from logos.data.session_inference import SessionContext, infer_session
from logos.data.vault_goals import VaultGoal, collect_vault_goals

log = logging.getLogger(__name__)

CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "domains.yaml"
SPRINT_STATE = Path("/dev/shm/hapax-sprint/state.json")
STIMMUNG_STATE = Path("/dev/shm/hapax-stimmung/state.json")
NARRATIVE_COOLDOWN_S = 1800
MORNING_ABSENCE_HOURS = 8.0

_last_narrative: str | None = None
_last_narrative_at: float = 0.0


@dataclass
class GoalSummary:
    id: str
    title: str
    priority: str
    status: str
    progress: float | None
    stale: bool
    file_path: str
    obsidian_uri: str
    target_date: str | None = None


@dataclass
class SprintSummary:
    current_sprint: int = 0
    measures_completed: int = 0
    measures_total: int = 0
    blocking_gate: str | None = None
    next_measure: str | None = None
    next_measure_title: str | None = None
    models: dict[str, float] = field(default_factory=dict)


@dataclass
class DomainState:
    domain: str
    top_goal: GoalSummary | None = None
    goal_count: int = 0
    stale_count: int = 0
    recency_hours: float = float("inf")
    health: str = "dormant"
    sprint_progress: SprintSummary | None = None
    next_action: str | None = None
    next_action_link: str | None = None


@dataclass
class OrientationState:
    session: SessionContext = field(default_factory=SessionContext)
    domains: list[DomainState] = field(default_factory=list)
    briefing_headline: str | None = None
    briefing_generated_at: str | None = None
    system_health: str = "unknown"
    drift_high_count: int = 0
    narrative: str | None = None
    narrative_generated_at: str | None = None
    stimmung_stance: str = "nominal"


def _load_domain_registry() -> dict[str, dict]:
    try:
        data = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
        return data.get("domains", {}) if isinstance(data, dict) else {}
    except Exception:
        log.warning("Failed to load domain registry from %s", CONFIG_PATH)
        return {}


def _get_sprint_summary() -> SprintSummary | None:
    try:
        data = json.loads(SPRINT_STATE.read_text(encoding="utf-8"))
        nb = data.get("next_block") or {}
        models = {}
        for name, m in (data.get("models") or {}).items():
            if isinstance(m, dict):
                models[name] = m.get("current", m.get("baseline", 0.0))
        return SprintSummary(
            current_sprint=data.get("current_sprint", 0),
            measures_completed=data.get("measures_completed", 0),
            measures_total=data.get("measures_total", 0),
            blocking_gate=data.get("blocking_gate"),
            next_measure=nb.get("measure"),
            next_measure_title=nb.get("title"),
            models=models,
        )
    except Exception:
        return None


def _get_stimmung_stance() -> str:
    try:
        data = json.loads(STIMMUNG_STATE.read_text(encoding="utf-8"))
        return data.get("stance", "nominal")
    except Exception:
        return "nominal"


def _get_briefing() -> tuple[str | None, str | None]:
    try:
        from logos.data.briefing import collect_briefing

        b = collect_briefing()
        if b:
            return b.headline, b.generated_at
    except Exception:
        pass
    return None, None


def _get_health_summary() -> tuple[str, int]:
    try:
        from logos.data.health import collect_health

        h = collect_health()
        status = h.status if h else "unknown"
    except Exception:
        status = "unknown"

    try:
        from logos.data.drift import collect_drift

        d = collect_drift()
        high = sum(1 for item in (d.drift_items if d else []) if item.severity == "high")
    except Exception:
        high = 0

    return status, high


def _sprint_measure_statuses() -> dict[str, str] | None:
    try:
        data = json.loads(SPRINT_STATE.read_text(encoding="utf-8"))
        measures = data.get("measures", {})
        if isinstance(measures, dict):
            return {
                k: v.get("status", "pending")
                for k, v in measures.items()
                if isinstance(v, dict)
            }
    except Exception:
        pass
    return None


def _should_generate_narrative(
    session: SessionContext,
    stance: str,
    *,
    last_narrative_age_s: float = float("inf"),
) -> bool:
    if stance in ("degraded", "critical"):
        return False
    if last_narrative_age_s < NARRATIVE_COOLDOWN_S:
        return False
    if session.session_boundary:
        return True
    if session.absence_hours >= MORNING_ABSENCE_HOURS:
        return True
    return False


def _goal_to_summary(g: VaultGoal) -> GoalSummary:
    return GoalSummary(
        id=g.id,
        title=g.title,
        priority=g.priority,
        status=g.status,
        progress=g.progress,
        stale=g.stale,
        file_path=g.file_path,
        obsidian_uri=g.obsidian_uri,
        target_date=g.target_date,
    )


def _domain_priority(ds: DomainState) -> tuple[int, float]:
    priority = 100
    if ds.health == "blocked":
        priority = 0
    elif ds.stale_count > 0 and ds.top_goal and ds.top_goal.priority == "P0":
        priority = 10
    elif ds.health == "active":
        priority = 30
    elif ds.health == "stale":
        priority = 50
    return (priority, ds.recency_hours)


def collect_orientation() -> OrientationState:
    """Assemble orientation state from all sources."""
    registry = _load_domain_registry()
    session = infer_session(domains=registry)
    sprint_statuses = _sprint_measure_statuses()
    all_goals = collect_vault_goals(sprint_measure_statuses=sprint_statuses)
    sprint_summary = _get_sprint_summary()
    briefing_headline, briefing_generated_at = _get_briefing()
    system_health, drift_high = _get_health_summary()
    stance = _get_stimmung_stance()

    domain_states: list[DomainState] = []
    for domain_name, domain_cfg in registry.items():
        domain_goals = [g for g in all_goals if g.domain == domain_name and g.status == "active"]
        stale = [g for g in domain_goals if g.stale]
        top = domain_goals[0] if domain_goals else None
        recency = session.domain_recency.get(domain_name, float("inf"))

        has_sprint = "sprint" in (domain_cfg.get("apis") or {})
        blocked = has_sprint and sprint_summary and sprint_summary.blocking_gate
        if blocked:
            health = "blocked"
        elif stale:
            health = "stale"
        elif domain_goals and recency < domain_cfg.get("staleness_days", 30) * 24:
            health = "active"
        else:
            health = "dormant"

        next_action = None
        next_action_link = None
        if blocked and sprint_summary:
            next_action = f"Gate {sprint_summary.blocking_gate} blocking"
        elif has_sprint and sprint_summary and sprint_summary.next_measure:
            next_action = f"Next: {sprint_summary.next_measure} {sprint_summary.next_measure_title or ''}".strip()
        elif top:
            next_action_link = top.obsidian_uri

        ds = DomainState(
            domain=domain_name,
            top_goal=_goal_to_summary(top) if top else None,
            goal_count=len(domain_goals),
            stale_count=len(stale),
            recency_hours=recency,
            health=health,
            sprint_progress=sprint_summary if has_sprint else None,
            next_action=next_action,
            next_action_link=next_action_link,
        )
        domain_states.append(ds)

    domain_states.sort(key=_domain_priority)

    state = OrientationState(
        session=session,
        domains=domain_states,
        briefing_headline=briefing_headline,
        briefing_generated_at=briefing_generated_at,
        system_health=system_health,
        drift_high_count=drift_high,
        narrative=_last_narrative,  # serve cached narrative from prior generation
        stimmung_stance=stance,
    )

    return state
```

- [ ] **Step 2: Run tests**

```bash
uv run pytest tests/test_orientation.py -v
```

Expected: All PASS.

- [ ] **Step 3: Lint**

```bash
uv run ruff check logos/data/orientation.py && uv run ruff format logos/data/orientation.py
```

- [ ] **Step 4: Commit**

```bash
git add logos/data/orientation.py
git commit -m "feat: orientation collector — deterministic domain assembly"
```

---

### Task 8: Narrative Tests + Wiring

**Files:**
- Create: `tests/test_orientation_narrative.py`

- [ ] **Step 1: Write narrative tests**

```python
"""Tests for orientation narrative gating logic."""

from __future__ import annotations

from logos.data.orientation import _should_generate_narrative
from logos.data.session_inference import SessionContext


def test_narrative_triggers_on_session_boundary() -> None:
    session = SessionContext(session_boundary=True, absence_hours=3.0)
    assert _should_generate_narrative(session, "nominal", last_narrative_age_s=9999) is True


def test_narrative_suppressed_during_degraded() -> None:
    session = SessionContext(session_boundary=True, absence_hours=3.0)
    assert _should_generate_narrative(session, "degraded", last_narrative_age_s=9999) is False


def test_narrative_suppressed_during_critical() -> None:
    session = SessionContext(session_boundary=True, absence_hours=3.0)
    assert _should_generate_narrative(session, "critical", last_narrative_age_s=9999) is False


def test_narrative_suppressed_when_recent() -> None:
    session = SessionContext(session_boundary=True, absence_hours=3.0)
    assert _should_generate_narrative(session, "nominal", last_narrative_age_s=600) is False


def test_narrative_triggers_on_morning() -> None:
    session = SessionContext(session_boundary=False, absence_hours=10.0)
    assert _should_generate_narrative(session, "nominal", last_narrative_age_s=9999) is True


def test_narrative_does_not_trigger_steady_state() -> None:
    session = SessionContext(session_boundary=False, absence_hours=0.5)
    assert _should_generate_narrative(session, "nominal", last_narrative_age_s=9999) is False
```

- [ ] **Step 2: Run tests**

```bash
uv run pytest tests/test_orientation_narrative.py -v
```

Expected: All PASS (the function already exists from Task 7).

- [ ] **Step 3: Commit**

```bash
git add tests/test_orientation_narrative.py
git commit -m "test: narrative gating logic tests"
```

---

### Task 9: API Route + Cache Integration

**Files:**
- Create: `logos/api/routes/orientation.py`
- Modify: `logos/api/cache.py`

- [ ] **Step 1: Create orientation route**

```python
"""Orientation API route."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from logos.api.cache import cache

router = APIRouter(prefix="/api", tags=["orientation"])


@router.get("/orientation")
async def get_orientation() -> JSONResponse:
    from dataclasses import asdict, is_dataclass

    def _to_dict(obj: object) -> object:
        if is_dataclass(obj) and not isinstance(obj, type):
            return asdict(obj)
        return obj

    data = _to_dict(cache.orientation) if cache.orientation else {}
    age = cache.slow_cache_age()
    return JSONResponse(content=data, headers={"X-Cache-Age": str(age)})
```

- [ ] **Step 2: Add orientation field to DataCache in `logos/api/cache.py`**

Add field after `studio` (around line 38):

```python
    orientation: object | None = None
```

Add collector to `_refresh_slow_sync()` — after the existing collector list, before nudges special handling:

```python
        try:
            from logos.data.orientation import collect_orientation
            self.orientation = collect_orientation()
        except Exception:
            log.warning("orientation refresh failed", exc_info=True)
```

- [ ] **Step 3: Register route in the FastAPI app**

Find where routers are registered (likely `logos/api/__init__.py` or `logos/api/app.py`). Add:

```python
from logos.api.routes.orientation import router as orientation_router
app.include_router(orientation_router)
```

- [ ] **Step 4: Run existing API tests**

```bash
uv run pytest tests/logos/ -v -q 2>&1 | tail -20
```

- [ ] **Step 5: Commit**

```bash
git add logos/api/routes/orientation.py logos/api/cache.py
git commit -m "feat: /api/orientation endpoint + cache integration"
```

---

### Task 10: Tauri Backend Command

**Files:**
- Modify: `hapax-logos/src-tauri/src/commands/state.rs`
- Modify: `hapax-logos/src-tauri/src/main.rs` (or wherever invoke_handler is)

- [ ] **Step 1: Add get_orientation command**

In `state.rs`, add a proxy command following the existing pattern for proxy commands:

```rust
#[tauri::command]
pub async fn get_orientation() -> Result<serde_json::Value, String> {
    let url = "http://localhost:8051/api/orientation";
    let resp = reqwest::get(url)
        .await
        .map_err(|e| format!("orientation fetch failed: {e}"))?;
    let body: serde_json::Value = resp
        .json()
        .await
        .map_err(|e| format!("orientation parse failed: {e}"))?;
    Ok(body)
}
```

Register in invoke_handler:

```rust
state::get_orientation,
```

- [ ] **Step 2: Build to verify compilation**

```bash
cd hapax-logos && pnpm tauri build --debug 2>&1 | tail -20
```

- [ ] **Step 3: Commit**

```bash
git add hapax-logos/src-tauri/
git commit -m "feat: get_orientation Tauri command"
```

---

### Task 11: Frontend Types + Hook + Client

**Files:**
- Modify: `hapax-logos/src/api/types.ts`
- Modify: `hapax-logos/src/api/client.ts`
- Modify: `hapax-logos/src/api/hooks.ts`

- [ ] **Step 1: Add TypeScript types to types.ts**

```typescript
export interface SessionContext {
  last_active_domain: string;
  last_active_goal: string | null;
  last_active_measure: string | null;
  absence_hours: number;
  session_boundary: boolean;
  domain_recency: Record<string, number>;
  active_signals: string[];
}

export interface GoalSummary {
  id: string;
  title: string;
  priority: string;
  status: string;
  progress: number | null;
  stale: boolean;
  file_path: string;
  obsidian_uri: string;
  target_date: string | null;
}

export interface SprintSummary {
  current_sprint: number;
  measures_completed: number;
  measures_total: number;
  blocking_gate: string | null;
  next_measure: string | null;
  next_measure_title: string | null;
  models: Record<string, number>;
}

export interface DomainState {
  domain: string;
  top_goal: GoalSummary | null;
  goal_count: number;
  stale_count: number;
  recency_hours: number;
  health: "active" | "stale" | "dormant" | "blocked";
  sprint_progress: SprintSummary | null;
  next_action: string | null;
  next_action_link: string | null;
}

export interface OrientationState {
  session: SessionContext;
  domains: DomainState[];
  briefing_headline: string | null;
  briefing_generated_at: string | null;
  system_health: string;
  drift_high_count: number;
  narrative: string | null;
  narrative_generated_at: string | null;
  stimmung_stance: string;
}
```

- [ ] **Step 2: Add client invoke to client.ts**

```typescript
orientation: () => invoke<OrientationState>("get_orientation"),
```

Add `OrientationState` to the import from `./types`.

- [ ] **Step 3: Add hook to hooks.ts**

```typescript
export const useOrientation = () =>
  useQuery({
    queryKey: ["orientation"],
    queryFn: api.orientation,
    refetchInterval: SLOW,
  });
```

- [ ] **Step 4: Verify TypeScript compiles**

```bash
cd hapax-logos && pnpm tsc --noEmit 2>&1 | tail -20
```

- [ ] **Step 5: Commit**

```bash
git add hapax-logos/src/api/types.ts hapax-logos/src/api/client.ts hapax-logos/src/api/hooks.ts
git commit -m "feat: orientation TypeScript types, client invoke, and query hook"
```

---

### Task 12: OrientationPanel Component

**Files:**
- Create: `hapax-logos/src/components/sidebar/OrientationPanel.tsx`

- [ ] **Step 1: Build OrientationPanel**

```tsx
import { useState } from "react";
import { useOrientation, useBriefing } from "../../api/hooks";
import { useAgentRun } from "../../contexts/AgentRunContext";
import { SidebarSection } from "./SidebarSection";
import { DetailModal } from "../shared/DetailModal";
import { MarkdownContent } from "../shared/MarkdownContent";
import { formatAge } from "../../utils";
import type { DomainState } from "../../api/types";
import { open } from "@tauri-apps/plugin-shell";

const HEALTH_COLORS: Record<string, string> = {
  active: "border-green-400/15",
  stale: "border-yellow-400/15",
  dormant: "border-neutral-600/10 opacity-60",
  blocked: "border-orange-400/25",
};

function formatRecency(hours: number): string {
  if (!isFinite(hours)) return "";
  if (hours < 1) return `${Math.round(hours * 60)}m ago`;
  if (hours < 48) return `${Math.round(hours)}h ago`;
  return `${Math.round(hours / 24)}d ago`;
}

function DomainStrip({
  ds,
  expanded,
  onToggle,
  stimmungStance,
}: {
  ds: DomainState;
  expanded: boolean;
  onToggle: () => void;
  stimmungStance: string;
}) {
  if (ds.health === "dormant" && stimmungStance !== "nominal") {
    return (
      <div className="px-2 py-0.5 text-xs text-neutral-500 cursor-pointer" onClick={onToggle}>
        {ds.domain}
      </div>
    );
  }

  return (
    <div
      className={`border-l-2 ${HEALTH_COLORS[ds.health] || ""} px-2 py-1 cursor-pointer`}
      onClick={onToggle}
    >
      <div className="flex items-center justify-between text-xs">
        <span className="font-medium text-neutral-300">{ds.domain}</span>
        <span className="text-neutral-500">
          {formatRecency(ds.recency_hours)}
          {" \u2014 "}
          <span
            className={
              ds.health === "blocked"
                ? "text-orange-400"
                : ds.health === "stale"
                  ? "text-yellow-400"
                  : ds.health === "active"
                    ? "text-green-400"
                    : "text-neutral-500"
            }
          >
            {ds.health}
          </span>
        </span>
      </div>
      {ds.top_goal && (
        <div className="mt-0.5 text-xs">
          <span
            className="text-neutral-200 hover:underline cursor-pointer"
            onClick={(e) => {
              e.stopPropagation();
              open(ds.top_goal!.obsidian_uri);
            }}
          >
            {ds.top_goal.title}
          </span>
          {ds.top_goal.progress != null && (
            <span className="text-neutral-500 ml-2">
              {Math.round(ds.top_goal.progress * 100)}%
            </span>
          )}
          {ds.sprint_progress && (
            <span className="text-neutral-500 ml-2">
              {ds.sprint_progress.measures_completed}/{ds.sprint_progress.measures_total}
            </span>
          )}
        </div>
      )}
      {ds.next_action && (
        <div className="mt-0.5 text-xs text-neutral-400">
          {ds.health === "blocked" && <span className="text-orange-400 mr-1">!</span>}
          {ds.next_action}
        </div>
      )}
      {expanded && ds.goal_count > 1 && (
        <div className="mt-1 text-xs text-neutral-500">
          {ds.goal_count} goals ({ds.stale_count} stale)
        </div>
      )}
    </div>
  );
}

export function OrientationPanel() {
  const { data: orientation, dataUpdatedAt } = useOrientation();
  const { data: briefing } = useBriefing();
  const [expandedDomain, setExpandedDomain] = useState<string | null>(null);
  const [briefingOpen, setBriefingOpen] = useState(false);

  if (!orientation) {
    return <SidebarSection title="ORIENTATION" loading />;
  }

  const stance = orientation.stimmung_stance;

  let visibleDomains = orientation.domains;
  if (stance === "critical") {
    visibleDomains = orientation.domains.slice(0, 1);
  } else if (stance === "degraded") {
    visibleDomains = orientation.domains.slice(0, 2);
  }

  return (
    <>
      <SidebarSection title="ORIENTATION" age={formatAge(dataUpdatedAt)}>
        {orientation.narrative && stance === "nominal" && (
          <div className="text-xs text-neutral-300 mb-2 leading-relaxed">
            {orientation.narrative}
          </div>
        )}
        <div className="space-y-1">
          {visibleDomains.map((ds) => (
            <DomainStrip
              key={ds.domain}
              ds={ds}
              expanded={expandedDomain === ds.domain}
              onToggle={() =>
                setExpandedDomain(expandedDomain === ds.domain ? null : ds.domain)
              }
              stimmungStance={stance}
            />
          ))}
        </div>
        {orientation.briefing_headline && (
          <div
            className="mt-2 pt-1 border-t border-neutral-700/30 text-xs text-neutral-500 cursor-pointer hover:text-neutral-400"
            onClick={() => setBriefingOpen(true)}
          >
            {orientation.system_health} · {orientation.drift_high_count} high drift
            {orientation.briefing_generated_at && (
              <span className="ml-1">
                · {new Date(orientation.briefing_generated_at).toLocaleTimeString([], {
                    hour: "2-digit",
                    minute: "2-digit",
                  })}
              </span>
            )}
          </div>
        )}
      </SidebarSection>

      {briefingOpen && briefing && (
        <DetailModal title="Daily Briefing" onClose={() => setBriefingOpen(false)}>
          <MarkdownContent content={briefing.body} />
          {briefing.action_items.length > 0 && (
            <div className="mt-3">
              <h4 className="text-xs font-medium text-neutral-400 mb-1">Action Items</h4>
              {briefing.action_items.map((item, i) => (
                <div key={i} className="text-xs text-neutral-300 mb-1">
                  <span
                    className={
                      item.priority === "high"
                        ? "text-red-400"
                        : item.priority === "medium"
                          ? "text-yellow-400"
                          : "text-neutral-500"
                    }
                  >
                    [{item.priority.toUpperCase()}]
                  </span>{" "}
                  {item.action}
                </div>
              ))}
            </div>
          )}
        </DetailModal>
      )}
    </>
  );
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd hapax-logos && pnpm tsc --noEmit 2>&1 | tail -20
```

- [ ] **Step 3: Commit**

```bash
git add hapax-logos/src/components/sidebar/OrientationPanel.tsx
git commit -m "feat: OrientationPanel component with stimmung modulation"
```

---

### Task 13: Wire Sidebar + Delete Old Panels

**Files:**
- Modify: `hapax-logos/src/components/Sidebar.tsx`
- Delete: `hapax-logos/src/components/sidebar/GoalsPanel.tsx`
- Delete: `hapax-logos/src/components/sidebar/BriefingPanel.tsx`
- Delete: `logos/data/goals.py`

- [ ] **Step 1: Update Sidebar.tsx**

Remove imports for `GoalsPanel` and `BriefingPanel`. Add import for `OrientationPanel`. In the panels array, replace the `goals` and `briefing` entries with:

```typescript
{ id: "orientation", component: OrientationPanel, defaultOrder: 4 },
```

Remove any sidebar priority logic that referenced `useBriefing()` for staleness (orientation handles this internally).

- [ ] **Step 2: Delete old files**

```bash
rm hapax-logos/src/components/sidebar/GoalsPanel.tsx
rm hapax-logos/src/components/sidebar/BriefingPanel.tsx
rm logos/data/goals.py
```

- [ ] **Step 3: Update goals imports**

In `logos/api/cache.py`, change the goals collector import:

```python
# Replace:
from logos.data.goals import collect_goals
# With:
from logos.data.vault_goals import collect_vault_goals
```

In `logos/data/nudges.py`, update `_collect_goal_nudges` to import from `vault_goals`:

```python
# Replace:
from logos.data.goals import collect_goals
# With:
from logos.data.vault_goals import collect_vault_goals
```

- [ ] **Step 4: Verify compilation**

```bash
cd hapax-logos && pnpm tsc --noEmit 2>&1 | tail -20
```

- [ ] **Step 5: Run full test suite**

```bash
uv run pytest tests/ -q --ignore=tests/hapax_daimonion -x 2>&1 | tail -20
```

Fix any failures from stale imports.

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "feat: wire OrientationPanel, delete GoalsPanel + BriefingPanel + goals.py"
```

---

### Task 14: Goal Migration Script

**Files:**
- Create: `scripts/migrate_goals_to_vault.py`

- [ ] **Step 1: Write migration script**

```python
"""Migrate goals from operator.json to Obsidian vault notes.

Usage: uv run python scripts/migrate_goals_to_vault.py [--dry-run]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

OPERATOR_JSON = Path.home() / ".hapax" / "operator.json"
FALLBACK = Path(__file__).resolve().parents[1] / "profiles" / "operator-profile.json"
VAULT_GOALS_DIR = Path.home() / "Documents" / "Personal" / "20 Projects" / "hapax-goals"

DRY_RUN = "--dry-run" in sys.argv


def load_operator_goals() -> list[dict]:
    for path in [OPERATOR_JSON, FALLBACK]:
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            goals = data.get("goals", {})
            primary = goals.get("primary", [])
            secondary = goals.get("secondary", [])
            return [
                {**g, "category": "primary"} for g in primary
            ] + [
                {**g, "category": "secondary"} for g in secondary
            ]
    return []


def goal_to_note(g: dict) -> tuple[str, str]:
    fm = {
        "type": "goal",
        "title": g.get("name", g.get("id", "untitled")),
        "domain": "research",  # default — operator should recategorize
        "status": g.get("status", "active"),
        "priority": "P1" if g.get("category") == "primary" else "P2",
    }
    if g.get("last_activity_at"):
        fm["started_at"] = g["last_activity_at"][:10]

    yaml_str = yaml.dump(fm, default_flow_style=False, sort_keys=False)
    body = g.get("description", "") or g.get("progress_summary", "") or ""
    slug = g.get("id", "goal").replace(" ", "-").lower()
    content = f"---\n{yaml_str}---\n\n{body}\n"
    return slug, content


def main() -> None:
    goals = load_operator_goals()
    if not goals:
        print("No goals found in operator.json. Nothing to migrate.")
        return

    if not DRY_RUN:
        VAULT_GOALS_DIR.mkdir(parents=True, exist_ok=True)

    for g in goals:
        slug, content = goal_to_note(g)
        path = VAULT_GOALS_DIR / f"{slug}.md"
        if DRY_RUN:
            print(f"[dry-run] Would write: {path}")
            print(content[:200])
            print("---")
        else:
            path.write_text(content, encoding="utf-8")
            print(f"Created: {path}")

    print(f"\nMigrated {len(goals)} goals to {VAULT_GOALS_DIR}")
    if not DRY_RUN:
        print("Review domain assignments — all defaulted to 'research'.")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Test dry-run**

```bash
uv run python scripts/migrate_goals_to_vault.py --dry-run
```

- [ ] **Step 3: Commit**

```bash
git add scripts/migrate_goals_to_vault.py
git commit -m "feat: goal migration script — operator.json to vault notes"
```

---

### Task 15: Smoke Test

**Files:** None (verification only)

- [ ] **Step 1: Start logos API and verify orientation endpoint**

```bash
uv run logos-api &
sleep 3
curl -s http://localhost:8051/api/orientation | python -m json.tool | head -40
```

Expected: JSON with `session`, `domains`, `briefing_headline`, `system_health`, `stimmung_stance` fields.

- [ ] **Step 2: Run full backend test suite**

```bash
uv run pytest tests/ -q --ignore=tests/hapax_daimonion -x
```

Expected: All PASS.

- [ ] **Step 3: Check for stale imports**

```bash
rg "from logos.data.goals import\|from logos.data import goals\|GoalsPanel\|BriefingPanel" --type py --type ts logos/ hapax-logos/src/ tests/
```

Expected: No matches.

- [ ] **Step 4: Build frontend**

```bash
cd hapax-logos && pnpm tauri build --debug 2>&1 | tail -20
```

Expected: Successful build.

- [ ] **Step 5: Commit any fixes**

```bash
git add -A && git commit -m "fix: smoke test cleanup"
```

---

## Deferred (Phase 5 — Ecosystem Updates)

Separate tasks after core orientation panel is merged and stable:

1. **Obsidian plugin update** — Add `Goal` note kind to `obsidian-hapax` sections.ts
2. **Briefing agent update** — Include orientation context in daily briefing synthesis
3. **Drift detector update** — Check for vault goal notes instead of operator.json goals
4. **operator.json cleanup** — Remove goals section after vault migration confirmed stable
5. **Nudges collector update** — Replace `collect_goals` import with `collect_vault_goals` in nudges.py
6. **MCP tool update** — Update `goals` and `daily_summary` tools, add `orientation` tool
