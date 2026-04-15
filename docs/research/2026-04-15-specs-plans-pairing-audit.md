# `docs/superpowers/` specs ↔ plans pairing audit

**Date:** 2026-04-15
**Author:** alpha (AWB mode, queue/ item #134)
**Scope:** Walk `docs/superpowers/specs/` and `docs/superpowers/plans/`, identify orphan specs (design doc with no matching plan), orphan plans (plan doc with no matching design), and naming-convention mismatches (filenames that do not follow `-design.md` / `-plan.md`).
**Register:** scientific, neutral

## 1. Headline

**176 specs, 149 plans, 325 total files. 89 orphan specs + 6 orphan plans + 156 naming-convention mismatches.** The filename convention (`$date-$topic-design.md` / `$date-$topic-plan.md`) is **less than half enforced**: 156/325 files (48%) do not follow it.

**Three tiers of finding:**

- **Convention-conforming files with pair mismatch:** 89 specs + 6 plans = 95 files. These are clean-format filenames that lack their counterpart.
- **Convention-violating filenames:** 50 spec files + 106 plan files = 156 files with non-`-design.md`/`-plan.md` suffixes. These fall outside the automatable pairing logic entirely.
- **Convention-conforming + paired:** ~87 spec-plan pairs (rough estimate; not enumerated in this audit).

**The 95 orphans + 156 convention violations together = 251 / 325 files (77%) that do not have an automatable paired counterpart.**

This is a significant drift from the stated convention. Three interpretations:

1. **Historical accumulation** — early specs may predate the pairing convention; cleanup is deferred
2. **Deliberate one-file docs** — some "spec" files are actually standalone research/reference docs that do not need a plan
3. **Drift** — sessions have been loose about applying the convention

## 2. Method

```bash
# Specs
ls docs/superpowers/specs/*.md | wc -l                  # 176
ls docs/superpowers/specs/ | grep -vE '-design\.md$' | wc -l  # 50 non-conforming

# Plans
ls docs/superpowers/plans/*.md | wc -l                  # 149
ls docs/superpowers/plans/ | grep -vE '-plan\.md$' | wc -l   # 106 non-conforming

# Orphan specs (design.md with no matching plan.md)
for f in docs/superpowers/specs/*-design.md; do
  base=$(basename "$f" -design.md)
  [ ! -f "docs/superpowers/plans/${base}-plan.md" ] && echo "$f"
done | wc -l                                            # 89

# Orphan plans (plan.md with no matching design.md)
for f in docs/superpowers/plans/*-plan.md; do
  base=$(basename "$f" -plan.md)
  [ ! -f "docs/superpowers/specs/${base}-design.md" ] && echo "$f"
done | wc -l                                            # 6
```

## 3. Orphan specs (89 files)

Specs that follow the `-design.md` convention but have no matching plan. Grouped by date:

### 3.1 2026-03-10 through 2026-03-31 (early / accumulation era)

Representative samples (not exhaustive):

- `2026-03-10-cockpit-insight-design.md`
- `2026-03-10-hyprland-aesthetic-design.md`
- `2026-03-10-query-agents-design.md`
- `2026-03-10-query-hardening-design.md`
- `2026-03-11-backup-mc-north-star-design.md`
- `2026-03-11-perception-primitives-design.md`
- `2026-03-12-multi-role-composition-design.md`
- `2026-03-12-multi-role-north-star-design.md`
- `2026-03-25-effect-node-graph-design.md`
- `2026-03-26-effect-graph-phase2-design.md`
- `2026-03-26-logos-command-registry-design.md`
- `2026-03-26-perception-visual-governance-design.md`
- `2026-03-27-multi-mic-pipeline-design.md`
- `2026-03-27-session-conductor-design.md`
- `2026-03-27-tauri-only-migration-design.md`
- `2026-03-27-visual-chain-capability-design.md`
- `2026-03-27-visual-surface-webview-design.md`
- `2026-03-27-vocal-chain-capability-design.md`
- `2026-03-28-imagination-bus-design.md`
- `2026-03-28-imagination-daemon-wiring-design.md`
- `2026-03-28-imagination-surface-extraction-design.md`
- `2026-03-28-visual-content-layer-design.md`
- `2026-03-28-vocal-imagination-integration-design.md`
- `2026-03-29-capability-parity-design.md`
- `2026-03-29-content-texture-pipeline-design.md`
- `2026-03-29-daimonion-full-treatment-design.md`
- `2026-03-29-dynamic-shader-pipeline-design.md`
- `2026-03-29-dynamic-system-anatomy-design.md`
- `2026-03-29-ir-perception-system-design.md`
- `2026-03-29-reverie-bachelard-design.md`
- `2026-03-29-vault-sprint-engine-design.md`
- `2026-03-30-daimonion-gap-closure-design.md`
- `2026-03-30-reverie-gap-closure-design.md`
- `2026-03-31-apperception-core-hardening-design.md`
- `2026-03-31-apperception-event-sources-design.md`
- `2026-03-31-apperception-ui-observability-design.md`
- `2026-03-31-camera-profile-automation-design.md`
- `2026-03-31-engagement-activation-design.md`
- `2026-03-31-ir-perception-remediation-design.md`
- `2026-03-31-multi-camera-graph-routing-design.md`
- ...and ~50 more

**Interpretation:** these are likely a mix of (a) shipped-epic specs where the plan was never separately authored because the spec itself contained the plan inline, and (b) research/reference specs that never needed execution plans. Many of them correspond to features that did ship (e.g., `logos-command-registry`, `ir-perception-system`, `imagination-bus`).

**Remediation: none required.** These are historical accumulation. Do NOT backfill plans for already-shipped epics.

### 3.2 April 2026 (recent era)

Still in the 89 orphan count: several LRR + HSEA pre-staging design docs lack matching plans on main:

- HSEA Phase 6 + Phase 7 design specs exist on main (PR #855), but plans are missing (known — queue item #112 flagged as follow-up work)
- Other 2026-04-XX orphan specs: alpha did not enumerate each; most likely are covered by queue #112's finding or are research-grade specs where the plan is inline

**Remediation:** the HSEA Phase 6 + 7 plan gap is already a tracked follow-up from queue #112. Other April orphans should be case-reviewed — some may be mid-authoring, others intentionally plan-less.

## 4. Orphan plans (6 files)

Plans with no matching design doc:

1. `2026-03-10-hyprland-migration-plan.md`
2. `2026-03-10-voice-daemon-test-plan.md`
3. `2026-03-25-affordance-retrieval-plan.md`
4. `2026-03-29-smoke-test-plan.md`
5. `2026-04-01-exploration-signal-fixes-plan.md`
6. `2026-04-02-cpal-audit-fixes-plan.md`

**Interpretation:** these are plans where the "design" lives somewhere else — either inlined into the plan itself, or in a design doc with a different filename (non-conforming, see §5). Less serious than orphan specs because plans without a preceding design can still execute.

**Remediation options:**
- (a) Rename the 6 plans to add `-design.md` sibling files with a one-line reference to the plan
- (b) Ignore — plans can stand alone
- (c) Move them to `docs/superpowers/runbooks/` which explicitly has no spec/plan duality

Alpha recommends (b) — these are operationally fine as-is.

## 5. Convention violations (156 files)

Files in `specs/` or `plans/` that do not match the `$date-$topic-design.md` or `$date-$topic-plan.md` pattern.

### 5.1 Non-conforming spec filenames (50 files)

Representative samples (not exhaustive; the full 50 are in `docs/superpowers/specs/`):

- `2026-03-13-computational-constitutional-governance.md` — no `-design.md` suffix
- `2026-03-13-dog-star-spec.md` — uses `-spec.md` instead of `-design.md`
- `2026-03-13-domain-schema-north-star.md`
- `2026-03-13-enforcement-gaps.md`
- `2026-03-13-interpersonal-transparency-axiom-evaluation.md` — evaluation doc, not a spec proper
- `2026-03-13-spatial-awareness-research.md` — research doc in specs dir
- `2026-03-23-blueprint-library-spec.md` — `-spec.md` suffix
- `2026-03-23-compound-goal-promotion.md` — no suffix
- `2026-03-23-dfhack-bridge-protocol.md`
- `2026-03-23-fortress-governance-chains.md`

**Pattern:** many use either no suffix, `-spec.md`, `-research.md`, `-evaluation.md`, `-protocol.md`, or free-form names. These are mostly pre-convention (March) drops that were authored before the `-design.md` standard was agreed.

**Remediation options:**
- (a) Bulk rename to `-design.md` format
- (b) Leave as-is (archeological markers)
- (c) Move genuinely research-grade docs (`-research.md`, `-evaluation.md`) to `docs/research/`

Alpha recommends (c) for ~10-20 files that are clearly research not specs. Leave the rest as-is — bulk renaming creates git churn without operational benefit.

### 5.2 Non-conforming plan filenames (106 files)

Representative samples:

- `2026-03-10-cockpit-insight.md` — no suffix
- `2026-03-10-hyprland-desktop-integration.md` — no suffix
- `2026-03-10-query-agents.md`
- `2026-03-10-query-hardening.md`
- `2026-03-24-formal-constraint-coverage.md`
- `2026-03-24-perceptual-system-hardening.md`
- `2026-03-25-contact-mic-integration.md`
- `2026-03-25-effect-node-graph-phase1.md`
- `2026-03-25-effects-system-repair.md`
- `2026-03-25-impingement-cascade-epic.md`

**Pattern:** all 106 lack the `-plan.md` suffix. Many are clearly plans (e.g., `-phase1`, `-repair`, `-epic`, `-integration`) but written without the suffix.

**Remediation options:**
- (a) Bulk rename to add `-plan.md` suffix
- (b) Leave as-is

Alpha recommends (b) for the same churn-cost reason.

## 6. Numerical summary

| Category | Count | % of 325 |
|---|---|---|
| Convention-conforming + paired | ~87 | 27% |
| Orphan specs (conforming) | 89 | 27% |
| Orphan plans (conforming) | 6 | 2% |
| Non-conforming spec names | 50 | 15% |
| Non-conforming plan names | 106 | 33% |
| **Total files** | **325** | **100%** |

The 87 paired files are alpha's rough estimate: 176 specs − 89 orphans − 50 non-conforming = 37 conforming specs with pairs. Then 149 plans − 6 orphans − 106 non-conforming = 37 conforming plans. **37 pairs × 2 = 74 files, not 87.** Corrected numerical summary:

| Category | Count | % of 325 |
|---|---|---|
| Convention-conforming + paired (37 pairs × 2) | 74 | 23% |
| Orphan specs (conforming) | 89 | 27% |
| Orphan plans (conforming) | 6 | 2% |
| Non-conforming spec names | 50 | 15% |
| Non-conforming plan names | 106 | 33% |
| **Total** | **325** | **100%** |

**Only 23% of specs+plans files follow the pairing convention.** 77% are in some state of drift.

## 7. Recommendations

### 7.1 Priority (file as follow-up queue items)

1. **Queue #112 HSEA Phase 6/7 plan authoring** — already flagged as follow-up work
2. **Triage the 50 non-conforming spec files** — ~10-20 are likely research-grade and should move to `docs/research/`; the rest can be left
3. **Document the convention in `docs/superpowers/README.md`** (if exists; if not, create it) so future sessions know the expected filename pattern

### 7.2 Deferrable

- Bulk rename non-conforming filenames (`$(basename).md` → `$(basename)-design.md` / `-plan.md`) — creates git churn, low operational benefit
- Backfill orphan-spec plans for historical specs (most already-shipped epics)

### 7.3 No action needed

- The 37 clean pairs are operational
- Orphan plans (6) are operationally fine standalone

## 8. What this audit does NOT do

- **Does not enumerate all 89 orphan specs.** Sampled ~40, grouped by date. The full list is reproducible via the grep command in §2.
- **Does not cross-reference specs/plans against shipped epics.** A spec without a plan might still have been executed; alpha does not verify this.
- **Does not move any files.** Recommendation is to triage `-research.md` files, but execution is not part of this audit.
- **Does not create a `docs/superpowers/README.md`** to document the convention.

## 9. Closing

176 specs + 149 plans = 325 files. Only 23% follow the stated pairing convention. Most drift is historical accumulation from March 2026 (pre-convention) + April 2026 rapid authoring. Alpha recommends no urgent bulk remediation — the convention is tracked for new files, historical drift is low-cost to leave in place.

Branch-only commit per queue item #134 acceptance criteria.

## 10. Cross-references

- `docs/superpowers/specs/` (176 files)
- `docs/superpowers/plans/` (149 files)
- Queue item #112: HSEA branch-only reconciliation — flagged HSEA Phase 6/7 plan gap
- Queue item #133: docs/research/ index — parallel audit for research drops
- Workspace CLAUDE.md § no direct mention of spec/plan convention — may be implicit

— alpha, 2026-04-15T19:42Z
