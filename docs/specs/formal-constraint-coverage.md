# Formal Constraint Coverage — System-Wide Formalization

Bring the ~60% of the hapax system currently under convention-based governance
into formal constraint, where the domain benefits from it.

**Status:** Design
**Scope:** hapax-council, hapax-officium, hapax-mcp, hapax-watch, hapax-constitution
**Depends on:** Axiom governance (merged), voice composition ladder (proven), design language (merged)

---

## 1. Problem

The hapax system operates under two regimes: a formally verified core (voice daemon,
consent algebra, deontic consistency checker) and a convention-based periphery
(reactive engine, agent contracts, filesystem bus, configuration, wire protocols).
The convention-based portion accounts for ~60% of the system by surface area.

Specific failure modes observed or structurally possible:

- **Silent schema drift**: Officium filesystem bus accepts any YAML frontmatter on write.
  A misspelled key (`stauts` instead of `status`) propagates undetected until a reader
  silently defaults it. No failure signal.
- **Unguarded agent output**: 143 `.write_text()` calls in council agents lack axiom
  enforcement. Only `briefing.py` calls `enforce_output()`. An LLM-generated output
  violating T0 implications (e.g., feedback language) would persist unchecked.
- **Configuration fragility**: 61 environment variables across both projects, parsed via
  manual `int()`/`float()` casts with bare defaults. A typo in an env var name silently
  falls back to default. No startup validation.
- **Type system disabled**: Pyright installed but running in "basic" mode with all
  `report*` checks set to `false`. The type annotations exist but are not enforced.
- **Wire protocol mismatch**: Watch client sends `ts` in voice-trigger payloads; server
  silently drops it. 4 fields exist server-side that the client cannot populate.
- **Reactive engine opacity**: 14 rules execute as ad-hoc callbacks with implicit phase
  ordering. No formal contracts on rule preconditions, postconditions, or phase
  transition invariants.

## 2. Non-Goals

- Formalizing LLM prompt content (irreducibly natural language)
- Formalizing agent *input* schemas (agents accept natural language by design)
- Replacing the canon/precedent system with machine-checkable logic
  (interpretive flexibility is a feature)
- Full formal verification of the reactive engine (FSM modeling is sufficient)
- Strict-mode pyright in a single pass (incremental tightening)

## 3. Design

Six workstreams, ordered by leverage. Each is independently deployable.

### 3.1 Typed Configuration (pydantic-settings)

**Current state:** 61 env vars, `os.getenv()` with manual casts, zero validation.

**Target state:** A single `Settings` model per project, validated at import time.

```
shared/settings.py (new)
├── CouncilSettings(BaseSettings)
│   ├── litellm: LiteLLMSettings          # base_url, api_key
│   ├── qdrant: QdrantSettings             # url
│   ├── ollama: OllamaSettings             # host
│   ├── langfuse: LangfuseSettings         # host, public_key, secret_key
│   ├── ntfy: NtfySettings                 # base_url, topic, dedup_cooldown_s
│   ├── engine: EngineSettings             # debounce_ms, gpu_concurrency, ...
│   ├── paths: PathSettings                # home, vault_path, profiles_dir
│   ├── logging: LogSettings               # level, human, service_name
│   └── governance: GovernanceSettings     # axiom_enforce_block
└── model_config = SettingsConfigDict(env_nested_delimiter="__")
```

**Validation rules:**
- URLs: `AnyHttpUrl` type with scheme enforcement
- Ports: `int` with `ge=1, le=65535`
- Secrets: `SecretStr` for API keys (prevents accidental logging)
- Booleans: Pydantic's native bool parsing (accepts "true"/"1"/"yes")
- Paths: `DirectoryPath` / `FilePath` where the path must exist at startup
- Engine numerics: bounds matching current ad-hoc defaults (e.g., `debounce_ms: int = Field(ge=50, le=10000, default=1500)`)

**Startup behavior:** `settings = CouncilSettings()` at module level in `shared/settings.py`.
Import-time crash on invalid config (fail-fast). All existing `os.getenv()` calls
replaced with `settings.X.field` references.

**Migration:** Officium gets `OfficiumSettings(BaseSettings)` with the same pattern.
Shared fields (LiteLLM, Qdrant, Langfuse) use the same nested model classes, different
defaults (different ports).

### 3.2 Filesystem Bus Schemas (officium)

**Current state:** 13 document types with ad-hoc YAML frontmatter. No write-time
validation. Defensive coercion on read.

**Target state:** Pydantic models for each document type. Validated on write.
Readers consume typed models instead of raw dicts.

```
shared/vault_schemas.py (new)
├── VaultDocBase(BaseModel)
│   ├── type: str                          # discriminator
│   ├── date: date | None = None
│   └── model_config: extra="ignore"
├── PersonDoc(VaultDocBase)
│   ├── type: Literal["person"]
│   ├── name: str
│   ├── team: str
│   ├── role: str
│   ├── cadence: Literal["weekly", "biweekly", "monthly"]
│   ├── status: Literal["active", "inactive"] = "active"
│   ├── last_1on1: date | None = None      # alias "last-1on1"
│   ├── cognitive_load: Literal["low","moderate","medium","high","critical"] | None
│   └── ... (all 20 fields, typed)
├── CoachingDoc(VaultDocBase)
├── FeedbackDoc(VaultDocBase)
├── MeetingDoc(VaultDocBase)
├── DecisionDoc(VaultDocBase)
├── GoalDoc(VaultDocBase)
├── OkrDoc(VaultDocBase)
│   └── key_results: list[KeyResult]       # nested model
├── IncidentDoc(VaultDocBase)
├── PostmortemActionDoc(VaultDocBase)
├── ReviewCycleDoc(VaultDocBase)
├── StatusReportDoc(VaultDocBase)
├── PrepDoc(VaultDocBase)
└── ReferenceDoc(VaultDocBase)
```

**Write path:** `vault_writer._write_md()` gains a `schema: type[VaultDocBase] | None`
parameter. When provided, frontmatter dict is validated via `schema.model_validate(fm)`
before YAML dump. Validation error → raise, not silent fallback.

**Read path:** Collectors gain a `_parse_typed(path, schema)` helper that returns a
typed model instead of a raw dict. Defensive coercion code removed — Pydantic handles
type coercion. Unknown `type` values fall through to `VaultDocBase` (forward-compatible).

**Field aliases:** Pydantic `Field(alias="last-1on1")` for hyphenated YAML keys.
`model_config = ConfigDict(populate_by_name=True)` so both forms work.

**Migration:** Existing documents are not modified. The models use `Optional` with
defaults for all non-required fields. A one-time `vault_validate.py` script scans
all existing documents and reports violations without modifying them.

### 3.3 Runtime Axiom Enforcement

**Current state:** `enforce_output()` exists but is called by 1 of ~20 agents.
`check_fast()` runs in voice governor only. 8 enforcement patterns defined.

**Target state:** All agent output passes through enforcement. No new code path
needed — wire existing infrastructure into the agent execution boundary.

**Architecture:**

```
Agent.run()
  └── pydantic-ai output_type validation (existing)
       └── enforce_output(agent_id, text)     ← NEW: universal gate
            ├── check_output(text)            # pattern matching (existing)
            ├── _is_excepted(agent_id, ...)   # exception check (existing)
            ├── T0 violation → quarantine + block (if AXIOM_ENFORCE_BLOCK=1)
            ├── T1 violation → audit log
            └── clean → pass through
```

**Implementation approach — GovernorWrapper integration:**

`shared/governance/governor.py` already implements a per-agent governance wrapper with
output policy checking. The gap is that most agents don't use it.

New: `shared/governance/enforced_agent.py`:
```python
async def run_enforced(
    agent: Agent[D, R],
    prompt: str,
    *,
    agent_id: str,
    deps: D | None = None,
) -> R:
    """Run a pydantic-ai agent with mandatory axiom enforcement on output."""
    result = await agent.run(prompt, deps=deps)
    text = _extract_text(result.output)  # model_dump() or str()
    enforce_output(agent_id, text)       # raises on T0 if blocking enabled
    return result.output
```

All agents that produce text output migrate from `agent.run()` to `run_enforced()`.
Agents producing only structured data (no natural language) are exempt.

**Pattern expansion:** Add patterns for all 5 axioms (currently only 3 covered):
- `interpersonal_transparency`: detect persistent person-state without consent contract
- `corporate_boundary`: detect employer-system URLs/hostnames in output

**Reactive engine enforcement:** Phase 2 (cloud LLM) rule handlers that produce text
gain `enforce_output()` calls. Phase 0/1 rules are deterministic and exempt.

### 3.4 Reactive Engine Phase Contracts

**Current state:** 3 phases (0=deterministic, 1=GPU, 2=cloud LLM), strict barriers,
but rules are untyped `(filter_fn, produce_fn)` tuples. Phase assignment is implicit
in the `Action.phase` field set by each rule's produce function.

**Target state:** Typed rule protocol with explicit phase declaration and
pre/postcondition contracts.

**Rule protocol:**

```python
@dataclass(frozen=True)
class RuleSpec:
    """Formal rule declaration — replaces ad-hoc tuples."""
    id: str
    phase: Phase                           # Phase.DETERMINISTIC | GPU | CLOUD
    trigger: Callable[[ChangeEvent], bool]
    produce: Callable[[ChangeEvent], list[Action]]
    cooldown_s: float = 0
    quiet_window_s: float = 0
    doc_types: frozenset[str] = frozenset() # empty = all types
    directories: frozenset[str] = frozenset()
    axiom_exempt: bool = False             # if True, skip enforce_output on actions

class Phase(IntEnum):
    DETERMINISTIC = 0
    GPU = 1
    CLOUD = 2
```

**Phase contract invariants** (enforced by RuleRegistry):
1. A rule's `produce()` may only return `Action` objects with `phase <= rule.phase`
   (a deterministic rule cannot schedule GPU work)
2. Phase barriers: all phase N actions complete before phase N+1 starts (existing,
   now documented as invariant)
3. Within a phase, actions execute in priority order (ascending), concurrency bounded
   by phase semaphore (existing)
4. `depends_on` references must name actions in the same or earlier phase
   (cross-phase forward dependencies are illegal)

**Validation:** `RuleRegistry.register(spec)` validates:
- Unique rule ID
- Phase is a valid `Phase` enum member
- No duplicate registrations
- `doc_types` and `directories` are non-overlapping with other rules at same phase
  (advisory warning, not blocking — multiple rules can match the same event)

**Migration:** Existing rules in `reactive_rules.py` are wrapped in `RuleSpec` objects.
The `Rule` dataclass in `models.py` is replaced. `build_default_rules()` returns
`list[RuleSpec]` instead of `list[Rule]`.

### 3.5 Pyright Incremental Tightening

**Current state:** "basic" mode, all `report*` checks disabled. Violation count unknown
(baseline measurement blocked).

**Target state:** "standard" mode with progressive enablement.

**Phased rollout:**

| Phase | Checks enabled | Target |
|-------|---------------|--------|
| P1 | `reportMissingImports: true`, `reportMissingTypeStubs: true` | Import hygiene |
| P2 | `reportReturnType: true`, `reportArgumentType: true` | Call-site correctness |
| P3 | `reportCallIssue: true`, `reportAssignmentType: true` | Full standard |
| P4 | `typeCheckingMode: "standard"` | Drop explicit overrides |

**Process:** Each phase:
1. Enable the checks in `pyrightconfig.json`
2. Run `uv run pyright` to measure violations
3. Fix violations (prioritize `shared/` and `logos/` — agent code last)
4. Commit, move to next phase

**CI integration:** Add pyright to the GitHub Actions test matrix. Initially
`continue-on-error: true` (non-blocking). Promote to blocking after P3.

**Officium follows council** — same phases, same cadence, separate PRs.

### 3.6 Wire Protocol Contracts (watch ↔ council)

**Current state:** Kotlin `@Serializable` data classes on client, Pydantic models on
server. No shared schema. 4 known mismatches.

**Target state:** Shared JSON Schema files checked into both repos. Mismatches resolved.

**Schema location:** `hapax-council/schemas/watch/` (single source of truth)

```
schemas/watch/
├── sensor-payload.schema.json
├── sensor-reading.schema.json
├── voice-trigger.schema.json
├── gesture.schema.json
├── health-summary.schema.json
├── phone-context.schema.json
└── VERSION                         # semver, bumped on breaking changes
```

**Generation:** Pydantic models → JSON Schema via `model_json_schema()`. The server
models are authoritative. Schemas are committed artifacts (not generated at build time)
so the watch project can reference them without a Python dependency.

**Kotlin consumption:** The watch project reads schemas for documentation and test
validation. Kotlin serialization codec is the actual runtime contract — schemas serve
as the alignment checkpoint.

**Mismatch resolution:**

| Mismatch | Resolution |
|----------|------------|
| Voice-trigger `ts` ignored | Add `ts: int \| None` to server `VoiceTriggerPayload`. Use client timestamp when present, fall back to server clock. |
| EDA fields missing from client | No change needed — fields are optional. Add Kotlin TODO for future EDA sensor integration. |
| Battery always null | No schema change — client-side implementation issue. Track as watch backlog. |
| Health summary no precise time | Add optional `ts: int \| None` to `HealthSummaryPayload` for precise timing. |

**Versioning:** `VERSION` file contains `MAJOR.MINOR.PATCH`. Breaking changes
(required field added, field removed, type changed) bump MAJOR. Additive changes
(new optional field) bump MINOR. Documentation-only changes bump PATCH.

## 4. Cross-Cutting Concerns

### 4.1 Testing Strategy

Each workstream adds tests appropriate to its formality level:

| Workstream | Test type | Location |
|------------|-----------|----------|
| 3.1 Config | Unit: validate happy path, missing required, invalid types | `tests/test_settings.py` |
| 3.2 Bus schemas | Unit: validate each doc type, reject malformed | `tests/test_vault_schemas.py` (officium) |
| 3.3 Axiom enforcement | Integration: agent output blocked on T0 | `tests/test_enforcement_integration.py` |
| 3.4 Engine contracts | Unit: phase invariant violations, rule registration | `tests/test_engine_contracts.py` |
| 3.5 Pyright | CI gate (initially non-blocking) | `.github/workflows/typecheck.yml` |
| 3.6 Wire schemas | Unit: JSON Schema validates sample payloads | `tests/test_watch_schemas.py` |

### 4.2 Rollback Safety

All workstreams are additive. No existing behavior changes until the new code
is proven:

- **Config:** Old `os.getenv()` calls coexist with `settings.X` during migration.
  Feature flag: `HAPAX_USE_SETTINGS=1` to enable new path.
- **Bus schemas:** `schema` parameter defaults to `None` (no validation). Opt-in per
  write function.
- **Axiom enforcement:** `AXIOM_ENFORCE_BLOCK` remains `0` (audit-only) until
  confidence established.
- **Engine contracts:** `RuleSpec` wraps existing functions — no behavioral change until
  invariant checking is enabled via `ENGINE_STRICT_PHASES=1`.
- **Pyright:** `continue-on-error: true` in CI.
- **Wire schemas:** Schema files are documentation artifacts. No runtime behavior change.

### 4.3 Dependency Order

```
3.1 Config ──────────────────────► (no deps, pure addition)
3.2 Bus schemas ─────────────────► (no deps, pure addition)
3.3 Axiom enforcement ───────────► depends on 3.1 (reads AXIOM_ENFORCE_BLOCK from settings)
3.4 Engine contracts ────────────► depends on 3.3 (enforcement in phase 2 handlers)
3.5 Pyright ─────────────────────► depends on 3.1, 3.2 (new code must type-check)
3.6 Wire schemas ────────────────► (no deps, pure addition)
```

Workstreams 3.1, 3.2, and 3.6 can execute in parallel.
Workstream 3.3 follows 3.1.
Workstream 3.4 follows 3.3.
Workstream 3.5 follows 3.1 + 3.2 (so new models are included in the check).

## 5. Success Criteria

| Metric | Before | After |
|--------|--------|-------|
| Write-time validated document types (officium) | 0/13 | 13/13 |
| Agent outputs passing through enforcement | 1/~20 | ~20/~20 |
| Env vars with schema validation | 0/61 | 61/61 |
| Reactive engine rules with typed contracts | 0/14 | 14/14 |
| Pyright mode | basic (disabled) | standard (CI-gated) |
| Cross-repo wire schemas | 0 | 6 (all watch endpoints) |
| Axiom enforcement patterns covering all axioms | 3/5 | 5/5 |

## 6. Resolved Questions

1. **Pyright baseline**: 414 errors at basic mode, 447 at standard (+33 new errors).
   The delta is small — standard mode is achievable without a major remediation effort.
   The 414 existing errors are the real work; the mode change adds only 8% more.

2. **Officium engine alignment**: Both engines share Rule/Action/ActionPlan structure.
   Differences: council has 3 phases (deterministic/GPU/cloud) vs officium's 2
   (deterministic/LLM); council has per-rule cooldown, officium does not; council's
   ChangeEvent includes frontmatter enrichment. A shared `RuleSpec` is viable with
   optional `cooldown_s` field and phase-as-semantic-label (Phase enum values are
   project-specific). Shared types should live in `hapax-sdlc` (both projects already
   depend on it). Each project keeps its own executor and rule definitions.

3. **Enforcement in audit-only mode**: 2 weeks of clean audit logs before promoting
   to blocking. Confirmed as reasonable — the quarantine mechanism already exists
   and `AXIOM_ENFORCE_BLOCK` flag is wired.

4. **Bus schema strictness**: Use `extra="ignore"` (not `forbid`). Research confirmed:
   organic field growth through agent code is the normal evolution pattern (e.g.,
   `meeting_lifecycle.py` adds `week`, `source`, `tags` fields not in `vault_writer`).
   Readers already use `.get()` defensively. `forbid` would require schema updates
   before any agent feature that touches frontmatter — friction with zero safety gain.

## 7. Open Questions (remaining)

None. All design questions resolved. Ready for implementation planning.
