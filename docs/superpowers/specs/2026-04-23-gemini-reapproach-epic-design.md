# Gemini Re-Approach Epic — Design

**Date:** 2026-04-23
**Follow-up to:** `2026-04-23-gemini-audit-remediation-design.md` (Phase 1-5 merged: #1225–#1229)
**Scope:** Re-approach the feature work Gemini attempted but which had to be reverted or was left as a ghost PR, grounded in operator-stated intent from Gemini's transcripts and any salvageable Gemini material.

## Salvaged artifacts (reachable via reflog from dropped stash `5cc531c3a`)

All recoverable by `git show <blob>`:
- `content_programmer.py` at `git show 7b96fccb7:agents/showrunner/content_programmer.py` — Gemini's 187-line Showrunner daemon (reverted commit)
- `d4a4b0113` diff — Gemini's first HOMAGE-layout pass (1159 lines, reverted)
- `28f68afc5` diff — Gemini's correction pass (118 lines, reverted)
- YouTube-cadence research doc at `git show da77cb43c:docs/research/2026-04-23-youtuber-cadence-techniques.md` (from stash's untracked-files tree) — delta-authored 4-archetype research (actually 3 distinct archetypes — see Epic A notes)

## Three epics + two polish gaps

### Epic A — Content Programming Layer / "Showrunner" (task #164)

**Operator-stated intent (2026-04-22 05:28 UTC):** Content programming has structure — segments with format + thesis + verbal script + screen directions, planned in advance. Director loop moves are *reactive* moves within a content-programming framework. "GROUNDING ATTEMPT RESEARCH PLATFORM" is the mission. "The outsource must not damage or pollute the grounding network. The outsourcing MUST NOT SEVER GROUNDING CHAINS OR POLLUTE GROUNDING ATTEMPTS." At 06:23 UTC: "Create formal design docs, specs, plans and then implement" on "opus 3.6."

**What Gemini did wrong:**
- Bypassed the existing `ProgrammePlanner` / `ProgrammePlanStore` / `ProgrammeManager` infrastructure entirely.
- Wrote directly to `/dev/shm/hapax-daimonion/recruitment-log.jsonl` with score=0.99, fabricating `AffordancePipeline` decisions (Ring-2 bypass, `project_unified_recruitment` constitutional violation).
- Injected "MANDATORY VERBAL SCRIPT" into the director prompt, dictating speech (violates `programmes_enable_grounding`: programmes are affordance-*expanders*, not replacers).
- Hardcoded absolute path in `sys.path.insert` — worktree-hostile.
- Used `model="custom_openai/claude-opus"` — not a LiteLLM route; operator specified "opus 3.6" which requires adding a `showrunner` alias in `shared/config.py`.

**What's salvageable:**
- Segment → Beat → screen_directions *schema* is correct. Format + thesis + verbal_script + beats are the right primitives.
- "Relatable YouTube format BUT TWISTED AROUND" prompt constraint matches operator [05:45:43Z] directive; preserve verbatim.
- `response_format={"type":"json_object"}` + markdown-fence fallback — sensible robustness.
- Three cadence archetypes from the research doc (Clinical Pause / Freeze-Frame Reaction / Percussive Glitch — the research header attributes Young Don + RM Brown to the same archetype so there is no distinct 4th) are a valid cadence ontology worth encoding as a soft-prior lookup.
- **Critical architectural finding** from the doc: *"visual pause, never stop ffmpeg"* — hiding YouTube via `camera_override` to `operator-brio.conversing`, not `SIGSTOP` ffmpeg. Preserves `feedback_never_drop_speech`.

**Design principles:**
1. Extend `agents/programme_manager/`, don't replace. Segment is a sub-programme primitive; Beat is a sub-segment primitive. Both go through existing lifecycle / abort-evaluator / outcome-log machinery.
2. Every `Beat.screen_directions_prior` is a dict of `capability_name → bias_multiplier` (soft prior through AffordancePipeline), never a direct dispatch.
3. No writes to `recruitment-log.jsonl` from outside the pipeline.
4. Director prompt gets a `## Current segment context` section rendering format / thesis / beat.narrative_goal / beat.verbal_script as **guidance**, never as mandatory script. Existing regression test `test_director_no_mandatory_script` already pins the invariant.
5. LiteLLM `balanced` alias initially (claude-sonnet). Operator ratifies Opus 3.6 / "showrunner" alias separately — ship on `balanced`, flip the route when green.

See **Plan A** for phase-by-phase execution.

### Epic B — HOMAGE Ward Layout Hardening

**Operator-stated intent (2026-04-23 06:34 → 13:01 UTC):**
- Fix default positioning to avoid occlusion.
- Optimize size by ward intent + content.
- "wards falling off the screen" (post-revert: analysis proves NO HOMAGE ward is geometrically off-frame; real issue is *overlap*).
- "no flashing. Audio reactivity is good. Blinking is bad."
- CBIP should be "highly transformed, dynamic, audio-reactive, visually interesting, indicative of the vinyl album + chessboard backdrop, NO flashing."
- Reduce reverie/sierpinski/CBIP by 10%.
- Fix sierpinski cropping.
- "HARDM totally reverted again" — the revert anxiety.

**What Gemini did wrong (reverted in #1225):**
- Deleted 4 Epic 2 Phase C hothouse wards from `default.json` (`impingement_cascade`, `recruitment_candidate_panel`, `activity_variety_log`, `grounding_provenance_ticker`) — unauthorized.
- Introduced alpha-beat-modulation (`paint_with_alpha(0.4 + beat_smooth * 0.3)`) — exact pattern `feedback_no_blinking_homage_wards` forbids.
- Duplicated scanline block in `album_overlay.py` (copy-paste bug overwrote the Step-4 shadow mask).
- Dropped `z_order` / `target` / `render_target` fields from `_FALLBACK_LAYOUT` video_outs — would break v4l2/RTMP/HLS if fallback ever loaded.
- Changed `layout.py` sierpinski scale 0.75 → 0.675 *after* `sierpinski_renderer.py` — one-file parity break (caught by operator as "cropped").

**What's salvageable from Gemini:**
- `28f68afc5`'s chromatic aberration core — R/G/B push_group/pop_group split, constant final `paint_with_alpha(ALPHA)`. Structurally sound; alpha is constant per-tick (allowed by `no_blinking_homage_wards`).
- The 10% reduction ratio (`SIZE 300→270`, `NATURAL_SIZE 300→270`, sierpinski 0.675) is defensible *if* applied atomically with scale-parity regression.

**Post-revert analysis — the ACTUAL gap is occlusion, not off-frame:**
- `thinking-indicator-tr` (1620,20 w=170 → 1790) overlaps `hardm-dot-matrix-ur` (1600,20 w=256 → 1856) at x=1620..1790, y=20..64.
- `stance-indicator-tr` (1800,24 w=100 → 1900) sits on top of HARDM.
- `captions_strip` (40,930 h=110 → 1040) collides with `gem-mural-bottom` (40,820 h=240 → 1060) — captions was supposed to be retired at GEM cutover 2026-04-21 but source + surface + assignment survive.
- Existing `test_thinking_indicator_z_above_hardm_avoids_occlusion` pins z-order dominance, but z-dominance is not enough — HARDM under the thinking text still loses information density. Operator wants spatial separation.

See **Plan B** for phase-by-phase execution.

### Epic C — FINDING-V Chat-Keywords Ward (task #180)

**Operator-stated intent:** No direct transcript — task queued from FINDING-V Q4. Existing research doc `docs/research/2026-04-20-chat-keywords-ward-design.md` specifies a `ChatKeywordsWard` rendering **topic texture** (what words recur across authors), distinct from `ChatAmbientWard` which renders rate/tier volume only. Three livestreams at identical rates produce identical ambient output — keyword surface disambiguates.

**Status:** FINDING-V publisher spec explicitly *deferred* this (§4.2 of `2026-04-21-finding-v-publishers-design.md`). Task #180 is the scope.

**Gap (neither end exists):**
- Producer: rolling-window keyword extractor with author-diversity weighting + stop-word filtering. Nothing writes this.
- Consumer: `ChatKeywordsWard` cairo source rendering topic texture. Not implemented.

**Legacy surface NOT to duplicate:** `legibility_sources.py::ChatKeywordLegendCairoSource` is a static HOMAGE-transitional fallback, not data-driven.

See **Plan C** for phase-by-phase execution.

### Gap 2 — LITELLM key DRY (shipped via PR #1229)

Already landed. Documented here for completeness.

### Gap 3 — Vinyl-empty prompt string

Research recommended **no change**. `director_loop.py:1982-1991` uses `_vinyl_is_playing()` (task #185, completed — a 3-signal gate reading override flag + album-cover confidence + hand-on-turntable freshness) to choose between two deterministic prompt strings. This is **perception**, not an expert rule — the same kind of grounded state the LLM cannot otherwise see. `feedback_no_expert_system_rules` governs *behavioral gates* (cadence timers, threshold cutoffs), not state reporting in prompts. Task #185 closed. No action.

## Model routing note

`shared/config.py:95` MODELS dict maps `balanced → claude-sonnet`. Operator directed "opus 3.6" for showrunner work. Adding a `showrunner` alias routing to claude-opus-3.6 is a config change that Epic A Phase 2 ships with a feature flag — the Segment planner runs on `balanced` until operator flips the flag.

## Scope boundaries (not in this epic)

- Audio repo/live reconcile (`voice-fx-loudnorm.conf`, `pc-loudnorm.conf`) — deferred as operator-discretion per Phase 4 of the audit remediation design.
- `hapax-usb-router.service` install-vs-delete — operator decision, not code.
- Task #186 token-pole: **research shows already shipped** (commits `cfff06e41`, `6afcde7bb`, `cf09f73e2`). Plan B Phase D just marks it closed with a goldens test.
- Task #178 FINDING-V orphan-consumer wards: 4/5 shipped pre-audit; Epic C addresses the last (chat-keywords).
- Task #191 GEM ward — separate epic already in flight.

## Success criteria

- Epic A Phase 1-2 ship: Segment primitive in-tree, SegmentPlanner+prompt under `agents/programme_manager/`, zero runtime integration until Phase 3 ratification.
- Epic B all 4 phases ship: no-occlusion invariant test passes live, scale-parity regression test pins layout.py ↔ sierpinski_renderer.py, CBIP audio-reactive without any alpha-beat modulation, token-pole task #186 marked closed with goldens test.
- Epic C both phases ship: `scripts/chat-keywords-producer.py` + systemd unit active; `ChatKeywordsWard` on the broadcast showing real keyword texture.
- All changes pass `feedback_no_expert_system_rules` + `feedback_grounding_exhaustive` + `feedback_no_blinking_homage_wards`.
