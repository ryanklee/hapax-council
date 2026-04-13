# CLAUDE.md Excellence — Execution Plan

**Date:** 2026-04-13
**Author:** beta
**Status:** in progress
**Design doc:** `docs/superpowers/specs/2026-04-13-claude-md-excellence-design.md`

## Constraints

- **Branch discipline:** one feature branch across all repos at a time. Each PR merges before the next starts.
- **Council edits go through the beta worktree** at `~/projects/hapax-council--beta/`, never alpha's.
- **Upstream-owned repos** (`atlas-voice-training`, `tabbyAPI`) cannot accept pushes. Local-only files via `.git/info/exclude`.
- **Workspace root** (`~/projects/`) has no remote — commit directly to local main.

## PR sequence

Serialized. Each step merges before the next.

### PR 1 — council trim + spec + plan (this branch)

Repo: `hapax-council`
Branch: `docs/claude-md-excellence`
Files:
- `docs/superpowers/specs/2026-04-13-claude-md-excellence-design.md` — new (this repo's canonical record)
- `docs/superpowers/plans/2026-04-13-claude-md-excellence-plan.md` — new (this file)
- `CLAUDE.md` — major surgery, 405 → ~200 lines. See §Surgery map below.
- `vscode/CLAUDE.md` — add 1-line sister-extension sync warning.

Surgery map for `hapax-council/CLAUDE.md`:

| Section | Action | Rationale |
|---|---|---|
| Header + architecture | Keep, minor polish | Load-bearing |
| Design Language | Keep | Load-bearing |
| Logos API | Keep | Load-bearing |
| Orientation Panel | Keep, trim key-files list | Useful pointers |
| Obsidian Integration | Keep, condense plugins list | Useful |
| Command Registry | Keep | Useful |
| Tauri-Only Runtime | Compress visual surface forensics (~line 101) | The "Bridge repair" + "custom[0] routing" paragraphs are historical; collapse into one pointer |
| Unified Semantic Recruitment | Keep | Architecturally load-bearing |
| **Daimonion dispatch split (PR #555 regression)** | **Delete** | Pure retrospective; regression is pinned in tests |
| **Impingement consumer bootstrap (F6, PRs #702 + #705)** | Compress to 2 lines, drop PR refs | Pattern useful, history not |
| Studio Compositor header | Keep | Load-bearing |
| **Compositor unification epic narrative** | **Delete** | Shipped; point to handoff |
| Key modules bullet list | Reduce from 24 to ~8 | Drop dormant/deferred items |
| **Director loop bootstrap (fixed 2026-04-12)** | **Delete** | Commit message |
| **Director loop max_tokens (fixed 2026-04-12)** | **Delete** | Commit message |
| **YouTube player extraction resilience (fixed 2026-04-12)** | **Delete** | Commit message |
| **Studio compositor service env (fixed 2026-04-12)** | **Delete** | Commit message |
| Camera USB robustness | Keep one line | Hardware context useful |
| **Camera 24/7 resilience epic narrative (~60 lines)** | **Delete, replace with 1-line pointer** | Shipped; handoff exists |
| Reverie Vocabulary Integrity | Compress ~50% | Keep the invariant, drop incident narratives |
| Voice FX Chain | Keep | Useful |
| Council-Specific Conventions | Keep | Useful |
| **Build rebuild scripts (FU-6 / FU-6b, 2026-04-12)** | Compress to 2 lines, drop date | Invariant useful |
| Axiom Governance | Keep | Load-bearing |
| SDLC Pipeline | Keep | Useful |
| Claude Code Hooks | Keep | Load-bearing |
| IR Perception | Compress — keep fleet table + data flow, drop "currently non-functional" apologies | |
| Bayesian Presence Detection | Compress tables, drop two-paragraph signal design prose | |
| Key Modules | Keep | Load-bearing |
| Voice Grounding Research Continuity | Keep | Useful |
| Prompt Compression Benchmark | Keep but compress | Useful |
| Composition Ladder Protocol | Keep | Load-bearing |

Target: ~200 lines post-surgery.

### PR 2 — officium trim + vscode sync note

Repo: `hapax-officium`
Branch: `docs/claude-md-polish`
Files:
- `CLAUDE.md` — remove `cycle_mode.py` rot aside from the Logos API section.
- `vscode/CLAUDE.md` — add sister-extension sync warning.

### PR 3 — hapax-phone new CLAUDE.md

Repo: `hapax-phone`
Branch: `docs/add-claude-md`
Files:
- `CLAUDE.md` — new file, based on research brief (see design doc §Research findings).

### PR 4 — watch sprint roadmap

Repo: `hapax-watch`
Branch: `docs/claude-md-trim`
Files:
- `CLAUDE.md` — remove the "Sprint Roadmap" section (rot target).

### PR 5 — distro-work polish

Repo: `distro-work`
Branch: `docs/claude-md-trim`
Files:
- `CLAUDE.md` — drop Pop!_OS historical line.

### Local step A — workspace root

Repo: `~/projects/` (no remote)
Commit: directly to local main.
Files:
- `CLAUDE.md` — fix sub-project claim; add top-level navigation pointer; add external-deps section for tabbyAPI.

### Local step B — atlas-voice-training

Repo: `atlas-voice-training` (upstream-owned)
Action: create `CLAUDE.md`, add to `.git/info/exclude`.

### Local step C — tabbyAPI

Repo: `tabbyAPI` (upstream-owned)
Action: create `CLAUDE.md`, add to `.git/info/exclude`.

## Ordering rationale

1. **PR 1 first** — it carries the design doc and this plan, giving every subsequent PR a canonical reference.
2. **PRs 2–5 serialized** — branch discipline allows only one feature branch across all repos.
3. **Local steps last** — no PR gating, can batch after all remote PRs land.

## Post-merge hygiene

- After PR 1 merges: alpha (when resumed) rebases to pick up the new `CLAUDE.md`.
- Delta worktree (if active) continues on its own branch; no conflict surface with docs-only changes.

## Done criteria

- All 5 PRs merged.
- All 3 local files on disk.
- `/revise-claude-md` re-audit reports ≥ 90 on every file.

## Status (post-execution)

All 5 PRs merged 2026-04-13 06:06–06:13 UTC.

| # | Repo | PR | Merge SHA |
|---|---|---|---|
| 1 | hapax-council | [#726](https://github.com/ryanklee/hapax-council/pull/726) | `f0ca6b323` |
| 2 | hapax-officium | [#63](https://github.com/ryanklee/hapax-officium/pull/63) | `25a98b2` |
| 3 | hapax-phone | [#2](https://github.com/ryanklee/hapax-phone/pull/2) | `6c00c57` |
| 4 | hapax-watch | [#22](https://github.com/ryanklee/hapax-watch/pull/22) | `faea109` |
| 5 | distro-work | [#27](https://github.com/ryanklee/distro-work/pull/27) | `fc8bb95` |

Local-only files in place: `~/projects/atlas-voice-training/CLAUDE.md`, `~/projects/tabbyAPI/CLAUDE.md`, `~/dotfiles/workspace-CLAUDE.md` (symlinked into `~/projects/CLAUDE.md`).

Followups landed in the audit pass on the same day: see `docs/superpowers/audits/2026-04-13-claude-md-excellence-audit.md` for findings + remediation status.
