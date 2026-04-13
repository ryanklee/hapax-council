# CLAUDE.md Excellence — Post-Execution Audit

**Date:** 2026-04-13
**Author:** beta
**Spec:** [`../specs/2026-04-13-claude-md-excellence-design.md`](../specs/2026-04-13-claude-md-excellence-design.md)
**Plan:** [`../plans/2026-04-13-claude-md-excellence-plan.md`](../plans/2026-04-13-claude-md-excellence-plan.md)

Audit performed against the 5 PRs that shipped earlier the same day. Verifies the design doc's success criterion ("every existing CLAUDE.md scores ≥ 90 on the rubric") and surfaces gaps the original execution missed.

## Re-grades (post-trim, 100-point rubric)

| File | Cmd | Arch | Pattern | Concise | Current | Action | Total | Grade | Δ |
|---|---|---|---|---|---|---|---|---|---|
| `hapax-council/CLAUDE.md` | 18 | 19 | 14 | 12 | 14 | 13 | **90** | A | +35 |
| `hapax-council/vscode/CLAUDE.md` | 18 | 17 | 13 | 14 | 14 | 13 | **89** | B+ | +7 |
| `hapax-officium/CLAUDE.md` | 18 | 19 | 14 | 14 | 15 | 14 | **94** | A | +7 |
| `hapax-officium/vscode/CLAUDE.md` | 18 | 17 | 13 | 14 | 14 | 13 | **89** | B+ | +7 |
| `hapax-mcp/CLAUDE.md` | 19 | 19 | 13 | 15 | 15 | 14 | **95** | A+ | 0 |
| `hapax-constitution/CLAUDE.md` | 18 | 15 | 13 | 12 | 15 | 13 | **86** | B | −4 |
| `hapax-watch/CLAUDE.md` | 19 | 18 | 13 | 15 | 13 | 14 | **92** | A | +1 |
| `hapax-phone/CLAUDE.md` | 19 | 19 | 14 | 14 | 15 | 14 | **95** | A+ | new |
| `distro-work/CLAUDE.md` | 19 | 19 | 13 | 14 | 15 | 14 | **94** | A | +5 |
| `atlas-voice-training/CLAUDE.md` | 19 | 19 | 14 | 14 | 15 | 15 | **96** | A+ | new |
| `tabbyAPI/CLAUDE.md` | 19 | 18 | 14 | 14 | 15 | 15 | **95** | A+ | new |
| `~/projects/CLAUDE.md` (symlink) | 18 | 18 | 13 | 13 | 14 | 13 | **89** | B+ | +1 |

**Average: 92 (A−).** Median: 93. Min: 86 (constitution).

## Gaps vs the success criterion

The spec's success criterion is **every file ≥ 90**. Three files are below:

1. `hapax-constitution/CLAUDE.md` — 86 (B). Lost 4 points to **conciseness** because lines 17–19 carry "NEVER switch branches in primary worktree", "Always PR completed work", "You own every PR you create through to merge" — all duplicated from workspace root and council CLAUDE.md.
2. `hapax-council/vscode/CLAUDE.md` — 89 (B+). Architecture clarity is dragged by the sister-file duplication; sync warning is correct but overstated.
3. `hapax-officium/vscode/CLAUDE.md` — 89 (B+). Same as above.
4. `~/projects/CLAUDE.md` — 89 (B+). Architecture clarity is fine but actionability suffers from the symlink-into-dotfiles indirection being undocumented.

These four files are addressed in **Phase C** of the audit follow-up (see Findings + Remediation below).

## Findings

Findings are tagged: 🔴 high, 🟡 medium, 🟢 low.

### Consistency

| ID | Severity | Finding | Remediation |
|---|---|---|---|
| C-1 | 🔴 | `hapax-phone/CLAUDE.md` is invisible in the local working tree — `main` is 2 ahead, 1 behind `origin/main` because the operator has unmerged local commits. | Operator must rebase or merge their local commits onto `origin/main`. Not safe to fix autonomously. |
| C-2 | 🟡 | `distro-work` primary worktree was 1 behind `origin/main`. | Fixed in Phase A by `git merge --ff-only origin/main`. |
| C-3 | 🟡 | Sister vscode warning understates intentional differences (claims port-only; constitution-path style also differs). | Phase C2 normalizes the constitution-path style. |
| C-4 | 🟢 | `hapax-watch` and `hapax-phone` use different sister-app callout styles. | Defer; cosmetic. |
| C-5 | 🟢 | `hapax-mcp/CLAUDE.md` line 39 lists `cycle_mode` in the read-only tool list. | Phase C3 verifies against `server.py` and reconciles. |
| C-6 | 🟢 | `hapax-constitution/CLAUDE.md` duplicates workspace-root conventions. | Phase C4 drops the duplicates. |

### Completeness

| ID | Severity | Finding | Remediation |
|---|---|---|---|
| Co-1 | 🔴 | The success criterion ("every CLAUDE.md ≥ 90") was never measured. | This audit. |
| Co-2 | 🔴 | No automated enforcement existed. | Phase B wires `pre-commit` hook + GHA workflow + PR template clause. |
| Co-3 | 🟡 | Workspace-root CLAUDE.md is a symlink to dotfiles; not documented. | Phase C adds a one-line provenance note. |
| Co-4 | 🟡 | `.git/info/exclude` is per-clone state; portability fragile. | Defer to Phase D — not blocking. |
| Co-5 | 🟡 | Only council mentions the rotation policy by name. | Phase C adds a one-line trailer to every other workspace CLAUDE.md. |
| Co-6 | 🟢 | Spec/plan didn't link the implementing PRs. | Phase B5 adds the Status appendix to the plan. |

### Robustness

| ID | Severity | Finding | Remediation |
|---|---|---|---|
| R-1 | 🟡 | Rot script v1 had 8 known weak spots (silent skip, narrow patterns, no auto-discovery, no test coverage). | Phase B1 ships v2: auto-discovery via `find`, wider patterns (`not yet`, `migration pending`, `temporary workaround`, `--strict` for `TODO`/`FIXME`/`XXX`), error on missing target, 9 smoke tests. |
| R-2 | 🟡 | `hapax-watch/CLAUDE.md` line 49 has "battery percentage not yet captured — TODO" — a rot pattern v1 missed. | Caught by v2 in-flight pattern. Phase C1 removes it. |
| R-3 | 🟡 | Alpha worktree has uncommitted state — files marked deleted by rebuild-logos timer. | Documented behavior; alpha session recovers via `git restore .` on resume. Not addressed here. |
| R-4 | 🟢 | Workspace-root symlink isn't sanity-checked. | Defer. |

### Dead code / leftovers

| ID | Severity | Finding | Remediation |
|---|---|---|---|
| D-1 | 🟢 | No leftover branches across any owned repo. | ✓ Verified. |
| D-2 | 🟢 | No leftover worktrees outside the canonical alpha/beta/delta. | ✓ Verified. |
| D-3 | 🟢 | `git remote prune` revealed 6 stale remote-tracking branches across 4 repos. | Cleaned in Phase A4. |

### Missed opportunities

| ID | Severity | Finding | Remediation |
|---|---|---|---|
| M-1 | 🟡 | Rot script could be a hook. | Wired in Phase B2. |
| M-2 | 🟡 | No CLAUDE.md grade reporting. | This audit doc IS the report; future audits regenerate it. |
| M-3 | 🟢 | Sister-extension files could be deduplicated entirely. | Defer; duplication is currently bounded by sync warning + Phase C2 normalization. |
| M-4 | 🟢 | No CONTRIBUTING.md or onboarding pointer. | Defer; single-operator system, lower priority. |
| M-5 | 🟢 | Plan doc missing reverse links to PRs. | Phase B5 adds Status appendix. |
| M-6 | 🟢 | Quarterly review reminder not scheduled. | Defer; weekly-review system already exists and rotation-policy check runs on every PR via Phase B3. |

## Phase B deliverables landed in this audit

- ✓ B1 — `scripts/check-claude-md-rot.sh` rewritten as v2 (auto-discovery, wider patterns, modes, typo guard)
- ✓ B1 — `tests/test_check_claude_md_rot.sh` covers 9 fixtures (clean, fix-date, PR fingerprint, beta-PR, currently-broken, in-flight, TODO non-strict, TODO strict, missing target)
- ✓ B2 — `claude-md-rot` pre-commit hook entry on files matching `CLAUDE\.md$`
- ✓ B3 — `.github/workflows/claude-md-rot.yml` triggered on `**/CLAUDE.md` paths (the regular CI workflow's `paths-ignore` skips these)
- ✓ B4 — `.github/pull_request_template.md` carries a CLAUDE.md hygiene checkbox
- ✓ B5 — Plan doc Status appendix; spec doc carries plan + audit cross-links
- ✓ B6 — This audit doc
- ✓ B7 — Phase C remediation list (below)

## Phase C work (sibling repos, one PR each)

| # | Repo | Change |
|---|---|---|
| C1 | `hapax-watch` | Remove "battery percentage not yet captured" gotcha (R-2). Add rotation-policy trailer (Co-5). |
| C2 | `hapax-officium` | Normalize constitution-path style across both vscode CLAUDE.mds (C-3). Add rotation-policy trailer to main CLAUDE.md (Co-5). |
| C3 | `hapax-mcp` | Verify `cycle_mode` tool name against `server.py` and reconcile (C-5). Add rotation-policy trailer (Co-5). |
| C4 | `hapax-constitution` | Drop duplicated workspace conventions (C-6). Add rotation-policy trailer (Co-5). |
| C5 | `distro-work` | Add rotation-policy trailer (Co-5). |

## Deferred (Phase D)

- D1 — Generate-vs-duplicate decision for the two vscode CLAUDE.mds.
- D2 — Move atlas + tabbyAPI local files into a tracked dotfiles location.
- D3 — Sister-something cross-references for mcp ↔ vscode-extensions, constitution ↔ council ↔ officium.
- D4 — Quarterly audit calendar entry / `/weekly-review` integration.
- D5 — Operator's hapax-phone divergence reconciliation (C-1).
