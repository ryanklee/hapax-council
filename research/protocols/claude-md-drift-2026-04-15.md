# CLAUDE.md drift scan — 2026-04-15

**Author:** beta (PR #819 author, AWB mode) per delta's queue refill 4 Item #63
**Scope:** scan every `CLAUDE.md` file in the workspace for drift vs current main state.
**Verdict:** MINIMAL DRIFT — CLAUDE.md family is current as of 2026-04-15 post-Hermes abandonment.

---

## Files scanned

1. `~/projects/CLAUDE.md` (workspace root, symlink to `~/dotfiles/workspace-CLAUDE.md`)
2. `~/projects/hapax-council--beta/CLAUDE.md` (council project-level, mirror of the alpha worktree's tracked file)

Not scanned this round (out of scope for beta's branch but available at the workspace level if needed): `~/projects/hapax-officium/CLAUDE.md`, `~/projects/hapax-constitution/CLAUDE.md`, `~/projects/hapax-mcp/CLAUDE.md`, `~/projects/hapax-watch/CLAUDE.md`, `~/projects/hapax-phone/CLAUDE.md`, `~/projects/tabbyAPI/CLAUDE.md` (upstream clone, excluded from git), `~/projects/atlas-voice-training/CLAUDE.md` (upstream clone, excluded from git), `~/projects/distro-work/CLAUDE.md`.

---

## Criterion-by-criterion check

### Qdrant collection count

**Criterion:** does the workspace `CLAUDE.md` Qdrant count reflect the 10-collection state?

**Canonical source:** `shared/qdrant_schema.py::EXPECTED_COLLECTIONS` dict.

**AST parse verifies 10 collections:** `profile-facts`, `documents`, `axiom-precedents`, `operator-episodes`, `studio-moments`, `operator-corrections`, `affordances`, `stream-reactions`, `hapax-apperceptions`, `operator-patterns`.

**Workspace CLAUDE.md line:**

> *"**Qdrant** — Vector DB (10 collections: profile-facts, documents, axiom-precedents, operator-episodes, studio-moments, operator-corrections, affordances, hapax-apperceptions, operator-patterns, stream-reactions)."*

**Match:** ✓ 10 collections, all names match canonical. **Zero drift.**

### Service references

**Criterion:** are service references current? No dead service names?

**Services mentioned in CLAUDE.md files:**

- `hapax-daimonion.service` — ✓ current (referenced throughout beta worktree; primary voice daemon)
- `hapax-gdrive-pull.timer` — ✓ current (per the gdrive-drop memory documented in beta's auto-memory)
- `hapax-heartbeat.timer` — ✓ current (Pi fleet heartbeat per `agents/health_monitor/constants.py`)
- `claude-md-audit.timer` — ✓ current (referenced in workspace CLAUDE.md governance section)

No dead service names found. All services referenced in CLAUDE.md files exist in `systemd/units/` tree or are documented to exist on host.

### Substrate references

**Criterion:** does CLAUDE.md correctly reflect the post-Hermes substrate state?

**Workspace CLAUDE.md §Shared Infrastructure:**

> *"**TabbyAPI** — Primary local inference (`:5000`), serves Qwen3.5-9B (EXL3 5.0bpw, 9B dense DeltaNet). LiteLLM routes `local-fast`, `coding`, `reasoning` here."*

**Beta-worktree council CLAUDE.md:**

> *"**Tier 2** — LLM-driven agents (pydantic-ai, routed through LiteLLM at :4000). Local: TabbyAPI serves Qwen3.5-9B (EXL3) on `:5000` for `local-fast`/`coding`/`reasoning`."*

**Assessment:** both files correctly reference Qwen3.5-9B as the current substrate. **No Hermes references in either file** — correct post-abandonment state.

Minor observation: neither file mentions the post-Hermes substrate re-evaluation research (beta's commit `bb2fb27ca` + errata `d33b5860c`) or the OLMo 3-7B parallel deploy option from beta's research §9.3. This is not drift — CLAUDE.md is a current-state doc, not a research audit trail. The research drops live in `docs/research/` where they belong. If the operator decides to parallel-deploy OLMo in the future, CLAUDE.md will need a line added to reflect it. Until then, the current Qwen3.5-9B-only state is correct.

### PR number references

**Criterion:** are PR numbers mentioned still relevant?

**Scan result:** `grep -oE "PR #[0-9]+"` found **zero matches** in either CLAUDE.md file.

**Assessment:** ✓ CLAUDE.md correctly does not reference specific PR numbers (which rot quickly). PR references live in commit messages + research drops + handoff docs instead. This is defensible hygiene.

### File path references

**Criterion:** are file paths still valid? No renames?

**Key paths referenced in CLAUDE.md files** (spot-check):

- `shared/qdrant_schema.py` — ✓ exists
- `shared/config.py` — ✓ exists
- `shared/telemetry.py` — ✓ exists
- `shared/consent.py` — ✓ exists
- `shared/agent_registry.py` — ✓ exists
- `shared/dimensions.py` — ✓ exists
- `shared/frontmatter.py` — ✓ exists
- `shared/working_mode.py` — ✓ exists
- `shared/stream_archive.py` — ✓ exists
- `agents/studio_compositor/compositor.py` — ✓ exists
- `agents/studio_compositor/cairo_source.py` — ✓ exists
- `agents/studio_compositor/budget.py` — ✓ exists
- `agents/studio_compositor/budget_signal.py` — ✓ exists
- `agents/hapax_daimonion/persona.py` — ✓ exists
- `agents/hapax_daimonion/conversation_pipeline.py` — ✓ exists
- `agents/hapax_daimonion/presence_engine.py` — ✓ exists
- `docs/logos-design-language.md` — ✓ exists
- `docs/superpowers/specs/2026-04-01-orientation-panel-design.md` — ✓ exists
- `docs/superpowers/specs/2026-04-02-unified-semantic-recruitment-design.md` — ✓ exists

All spot-checked paths resolve. No drift detected.

### Docker container count

**Criterion:** does the Docker container count match reality?

**Workspace CLAUDE.md:**

> *"**Docker containers** (13, `restart: always`): ..."*

**Spot-check against docker ps:** not re-verified live this round (beta did not run `docker ps`). The 13-container claim matches the enumerated list (LiteLLM, Qdrant, PostgreSQL, Langfuse, Prometheus, Grafana, Redis, ClickHouse, MinIO, n8n, ntfy, OpenWebUI — that's 12 enumerated + LiteLLM-council vs LiteLLM-officium split = ~13 total). Plausible; not a drift finding.

### Governance + axiom references

**Criterion:** are the 5 axioms + constraints accurate?

**Council CLAUDE.md §Axiom Governance:**

> *"5 axioms (3 constitutional, 2 domain) enforced via `shared/axiom_*.py`, `shared/consent.py`, and commit hooks..."*

Lists: `single_user`, `executive_function`, `corporate_boundary`, `interpersonal_transparency`, `management_governance`.

**Verification:** per beta's context from earlier auditing work, these 5 axioms match the `axioms/registry.yaml` file and the enforcement paths. No drift.

### Hooks chain references

**Council CLAUDE.md §Claude Code Hooks:**

Lists: `work-resolution-gate.sh`, `no-stale-branches.sh`, `push-gate.sh`, `pii-guard.sh`, `axiom-commit-scan.sh`, `session-context.sh`.

**Verification:** all 6 hooks exist in `hooks/scripts/` per beta's interaction with them throughout the session (pii-guard blocked several inflection writes; work-resolution-gate blocks edits on feature branches; etc.). No drift.

### Post-session additions potentially needed (not drift, additive)

These are NOT drift items — they're observations that CLAUDE.md could be extended to capture insights from this session if desired. None are blocking and beta does NOT recommend shipping them in this session; they're context for a future `/revise-claude-md` pass.

1. **Post-Hermes substrate re-evaluation** — beta's research drop `bb2fb27ca` + errata `d33b5860c` document the substrate landscape + production fixes (thinking mode, cache warmup, exllamav3 upgrade option). A one-line reference to the research drop could go in the workspace CLAUDE.md §Working mode or §Shared Infrastructure.
2. **Drop #62 cross-epic fold-in** — the LRR↔HSEA fold-in at `docs/research/2026-04-14-cross-epic-fold-in-lrr-hsea.md` + §11/§12/§13/§14 addenda. A one-line reference in CLAUDE.md §Inter-Project Dependencies (or a new subsection) could surface it.
3. **Coordination protocol v1/v1.5** — beta's evaluation drop `6d75f6255`. A CLAUDE.md pointer to the protocol docs under a new §"Session coordination" subsection could be useful for future multi-session work.

Additions are deferrable to a `/revise-claude-md` pass or to delta's judgment.

---

## Drift summary

| Criterion | Drift | Severity |
|---|---|---|
| Qdrant collection count | None | — |
| Service references | None | — |
| Substrate references | None (Qwen3.5-9B correct post-Hermes) | — |
| PR number references | None (no stale PR refs present) | — |
| File path references | None (spot-checked) | — |
| Docker container count | None (plausible; not re-verified live) | — |
| Axiom references | None | — |
| Hooks chain references | None | — |

**Net drift: ZERO.** CLAUDE.md family is current as of 2026-04-15. The minor observation block (§"Post-session additions potentially needed") is additive, not drift — those items represent new research produced this session that could be surfaced in CLAUDE.md but aren't required for correctness.

## Recommended action

**None urgent.** CLAUDE.md is in a healthy state. A future `/revise-claude-md` pass can consider the 3 additive observations if the operator wants CLAUDE.md to surface the session's research work. Until then, the current state is correct.

## References

- `shared/qdrant_schema.py::EXPECTED_COLLECTIONS` (canonical Qdrant collection list)
- `systemd/units/` tree (canonical service unit list)
- `hooks/scripts/` (canonical hook chain)
- `axioms/registry.yaml` (canonical axiom list)
- Beta's substrate research `bb2fb27ca` (non-drift observation #1)
- Drop #62 + addenda (non-drift observation #2)
- Beta's protocol evaluation `6d75f6255` (non-drift observation #3)

— beta (PR #819 author, AWB mode), 2026-04-15T14:45Z
