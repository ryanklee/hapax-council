# Active Work Index

**Purpose:** Living index of every in-flight workstream. Kept fresh — updated whenever status changes. This is the canonical "what is Hapax actually doing right now" document.

**Policy (operator, 2026-04-18):**
- Keep detailed plan documents on everything going forward.
- Keep them fresh and updated so as not to lose track of anything.
- Every new workstream starts with a plan doc in this index.

**Update cadence:** Every tick of the `/loop` dynamic mode. At minimum: when an item advances state (researched → spec → plan → in-PR → merged → active).

---

## Workstream Status Legend

- 🟢 **ACTIVE** — currently being implemented / PR open
- 🟡 **QUEUED** — spec + plan exist, awaiting execution slot
- 🔵 **SPEC** — spec exists, plan does not yet
- 🟣 **RESEARCH** — research done, provisionally approved, spec pending
- ⚫ **BLOCKED** — waiting on external dependency
- ✅ **DONE** — merged to main, service restarted, deployed
- 🔁 **ITERATION** — research done but needs operator iteration before spec

---

## 1. HOMAGE Epic

**Lead doc:** `docs/superpowers/specs/2026-04-18-homage-framework-design.md`
**Plan:** `docs/superpowers/plans/2026-04-18-homage-framework-plan.md`

| Phase | Status | Landed | PR |
|---|---|---|---|
| 1 — Spec + plan docs | ✅ | 2026-04-18 | #1049 |
| 2 — HomagePackage + BitchX data | ✅ | 2026-04-18 | #1050 |
| 3 — FSM + choreographer + 5 metrics | ✅ | 2026-04-18 | #1051 |
| 4 — 4 legibility surfaces → BitchX | ✅ | 2026-04-18 | #1052 |
| 5 — IntentFamily + catalog + dispatchers | ✅ | 2026-04-18 | #1053 |
| 11a — 6 hothouse wards (batch 1) | ✅ | 2026-04-18 | #1054 |
| 11b — 6 content wards (batch 2) | ✅ | 2026-04-18 | #1055 |
| 6 — Ward↔shader bidirectional coupling | 🟡 | — | — |
| 7 — Voice register enum + CPAL wiring | 🟡 | — | — |
| 8 — StructuralIntent.homage_rotation_mode | 🟡 | — | — |
| 9 — Research condition + PerceptualField.homage | 🟡 | — | — |
| 10 — Rehearsal + audit runbook (no PR) | 🟡 | — | — |
| 11c — 6 overlay-zone + reverie (batch 3) | 🟡 | — | — |
| 12 — Consent-safe variant + retirement + flag flip | 🟡 | — | — |

**Next up:** Phase 6 — ward↔shader bidirectional coupling.

---

## 2. HOMAGE Follow-On (Research Dossier Cascade)

**Lead doc:** `docs/superpowers/research/2026-04-18-homage-follow-on-dossier.md` (this dossier)

**Policy:** Each research item gets its own spec stub, then its own plan doc, then its own PR(s). **Synergy pass deferred to last.**

### Rendering / Compositor Wards

| Task | Status | Spec stub | Plan | PR |
|---|---|---|---|---|
| #121 HARDM | 🔵 SPEC | [design](../specs/2026-04-18-hardm-dot-matrix-design.md) | — | — |
| #122 DEGRADED-STREAM | 🔵 SPEC | [design](../specs/2026-04-18-degraded-stream-design.md) | — | — |
| #123 Chat ambient ward | 🔵 SPEC | [design](../specs/2026-04-18-chat-ambient-ward-design.md) | — | — |
| #127 SPLATTRIBUTION | 🔵 SPEC | [design](../specs/2026-04-18-splattribution-design.md) | — | — |
| #128 Preset variety | 🔵 SPEC | [design](../specs/2026-04-18-preset-variety-expansion-design.md) | — | — |
| #132 Operator sidechat | 🔵 SPEC | [design](../specs/2026-04-18-operator-sidechat-design.md) | — | — |
| #135 Camera naming | 🔵 SPEC | [design](../specs/2026-04-18-camera-naming-classification-design.md) | — | — |
| #136 Follow-mode | 🔵 SPEC | [design](../specs/2026-04-18-follow-mode-design.md) | — | — |
| #124 Reverie preservation | 🔵 SPEC | [design](../specs/2026-04-18-reverie-substrate-preservation-design.md) | — | — |
| #125 Token pole HOMAGE | 🟣 | — | — | — |
| #126 Pango text repository | 🔁 (blocked on #155 linter) | — | — | — |
| #128 Preset variety expansion | 🟣 (drafting) | — | — | — |

### Perception → Representation

| Task | Status | Spec stub | Plan | PR |
|---|---|---|---|---|
| #129 Facial obscuring (HARD) | 🔵 SPEC | [design](../specs/2026-04-18-facial-obscuring-hard-req-design.md) | — | — |
| #135 Camera naming | 🟣 | — | — | — |
| #136 Follow-mode | 🟣 | — | — | — |

### Audio I/O + Mic

| Task | Status | Spec stub | Plan | PR |
|---|---|---|---|---|
| #133 Rode Wireless Pro | 🟣 | — | — | — |
| #134 Audio pathways audit | 🔵 SPEC | [design](../specs/2026-04-18-audio-pathways-audit-design.md) | — | — |

### Music + Content Sources

| Task | Status | Spec stub | Plan | PR |
|---|---|---|---|---|
| #127 SPLATTRIBUTION | 🟣 | — | — | — |
| #130 Local music repository | 🟣 | — | — | — |
| #131 SoundCloud integration | 🟣 ⚫ | — | — | — |

### Operator ↔ Hapax Sidechannel

| Task | Status | Spec stub | Plan | PR |
|---|---|---|---|---|
| #132 Operator sidechat | 🟣 | — | — | — |

### Synergy Pass

| Task | Status | Doc |
|---|---|---|
| Cross-cutting synergy analysis | 🟡 (DEFERRED to after all 16 stubs) | — |

---

### CVS Large-Scope Redesigns (specs landed)

| Task | Title | Spec | Status |
|---|---|---|---|
| #146 | Token pole reward mechanic | [design](../specs/2026-04-18-token-pole-reward-mechanic-design.md) | 🔵 SPEC |
| #149 | Audio reactivity contract | [design](../specs/2026-04-18-audio-reactivity-contract-design.md) | 🔵 SPEC |
| #150 | Vision integration | [design](../specs/2026-04-18-vision-integration-design.md) | 🔵 SPEC |
| #155 | Anti-personification linter | [design](../specs/2026-04-18-anti-personification-linter-design.md) | 🔵 SPEC |
| #156 | Role derivation research template | [design](../specs/2026-04-18-role-derivation-research-template-design.md) | 🔵 SPEC |
| #157 | Non-destructive overlay layer | [design](../specs/2026-04-18-non-destructive-overlay-design.md) | 🔵 SPEC |

### Fix-PR Briefs (ready to ship, no spec needed)

| Task | Title | Brief |
|---|---|---|
| #158 | Director "do nothing" invariant | [brief](./2026-04-18-director-no-op-fix-brief.md) 🚨 |

---

## 3. Context-Void Sweep Recoveries (2026-04-18)

**Source:** [`docs/superpowers/research/2026-04-18-context-void-sweep.md`](../research/2026-04-18-context-void-sweep.md)
**Swept:** 4 most recent transcripts covering 2026-03-25 through 2026-04-18.
**Found:** 19 dropped operator commitments / directives. All now tracked.

### Priority banding

**HIGH (governance-critical or active leak):**
| Task | Title | Status |
|---|---|---|
| #155 CVS #16 | Anti-personification persona constraint | 🟣 INVESTIGATE |
| #158 CVS #19 | Director "do nothing interesting" invariant regression | 🟣 SPEC-READY |
| #147 CVS #8 | Token-pole qualifier research (healthy/non-manipulative) | 🟣 RESEARCH |
| ~~#154 CVS #15~~ | ~~Hookify glob noise~~ | ⛔ DROPPED 2026-04-18 (already resolved per operator) |

**MEDIUM (capability gap / operator-flagged value):**
| Task | Title | Status |
|---|---|---|
| #150 CVS #11 | Video/image classification underused in livestream | 🟣 SCOPE |
| #144 CVS #5 | YT description auto-update from shared links ("powerful reuseable") | 🟣 SPEC |
| #146 CVS #7 | Token pole reward mechanic (emoji spew + chat tokens) | 🟣 SPEC |
| #156 CVS #17 | Role derivation methodology (general-case + Hapax-specific) | 🟣 RESEARCH |
| #157 CVS #18 | Non-destructive overlay effects layer | 🟣 SPEC |
| #140 CVS #1 | Stream Deck control surface | 🟣 SPEC |
| #141 CVS #2 | KDEConnect interim control path | 🟣 SPEC |
| #142 CVS #3 | Vinyl half-speed toggle + correction | 🟣 SPEC |

**INVESTIGATE FIRST (may be covered; verify before specc-ing):**
| Task | Title | Cross-reference |
|---|---|---|
| #143 CVS #4 | ARCloud integration + IR cadence | #127 SPLATTRIBUTION |
| #145 CVS #6 | 24c ducking for YT/React | #134 audio pathways + PR #778 |
| #148 CVS #9 | Reactivity sync/granularity gap | #74-78 A+ livestream + #91 sim runs |
| #149 CVS #10 | 24c global reactivity contract | #134 audio pathways |
| #153 CVS #14 | Worktree cap workflow | workspace CLAUDE.md policy |
| #152 CVS #13 | Session naming enforcement | hook ecosystem |

**META / GLOBAL CLAUDE.md:**
| Task | Title | Destination |
|---|---|---|
| #151 CVS #12 | Cross-agent audit preparedness (Gemini) | Global CLAUDE.md directive |

---

## 4. Standing Tasks Not Part of HOMAGE

| ID | Title | Status | Notes |
|---|---|---|---|
| #40 | Phase 7 legacy prompt cleanup PR | 🟡 (overdue) | Post-validation cleanup; blocked only by execution slot |
| #56 | Phase 4 PyMC MCMC BEST analysis | ⚫ | Data-sufficiency gated (livestream accumulation) |
| hapax-constitution#46 | Operator merge + registry.yaml patch | ✅ | Closed per task #58 |

---

## 5. Context-Void Sweep

**Launched:** 2026-04-18
**Completed:** 2026-04-18 (~4.7 min wall time)
**Agent:** general-purpose sweeping 4 most recent transcripts (152M + 106M + 88M + 112M)
**Output (permanent):** [`docs/superpowers/research/2026-04-18-context-void-sweep.md`](../research/2026-04-18-context-void-sweep.md)

**Result:** 19 dropped commitments recovered, triaged to §3 above. Tasks #140–#158 created. Task #138 (triage) complete.

---

## 6. Plan-Doc Freshness Policy

Every spec stub and plan under `docs/superpowers/{specs,plans}/` MUST:
1. Carry a `**Status:**` line at the top updated when the doc's phase changes.
2. Carry a `**Last updated:**` date on every substantive edit.
3. Link back to this active-work index so the graph is traversable from either end.

If a doc goes stale (no update in 14 days while its status is ACTIVE or QUEUED), it is flagged for rescue in the next tick.

---

## 7. Change Log

- **2026-04-18** — Index created. HOMAGE epic through Phase 11b merged. Research dossier with 16 findings provisionally approved. Context-void sweep dispatched.
- **2026-04-18 (later)** — Spec stubs written for #129 (facial obscuring), #122 (DEGRADED-STREAM), #134 (audio pathways). Tasks #137/138/139 created for index maintenance + sweep triage + deferred synergy analysis.
- **2026-04-18 (later)** — Context-void sweep returned. 19 dropped commitments recovered as tasks #140–#158. Index §3 added with HIGH/MEDIUM/INVESTIGATE/META priority banding.
- **2026-04-18 (final)** — All 19 CVS research agents returned. Findings in [`cvs-research-dossier.md`](../research/2026-04-18-cvs-research-dossier.md) §2. **Active regressions surfaced:** #158 director no-op 25% live, #142 album-identifier 2× hardcoded, #155 anti-personification violations, #152 session-naming, #154 hookify parser. Next tick: fix-PRs on actives + spec stubs on large-scope redesigns.
