# Workstream realignment v4 — audit-incorporated — 2026-04-25T02:15Z (rev 02:55Z)

**Author:** beta (drafted) + workstream-weaver round 2 (audit fold)
**Supersedes:** none yet — appends/updates `2026-04-24-workstream-realignment-v3.md` (v3-final) and `2026-04-25-workstream-realignment-v3-delta-update.md`
**Audit-incorporation status:** **30 rows folded in full.** Round-1 draft folded only AUDIT-01 (29 rows held as `[ROW NOT DELIVERED]` placeholders). Round-2 (this revision) received the verbatim text of AUDIT-02..AUDIT-31 and incorporates each into §3 census, §4 dependency edges, §5 per-session queues, and §6 trade-offs. AUDIT-26 is folded as one row with AUDIT-06 (proposal-twin of implementation, per upstream's own note). AUDIT-28 is shipped (#1358) and stays retired. **Net: 30 rows in, 0 placeholders remaining.**

## 0. Five-bullet TL;DR — what changed in v4

1. **Sixteen PRs shipped since v3-final** (#1341, #1342, #1344, #1345, #1347, #1348, #1349, #1350, #1352, #1353, #1354, #1355, #1356, #1357, #1358 + #1359 already implicit). Phase 0 STUB → Phase 0 FULL → Phase 1 → Phase 4 → Phase 5 → Phase 6c-i.A → Phase 6d-i.A all live. Critical-path keystone (Phase 1 PresenceEngine #1353) merged 01:34Z. Bayesian wave is now in **migration phase**, not infrastructure phase.
2. **Phase 6 cluster wave is fully unblocked.** 6c-i.A (epsilon, #1355) shipped, 6c-i.B awaits pickup, 6c-ii deferred. 6d-i.A (beta, #1357) shipped. **6a (delta) and 6b (alpha) remain unclaimed** — that is the highest-leverage next-tick action.
3. **Three critical privacy/anonymity regressions surfaced.** AUDIT-01 (DURF un-redacted terminal capture, delta WSJF 13), AUDIT-05 (OMG cascade legal-name leak, epsilon WSJF 13), and AUDIT-07 (director still uses Boolean `_vinyl_is_playing()`, delta WSJF 12). All three NEW; not in any v3-final queue. Until shipped, DURF default-on must remain blocked, OMG cascade publishes outward must be paused, and Phase 2 vinyl/music cluster blocks Phase 3.
4. **AUDIT-28 = HPX003+HPX004 → CI** is already shipped (#1358, beta). Per the user's task spec it does not re-enter the queue — listed in §3.1 retired.
5. **#1351 is still scope-mixed and OPEN.** Per v3-final note: drop the docs + DURF overlap; keep bed-music rotation flip as Workstream B. Delta to scope-resolve before next pickup. AUDIT-01 (DURF privacy) is now also a delta-owned blocker on top of #1351.

### Top action per session this tick

| Session | Top action (WSJF order, audit-incorporated) |
|---|---|
| **alpha** | **AUDIT-04 (Phase 4 envelope ships empty `[]` claim lists, WSJF 10)** — director/conversation/persona/autonomous_narrative all call `render_envelope([], floor=...)`. With Phase 4 merged (#1347), this is the bridge to Phase 6 cluster wave. Then Phase 6b mood/stimmung claims (WSJF 8, lane-canonical). DEVIATION-025 P0 (WSJF 13) is force-decided this tick: alpha claims OR beta auto-takes. |
| **beta** | **AUDIT-02 (Phase 6 inline LRs bypass HPX003 gate, WSJF 11)** — extend HPX003 AST-walk to flag `DEFAULT_SIGNAL_WEIGHTS: dict` literals in `agents/**/*.py`; backfill `system_degraded_*` and `speaker_is_operator` cluster entries in `lr_registry.yaml`. Then audit catchup on #1342/#1344/#1345/#1347/#1352/#1355/#1357. Audit hold on #1349 DURF Phase 2 — see AUDIT-01 §4. AUDIT-06+26 (claim-before-parallel hook implementation, WSJF 11) is co-equal P0. |
| **delta** | **Scope-resolve #1351 (DURF Phase 10 + bed-music)**. Then **AUDIT-01 DURF privacy redaction (WSJF 13, NEW, critical)** + **AUDIT-07 vinyl Boolean → MusicPlayingEngine + AUDIT-30 stub (WSJF 12+7, paired)**. Phase 6a activity claims (WSJF 8) follows. Phase 2 ownership trade-off in §6 may transfer some load to alpha. |
| **epsilon** | **AUDIT-05 (OMG cascade legal-name leak, WSJF 13)** — operator existential-risk class; cheap fix; 7 OMG modules + regression test. Then **AUDIT-03 (RefusalGate has zero call sites, WSJF 9)** — wire 4 narration surfaces. Then Phase 6c-i.B perception_loop wire-in. |

## 1. What changed since v3-final + v3-delta-update

Read v3-final (`2026-04-24-workstream-realignment-v3.md`) and the delta supplement (`2026-04-25-workstream-realignment-v3-delta-update.md`) first; v4 does not re-derive ruling principles or census those docs already cover.

### 1.1 Shipped between v3-final tail (00:45Z) and v4 (02:15Z)

In addition to the v3-delta-update §1 table:

| PR | Title | Owner | Merged | Phase / scope |
|---|---|---|---|---|
| #1355 | Bayesian Phase 6c-i.A SpeakerIsOperatorEngine module | epsilon | 2026-04-25T02:03:11Z | identity-cluster — module + 18 tests + prior_provenance entry; 328 LOC additions, 0 deletions; wire-in deferred to 6c-i.B |
| #1356 | v3-delta-update doc | beta | <02:15Z | docs-only; Phase 0+1 + 3499-004 + DURF status |
| #1357 | Bayesian Phase 6d-i.A SystemDegradedEngine | beta | <02:15Z | meta/system claim — first 6d cluster move |
| #1358 | HPX003+HPX004 wired to CI | beta | <02:15Z | governance gate — Claim/LRDerivation/prior_provenance now CI-enforced. **This is AUDIT-28 (per user spec) — DO NOT re-add to queue.** |

### 1.2 Still-open (non-dependabot)

- **#1349 DURF Phase 2** — beta, OPEN, auto-merge armed; CI in-flight; BEHIND main pending rebase. **Now tied to AUDIT-01** (see §4). Do not admin-merge until AUDIT-01 redaction primitive is at least scoped.
- **#1351 DURF Phase 10 + 2026-04-24 docs + bed-music rotation flip (scope-mixed)** — delta, OPEN. v3-final note still applies: drop docs (already on main), drop DURF overlap (already on main via #1349/#1350/#1352), keep bed-music rotation flip as actual focus. **Delta to scope-resolve before next pickup.**
- **Dependabot #1325/1326/1327/1328/1323/1324/590** — blocked on main-CI-red `test` failures (pre-existing, not PR-caused).

### 1.3 Peer state at 02:15Z (from yamls)

- **alpha.yaml** (last updated 21:25Z): standing tick post-#1352. Phase 4 #1347 closed. AUTH-PALETTE-MOKSHA + AUTH-GEAL bundle still in vault, not yet PR'd. **Note — alpha.yaml is the staleest of the four (~5h since last update).** AUDIT-23 confirms ~65% stale; refresh prescribed in §5.2.
- **beta.yaml** (last updated 01:13Z): #1353 PR description content; older sections preserve 23-tick night-watch trail. Currently coordinating + audit-catchup mode. **AUDIT-25 flags 565-line bloat;** split into ≤200-line current-state + archive prescribed in §5.1.
- **delta.yaml** (last updated 22:05Z): FINDING sweep complete (W/V/X/mobile all closed). Queue drained. Next pickups listed: PR C cleanup (already done), ytb-003 thumbnail, ytb-009 captions, ytb-012 Shorts. **Did not pick up Phase 2 / Phase 3 yet.**
- **epsilon.yaml** (last updated 02:09Z): #1355 module shipped, 6c-i.B handoff filed for beta or peer pickup, 6c-ii deferred. Watch cadence.

## 2. Ruling principles unchanged

Cite v3-final §2. Ten principles intact. Two reinforcements at v4:

- **(11, reinforcement of #4):** "Session-callable" extends to **scope-resolution of own PRs**. #1351 has been scope-mixed for ~24h; delta is session-empowered to either split or close-and-reopen without operator gating.
- **(12, reinforcement of #9):** Verify-before-claiming-done now has CI teeth via #1358. HPX003 + HPX004 reject Claim instances without `LRDerivation` or `prior_provenance.yaml`. Phase 6 migration PRs that miss either gate will fail CI, not silently regress. **AUDIT-02 surfaces a coverage gap — inline `DEFAULT_SIGNAL_WEIGHTS: dict` literals are not yet AST-flagged; HPX003 must be extended to close the gap before further Phase 6 cluster engines land.**

## 3. Census update

### 3.1 Shipped + retired since v3-final (clean off the active queue)

In addition to v3-final §3.1:

| Item | PR | Note |
|---|---|---|
| Phase 0 STUB | #1341 | beta; ~80 LOC API surface |
| Phase 0 FULL | #1350 | beta; keystone — ClaimEngine[T] + kill-switch + HPX003/HPX004 stubs (CI wiring deferred to #1358) |
| Phase 1 PresenceEngine refactor | #1353 | beta; bit-identical regression pin |
| Phase 4 prompt envelope | #1347 | alpha; per-surface floor table |
| Phase 5 refusal gate | #1344 | epsilon; Langfuse claim_discipline score |
| Phase 5/4 surface-key alignment fix | #1348 | epsilon; dependency cleanup |
| Phase 6c-i.A SpeakerIsOperatorEngine module | #1355 | epsilon; wire-in deferred to 6c-i.B |
| Phase 6d-i.A SystemDegradedEngine | #1357 | beta; first 6d cluster move |
| ef7b-165 Phase 9 egress footer module | #1342 | delta; governance |
| ef7b-165 Phase 9 Part 2 EgressFooterCairoSource | #1345 | delta; ward implementation |
| AUTH-HOMAGE default-flip | #1352 | alpha; session-callable, MERGED |
| 3499-004 gmail-sync inotify-flood fix | #1354 | beta; operational-critical |
| HPX003+HPX004 → CI (AUDIT-28) | #1358 | beta; CI gate |
| v3-delta-update doc | #1356 | beta; docs-only |

**Note on alpha lane staleness (per AUDIT-23):** the v3-final alpha queue listed AUTH-PALETTE-MOKSHA + AUTH-GEAL bundle. Per `alpha.yaml`, MIRC + GEAL + HOMAGE all shipped pre-21:25Z (#1289/#1290/#1288 then #1352). AUTH-PALETTE-MOKSHA remains genuinely unshipped (asset-gated on Moksha .edc). AUTH-GEAL surface itself is closed via #1290 + #1352. Refreshed in §5.2 below.

### 3.2 Bayesian phases — state after Phase 0/1/4/5/6c-i.A/6d-i.A

| Phase | v3-final WSJF | v4 status | Owner | Notes |
|---|---|---|---|---|
| **0** STUB + FULL | 15 | **DONE** | beta | #1341 + #1350 |
| **1** PresenceEngine | 14 | **DONE** | beta | #1353 |
| **2** Vinyl/music cluster + pgmpy | 12 | **OPEN — delta unclaimed; AUDIT-07 sharpens scope; AUDIT-30 STUB pairs** | delta | claim-before-parallel applies; alpha co-author candidate per §6 trade-off |
| **2b** Livestream classifiers | 10 | **OPEN — delta unclaimed** | delta | YAMNet + SigLIP2 + PaddleOCR; ~1GB weights download |
| **3** Frame-for-llm split | 14 | **OPEN — delta unclaimed** | delta | independent from 4; closes OCR-dominance attack surface |
| **4** Prompt envelope | 11 | **DONE — but AUDIT-04 surfaces empty-claim-list regression** | alpha | #1347 merged but envelopes ship `[]`; AUDIT-04 wires real posterior sources |
| **5** R-Tuning refusal gate | 9 | **DONE — but AUDIT-03 surfaces zero call sites** | epsilon | #1344 + alignment fix #1348; library-only until AUDIT-03 wires the 4 surfaces |
| **6a** Activity claims | 8 | **OPEN — delta unclaimed** | delta | unblocks Phase 7 |
| **6b** Mood/stimmung claims | 8 | **OPEN — alpha unclaimed** | alpha | lane-canonical for alpha |
| **6c-i.A** speaker_is_operator engine | 7 | **DONE** | epsilon | #1355 |
| **6c-i.B** wire-in to perception_loop | (subset of 6c) | **OPEN — epsilon ready** | epsilon | single-surface change; handoff filed |
| **6c-ii** chat-author multi-source noisy-OR | (subset of 6c) | **OPEN — epsilon deferred** | epsilon | governance-sensitive; beta pre-merge audit required |
| **6d-i.A** SystemDegradedEngine | 6 | **DONE** | beta | #1357; AUDIT-16 wires real `engine_queue_depth_high` signal |
| **6d-i.B / 6d-ii / 6d-iii** consent + budget + degradation cascade | (remainder of 6d) | **OPEN — beta unclaimed** | beta | next beta lane pickup after audit catchup |
| **7** T1-T8 posterior interrogations | 11 | **OPEN — alpha + beta** | alpha + beta | research-spec-plan not yet started; co-authored |

### 3.3 v3-final carryovers — unchanged unless noted

The bulk of v3-final §3.3 (38 rows) is preserved. Material updates:

| v3-final row | Update at v4 |
|---|---|
| Row 4 — DEVIATION-025 P0 Langfuse (alpha, WSJF 13) | **STILL UNCLAIMED.** Carried unchanged through v3-draft → v3-final → v3-delta. Three queue-revisions in 24h have not produced a claim. Two options: (a) reassign to beta (observability lane affinity) on next tick; (b) operator-decide whether the data-loss-critical framing still holds. Per "no operator-approval waits": pick (a). |
| Row 14 — ef7b-164 content programming (alpha, WSJF 12) | Unchanged; alpha unclaimed. **AUDIT-18 + AUDIT-19 sharpen this — director already sets `_current_programme_band` but the prompt never references it; AUDIT-18 wires the prompt slot, AUDIT-19 promotes programme-active to a Phase 6d meta-claim engine.** |
| Row 15 — **ef7b-165 de-monetization safety** (delta, WSJF 14) | Phase 9 + Phase 9 Part 2 shipped (#1342, #1345). Phase 10 is in-flight scope-mixed at #1351. Treat #1351 as the live ef7b-165 surface; close once scope-resolved. |
| Row 19 — 3499-004 gmail-sync (beta, WSJF 9) | **DONE** (#1354). **AUDIT-31 surfaces follow-up:** promote `_should_skip` from event-handler internal to watchdog `ignore_patterns`; eliminates ~6,000 callbacks per gmail-sync window. |
| Rows 24-44 (alpha standing + delta HOMAGE chain + epsilon AUTH bundle + standing infra) | Unchanged. None shipped this tick. |
| AUTH-HOMAGE default-flip (alpha, session-callable) | **DONE** (#1352). |

### 3.4 New items from the audit wave (30 rows folded)

The 30-row audit table from the upstream research agent is folded below in WSJF order. AUDIT-26 is folded as one row with AUDIT-06 (proposal-twin of implementation). AUDIT-28 is shipped (#1358) and listed in §3.1; not re-entered.

#### 3.4.1 Critical (WSJF ≥ 11)

| ID | Title | Touch | WSJF | Owner | Effort |
|---|---|---|---|---|---|
| **AUDIT-01** | DURF pixel capture broadcasts un-redacted terminal contents | durf | **13** | delta | M |
| **AUDIT-05** | OMG cascade publishes outward without OperatorReferentPicker (legal-name leak) | ops | **13** | epsilon | M |
| **AUDIT-07** | Director still uses Boolean `_vinyl_is_playing()`; Phase 2 not started | director | **12** | delta | L |
| **AUDIT-02** | Phase 6 inline LRs (SystemDegraded + SpeakerIsOperator) bypass HPX003 gate | bayesian | **11** | beta | M |
| **AUDIT-04** | Phase 4 prompt envelope ships with empty `[]` claim lists at all 4 surfaces | bayesian | **10** | alpha | L |
| **AUDIT-06+26** | Claim-before-parallel-work hook implementation | ops | **11** | beta | M |
| **AUDIT-03** | Phase 5 RefusalGate has zero call sites; library-only | bayesian | **9** | epsilon | L |

#### 3.4.2 Synergy (WSJF 5-7)

| ID | Title | Touch | WSJF | Owner | Effort |
|---|---|---|---|---|---|
| **AUDIT-10** | DURF Phase-2 Wayland-pixel-capture contradicts spec §5 | durf | 7 | delta + epsilon | S |
| **AUDIT-18** | Director ↔ programmes: `_current_programme_band` set but prompt never references it | director | 7 | alpha | S |
| **AUDIT-30** | Phase 2 `MusicPlayingEngine` STUB (~30 LOC mirror of Phase 0 STUB) | bayesian | 7 | delta | S |
| **AUDIT-16** | gmail-sync filter → Phase 6d-i.B `engine_queue_depth_high` adapter | bayesian | 6 | beta | S |
| **AUDIT-17** | Director cadence ↔ SystemDegradedEngine bidirectional loop | director | 6 | alpha + delta | M |
| **AUDIT-19** | Programme as Phase 6d meta-claim `P(programme_active=showcase\|t)` | bayesian | 6 | beta | L |
| **AUDIT-27** | Axiom precedent `sp-su-005-worktree-isolation` | ops | 6 | epsilon | S |
| **AUDIT-31** | Promote `_should_skip` to watchdog `ignore_patterns` | ops | 6 | beta | M |
| **AUDIT-09** | `TemporalProfile.bocd_hazard` declared but never consumed | bayesian | 5 | beta | M (option a); S (option b) |
| **AUDIT-22** | Publication-contract redaction generalization (16 contracts share schema, no central transform pipeline) | ops | 5 | epsilon | L |
| **AUDIT-23** | v3-final alpha lane ~65% stale at authoring (currency drift) | workstream | 5 | beta | S |
| **AUDIT-29** | Add `shared/operator_referent.py` + speech_lexicon to CODEOWNERS | ops | 5 | epsilon | S |

#### 3.4.3 Aesthetic / Doc / Minor (WSJF ≤ 4)

| ID | Title | Touch | WSJF | Owner | Effort |
|---|---|---|---|---|---|
| **AUDIT-08** | Spec divergence: `prior_provenance` vs code `prior_provenance_ref` | bayesian | 4 | beta | S |
| **AUDIT-12** | DURF aesthetic below Sierpinski-caliber (no reflection layer) | durf | 4 | delta | M |
| **AUDIT-14** | LORE-MVP wards are text-in-a-box (chiron grammar) | lore | 4 | delta | M |
| **AUDIT-20** | Inflection bus → impingement bus QM2 infra unused | ops | 4 | beta | M |
| **AUDIT-24** | onboarding-delta.md body conceptually stale | relay | 4 | beta | M |
| **AUDIT-13** | DURF privileged ward inside unprivileged scrim contradiction | scrim | 3 | delta + epsilon | S |
| **AUDIT-15** | LORE wards registered but unplaced in `default.json` | lore | 3 | delta | S |
| **AUDIT-21** | SHA-pinned-URL primitive only consumed by OMG; promote as redistributable-asset bridge | ops | 3 | epsilon | M |
| **AUDIT-25** | alpha.yaml duplicate top-level keys; beta.yaml bloat (565 lines) | relay | 3 | beta | S |
| **AUDIT-11** | `test_default_layout_render_stage_pins.py` docstring stale + self-contradictory | scrim | 2 | delta | S |

#### 3.4.4 Retired (already shipped)

| ID | Title | Disposition |
|---|---|---|
| **AUDIT-28** | HPX003+HPX004 to pre-commit + CI | **SHIPPED #1358 — DO NOT RE-ADD** |
| **AUDIT-26** | Claim-before-parallel-work hook proposal | **FOLDED into AUDIT-06** (proposal-twin) |

#### 3.4.5 Per-row scope, acceptance criteria, dependencies

For implementation reviewers — the full upstream-row content per audit ID:

**AUDIT-01 — DURF pixel capture redaction**
- Scope: `agents/studio_compositor/durf_source.py` (~472 LOC); spec contradiction with `docs/research/2026-04-24-durf-design.md` §5; possible new helper module for OCR-hashing/pattern redaction (~150 LOC); test additions in `tests/studio_compositor/test_durf_source.py`.
- Acceptance: Phase 2 capture path exposes a `_redact()` callable invoked between grim PNG load and Cairo composite (bypass via `HAPAX_DURF_RAW=1`); regression test on fixture PNG with `sk-ant-` patterns; DURF refuses on `consent-state.txt = consent-safe`; spec §5 contradiction resolved before flag default-on.
- Dependencies: none structural; underlying `durf_source.py` already on main. Unblocks DURF default-on flip; per upstream linkage AUDIT-13 + AUDIT-12.

**AUDIT-02 — Phase 6 inline LRs bypass HPX003**
- Scope: `agents/hapax_daimonion/system_degraded_engine.py:54-66` (4 inline signals); `speaker_is_operator_engine.py`; `shared/lr_registry.yaml` (148 LOC, missing `system_degraded_*` and `speaker_is_operator` clusters); `scripts/check-claim-registry.py` AST-walk extension (~40 LOC).
- Acceptance: lr_registry has `engine_queue_depth_high`, `drift_significant`, `gpu_pressure_high`, `director_cadence_missed` validated by LRDerivation; prior_provenance has `system_degraded` claim entry; HPX003 AST-walks `agents/**/*.py` for `DEFAULT_SIGNAL_WEIGHTS: dict` literals and fails on missing registry entries; new test passes.
- Dependencies: #1358. Unblocks: AUDIT-19; Phase 6c migration confidence.

**AUDIT-03 — Phase 5 RefusalGate zero call sites**
- Scope: `shared/claim_refusal.py` (~260 LOC); 4 narration surfaces — `director_loop.py:1969`, `conversation_pipeline.py:281`, `persona.py:288`, `autonomous_narrative/compose.py:164`; posterior-lookup helper.
- Acceptance: `grep RefusalGate agents/` ≥4 hits; each surface calls `RefusalGate(surface=...).check(text, claim_lookup)` post-emission; rejected → 1 re-roll → `[UNKNOWN]` envelope sentinel; Langfuse `claim_discipline` score per emission; per-surface rejection-rate Prometheus gauge.
- Dependencies: Phase 4 (#1347 merged), Phase 6 cluster engines (in flight). Unblocks: Phase 7 T1-T8 posteriors; gate 19 (refusal-rate dashboard).

**AUDIT-04 — Phase 4 envelope ships empty claim lists**
- Scope: 4 sites — `director_loop.py:1969`, `conversation_pipeline.py:281`, `persona.py:288`, `autonomous_narrative/compose.py:164`; per-surface posterior-source resolver (~80 LOC); Phase 6 cluster engine wiring per surface.
- Acceptance: each `render_envelope([], floor=...)` replaced with `render_envelope(_collect_relevant_claims(surface, ts), floor=...)`; reads from `ClaimRegistry` populated by Phase 6a/6b/6c/6d engines; director surface shows ≥3 non-empty claims under live broadcast (snapshot test); persona surface shows speaker_is_operator + presence claims minimum.
- Dependencies: AUDIT-02; Phase 6a (delta) + 6b (alpha) + 6c (epsilon) + 6d (beta) cluster engines. Unblocks: AUDIT-03 posterior lookup; Phase 7 T1-T8.

**AUDIT-05 — OMG ReferentPicker legal-name leak**
- Scope: 7 OMG modules (`agents/omg_credits_publisher/`, `omg_email_setup/`, `omg_now_sync/`, `omg_pastebin_publisher/`, `omg_purl_registrar/`, `omg_statuslog_poster/`, `omg_weblog_publisher/`, `omg_web_builder/`, `omg_weblog_composer/`); `shared/operator_referent.py` (~70 LOC, picker exists); `shared/governance/publication_allowlist.py` (262 LOC contract loader exists).
- Acceptance: `grep OperatorReferentPicker|operator_referent agents/omg_*/` ≥7 hits; every templated post substitutes `{operator}` via `OperatorReferentPicker.pick_for_vod_segment(<post-id>)`; new regression test `tests/governance/test_omg_no_legal_name.py` asserts rendered output of every OMG composer over fixture impingement contains zero matches against operator's legal name; publication contracts `redactions:` lists include legal name pattern.
- Dependencies: none. Unblocks: AUDIT-29; ytb-OMG cascade Phase D+ on safe footing.

**AUDIT-06+26 — Claim-before-parallel-work hook implementation**
- Scope: `hooks/scripts/relay-coordination-check.sh` (~120 LOC, currently advisory-only); session yaml claims block schema in 4 yamls; new lock primitive at `~/.cache/hapax/relay/claims/{path-slug}.lock`.
- Acceptance: `relay-coordination-check.sh` exits non-zero (BLOCKS) when Edit/Write targets a path under watched-prefix list AND another session's relay yaml advertises `currently_working_on.path_claim` overlap (bypass via `HAPAX_RELAY_CHECK_HOOK=0` or `HAPAX_INCIDENT=1`); each yaml gains `path_claims: [{path, until, reason}]` block; `cc-claim` sets it, `cc-close` clears; 30-min TTL on stale claims; test exercises block path with fake peer yaml.
- Dependencies: none. Unblocks: confidence in cross-lane Phase 6 wave.

**AUDIT-07 — Director Boolean vinyl predicate**
- Scope: `director_loop.py:942` (def), `:988` (`_curated_music_framing`), `:999` + `:2031` (consumers); new `agents/hapax_daimonion/vinyl_spinning_engine.py` (~250 LOC); `music_playing_engine.py` (~250 LOC compound noisy-OR per spec §10 layer 2); registry entries.
- Acceptance: VinylSpinningEngine + MusicPlayingEngine exist as `ClaimEngine[bool]` consumers; HPX003+HPX004 green; `_curated_music_framing` retired/stubbed; music-framing branch reads `MusicPlayingEngine.posterior` against per-surface floor; snapshot regression: legacy True now `MusicPlayingEngine.posterior > 0.7`; `tactical-fence-baseline-2026-04-24` git tag remains rollback target.
- Dependencies: Phase 0 FULL, Phase 1. Unblocks: Phase 2b YAMNet tap; AUDIT-19.

**AUDIT-08 — Spec divergence prior_provenance**
- Scope: `shared/claim.py:119`; spec `docs/research/2026-04-24-universal-bayesian-claim-confidence.md`.
- Acceptance: rename or amend spec; document at `docs/decisions/2026-04-25-prior-provenance-naming.md`; validator + Pydantic models reflect chosen name; test added.
- Dependencies: AUDIT-02.

**AUDIT-09 — bocd_hazard unconsumed**
- Scope: `shared/claim.py:76`; spec §6 BOCD mandate; zero consumers.
- Acceptance: option (a) BOCD wired into ClaimEngine state-transition dwell + PresenceEngine demonstrating use + regression test on synthetic changepoint; OR (b) field removed + spec §6 marked Phase-7-deferred.
- Dependencies: Phase 1. Unblocks: Phase 7 T6 changepoint-aware τ_mineness.

**AUDIT-10 — DURF spec §5 contradiction**
- Scope: Phase-2 path (grim window capture); spec §5.
- Acceptance: spec amendment recorded (retract §5 with operator directive justifying reversal OR Phase 2 reverted to text-only); `axioms/precedents/sp-su-durf-001-phase2-pixel-capture.yaml` records precedent (single_user axiom); decision-of-record cited in module docstring.
- Dependencies: AUDIT-01 redaction first; AUDIT-27 axiom precedent. Unblocks: clean DURF default-on flip.

**AUDIT-11 — Stale layout-pin docstring**
- Scope: module docstring lines 1-18 of `tests/test_default_layout_render_stage_pins.py`.
- Acceptance: module docstring rewritten to reflect current taxonomy from `z_plane_constants.WARD_Z_PLANE_DEFAULTS` (surface-scrim/mid-scrim/beyond-scrim); internal contradiction (sierpinski "substrate" vs "beyond-scrim") removed.
- Dependencies: none.

**AUDIT-12 — DURF aesthetic reflection layer**
- Scope: `durf_source.py` (Phase 3 deferral noted line 34); reflection layer addition (~200 LOC); `feedback_gem_aesthetic_bar` operator directive.
- Acceptance: reflection layer renders below captured panes (vertical mirror with linear alpha decay 1.0→0.0 over ~30% of pane height); slow temporal warp (cosine-modulated horizontal shear at 0.05 Hz, ≤4 px); operator visual review on smoke screenshot before flag flip; regression test asserts non-blank reflection region.
- Dependencies: AUDIT-01 (privacy first); AUDIT-13. Unblocks: DURF default-on consideration.

**AUDIT-13 — DURF privileged-ward-in-unprivileged-scrim**
- Scope: `z_plane_constants.py:54-66` (DURF surface-scrim pin); rationale comment block lines 59-65.
- Acceptance: decision recorded in `docs/decisions/2026-04-25-durf-z-plane.md` or scrim-taxonomy spec; if kept at surface, fronted-cycle alpha (0.94) clipped by depth-modulator; if moved, regression-tested against cycle visibility.
- Dependencies: AUDIT-12 visual review. Unblocks: scrim taxonomy clean closure.

**AUDIT-14 — LORE-MVP chiron grammar**
- Scope: `chronicle_ticker.py` (~308 LOC) + `programme_state_ward.py` (~302 LOC); `feedback_gem_aesthetic_bar`.
- Acceptance: each ward's render path replaces flat rect+text with ≥2 visual layers (signal-density grid behind text, algorithmic glyph progression, OR temporal smear of prior entries); text legible at broadcast 1080p (snapshot test); operator visual review before flag default-on.
- Dependencies: AUDIT-15. Unblocks: flag-on broadcast adoption.

**AUDIT-15 — LORE wards unplaced**
- Scope: `cairo_sources/__init__.py:160-170` (registration); `default.json` (798 LOC, zero LORE references).
- Acceptance: `default.json` adds 2 surface assignments (one per LORE ward) with documented bbox + z-plane + on-flag-only conditional; pin test extended; both wards render in slots when flags enabled.
- Dependencies: AUDIT-14 (prefer redesigned wards before placement). Unblocks: AUDIT-18 (director ↔ programmes).

**AUDIT-16 — gmail-sync filter → engine_queue_depth_high adapter**
- Scope: `logos/engine/watcher.py:81-100`; `system_degraded_engine.py` (signal `engine_queue_depth_high` declared line 58 but unwired); ~10-30 LOC adapter.
- Acceptance: SystemDegradedEngine receives observations from real signal (not synthetic); when queue depth crosses watermark for `enter_ticks` consecutive ticks, `state == "DEGRADED"`; new test validates contract end-to-end with faked queue; lr_registry has entry (also AUDIT-02).
- Dependencies: AUDIT-02; v3-final row 19. Unblocks: Phase 6d-i.B; 3499-004 closure.

**AUDIT-17 — Director cadence ↔ SystemDegradedEngine loop**
- Scope: `director_loop.py` cadence emission; `system_degraded_engine.py:64` (`director_cadence_missed` declared, unwired); ~30 LOC adapter on either end.
- Acceptance: when director skips ≥2 consecutive ticks while ≥1 impingement queued, observation flows to engine; when `state == "DEGRADED"`, director's cadence selector lengthens gap by documented multiplier (e.g. 1.5x); round-trip test asserts loop converges.
- Dependencies: AUDIT-02, AUDIT-16. Unblocks: AUDIT-19; cadence dashboard.

**AUDIT-18 — Director programme prompt slot**
- Scope: `director_loop.py:1116`, `:1775`, `:1784`; prompt construction starting `:1963` (no programme_band reference); `feedback_hapax_authors_programmes` + `project_programmes_enable_grounding`.
- Acceptance: director prompt builder appends programmes-aware section (`<active_programme>...</active_programme>`) when `_current_programme_band is not None` (programmes as soft prior, not hard gate); enumerates currently-recruited content programmes by name + brief description; snapshot test pins prompt body.
- Dependencies: AUDIT-19. Unblocks: AUDIT-19 (P(programme_active) feeds back); ef7b-164 content programming (alpha queue 2).

**AUDIT-19 — Programme-active meta-claim engine**
- Scope: new `agents/hapax_daimonion/programme_active_engine.py` (~250 LOC mirror of SystemDegradedEngine); registry entries; consumer in director prompt (AUDIT-18).
- Acceptance: ProgrammeActiveEngine exists as `ClaimEngine[bool]` per programme value (showcase/chronicle/ambient/...) — multi-class, one engine per active programme name; signals (time-of-day window, recent imagination salience, operator override); HPX003+HPX004 green; director prompt reads posteriors; rendering applies as soft priors not hard gates.
- Dependencies: AUDIT-02, AUDIT-18. Unblocks: content-programming layer; programmes-as-grounding-substrate.

**AUDIT-20 — Inflection→impingement bridge**
- Scope: `agents/quality_observability/impingement_sampler.py` (~120 LOC, QM2 #1293); relay inflections directory; new bridge `agents/inflection_to_impingement.py` (~80 LOC).
- Acceptance: bridge daemon tails `inflections/*.md` and emits Impingement per inflection event onto `/dev/shm/hapax-dmn/impingements.jsonl`; each emission has stable id, type, source filename; QM2 sampler shows non-zero rate after peer relay event in test; systemd user unit `hapax-inflection-bridge.service` ships.
- Dependencies: none (#1293 shipped). Unblocks: richer impingement-novelty score.

**AUDIT-21 — SHA-pinned-URL redistributable-asset bridge**
- Scope: `shared/aesthetic_library/loader.py` + `web_export.py`; `omg_credits_publisher/data.py:14` (sole consumer); other surfaces (`hapax_assets_publisher/`, `studio_compositor/album_overlay.py`).
- Acceptance: `web_export.py` documented in `docs/aesthetic-library/README.md` as canonical "redistributable-asset URL primitive"; ≥1 new consumer outside OMG; test asserts SHA-pinned URL bit-stable for fixture asset across runs.
- Dependencies: none. Unblocks: discovery of further surfaces.

**AUDIT-22 — Publication-contract redaction generalization**
- Scope: 16 contracts in `axioms/contracts/publication/`; `shared/governance/publication_allowlist.py` (262 LOC, has loader but no transform pipeline).
- Acceptance: `publication_allowlist.py` gains `RedactionTransform` registry (transforms registered by name: `legal_name`, `email_address`, `gps_coordinate`, applied per `redactions:` field uniformly); ≥3 transforms shipped + unit-tested; all 16 contracts converted from per-key string-literal to named-transform invocation; new linter (or `axiom-commit-scan.sh`) flags unknown transform names.
- Dependencies: AUDIT-05. Unblocks: dedup of per-surface redaction logic; safer addition of new outbound surfaces.

**AUDIT-23 — Alpha lane currency drift**
- Scope: v3-final §5 alpha queue (10 items); operator alpha vault claims; v3-delta-update.
- Acceptance: alpha queue refreshed from current vault `currently_working_on` + recently-merged PRs; line-by-line items kept-with-updated-status or moved to §3.1 Shipped/retired; currency disclosure paragraph under §1 (last-refresh ts + lane); PR review checklist asserts date-stamped refresh banner.
- Dependencies: none. Unblocks: confidence in alpha queue pulls. **Folded inline at §5.2 below; this row marks the prescription as a doc-maintenance item.**

**AUDIT-24 — onboarding-delta.md conceptual staleness**
- Scope: `~/.cache/hapax/relay/onboarding-delta.md` (~14.9 KB). 270s blockquote IS present (lines 27, 56, 95, 99); the "conceptually stale" charge survives (still describes delta as "coordinator + queue populator" while delta is now an implementer per delta.yaml — 3 PRs shipped this cycle).
- Acceptance: onboarding text refreshed to reflect 2026-04-24+ realities (cc-task vault SSOT D-30 Phase 4 active; HPX003+HPX004 in CI; Phase 4 envelope merged; Phase 6 wave in flight; concrete examples from this 24h); 270s blockquote retained verbatim; symmetric refresh of `onboarding-{alpha,beta,epsilon}.md`.
- Dependencies: none. Unblocks: new-session start quality.

**AUDIT-25 — Relay yaml duplicate keys + bloat**
- Scope: alpha.yaml (95 lines, duplicate `role:` and `currently_working_on:` keys — silent shadowing); beta.yaml (565 lines).
- Acceptance: alpha.yaml deduplicated (each top-level key once; yamllint rule or pre-commit hook flags duplicates); beta.yaml split into current-state ≤200 lines + archive at `~/.cache/hapax/relay/beta-archive-2026-04-24.yaml`; optional schema definition `~/.cache/hapax/relay/_session-schema.yaml`.
- Dependencies: none. Unblocks: automated relay-yaml validation downstream (AUDIT-06 schema bump).

**AUDIT-27 — Worktree-isolation axiom precedent**
- Scope: new `axioms/precedents/sp-su-005-worktree-isolation.yaml` (~30 LOC); cross-references `feedback_worktree_persistence.md`, `feedback_branch_discipline.md`, `hooks/scripts/no-stale-branches.sh`.
- Acceptance: precedent file exists with single_user axiom anchor; lists two 24h-window incidents (alpha #1347 recovery + beta Phase 1 recovery) and foreign-DURF-commit collision in alpha.yaml; decision: subagent code MUST NOT use isolated worktrees (no exceptions); `axiom-commit-scan.sh` recognizes precedent reference for grep-match logging.
- Dependencies: none. Unblocks: AUDIT-26 implementation reviewer cites precedent.

**AUDIT-29 — CODEOWNERS for operator_referent + speech_lexicon**
- Scope: `.github/CODEOWNERS`.
- Acceptance: add `shared/operator_referent.py @ryanklee` and `shared/speech_lexicon.py @ryanklee`; optionally `axioms/implications/non-formal-referent-policy.yaml @ryanklee`; auto-merge skips PRs touching either file.
- Dependencies: AUDIT-05 (make protection meaningful by ensuring usage is correct first). Unblocks: governance hygiene around two anonymity primitives.

**AUDIT-30 — Phase 2 MusicPlayingEngine STUB**
- Scope: new `agents/hapax_daimonion/music_playing_engine.py` STUB (~30 LOC API surface only); pairs with full Phase 2 (AUDIT-07).
- Acceptance: file with frozen API mirroring SystemDegradedEngine shape; stub raises NotImplementedError on contribute() until full lands; posterior returns prior; lr_registry + prior_provenance entries land alongside stub; HPX003+HPX004 green at stub-merge.
- Dependencies: Phase 0 FULL (#1341). Unblocks: AUDIT-07; Phase 2b draft can import stub today.

**AUDIT-31 — _should_skip → ignore_patterns**
- Scope: `logos/engine/watcher.py:81-100`.
- Acceptance: `_should_skip` rules ported to `PatternMatchingEventHandler.ignore_patterns`; benchmark: a sync that previously generated ~6,000 inotify events generates 0 watchdog callbacks; existing test ported to assert handler does not receive filtered events.
- Dependencies: v3-final row 19. Unblocks: logos-API event loop responsiveness during gmail-sync windows.

## 4. Critical-path edges (post-Phase-1, audit-incorporated)

```
[Phase 0 STUB #1341] → [Phase 0 FULL #1350] → [Phase 1 #1353]
                                                    │
                                                    ├─→ [AUDIT-02 lr_registry backfill, beta] ── HARD GATE for further 6x
                                                    │       │
                                                    │       ├─→ [Phase 6a, delta]              ← UNCLAIMED + AUDIT-30 STUB
                                                    │       ├─→ [Phase 6b, alpha]              ← UNCLAIMED
                                                    │       ├─→ [Phase 6c-i.A #1355 DONE]
                                                    │       │       └─→ [Phase 6c-i.B]         ← UNCLAIMED (handoff filed)
                                                    │       │               └─→ [Phase 6c-ii]
                                                    │       └─→ [Phase 6d-i.A #1357 DONE]
                                                    │               ├─→ [AUDIT-16 queue-depth wire-in, beta]
                                                    │               ├─→ [AUDIT-17 cadence loop, alpha+delta]
                                                    │               ├─→ [AUDIT-19 programme-active, beta] ── enables AUDIT-18
                                                    │               └─→ [Phase 6d-i.B/ii/iii]
                                                    │
                                                    └─→ [AUDIT-04 envelope claim-list wire, alpha]
                                                            ├─ depends on AUDIT-02 + each Phase 6 cluster engine
                                                            └─→ [AUDIT-03 RefusalGate wire-in, epsilon]
                                                                    └─→ [Phase 7 spec, alpha+beta]

[Phase 4 #1347] → [AUDIT-04 wires real claim sources]   ← envelope is structurally live but semantically empty until AUDIT-04
[Phase 5 #1344 + #1348] → [AUDIT-03 wires 4 surfaces]  ← gate is library-only until AUDIT-03

[HPX003+HPX004 #1358] → [AUDIT-02 AST-walk extension]    ← closes inline-LR loophole
                       → AUDIT-08 spec-vs-code naming reconcile

[#1349 DURF Phase 2] ← held by [AUDIT-01 redaction primitive]   ← NEW critical edge
                            ├─→ [AUDIT-10 spec §5 contradiction reconciled]
                            ├─→ [AUDIT-12 reflection layer for aesthetic floor]
                            └─→ [AUDIT-13 z-plane decision]

[AUDIT-27 axiom precedent] → [AUDIT-06+26 hook implementation]   ← precedent justifies hard-block
                                  └─→ [AUDIT-25 yaml dedup/split]   ← AUDIT-06 schema needs clean yamls

[OMG cascade outward publishing] ← held by [AUDIT-05 ReferentPicker wire-in]
                                       └─→ [AUDIT-22 redaction-transform pipeline]
                                       └─→ [AUDIT-29 CODEOWNERS gate]

[Phase 2 #unclaimed + AUDIT-07 + AUDIT-30 STUB] → [Phase 3 #unclaimed] → [Phase 2b #unclaimed]
                                                       ← delta lane, all unclaimed; saturation discussed in §6.1

[director cadence] → [AUDIT-17 bidirectional loop] → [SystemDegradedEngine state]
[director _current_programme_band] → [AUDIT-18 prompt slot] → [AUDIT-19 ProgrammeActiveEngine] → [Phase 6d cluster]

[gmail-sync #1354] → [AUDIT-31 _should_skip → ignore_patterns]   ← perf follow-up
                  → [AUDIT-16 wire to SystemDegradedEngine]      ← signal-side
```

The critical-path tension at v4 is **delta saturation, intensified by the audit fold**: AUDIT-01 (NEW, WSJF 13), AUDIT-07 + AUDIT-30 (NEW, WSJF 12+7), Phase 2 (WSJF 12), Phase 3 (WSJF 14), Phase 2b (WSJF 10), Phase 6a (WSJF 8), #1351 scope-resolution, AUDIT-10/-12/-13/-14/-15 DURF/LORE chain, the full HOMAGE twice-missed chain (rows 36–39), and Reverie 5-channel mixer all live in delta's queue. **AUDIT-07 elevates the case for redistribution: alpha takes Phase 2 outright (with AUDIT-30 STUB) so delta can focus on AUDIT-01 + AUDIT-07-implementation + #1351.** Trade-off in §6.1.

## 5. Per-session queues — refreshed (audit-incorporated)

### 5.1 beta (top 7, WSJF order)

1. **AUDIT-02 — HPX003 AST-walk extension + lr_registry backfill** — WSJF 11. Closes inline-LR loophole that may have grandfathered #1355/#1357. Unblocks AUDIT-04 dependency chain.
2. **AUDIT-06+26 — claim-before-parallel-work hook implementation** — WSJF 11. AUDIT-27 precedent justifies; AUDIT-25 yaml dedup is precondition. ~1-2 ticks.
3. **Audit catchup, slow post-merge (advisory)** — #1342, #1344, #1345, #1347, #1352, #1355, #1357 (7 PRs). Standard beta-lane discipline: one per tick. Catchup tail is what beta does between major moves.
4. **Phase 7 research-spec-plan, co-author with alpha** — τ_mineness threshold + per-element provenance strength; closes FINDING-X 54% empty-provenance baseline. WSJF 11.
5. **Phase 6d-i.B + 6d-ii + 6d-iii** — consent + budget + degradation cascade extension of #1357. Lane-canonical. WSJF 6 (carried). **Now coupled with AUDIT-16 (queue-depth signal wire) and AUDIT-19 (programme-active meta-claim).**
6. **AUDIT-23 + AUDIT-24 + AUDIT-25 (relay/doc maintenance bundle)** — alpha-currency refresh + onboarding refresh + yaml dedup. WSJF 5+4+3 = single bundle of ~3-5 ticks total. AUDIT-25 is precondition for AUDIT-06 schema.
7. **AUDIT-31 _should_skip → ignore_patterns** — WSJF 6, follow-up to #1354. Single-file change in `logos/engine/watcher.py`. 1 tick.

**Standing for beta:** 1d79-085 beta-substrate-execution-chain; ytb-OMG9 infra; #1292 QM1 follow-on; **AUDIT-08 (spec-vs-code prior_provenance naming) WSJF 4; AUDIT-09 (bocd_hazard) WSJF 5; AUDIT-20 (inflection bridge) WSJF 4** as filler ticks.

### 5.2 alpha (top 5, WSJF order)

> AUDIT-23 confirms alpha.yaml is the staleest of the four (~5h). Refreshed below by removing items shipped per `alpha.yaml.prs_merged_this_session` and surfacing what's actually unclaimed.

1. **AUDIT-04 — Phase 4 envelope wires real claim lists** — WSJF 10. CRITICAL — without it, Phase 4 (#1347) ships envelopes with `[]` claim lists at all 4 surfaces, so the per-surface floor table is operating on no signal. Alpha owns Phase 4 → alpha owns this fix. Depends on Phase 6 cluster engines, so co-staged with Phase 6b.
2. **DEVIATION-025 P0 Langfuse score calls** — WSJF 13, data-loss-critical. **Carried for 3 versions without claim.** Decision needed: alpha picks it up this tick OR reassign to beta (observability lane). Per "no operator-approval waits" + "stall ≫ revert" — if alpha doesn't claim by next tick, beta auto-reassigns.
3. **Phase 6b mood/stimmung claims migration** — lane-canonical post-Phase-1. WSJF 8. **No blocker.** Required for AUDIT-04 persona-surface claim list.
4. **AUDIT-18 director programme prompt slot** — WSJF 7. Single-file change in `director_loop.py`. Pairs with AUDIT-19 (beta).
5. **ef7b-164 content programming** — WSJF 12. Operator load-bearing directive (per v3-final). **AUDIT-18 + AUDIT-19 complete this surface — when both ship, ef7b-164 is structurally enabled.**

**Standing for alpha:** Phase 7 share (voice-surface T1-T8) co-author with beta WSJF 11; **AUDIT-17 (cadence-loop director-side adapter, WSJF 6, paired with delta);** AUTH-PALETTE-MOKSHA (vault-claimed, asset-gated on Moksha .edc).

**Removed from alpha queue (refreshed per AUDIT-23):**
- ~~AUTH-HOMAGE default-flip (session-callable)~~ — DONE #1352
- ~~AUTH-GEAL bundle~~ — DONE #1290 + #1352
- ~~AUTH-PALETTE-MIRC~~ — DONE #1289
- ~~Phase 4 prompt envelope~~ — DONE #1347 (but AUDIT-04 sharpens scope, see queue row 1)
- ~~SS1 live-validation flip~~ — operator action; flag exists, awaiting `HAPAX_AUTONOMOUS_NARRATIVE_ENABLED=1`
- ~~ef7b-031 / ef7b-040 / ef7b-056 LRR Phase A trio~~ — carried at WSJF 5/3/3 in standing

### 5.3 delta (top 7, WSJF order — heavy lane)

1. **AUDIT-01 — DURF pixel capture redaction** — NEW, WSJF 13, **critical privacy** on live broadcast. Folded from upstream audit. Blocks DURF default-on; held #1349 and #1351 effectively.
2. **AUDIT-07 + AUDIT-30 — Vinyl Boolean → MusicPlayingEngine + STUB** — NEW pair, WSJF 12+7. AUDIT-30 STUB is a 1-tick precondition (paired with delta-owns-Phase-2; if alpha takes Phase 2 per §6, AUDIT-30 owner shifts too). AUDIT-07 implementation is the full Phase 2 retire path.
3. **Phase 3 frame-for-llm split** — WSJF 14, dominant MF-DOOM fix; closes OCR-mediated modality dominance attack surface (medRxiv 2026-02-22; OWASP LLM01:2025).
4. **#1351 scope-resolution** — drop docs + DURF overlap, keep bed-music rotation flip as Workstream B. Session-callable. ~30 min.
5. **Phase 2 vinyl/music cluster + pgmpy** — WSJF 12. **Trade-off candidate: recommend alpha co-authors or takes outright; see §6.1.**
6. **Phase 6a activity claims migration** — WSJF 8, lane-canonical.
7. **AUDIT-12 + AUDIT-13 + AUDIT-14 + AUDIT-15 — DURF/LORE aesthetic + placement bundle** — WSJF 4+3+4+3 = single bundle of ~3-4 ticks. AUDIT-12 (DURF reflection) blocked by AUDIT-01. AUDIT-13 (z-plane decision) blocked by AUDIT-12. AUDIT-14 (LORE redesign) is independent. AUDIT-15 (LORE placement) blocked by AUDIT-14.

**Standing for delta (carried from v3-final §5.3 + audit additions):** Phase 2b (WSJF 10), ef7b-212 (WSJF 11), ef7b-213 (WSJF 11), scrim-taxonomy ef7b-174 with epsilon, HOMAGE twice-missed chain (#162/#163/#176/#177/#186/#189 + ef7b-099/106/112), Reverie 5-channel mixer wiring, **AUDIT-10 (spec §5 retraction, paired with epsilon) WSJF 7, AUDIT-11 (stale layout-pin docstring) WSJF 2, AUDIT-17 (cadence-loop signal-source side, paired with alpha) WSJF 6**, ytb-003 thumbnail, ytb-009 captions, mobile-substream, lssh-* retirements, 4 main-red follow-ups, ytb-LORE-EXT, ytb-012 Shorts.

### 5.4 epsilon (top 6, WSJF order — momentum lane)

1. **AUDIT-05 — OMG ReferentPicker legal-name leak** — NEW, WSJF 13, **operator existential-risk class**; cheap fix. 7 OMG modules + regression test + contract redaction lists. **Blocks all OMG cascade outward publishing until shipped.**
2. **AUDIT-03 — RefusalGate wire-in to 4 narration surfaces** — NEW, WSJF 9, library-only currently. ~3-4 ticks (per-surface posterior-lookup helper + 4 wire-in sites + per-surface rejection-rate gauge).
3. **Phase 6c-i.B perception_loop wire-in** — single-surface change at `perception_loop.py:214`. Handoff filed. ~15 min implementation. Continues #1355 → integration.
4. **Phase 6c-ii chat-author multi-source noisy-OR** — governance-sensitive (touches `shared/attribution.py`, `shared/governance/qdrant_gate.py`); beta pre-merge audit. WSJF 7.
5. **AUDIT-27 + AUDIT-29 — axiom precedent + CODEOWNERS bundle** — WSJF 6+5 = ~1-2 ticks. AUDIT-27 unblocks AUDIT-06+26 (beta queue 2). AUDIT-29 hardens AUDIT-05 protection retrospectively.
6. **AUDIT-22 — Publication-contract redaction-transform pipeline** — WSJF 5, depends on AUDIT-05. Generalizes redaction across 16 contracts.

**Standing for epsilon (carried + audit additions):** scrim-taxonomy ef7b-174 with delta; 60f6-021..027 7-task gaps chain; AUTH-ENLIGHTENMENT Phase 2 + Moksha enum follow-on (asset-gated); AUTH-PALETTE Phase 2 Moksha .edc loader (WSJF 4.5); HOMAGE F3/F4/F5 share (WSJF 4); OMG6 remaining phases + OMG8 Phase A (WSJF 3-4); **AUDIT-10 spec §5 retraction (paired with delta) WSJF 7; AUDIT-13 z-plane decision (paired with delta) WSJF 3; AUDIT-21 SHA-pinned-URL bridge promotion WSJF 3.**

## 6. Trade-offs and redistributions

### 6.1 Delta saturation, intensified by audit fold

Delta's WSJF-ordered top 7 sums to roughly 13 + 12 + 7 + 14 + (small) + 12 + 8 + (small bundle ~14) = 80 WSJF-points of P1 work plus the entire HOMAGE chain in standing. Alpha's top 5 (audit-incorporated) sums to 10 + 13 + 8 + 7 + 12 = 50. Beta's top 7 sums to 11 + 11 + (small) + 11 + 6 + (small bundle ~12) + 6 = 57. Epsilon's top 6 sums to 13 + 9 + (small) + 7 + 11 + 5 = 45.

**Recommendation: alpha takes Phase 2 outright + AUDIT-30 STUB.** Alpha already drafts against Phase 0 STUB imports per v3-final §6 step 3a; AUDIT-30 (a 30-LOC API-surface stub mirroring SystemDegradedEngine) is a natural alpha pickup before AUDIT-07's full implementation. The artifact is closer to alpha's hand than to delta's. **Delta keeps Phase 3 + Phase 2b + AUDIT-01 + AUDIT-07-full + #1351; alpha gains Phase 2 + AUDIT-30 in exchange for surrendering DEVIATION-025 P0 to beta** (per §5.2 row 2 escalation). Net: delta loses 12+7=19 WSJF, alpha is net +12+7-13 = +6 WSJF, beta +13.

**Beta takes AUDIT-31 outright.** `logos/engine/watcher.py` is beta's lane (3499-004 #1354 was beta), so AUDIT-31's `_should_skip → ignore_patterns` follow-up is beta-canonical regardless of delta saturation.

**This is session-callable.** Beta proposes; sessions decide on next-tick yamls.

### 6.2 #1349 DURF Phase 2 hold

#1349 has auto-merge armed and CI in-flight. Without AUDIT-01 redaction, merging exposes the privacy regression on the live broadcast surface. **Recommendation: beta disarms auto-merge on #1349 until either (a) AUDIT-01 redaction primitive is at minimum scoped + scheduled, or (b) explicit operator override.** This is a beta-callable safety hold consistent with verify-before-claiming-done (principle #9).

### 6.3 DEVIATION-025 P0 carry

DEVIATION-025 P0 Langfuse score calls have been the highest-WSJF unclaimed alpha item across v3-draft / v3-final / v3-delta — three queue-revisions, no claim. Two readings:
- Reading A: alpha is genuinely saturated and the WSJF rank is nominal-only.
- Reading B: the framing ("data-loss-critical, every Phase A session without this = permanent data loss for Claim 5") may be overstated; in 24h of unclaimed status, no apparent data-loss incident has surfaced.

Per "exhaust research before solutioning" (operator feedback) — both readings would benefit from alpha-side enumeration of what data is actually being lost vs what is recoverable. Held for next-tick alpha decision; if no claim at v5, beta auto-reassigns to its own lane. **Reinforced by §6.1 trade-off: if alpha takes Phase 2, alpha surrenders DEVIATION-025 P0 to beta in the same trade.**

### 6.4 OMG cascade outward-publishing freeze

Per AUDIT-05, OMG cascade publishes outward without operator referent picker — every templated post that interpolates `{operator}` may leak the legal name. **Recommendation: epsilon disarms auto-merge on any OMG-cascade PR until AUDIT-05 ships + AUDIT-29 CODEOWNERS lands.** Phase D+ of `ytb-OMG` cascade is on hold this tick. Existing merged OMG modules need a regression scan as part of AUDIT-05 acceptance.

### 6.5 AUDIT-04/AUDIT-03 wire-in dependency

Phase 4 envelope (#1347) and Phase 5 RefusalGate (#1344) both shipped as library-only — neither is end-to-end wired. AUDIT-04 (alpha) + AUDIT-03 (epsilon) close that gap. **They have a logical ordering: AUDIT-04 wires real claim-list sources first, then AUDIT-03 reads those sources from posterior lookup at refusal time.** Epsilon should wait on AUDIT-04 before completing AUDIT-03's posterior-lookup helper, OR both can proceed in parallel with the helper stubbed against the live `ClaimRegistry` API. Recommend parallel — `ClaimRegistry` shape is frozen at Phase 0 FULL.

## 7. Robustness gates

### 7.1 In force at v4 (incremental over v3-final)

In addition to v3-final §7's gates 1-23:

- **`HPX003` ruff rule (active)** — Claim constructor without matching LRDerivation entry. Wired to CI at #1358. **AUDIT-02 extends to AST-walk for `DEFAULT_SIGNAL_WEIGHTS: dict` literals.**
- **`HPX004` ruff rule (active)** — Claim without reconstructible `prior_provenance.yaml` record. Wired to CI at #1358.
- **`HAPAX_BAYESIAN_BYPASS=1`** — single kill-switch flag, **active** at Phase 0 FULL.
- **Phase 5 refusal-gate Langfuse `claim_discipline` score** — active at #1344. **AUDIT-03 will raise call-site count from 0 to ≥4 surfaces.**
- **Tactical-fence-baseline-2026-04-24 git tag** — at #1336 merge SHA; rollback target if Phase 2/3 regresses.

### 7.2 Phase-gated additions surfaced by v4

- **`HAPAX_DURF_RAW=1` bypass flag (proposed under AUDIT-01)** — explicit-opt-in to skip redaction; default unset, redaction-on. Active at AUDIT-01 ship.
- **`test_durf_consent_safe_suppression` regression test** — DURF refuses to start when `consent-state.txt = consent-safe`. Active at AUDIT-01 ship.
- **`test_omg_no_legal_name.py` regression test** — every OMG composer's rendered output over fixture impingement contains zero matches against operator legal name. Active at AUDIT-05 ship.
- **`HAPAX_RELAY_CHECK_HOOK=0` bypass flag (proposed under AUDIT-06+26)** — explicit-opt-out for incident-response paths; advisory mode otherwise. Active at AUDIT-06+26 ship.
- **`relay-coordination-check.sh` PreToolUse hook (proposed under AUDIT-06+26)** — blocks Edit/Write when path overlaps another session's `currently_working_on.path_claim`. Active at AUDIT-06+26 ship.
- **HPX003+HPX004 retroactive verification** (per AUDIT-02) — beta to verify #1355 + #1357 against the post-#1358 CI; AST-walk extension closes inline-LR loophole. ~30 min check + ~40 LOC extension. Active at AUDIT-02 ship.
- **`RedactionTransform` registry (proposed under AUDIT-22)** — named transforms applied across 16 publication contracts. ≥3 transforms shipped (legal_name, email_address, gps_coordinate). Active at AUDIT-22 ship.
- **`HAPAX_DURF_FORCE_ON` retirement gate (proposed under AUDIT-12)** — DURF default-on requires AUDIT-01 + AUDIT-12 + AUDIT-13 all shipped + operator visual review on smoke screenshot.
- **Per-surface refusal-rate Prometheus gauge (proposed under AUDIT-03)** — `refusal_rate_total{surface=...}` at each of director / conversation / persona / autonomous_narrative. Active at AUDIT-03 ship.
- **`P(programme_active=showcase|t)` posterior dashboard (proposed under AUDIT-19)** — Grafana panel reading ProgrammeActiveEngine posteriors per programme name. Active at AUDIT-19 ship.

## 8. Instrumentation

Unchanged from v3-final §8 + v3-delta §6. Phase-gated additions intact (Claim-posterior dashboard at Phase 1 = active; LR-registry drift dashboard at Phase 0 FULL = active; Refusal-rate dashboard at Phase 5 = active, but library-only until AUDIT-03; **Programme-active per-class posterior dashboard newly proposed under AUDIT-19;** **Inflection-event impingement-rate gauge proposed under AUDIT-20**).

## 9. Outstanding from v3-final + v3-delta

| Item | State at v4 |
|---|---|
| Audit catchup on #1342/1344/1345/1347 | Carried + extended to #1352/#1355/#1357 — beta queue P1 |
| Phase 7 research-spec-plan | Not started; alpha+beta co-author |
| 17 unscheduled research drops + 4 spec triage items | Unchanged from v3-final §3.4/§3.5 |
| HOMAGE twice-missed chain (#162/#163/#176/#177/#186/#189) | Unchanged; delta standing |
| 60f6-021..027 7-task gaps chain | Unchanged; epsilon standing |
| Worktree-collision codification | **AUDIT-27 axiom precedent + AUDIT-06+26 hook implementation close this** |
| Re-WSJF of full queue | Partial in v4 (Bayesian phases + 30 audit rows folded); tail items keep v3-final WSJF |

## 10. Audit-incorporation census (round 2)

Round 1 of v4 received only AUDIT-01 in full and held 29 rows as `[ROW NOT DELIVERED]`. Round 2 (this revision) received the verbatim text of AUDIT-02..AUDIT-31 directly from the upstream research agent's output and folded each.

**Final fold:**
- **30 rows** in scope (AUDIT-01..AUDIT-31, with AUDIT-26 folded as one with AUDIT-06)
- **30 rows folded** into census tables, dependency edges, per-session queues, and trade-offs
- **0 placeholders** remaining
- **AUDIT-28 retired** as already-shipped (#1358); not re-entered
- **AUDIT-26 merged with AUDIT-06** per upstream's own note (proposal-twin of implementation)

**WSJF distribution of folded audit rows:**
- Critical (≥11): 7 rows — AUDIT-01, -02, -03, -04, -05, -06+26, -07
- Synergy (5-7): 12 rows — AUDIT-09, -10, -16, -17, -18, -19, -22, -23, -27, -29, -30, -31
- Aesthetic / doc / minor (≤4): 9 rows — AUDIT-08, -11, -12, -13, -14, -15, -20, -21, -24, -25
- Retired (shipped): 1 row — AUDIT-28
- Folded with another row: 1 row — AUDIT-26 → AUDIT-06

**Per-session audit-fold load:**
- alpha: 3 rows (AUDIT-04 critical; AUDIT-17 + AUDIT-18 synergy)
- beta: 11 rows (AUDIT-02 + AUDIT-06+26 critical; AUDIT-08 + AUDIT-09 + AUDIT-16 + AUDIT-19 + AUDIT-20 + AUDIT-23 + AUDIT-24 + AUDIT-25 + AUDIT-31 synergy/doc)
- delta: 9 rows (AUDIT-01 + AUDIT-07 critical; AUDIT-10 + AUDIT-11 + AUDIT-12 + AUDIT-13 + AUDIT-14 + AUDIT-15 + AUDIT-30 synergy/aesthetic)
- epsilon: 6 rows (AUDIT-03 + AUDIT-05 critical; AUDIT-21 + AUDIT-22 + AUDIT-27 + AUDIT-29 synergy)

The asymmetry — beta with 11 rows, delta with 9 — is misleading without effort weighting. Beta's audit-fold is mostly small / single-file (AUDIT-08/-09/-20/-23/-24/-25/-31 are all S-or-bundleable). Delta's audit-fold is mostly M-effort or paired-with-Phase-2 (AUDIT-12/-14 are M; AUDIT-30 pairs with AUDIT-07 full). The §6.1 trade-off (alpha takes Phase 2 + AUDIT-30) compensates partially.

## 11. Open questions (v4-introduced + audit-derived)

In addition to v3-final §12's five surviving questions:

6. **Phase 2 ownership** — alpha-take-outright (with AUDIT-30 stub) vs delta-keep-with-alpha-co-author. Trade-off rationale in §6.1; session-callable on next-tick yamls. **Audit fold sharpens: AUDIT-30 STUB is a natural alpha pickup; AUDIT-07 full is the same Phase 2 retire path.**
7. **#1349 hold-vs-merge** — does AUDIT-01 redaction need to land BEFORE #1349 merges, or is "scoped + scheduled" sufficient? §6.2 proposes the looser bar; tightening to "shipped" extends the hold ~1-3 ticks.
8. **DEVIATION-025 P0 reading** — A (genuinely saturated) or B (framing overstated). §6.3 proposes alpha-or-beta forced-choice on next tick; either alpha claims or beta auto-takes. **Reinforced by §6.1: alpha-takes-Phase-2 is conditional on alpha surrendering DEVIATION-025 P0.**
9. **AUDIT-09 option (a) vs (b)** — wire BOCD into ClaimEngine state-transition dwell + PresenceEngine demonstration (multi-day work) vs remove the field + spec §6 marked Phase-7-deferred (<1 tick). Recommend (b) for v4-tick velocity; reintroduce as Phase 7 work if τ_mineness research surfaces a need.
10. **AUDIT-19 multi-class engine pattern** — one engine per programme name (showcase, chronicle, ambient, ...) is multi-class, not multi-instance. Spec §10 layer 2 currently models compound noisy-OR for boolean. Either AUDIT-19 extends spec to multi-class or wraps multi-class as bool-per-class. Defer decision to AUDIT-19 implementer.
11. **OMG cascade freeze duration** — AUDIT-05 + AUDIT-29 + AUDIT-22 form the safe-publishing bundle. Should the freeze remain until all three ship, or is AUDIT-05-only sufficient? Recommend AUDIT-05-only blocks new outward posts; AUDIT-22 + AUDIT-29 can land after as hardening.

## 12. Broadcast plan

On completion of this document:
1. File the doc at `docs/operations/2026-04-25-workstream-realignment-v4-audit-incorporated.md` (this file).
2. Beta commits + opens PR + admin-merges (per user spec — beta owns commit + PR cycle, not this drafting session).
3. Per-session dispatches: beta-to-{alpha,delta,epsilon}-2026-04-25T021500Z-realigned-queue-v4.md (one each, summarizing top-5 per lane + trade-offs from §6 + audit-row references).
4. Broadcast inflection at `~/.cache/hapax/relay/inflections/20260425T021500Z-beta-all-workstream-realignment-v4-audit-incorporated.md`.
5. Schedule 270s wake; monitor peer adoption + #1349 CI + #1351 scope-resolution + AUDIT-01/05/07 claim activity.

— beta (drafted), 2026-04-25T02:15Z; rev workstream-weaver round 2, 2026-04-25T02:55Z (audit fold complete)
