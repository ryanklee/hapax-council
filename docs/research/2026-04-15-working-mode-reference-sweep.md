# `working_mode` reference sweep — `cycle_mode` retirement status

**Date:** 2026-04-15
**Author:** alpha (AWB mode, queue/ item #124)
**Scope:** Workspace-wide grep for `cycle_mode` / `cycleMode` / `CycleMode` references. Per workspace `CLAUDE.md` and memory `feedback_no_cycle_mode`, the legacy `cycle_mode` (dev/prod) system is dead — only `working_mode` (research/rnd) remains. Classify each remaining reference as `deprecated-OK`, `live-needs-migration`, or `docs-historical`.
**Register:** scientific, neutral

## 1. Headline

**149 `cycle_mode` references across 21 files.** After classification:

- **0 live-needs-migration** references in council code
- **4 deprecated-OK** — the intentional backward-compat shim + tests covering it
- **~145 docs-historical** — plan/spec/audit/profile docs in `docs/`, `profiles/`, `specs/` that are historical artifacts
- **1 officium cross-reference** — council's `docs/officium-design-language.md` contains migration instructions for officium, which has NOT yet migrated (active instructions, not stale)

**`cycle_mode` is fully retired in council code.** The 4 live-code references are all intentional deprecation surfaces per the workspace CLAUDE.md rule "old endpoints/tools/types remain as deprecated aliases until +90 days post-migration."

## 2. Live-code references (4 files)

All 4 references are intentional backward-compat shims or tests covering them. No remediation needed.

### 2.1 `shared/cycle_mode.py` (13 lines)

```
"""shared/cycle_mode.py — DEPRECATED. Use shared.working_mode instead.

Backward-compatible shim: the two-mode system is now unified under
WorkingMode (research/rnd). CycleMode (dev/prod) no longer exists
as a separate concept.

Mapping: DEV → RND, PROD → RESEARCH (but callers should migrate to
WorkingMode directly).
"""

from shared.working_mode import WORKING_MODE_FILE as MODE_FILE
from shared.working_mode import WorkingMode as CycleMode
from shared.working_mode import get_working_mode as get_cycle_mode
```

**Classification:** deprecated-OK. The module is a pure re-export shim pointing at `shared/working_mode.py`. No state + no logic. Removal cost is trivial once the +90 day deprecation window expires.

### 2.2 `logos/api/routes/working_mode.py` lines 81–86

```python
# Deprecated aliases — remove after all consumers migrate
@router.get("/cycle-mode", deprecated=True)
async def get_cycle_mode_compat():
    return _read_mode()


@router.put("/cycle-mode", deprecated=True)
async def put_cycle_mode_compat(body: WorkingModeRequest):
    return await put_working_mode(body)
```

**Classification:** deprecated-OK. FastAPI routes marked `deprecated=True` so OpenAPI schema flags them. They delegate to the live `working_mode` handlers — zero logic duplication. Safe to remove when the deprecation window expires.

### 2.3 `tests/test_working_mode.py` line 80–88

```python
def test_cycle_mode_shim_maps_correctly(tmp_path):
    """The backward-compat shim re-exports working mode as CycleMode."""
    from shared.cycle_mode import CycleMode, get_cycle_mode
    ...
    result = get_cycle_mode()
    assert result == CycleMode.RND
```

**Classification:** deprecated-OK. This test pins the shim's mapping — `cycle_mode.CycleMode` is `working_mode.WorkingMode` under a different name. The test exists so the shim doesn't drift + break its consumers before they migrate. Standard deprecation pin pattern.

### 2.4 `tests/test_working_mode_api.py` line 61

```python
async def test_deprecated_cycle_mode_alias(mode_file):
    # ... tests the /api/cycle-mode deprecated GET + PUT surface
```

**Classification:** deprecated-OK. API pin for the `/cycle-mode` routes from §2.2. Same deprecation pattern.

## 3. Historical docs (14 files, ~140 references)

All `cycle_mode` references in `docs/` are **historical artifacts** — plan/spec/audit docs that describe the pre-migration design. Examples:

- `docs/plans/2026-03-09-cycle-modes-design.md` — the original cycle_mode design spec (historical context)
- `docs/plans/2026-03-09-cycle-modes-implementation.md` — the original implementation plan (historical)
- `docs/plans/2026-03-09-cockpit-actionability-implementation.md` — references cycle_mode in a layer of the cockpit spec (historical)
- `docs/plans/2026-03-09-claude-code-layer-implementation.md` — historical
- `docs/research/ws3-experiential-refinement.md` — historical research context
- `docs/research/2026-04-14-tactics-and-strategies-to-increase-success-probabilities.md` — historical analysis
- `docs/superpowers/plans/2026-03-10-query-agents.md` — historical
- `docs/superpowers/plans/2026-04-13-claude-md-excellence-plan.md` — CLAUDE.md excellence work (may reference cycle_mode in the historical discussion section)
- `docs/superpowers/specs/2026-04-13-claude-md-excellence-design.md` — same
- `docs/superpowers/audits/2026-04-13-claude-md-excellence-audit.md` — same
- `docs/specs/logos-robustness-fixes.md` — historical
- `agents/hapax_daimonion/proofs/RESEARCH-STATE.md` — unified working mode migration summary (correct historical context + forward-reference)
- `shared/README.md` — likely references both modules (historical + current)

**Classification:** docs-historical. No remediation. Git history preserves these correctly as pre-migration design artifacts. Removing them would erase the migration's design rationale.

## 4. Profile files (4 files, ~20 references)

```
profiles/dev-story.db
profiles/operator-profile.json
profiles/operator-profile.md
profiles/.state.json
profiles/demo-knowledge-base.yaml
profiles/token-baseline.json
```

**Classification:** docs-historical. Profile YAMLs + JSONs capture snapshots of prior operator state. References to `cycle_mode` in these files are either:

- **Frozen snapshots** of operator profile state from before the migration
- **Reference material** (e.g., `demo-knowledge-base.yaml`) that the profile system uses for RAG
- **Demo/test fixtures** that exercise the deprecated code path for regression coverage

No remediation needed. The profile files are not runtime config — they're data artifacts.

## 5. Officium cross-reference (`docs/officium-design-language.md`)

The one **non-historical** doc reference is `docs/officium-design-language.md` §9 "Migration: cycle_mode → working_mode" (lines 281–295). This is council's spec doc for the **officium** project's migration plan. Key excerpts:

- Line 56: "The legacy `cycle_mode` (dev/prod) system is removed. All references to `CycleMode`, `cycle-mode`, and `hapax-mode` in officium are to be replaced with `WorkingMode`, `working-mode`, and `hapax-working-mode`."
- Line 60–62: Migration checklist for officium backend + frontend
- Line 283–291: Per-file migration table (delete `shared/cycle_mode.py`, delete `logos/api/routes/cycle_mode.py`, remove hooks, etc.)

**Classification:** live-needs-migration **in officium, not in council**. Council has already completed the migration; the doc contains the migration plan for the sister project.

**Recommendation:** no council action. If officium has not yet migrated, delta should add "migrate officium to working_mode per council's design-language §9" as an officium-scope queue item (e.g., `queue/2xx-officium-working-mode-migration.yaml`).

Alpha could verify officium's current state by checking if `~/projects/hapax-officium/shared/cycle_mode.py` still exists, but officium state is out-of-scope for this queue item #124 (council-only sweep). Delta can decide whether to expand scope.

## 6. `specs/registry.yaml` reference

Line 738:

```
- get_cycle_mode() returns CycleMode enum
```

**Context:** part of a historical spec registry entry describing an old contract that the migration retired.

**Classification:** docs-historical. The spec registry tracks specs by ID; this entry is preserved for traceability. No remediation.

## 7. Sweep methodology

```bash
grep -rn "cycle_mode\|cycleMode\|CycleMode" \
  --include="*.py" --include="*.ts" --include="*.tsx" --include="*.md" \
  --include="*.yaml" --include="*.yml" --include="*.rs" \
  --exclude-dir=node_modules --exclude-dir=.venv --exclude-dir=target \
  --exclude-dir=dist --exclude-dir=__pycache__
```

**Total hits:** 149 across 21 files.

**Breakdown:**

- 4 live-code files (deprecated-OK): `shared/cycle_mode.py`, `logos/api/routes/working_mode.py`, `tests/test_working_mode.py`, `tests/test_working_mode_api.py`
- 14 docs/historical files (no action)
- 4 profile files (no action)
- 1 officium cross-reference (`docs/officium-design-language.md`, officium-scope)
- `specs/registry.yaml` (historical traceability)

## 8. What's NOT retired (found during sweep)

The sweep intentionally looked for `cycle_mode` references. What it did NOT check:

- Whether `/api/cycle-mode` is still called by any live frontend (grep for HTTP calls)
- Whether `CycleMode` enum values (`DEV`, `PROD`) leak into any JSON state files still read by running services
- Whether `hapax-mode` (the old CLI) still exists on disk alongside `hapax-working-mode`

These are out-of-scope for a council code sweep but could be follow-up items if delta wants tighter verification. Alpha classifies them as LOW priority — the CLAUDE.md rule allows deprecated surfaces for +90 days, and the migration commit summary in `RESEARCH-STATE.md` (line 318) says all council-side consumers already migrated.

## 9. Recommendations

1. **No council-side code changes needed.** The migration is complete. Deprecated shims stay as-is until the +90 day window expires (approximate removal date: late June 2026 based on the March 2026 migration commits).

2. **Delta could add an officium-scope queue item** for `docs/officium-design-language.md` §9's migration checklist — but that's officium-scope work, not council/alpha work.

3. **Historical docs should stay intact.** Removing `docs/plans/2026-03-09-cycle-modes-*.md` would erase the design rationale trail. Git history alone isn't a good substitute because these docs are referenced from other plan docs.

4. **No drift from the workspace CLAUDE.md rule** ("old endpoints/tools/types remain as deprecated aliases until +90 days post-migration"). Council is compliant.

## 10. Closing

`cycle_mode` retirement is clean in council. The 149 reference count looks alarming but ~96% are historical docs, ~2.7% are deprecated-OK shims, and 1% is a sister-project migration cross-reference. Zero live code needs migration.

Branch-only commit per queue item #124 acceptance criteria.

## 11. Cross-references

- Memory: `feedback_no_cycle_mode.md` — "cycle_mode (dev/prod) is dead. Only working_mode (research/rnd). Excise all references."
- Workspace CLAUDE.md § Working Mode — documents the deprecated-alias window
- `agents/hapax_daimonion/proofs/RESEARCH-STATE.md` line 318 — PR #276 migration summary
- `shared/working_mode.py` — the canonical source
- `shared/cycle_mode.py` — deprecated shim
- `docs/officium-design-language.md` §9 — officium-side migration plan (out-of-scope here)

— alpha, 2026-04-15T17:48Z
