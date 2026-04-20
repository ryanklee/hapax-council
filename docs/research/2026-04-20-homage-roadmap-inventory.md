# HOMAGE Roadmap Inventory

**Date:** 2026-04-20
**Author:** alpha (research dispatch)
**Audience:** operator, alpha/beta/delta sessions
**Register:** scientific, neutral
**Scope:** Resolve the operator's "what is Phase 8?" question across all HOMAGE-family plans; provide a per-phase status table; identify the highest-WSJF remaining HOMAGE work; cross-link to OQ-02 and LRR Phase 8.
**Authority sources:**
- `docs/superpowers/plans/2026-04-18-homage-framework-plan.md` (framework plan; 12 phases)
- `docs/superpowers/plans/2026-04-19-homage-completion-plan.md` (completion plan; 5 families A-E plus F retirement bundle)
- `docs/research/2026-04-20-homage-scrim-{1..6}-*.md` (six-doc research bundle)
- `docs/research/2026-04-20-nebulous-scrim-design.md` and `...-three-bound-invariants-triage.md`
- `docs/superpowers/handoff/2026-04-20-delta-wsjf-reorganization.md` (WSJF rubric §2.1)
- `git log --all` filtered for HOMAGE / homage / lrr-phase-8

---

## §1. HOMAGE family map - what each plan governs

The HOMAGE corpus comprises three structurally distinct artefacts, sequentially produced. They are not redundant: each consumes its predecessor's deliverables and adds a new layer of work. The map below names each artefact, its scope, and which "Phase N" labels it owns.

### §1.1 The HOMAGE Framework Plan (2026-04-18)

`docs/superpowers/plans/2026-04-18-homage-framework-plan.md` (532 lines). Twelve numbered phases, each one feature branch and one PR, executed sequentially over PRs #1049 to #1097 (see §2 commit table). This plan ships the HOMAGE *abstraction*: `HomagePackage` schema, `HomageTransitionalSource` mixin, choreographer FSM, `homage.*` IntentFamily, ward-shader bidirectional coupling, voice register, structural-director rotation hint, research condition, ward migration in three batches, consent-safe variant. The framework plan's Phase 8 is **`StructuralIntent.homage_rotation_mode`** (framework plan lines 348-376). All twelve framework phases are merged.

### §1.2 The HOMAGE Completion Plan (2026-04-19)

`docs/superpowers/plans/2026-04-19-homage-completion-plan.md` (2,076 lines). This plan was authored after the framework plan reached Phase 12 but the surface still failed the operator's visual-acceptance test. It is structured as **five families (A-E) plus Family F**, not numbered phases. Each family contains 1-7 sub-phases. Total surface: 23 dispatchable phases (A1-A6, B0-B6, C1-C4, D1-D3, E1, F1-F2; F3-F5 deferred post-live). The completion plan ships in a single branch (`hotfix/fallback-layout-assignment`) with parallel subagent dispatch. **There is no "Phase 8" in the completion plan** (the labels are A1, B3, C2, etc., not numeric).

### §1.3 The Scrim Research Bundle (2026-04-20)

Six-doc research dispatch authored in commit `828ca55d4` ("docs: HOMAGE wards x Nebulous Scrim - 6-cluster research bundle"):

- `...homage-scrim-1-algorithmic-intelligence.md` - fishbowl placement intelligence
- `...homage-scrim-2-disorientation-aesthetics.md` - register and dialect
- `...homage-scrim-3-nebulous-scrim-architecture.md` - scrim-as-substrate, three permeability modes
- `...homage-scrim-4-fishbowl-spatial-conceit.md` - depth bands and spatial grammar
- `...homage-scrim-5-choreographer-audio-coupled-motion.md` - audio coupling
- `...homage-scrim-6-ward-inventory-integration.md` - per-ward inventory + 13-ward classification

These are research/design documents (not dispatchable plans). They have not been converted into a sequenced implementation plan yet. The Nebulous Scrim three-bound invariants triage (`docs/research/2026-04-20-nebulous-scrim-three-bound-invariants-triage.md`) is the single derived plan-stub from this bundle and is logged as **OQ-02** in the alpha relay file. It carries its own >=3-PR phased plan stub but no dedicated `plans/` artefact yet.

### §1.4 Adjacent post-live iteration plans (2026-04-19)

Commit `27457c789` ("post-live: homage iteration plans") landed two adjacent plans not formally HOMAGE-tagged but downstream of HOMAGE acceptance:

- `docs/superpowers/plans/2026-04-19-preset-variety-completion-plan.md` (task #166) - 9-phase preset/chain variety plan; its own Phase 8 is gated on task #164 content-programming layer.
- `docs/superpowers/plans/2026-04-19-content-programming-layer-plan.md` (task #164) - 12-phase programme layer.

These are *not* HOMAGE phases per se. They iterate the surface that HOMAGE produced.

### §1.5 Disambiguation rule

When the operator says "Phase 8" in HOMAGE context, the literal-numeric reading resolves to **HOMAGE Framework Plan Phase 8 = StructuralIntent `homage_rotation_mode`** (shipped as commit `212be0e41`, PR #1071). The completion plan has no numeric Phase 8. The scrim bundle has no phase numbering. LRR Phase 8 is a separate epic (§6 below).

---

## §2. Per-phase status table

### §2.1 Framework Plan phase status

All twelve framework-plan phases are shipped. Verification cite: `git log --all --oneline | grep -iE "homage"` produced PRs #1049 -> #1097 in monotonically-increasing PR-number order matching the plan's execution-order section (framework plan lines 502-514).

| Phase | Description | Status | Cite |
|---|---|---|---|
| 1 | Spec + plan docs | shipped | `7f7ca5064` (#1049) `docs(homage): epic spec + 12-phase plan` |
| 2 | `HomagePackage` + BitchX data | shipped | `3c89510c0` (#1050) `feat(homage): HomagePackage abstraction + BitchX package data` |
| 3 | Transition FSM + choreographer + observability | shipped | `8ed469cd9` (#1051) `feat(homage): Phase 3 - transition FSM + choreographer + observability` |
| 4 | Migrate 4 legibility surfaces to BitchX grammar | shipped | `5a766657e` (#1052) `feat(homage): Phase 4 - migrate 4 legibility surfaces to BitchX grammar` |
| 5 | IntentFamily + catalog + dispatchers + director prompt | shipped | `24ac7900b` (#1053) `feat(homage): Phase 5 - IntentFamily + catalog + dispatchers + director prompt` |
| 6 | Ward-shader bidirectional coupling | shipped | `57a41a243` (#1060 cascade phase 3 bundle) and follow-on hotfixes |
| 7 | VoiceRegister + CPAL wiring | shipped | `11e563bae` (cascade phase 5 bundle, "HOMAGE Phase 7 + #123 chat ward") |
| **8** | **StructuralIntent `homage_rotation_mode`** | **shipped** | **`212be0e41` (#1071) `feat: HOMAGE Phase 8 rotation mode + exploration stimmung writer recovery`** |
| 9 | PerceptualField.homage + research condition `cond-phase-a-homage-active-001` | shipped | `469c6d5cd` (#1072) `feat(homage): phase 9 - PerceptualField.homage + LRR research condition cond-phase-a-homage-active-001` |
| 10 | Rehearsal + audit (no PR; runbook) | shipped (runbook) | `7f99b1d0f` (#1089) `docs(homage): Phase 10 - rehearsal + audit runbook` |
| 11a | Hothouse 6-ward migration | shipped | `b8e0482e0` (#1054) `feat(homage): Phase 11a - 6 hothouse wards migrated to BitchX grammar` |
| 11b | Content 6-ward migration | shipped | `8c86a1bef` (#1055) `feat(homage): Phase 11b - 6 content wards inherit HomageTransitionalSource` |
| 11c | Overlay/Reverie wrapper migration | shipped | `c7bc1d62b` (cascade phase 4 bundle, "HOMAGE Phase 11c/12 + #129 ...") |
| 12 | Consent-safe variant + flag promotion | shipped | `c7bc1d62b` (same cascade bundle) |

The framework plan's twelve phases produced the `HomageTransitionalSource` infrastructure but the resulting surface failed the operator's "one programmed instrument" acceptance test. This precipitated the completion plan.

### §2.2 Completion Plan family status

Family-letter labels (A-F), not numeric. Status sourced from commit log in the `feat(homage): completion epic` umbrella (commit `3bd0cf9f7`, PR #1107) and follow-up commits `6b090d40a` (#1104), `5433d646f` (#1102), `abd74fd9f` (#1101), `ab4bd4a9d` (#1100), `7ef0ab16a`, `54e2d36d6`, `6afcde7bb`. The completion plan was authored as a 23-phase parallel-subagent dispatch (plan §2). Most landed in the umbrella PR #1107; remaining items shipped as follow-on hotfixes.

| Family | Phase | Description | Status | Cite / note |
|---|---|---|---|---|
| **A - Render-layer rewrite (Option A)** | A1 | `EmissiveWardBase` shared base | shipped | within `3bd0cf9f7` umbrella |
| | A2 | Hothouse 6-ward emissive rewrite | shipped | within `3bd0cf9f7` |
| | A3 | Legibility 4-ward emissive rewrite | shipped | within `3bd0cf9f7` |
| | A4 | Content-ward emissive rewrite (token, album, captions, stream, research, vinyl) | shipped | within `3bd0cf9f7` + `6afcde7bb` (album/token follow-up) |
| | A5 | Pango/Px437 typography foundation | shipped | within `3bd0cf9f7` + `1fe4ddef5` CI font hardening |
| | A6 | Reverie substrate alpha damping | shipped | within `3bd0cf9f7` + `6afcde7bb` (album->HOMAGE substrate) |
| **B - Director->ward signal flow** | B0 | Narrative `structural_intent` write-path verification | partial / disputed | umbrella claims it; subsequent audits (D-26, D-27 in delta WSJF) found Phase-5 wire still uses `programme=None` |
| | B1 | Aggressive ward-property emphasis | shipped | within `3bd0cf9f7` + `6b090d40a` (#1104) emphasis-border-rendering |
| | B2 | `intent_family` -> ward-properties dispatch | shipped | within `3bd0cf9f7` |
| | B3 | Choreographer FSM un-bypass | partial | replaced by hotfix `3255fd40c`/`e566bf3e9` (#1097/#1096) - HOLD-default kept; reckoning §3.1 close not verified by direct removal |
| | B4 | Rotation-mode activation (steady/deliberate/rapid/burst) | shipped | within `3bd0cf9f7` |
| | B5 | Layout JSON: `chat_ambient` -> `ChatAmbientWard` | shipped | within `3bd0cf9f7` |
| | B6 | HARDM emphasis -> FX-chain bias | not shipped | no commit found referencing fx_chain_ward_reactor or HARDM-bias; remains plan-only |
| **C - Observability + governance** | C1 | `hapax_homage_*` Prometheus metrics | shipped | within `3bd0cf9f7` (observability scope mentioned in title) |
| | C2 | Open `cond-phase-a-homage-active-001` | shipped | already opened in framework Phase 9 (#1072); completion plan re-affirmed |
| | C3 | Visual-regression golden suite | partial | goldens exist (`ed8a61ba8` regen, `1fe4ddef5` CI font); 32-image full matrix not verified |
| | C4 | Phase 10 rehearsal automation script | not shipped | runbook `7f99b1d0f` exists; `scripts/run-phase-10-rehearsal.sh` not found in commit log |
| **D - Audio/presence polish** | D1 | Vinyl-on-stream filter-chain verification | shipped (post-live) | `0f7106ac2` "split Evil Pet path - voice -> Ryzen, livestream -> L6 USB" |
| | D2 | YouTube turn-taking gate | unknown | no specific commit cite; may be subsumed by content-programming work |
| | D3 | TTS cadence verification | shipped | covered by separate CPAL audit cycle |
| **E - Deploy + acceptance** | E1 | Phase 10 walkthrough + go-live | shipped | go-live occurred per `27457c789` "post-live: homage iteration plans" |
| **F - Expert-system retirement** | F1 | Retire `camera.hero` variety-gate | unknown | no isolated retirement commit; may be folded into umbrella |
| | F2 | Retire `narrative-too-similar` + `activity-rotation` | unknown | no isolated retirement commit |
| | F3 | `silence.*` capability registration | deferred post-live | plan §F3-F5 explicitly defers |
| | F4 | Director-micromove capability registry | deferred post-live | as above |
| | F5 | Restore `speech_production` recruitment path | deferred post-live | as above |

**Remaining completion-plan work** (from the audit above):
1. **B6** (HARDM -> FX-chain bias) - no shipping commit found.
2. **C4** (Phase 10 rehearsal automation) - runbook ships; automation script does not.
3. **C3** (visual-regression golden suite) - partial; full 32-image matrix incomplete.
4. **B0/B3** (structural_intent write path; FSM un-bypass) - partial; subsequent dead-bridge audit (D-26/D-27 in `2026-04-20-delta-wsjf-reorganization.md`) found the upstream chain still has dead links.
5. **F1/F2** (rule retirements) - verification needed; may be silently included in umbrella commit but not surfaced as separate retirement commits.
6. **F3/F4/F5** (post-live deferral) - explicitly deferred; remain valid unstarted work.

### §2.3 Scrim research bundle status

| Doc | Status |
|---|---|
| Six scrim docs (1-6) | research-only; no implementation plan dispatched |
| `nebulous-scrim-design.md` | research / design |
| `nebulous-scrim-three-bound-invariants-triage.md` | promoted to OQ-02 in alpha.yaml; >=3-PR phased plan stub authored; no `plans/` artefact yet |

OQ-01 (D-25 neon palette node) shipped as the smallest concrete bound-2 instance of OQ-02; commit `863509ac9`. This establishes the brightness-ceiling pattern that OQ-02 generalizes (triage doc §6).

---

## §3. Phase 8 - answer to operator's literal question

The unambiguous reading of "Phase 8" in HOMAGE-family context resolves as follows.

### §3.1 HOMAGE Framework Plan Phase 8 - STATUS: SHIPPED

**Title:** `StructuralIntent.homage_rotation_mode`.
**Plan location:** `docs/superpowers/plans/2026-04-18-homage-framework-plan.md` lines 348-376.
**Branch:** `feat/homage-structural-hint`.
**Ship commit:** `212be0e41` ("feat: HOMAGE Phase 8 rotation mode + exploration stimmung writer recovery", PR #1071).

**What was planned:**
1. Add `homage_rotation_mode: Literal["steady", "deliberate", "rapid", "burst"] | None = None` to `shared/structural_intent.py`.
2. Include the new field in the structural director's prompt and output schema (`agents/studio_compositor/structural_director.py`).
3. Choreographer reads the structural file for the active rotation mode; adjusts rotation cadence + burst triggers accordingly (`agents/studio_compositor/homage/choreographer.py`).
4. New tests at `tests/studio_compositor/homage/test_structural_homage_mode.py`.

**Acceptance (plan §Phase 8):** the structural director emits `homage_rotation_mode` at its 90 s cadence; the choreographer adjusts signature-artefact rotation rate accordingly; rehearsal-measurable.

**What's actually open against Phase 8:** the completion plan's Phase B4 (lines 1011-1086) extends Phase 8 by adding *semantic cadence numbers* to the four modes and changing the choreographer from a passive rotation-reader to an *active* rotation-producer (`Choreographer.maybe_rotate(now, rotation_mode, registry)` synthesises `ticker-scroll-out -> ticker-scroll-in` pairs on per-mode cadences: 30 s / 15 s / 4 s / 60 s + netsplit). Phase B4 is shipped per umbrella `3bd0cf9f7`.

**Net:** framework Phase 8 is closed; the rotation-mode behavioural surface it specified now ships extended cadence semantics from completion-plan B4. No outstanding work against framework Phase 8 itself.

### §3.2 HOMAGE Completion Plan - no Phase 8

The completion plan is family-keyed (A-F), not numeric. There is no completion-plan Phase 8.

### §3.3 LRR Phase 8 - separate epic (see §6)

If the operator's "Phase 8" reference is the LRR (Livestream Research Reckoning) epic rather than HOMAGE, the resolution is different. LRR Phase 8 = "Hapax Content Programming via Research Objectives", twelve sub-items, all shipped (commits `f4e0ec85` ... `0323fce02`). See §6 for full disambiguation.

---

## §4. Recommended next HOMAGE work - WSJF ranking

The WSJF rubric from `docs/superpowers/handoff/2026-04-20-delta-wsjf-reorganization.md` §2.1 is `WSJF = (Business Value + Time Criticality + Risk Reduction) / Job Size` with components on Fibonacci 1-3-5-8-13.

The remaining HOMAGE items from §2.2 are scored below:

| Item | BV | TC | RR | JS | WSJF | Notes |
|---|---|---|---|---|---|---|
| **OQ-02 phase-stub conversion to dispatchable plan** | 8 | 5 | 8 | 3 | **7.0** | Three-bound invariant work; cross-cuts ALL future scrim effects; D-25 already shipped the bound-2 pattern |
| **B6** HARDM emphasis -> FX-chain bias | 5 | 3 | 3 | 5 | **2.2** | Operator surface change; cross-modal coupling; non-blocking |
| **C4** Phase 10 rehearsal automation script | 5 | 3 | 5 | 3 | **4.3** | Reduces rehearsal regression risk on every future HOMAGE iteration |
| **C3** visual-regression golden suite (full 32-image) | 5 | 3 | 5 | 3 | **4.3** | Catches silent fall-back regressions; pairs with C4 |
| **F3/F4/F5** post-live retirements | 3 | 3 | 5 | 8 | **1.4** | Architecturally-significant but plan-explicitly-deferred |
| Scrim bundle -> dispatchable plan (six-cluster) | 8 | 3 | 5 | 13 | **1.2** | Large scope; cross-cuts wards, choreographer, audio coupling |
| Programme-layer plan (`task #164`) | 5 | 3 | 5 | 13 | **1.0** | Adjacent to HOMAGE; very large |

### §4.1 Recommendation

**Highest-WSJF unstarted HOMAGE work: convert OQ-02 (Nebulous Scrim three-bound invariants) from triage stub into a full dispatchable plan, then ship Phase 1 (metric selection + oracle authoring).**

Justification per the rubric:
- **BV = 8** because the three-bound invariant gates *every future scrim effect and effect chain*. Without it, additions are operator-eyeball-validated only.
- **TC = 5** because OQ-01 (D-25 neon shipped `863509ac9`) is the first verified bound-2 violation; pattern will recur until the framework lands.
- **RR = 8** because it unblocks the entire scrim-bundle implementation epic (six research docs currently un-implemented) by giving them a safe-to-merge gate.
- **JS = 3** because the triage doc already enumerates Phase 1 metric candidates (face-recognition L2 distance, SSIM/MS-SSIM, BPM-periodicity detector); a Phase 1 plan is mostly authoring.

The runner-up is **C4** (Phase 10 rehearsal automation, WSJF 4.3) because it converts the operator's "this looks like one programmed instrument" acceptance test from O(60-checkbox-eyeball) into O(script-runs-in-30 s + operator-spot-checks-5-items). Every future HOMAGE iteration benefits.

---

## §5. Cross-link to OQ-02 (Nebulous Scrim three-bound invariants)

### §5.1 OQ-02 origin

OQ-02 is logged in the alpha relay file (`operator_queue_adds_20260420.OQ-02`) and surfaced as a research-to-plan triage candidate at `docs/research/2026-04-20-nebulous-scrim-three-bound-invariants-triage.md` (promoted 2026-04-20T17:30Z per WSJF reorganization §10.7). It encodes three operator-stated bounds (triage doc §1):

1. **B1 anti-recognition** - face-pseudo-anonymisation under all effects + chains.
2. **B2 anti-opacity** - studio with inhabitants must always be perceptible.
3. **B3 anti-audio-visualizer** - surface must never read as Winamp/MilkDrop register.

### §5.2 Overlap with HOMAGE phases

OQ-02 emerged from the scrim research bundle (six docs `...homage-scrim-{1..6}-*.md`); its bounds are *general* across all HOMAGE work, not specific to the existing 12-phase framework or the 5-family completion plan.

**Specific overlap points:**

- **Framework Phase 6** (ward-shader coupling) - wrote `custom[4]` payload from choreographer to Reverie shader; OQ-02 B2 + B3 invariants would constrain *which* coupling values are safe.
- **Completion plan Phase A6** (Reverie substrate alpha damping) - already enforces a saturation ceiling (<= 0.55) for Reverie under BitchX; this is a hand-applied bound-2 enforcement and a clear precursor to the OQ-02 generalization.
- **Completion plan Phase A4** (album PiP-FX rewrite) - OQ-01 (D-25, the neon-edge-degeneracy fix) is the verified bound-2 instance; the same `colorgrade + bloom` chain audit pattern (triage doc §6) applies to multiple A4-touched wards.
- **Scrim bundle dispatch 3** (`...homage-scrim-3-nebulous-scrim-architecture.md`) - defines three permeability profiles (`semipermeable_membrane`, `solute_suspension`, `ionised_glow`); OQ-02's bounds gate which permeability + ward combinations are safe.
- **Scrim bundle dispatch 6** (`...homage-scrim-6-ward-inventory-integration.md`) - per-ward depth/motion table; OQ-02 B1 risks are different per depth band (deep wards face less recognition risk; surface wards face more).

### §5.3 Consolidation recommendation: keep separate

OQ-02 should remain its own epic, *not* be folded into the existing HOMAGE plans. Reasons:

1. **Different lifecycle.** HOMAGE framework + completion plans are about *building the surface*; OQ-02 is about *invariants the surface must satisfy*. Building and invariant-enforcement have different review paths (operator visual-acceptance vs metric-driven CI gate).
2. **Cross-cuts beyond HOMAGE.** OQ-02's bounds also gate non-HOMAGE work - Reverie effects, future content-programming-layer surfaces (task #164), GEM ward (commit `b6ec4a723`), any future ward family. Folding into HOMAGE would mis-scope it.
3. **The triage doc is already decoupled.** Triage doc §3 reuses the existing scrim-design's invariants (face-obscure ordering decided 2026-04-20: BEFORE scrim per WSJF §10.8); OQ-02 generalises rather than re-litigates.
4. **Sequencing.** OQ-02's Phase 1 (metric authoring) is small and independent (~3 SP per JS=3); folding it into the larger HOMAGE remediation work would obscure that.

What *should* happen: every new HOMAGE phase (B6, C3, C4, F3-F5, scrim-bundle dispatches) should cite the OQ-02 triage doc and confirm its work satisfies the three bounds. The triage doc §6 establishes the precedent: "every preset whose chain ends in `colorgrade + bloom` should be audited for the same brightness-ceiling ... this is a hand-applied bound-2 enforcement until the Phase 5 runtime check exists."

---

## §6. Cross-link to LRR Phase 8 (content programming)

### §6.1 LRR Phase 8 != HOMAGE Phase 8

The two epics share the "Phase 8" label but are otherwise unrelated.

**LRR Phase 8** = "Hapax Content Programming via Research Objectives" - twelve sub-items shipped between `f4e0ec85` (item 1) and `0323fce02` (item 10). Relevant artefacts:

- Plan: `docs/superpowers/plans/2026-04-15-lrr-phase-8-content-programming-via-objectives-plan.md`
- Spec: `docs/superpowers/specs/2026-04-15-lrr-phase-8-content-programming-via-objectives-design.md`
- Twelve commits (PRs #940 through #991), all merged.
- Subject matter: research-objective vault notes (`type: goal`-style), `hapax-objectives` CLI, director-loop scoring, objective overlay Cairo source, Stream Deck adapter, attention-bid dispatcher.

**HOMAGE Framework Phase 8** = `StructuralIntent.homage_rotation_mode` (one PR, #1071, three-day window).

### §6.2 No shared scope

The two phases share no scope, no files, and no commit chain. LRR Phase 8 ships a content-programming infrastructure (objectives + scoring + overlays); HOMAGE Phase 8 ships a structural-director enum field for ward-rotation cadence.

### §6.3 Disambiguation rule (operator-facing)

When the operator says "Phase 8", the preferred resolution priority is:
1. Most-recently-completed work in current session context - usually HOMAGE Phase 8 (rotation mode) if HOMAGE is the active topic, or LRR Phase 8 (content programming) if research/livestream-instrument work is active.
2. If ambiguous: ask which epic.
3. If the operator doesn't specify and no recent context exists: HOMAGE Phase 8 (rotation mode) is the more-recent ship (PR #1071, 2026-04-18 window) than LRR Phase 8 items (which spanned 2026-04-15 -> 2026-04-18 with the heaviest work in mid-cycle).

---

## §7. Sources / verification trail

- Framework plan: `docs/superpowers/plans/2026-04-18-homage-framework-plan.md` lines 1-532.
- Completion plan: `docs/superpowers/plans/2026-04-19-homage-completion-plan.md` lines 1-2076.
- HOMAGE commit search: `git log --oneline --all | grep -iE "homage" | head -50` produced 35 distinct commits between `7f7ca5064` (#1049, framework Phase 1) and `27457c789` (#1108, post-live iteration plans).
- LRR Phase 8 commit search: `git log --all --grep="lrr-phase-8" --oneline | head -20` produced 12 sub-item commits plus pre-staging.
- WSJF rubric: `docs/superpowers/handoff/2026-04-20-delta-wsjf-reorganization.md` §2.1 lines 53-63.
- OQ-02 triage: `docs/research/2026-04-20-nebulous-scrim-three-bound-invariants-triage.md` lines 1-116.
- OQ-01 (bound-2 reference instance): commit `863509ac9` (D-25 in WSJF reorganization).
- Six-doc scrim research bundle: commit `828ca55d4` ("docs: HOMAGE wards x Nebulous Scrim - 6-cluster research bundle").
- Post-live iteration: commit `27457c789` ("post-live: homage iteration plans + text_repo fix + CI typelib").

---

## §8. Single-sentence summary recommendation

**HOMAGE Framework Phase 8 (`StructuralIntent.homage_rotation_mode`) is shipped (commit `212be0e41`, PR #1071); the highest-WSJF unstarted HOMAGE-family work is converting OQ-02 (Nebulous Scrim three-bound invariants) from triage stub at `docs/research/2026-04-20-nebulous-scrim-three-bound-invariants-triage.md` into a dispatchable plan and shipping its Phase 1 (metric authoring), which gates every future scrim effect and is independent of the residual completion-plan items B6, C3, C4 and the explicitly-deferred F3/F4/F5 retirements.**
