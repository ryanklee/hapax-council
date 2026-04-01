# Orientation Panel Design

Reimagine the Logos dashboard Goals + Briefing + Action Items surface as a unified
orientation system that bridges Logos and Obsidian, supports all life domains, and
satisfies the Hapax governance axioms.

## Problem

The current Logos sidebar shows three disconnected widgets — Goals (flat list from
`operator.json`, currently 0 active), Briefing (daily static markdown, stale by noon),
Action Items (nudge list). The operator's actual planning lives in Obsidian (sprint
measures, gates, Bayesian posteriors, PARA-organized projects). Context dies at the
Logos-to-Obsidian transition.

**Axiom violations in current state:**

- ex-cognitive-009: related information not batched — operator must context-switch
  between Logos (health, nudges) and Obsidian (research planning) for coherent picture
- ex-state-003: no task context persistence across interruptions — system cannot answer
  "where did I leave off"
- ex-alert-004: goals system dormant (0 active) — no proactive surfacing of stale work

## Design Decisions

| # | Decision | Rationale |
|---|----------|-----------|
| 1 | Obsidian vault is single source of truth for all planning | Operator already organizes life in PARA vault (1924 notes). Logos reads, never writes notes. |
| 2 | `operator.json` goals section replaced by vault-native goal notes | Flat JSON list with no tooling → rich markdown notes with frontmatter, editable in Obsidian |
| 3 | Orientation panel replaces Goals + Briefing widgets | Coherent narrative, not widget soup (ex-cognitive-009) |
| 4 | Briefing remains a separate scheduled artifact | Reviewable history. Orientation panel consumes it as one input among many. |
| 5 | Session continuity inferred from telemetry | Zero operator burden (ex-routine-001). Git, Langfuse, IR presence, stimmung, file mtimes. |
| 6 | Deterministic assembly + conditional LLM narrative | Deterministic baseline satisfies mg-deterministic-001. LLM fires only at context boundaries. Stimmung gates LLM out during degraded/critical. |
| 7 | Write path: light write-back via existing sprint API only | Single-writer principle. sprint_tracker agent is sole vault writer. No new write paths. Corporate boundary (cb-degrade-001) satisfied — Obsidian plugin degrades to vault-only data when Logos unreachable. |
| 8 | Domain registry maps life domains to data sources | Composable perspectives: each domain independently queryable. Adding a domain = config change, not code. |

## Section 1: Vault-Native Goal Schema

**What dies:** `operator.json` goals section, `logos/data/goals.py`, `GoalsPanel.tsx`.

**What replaces it:** Goal notes in the Obsidian vault, one file per goal, organized
under PARA areas. The vault is already structured as `20 Projects/`, `30 Areas/`, etc.

**Goal note frontmatter schema:**

```yaml
type: goal                            # discriminator for vault scanning
title: Validate DMN Continuous Substrate model
domain: research                      # research | management | studio | personal | health
status: active                        # active | paused | completed | abandoned
priority: P1                          # P0 (urgent) | P1 (important) | P2 (routine)
started_at: '2026-03-30'
target_date: '2026-04-20'            # optional — some goals are open-ended
sprint_measures: ['4.1','4.2','4.3']  # optional — links to sprint system
depends_on: []                        # other goal IDs (filename stems)
tags: [bayesian-validation, dmn]
```

Note body is free-form markdown. Collector reads only frontmatter.

**Staleness:** Computed from file modification timestamp + domain-specific thresholds:

| Domain | Staleness threshold |
|--------|-------------------|
| research | 7 days |
| management | 14 days |
| studio | 14 days |
| personal | 30 days |
| health | 7 days |

No `last_activity_at` field — the filesystem is the signal.

**Sprint linkage:** Goals with `sprint_measures` get progress computed from the sprint
system. A goal like "Validate DMN" knows it's 2/5 measures complete because the sprint
API already tracks that.

## Section 2: Domain Registry

**File:** `config/domains.yaml`

Maps each life domain to its data sources, priority signals, and staleness thresholds.
The orientation collector iterates this registry. Adding a new domain means adding an
entry here, not writing new code.

```yaml
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
      midi_activity: true

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
      watch_data: true
```

**Governance compliance:**

- Composable perspectives: each domain independently queryable
- Corporate boundary (cb-degrade-001): officium and localhost sources degrade gracefully;
  unreachable domains show vault-only state (goals + file timestamps), never errors
- Executive function (ex-cogload-001): defaults work without customization

## Section 3: Telemetry Inference Engine

**New module:** `logos/data/session_inference.py` (deterministic, zero LLM)

Answers "where did the operator leave off" without asking.

**Input signals:**

| Signal | Source | Inference |
|--------|--------|-----------|
| Git commits/diffs | `git log` across repos in registry | Which project had recent work |
| Langfuse traces | Langfuse API (:3000) | Which agents ran, query recency |
| Vault file mtime | Filesystem scan of registered vault paths | Which notes were edited |
| IR presence | `/dev/shm/hapax-stimmung/state.json` | Session gaps (absence detection) |
| Stimmung stance | Same shm path | Cognitive state at last observation |
| Sprint state | `/dev/shm/hapax-sprint/state.json` | In-progress measures, blocking gates |
| Measure transitions | `/dev/shm/hapax-sprint/completed.jsonl` | Recent completions |

**Output:**

```python
@dataclass
class SessionContext:
    last_active_domain: str              # domain with most recent signal
    last_active_goal: str | None         # goal ID with most recent activity
    last_active_measure: str | None      # sprint measure if research domain
    absence_hours: float                 # hours since last IR presence
    session_boundary: bool               # True if absence > 2h
    domain_recency: dict[str, float]     # domain -> hours since last activity
    active_signals: list[str]            # human-readable signal descriptions
```

**Cadence:** Computed on-demand during orientation refresh (slow tier, 5 min). Reads
existing telemetry — no new collection infrastructure.

**Governance:** No person-adjacent data. Git author is always operator (single-user).
Langfuse traces are operator's own. IR detects presence, not identity.

## Section 4: Orientation Collector

**New module:** `logos/data/orientation.py`

**Replaces:** `logos/data/goals.py`

### Assembly Phase (deterministic, always runs)

```python
@dataclass
class GoalSummary:
    id: str
    title: str
    priority: str
    status: str
    progress: float | None       # 0.0-1.0 from sprint measures
    stale: bool
    file_path: str               # for obsidian:// URI
    target_date: str | None

@dataclass
class SprintSummary:
    current_sprint: int
    measures_completed: int
    measures_total: int
    blocking_gate: str | None
    next_measure: str | None
    next_measure_title: str | None
    models: dict[str, float]     # model name -> current posterior

@dataclass
class DomainState:
    domain: str
    top_goal: GoalSummary | None
    goal_count: int
    stale_count: int
    recency_hours: float
    health: str                  # "active" | "stale" | "dormant" | "blocked"
    sprint_progress: SprintSummary | None  # research domain only
    next_action: str | None
    next_action_link: str | None # obsidian:// URI or command hint

@dataclass
class OrientationState:
    session: SessionContext
    domains: list[DomainState]   # sorted by recency, then priority
    briefing: BriefingData | None
    system_health: str
    drift_high_count: int
    narrative: str | None        # LLM-generated, None if deterministic-only
    narrative_generated_at: str | None
    stimmung_stance: str
```

**Ranking:** Domains sorted by `(-priority_score, recency_hours)` where priority_score
reflects: blocked gates (highest), stale P0 goals, active sprint measures, then recency.

### Conditional LLM Phase

**Fires when ANY of:**

- `session.session_boundary == True` (returned after >2h absence)
- `session.absence_hours > 8` (morning / start of day)
- Domain state transition since last render (goal completed, gate failed, new blocker)
- Explicit operator request

**Does NOT fire when:**

- `stimmung_stance in ("degraded", "critical")` — deterministic only, no latency
- Steady-state work (no context boundary detected)
- Less than 30 minutes since last narrative generation

**LLM prompt (fast model, single call):**

```
You are the operator's orientation system. Given the current domain states,
session context, and today's briefing, produce a 2-4 sentence orientation.

Rules:
- Lead with where they left off and what changed
- Name the recommended next domain and action
- If a gate is blocking, say so plainly
- No rhetorical questions, no encouragement, no filler
- Direct and informative (ex-prose-001)
```

**Cache integration:** `OrientationState` added to `DataCache` slow refresh tier (5 min).
Narrative cached separately — regenerates only on context boundary, not every refresh.

## Section 5: Vault Goal Collector

**New module:** `logos/data/vault_goals.py`

```python
VAULT_BASE = Path.home() / "Documents" / "Personal"

@dataclass
class VaultGoal:
    id: str                      # filename stem
    title: str
    domain: str
    status: str
    priority: str
    started_at: str | None
    target_date: str | None
    sprint_measures: list[str]
    depends_on: list[str]
    tags: list[str]
    file_path: str               # absolute path for obsidian:// URI
    last_modified: datetime       # filesystem mtime
    stale: bool                  # computed from domain threshold
    progress: float | None       # from sprint measures if linked

def collect_vault_goals(domain_filter: str | None = None) -> list[VaultGoal]:
    """Scan vault for type: goal notes, compute staleness and progress."""
```

**Performance:** Full vault scan on first load, mtime-based change detection on
subsequent refreshes. `type: goal` frontmatter filter is fast — YAML parse only on
changed files.

**Sprint linkage:** Goals with `sprint_measures` get progress from
`/dev/shm/hapax-sprint/state.json` (existing, no new API call).

**Obsidian URI:** Each goal produces `obsidian://open?vault=Personal&file=...` for
direct navigation from the orientation panel.

## Section 6: Frontend — OrientationPanel

**Replaces:** `GoalsPanel.tsx` + `BriefingPanel.tsx` (both deleted).
`NudgeList.tsx` remains as separate composable panel below.

**New file:** `hapax-logos/src/components/sidebar/OrientationPanel.tsx`

### Layout

```
+-- ORIENTATION ----------------------------- age --+
|                                                    |
|  [narrative: 2-4 sentences, or deterministic       |
|   summary when LLM not triggered]                  |
|                                                    |
|  +-- research --------------- 2h ago -- active --+ |
|  | * Validate DMN model    2/5 measures           | |
|  |   Next: 7.2 correlation   > start              | |
|  |   ! G1 blocking                                | |
|  +------------------------------------------------+ |
|  +-- management ----------- 18h ago -- stale ---+ |
|  | * Q2 review prep         3 nudges             | |
|  +------------------------------------------------+ |
|  +-- studio --------------- 3d ago -- dormant --+ |
|  | * Finish beat tape        P2                  | |
|  +------------------------------------------------+ |
|                                                    |
|  Briefing: 94.6% uptime . 173 drift . 07:00       |
+----------------------------------------------------+
```

### State Encoding (design language compliant)

| Domain health | Border color | Text treatment |
|--------------|-------------|----------------|
| active | green-400 at 15% | Normal |
| stale | yellow-400 at 15% | Age highlighted |
| dormant | neutral, dimmed | Compressed (1 line) |
| blocked | orange-400 at 25% | Block reason visible |

### Interactions

- Click domain strip: expands to show all goals in that domain
- Click goal: opens Obsidian via `obsidian://` URI (Tauri `shell.open`)
- Click "start" on measure: calls existing sprint transition API
- Click briefing line: opens briefing detail modal (preserved from BriefingPanel)

### Stimmung Modulation

| Stance | Behavior |
|--------|----------|
| Nominal | All domains visible, narrative shown |
| Cautious | Dormant domains compressed to single line |
| Degraded | Only top domain + system health, no narrative |
| Critical | Single line: most urgent action item only |

### Data Hook

```typescript
useOrientation()  // refetch: 5min (SLOW), returns OrientationState
```

New Tauri command `get_orientation()` in `state.rs` proxies to `/api/orientation`.

## Section 7: API Surface

### New

- `GET /api/orientation` — returns `OrientationState` (route: `logos/api/routes/orientation.py`)

### Modified

| File | Change |
|------|--------|
| `logos/api/cache.py` | Add `orientation: OrientationState` to DataCache, slow refresh |
| `hapax-logos/src/api/hooks.ts` | Add `useOrientation()` hook |
| `hapax-logos/src/api/types.ts` | Add OrientationState, DomainState TypeScript types |
| `hapax-logos/src-tauri/src/commands/state.rs` | Add `get_orientation()` command |
| `hapax-mcp/src/hapax_mcp/server.py` | Update `goals` tool to read `/api/orientation`; add `orientation` tool |
| `obsidian-hapax/src/sections.ts` | Add `Goal` note kind with domain state rendering |

### Deleted

| File | Reason |
|------|--------|
| `logos/data/goals.py` | Replaced by `vault_goals.py` |
| `hapax-logos/src/components/sidebar/GoalsPanel.tsx` | Replaced by `OrientationPanel.tsx` |
| `hapax-logos/src/components/sidebar/BriefingPanel.tsx` | Merged into `OrientationPanel.tsx` |

## Section 8: Migration Path

### Phase 1 — Vault Goals (no frontend changes)

1. Define goal note schema (this spec)
2. Migration script: read `operator.json` goals, create vault notes with frontmatter
3. Implement `logos/data/vault_goals.py` collector
4. Wire into existing `/api/goals` endpoint as drop-in replacement
5. Verify existing GoalsPanel still renders with new source

### Phase 2 — Session Inference + Orientation Collector

1. Implement `logos/data/session_inference.py`
2. Implement `logos/data/orientation.py` (deterministic assembly only)
3. Add `config/domains.yaml` with default registry
4. Add `GET /api/orientation` endpoint + cache integration
5. Verify: orientation state assembles correctly from vault + sprint + telemetry

### Phase 3 — LLM Orientation Narrative

1. Add conditional LLM phase to orientation collector
2. Implement context boundary detection (absence duration, domain transitions)
3. Implement stimmung gating (no LLM in degraded/critical)
4. Verify: narrative fires at correct boundaries, deterministic fallback works

### Phase 4 — Frontend

1. Build `OrientationPanel.tsx`
2. Delete `GoalsPanel.tsx` + `BriefingPanel.tsx`
3. Update `Sidebar.tsx` layout
4. Add Tauri command + `useOrientation()` hook
5. Wire stimmung-responsive density modulation

### Phase 5 — Ecosystem Updates

1. Update `hapax-mcp` tools (goals -> orientation)
2. Update `obsidian-hapax` plugin (Goal note section type)
3. Update briefing agent to include orientation context
4. Delete `operator.json` goals section
5. Update drift detector to validate goal notes exist instead of operator.json

## Governance Compliance Matrix

| Axiom | Implication | How satisfied |
|-------|------------|---------------|
| Single User (su) | No multi-user features | All data is operator's own telemetry and vault |
| Executive Function (ex-cognitive-009) | Batch related info in single views | Orientation panel unifies goals + briefing + sprint + domain state |
| Executive Function (ex-state-003) | Persist context across interruptions | Session inference from telemetry — zero operator burden |
| Executive Function (ex-routine-001) | Automate recurring tasks | Orientation refreshes on cache timer, narrative on context boundary |
| Executive Function (ex-prose-001) | Direct, informative LLM prose | Prompt explicitly prohibits filler, rhetorical questions |
| Executive Function (ex-init-001) | Zero config beyond env vars | Domain registry ships with defaults |
| Management Governance (mg-deterministic-001) | Deterministic where possible | Assembly phase is pure data; LLM is conditional overlay |
| Management Governance (mg-boundary-001) | No generated feedback about people | Orientation is about operator's own domains, not team members |
| Corporate Boundary (cb-degrade-001) | Graceful degradation | Unreachable sources produce vault-only domain state, never errors |
| Interpersonal Transparency | Consent-gated data | No person-adjacent data in telemetry signals |
| Composable Perspectives | Independently tappable views | Each domain queryable in isolation; orientation assembles but doesn't lock |
| Design Language (section 5) | Fixed position, state via color/motion | Domain strips at fixed positions, health encoded via border color |
| Stimmung/Accommodation | Density modulation | Four-tier degradation from full to single-line |
