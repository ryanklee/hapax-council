# HSEA Phase 2 — Core Director Activities — Design Spec

**Date:** 2026-04-15
**Author:** delta (pre-staging extraction from HSEA epic spec per alpha's 06:20Z delegation of the operator directive "activities extraction, always be working")
**Status:** DRAFT pre-staging — awaiting operator sign-off + cross-epic dependency resolution before Phase 2 open
**Epic reference:** `docs/superpowers/specs/2026-04-14-hsea-epic-design.md` §5 Phase 2 (canonical source)
**Plan reference:** `docs/superpowers/plans/2026-04-15-hsea-phase-2-core-director-activities-plan.md` (companion TDD checkbox plan)
**Branch target:** `feat/hsea-phase-2-core-director-activities`
**Cross-epic authority:** `docs/research/2026-04-14-cross-epic-fold-in-lrr-hsea.md` (drop #62) — §3 ownership table, §5 unified sequence row UP-10, and §10 Q3 ratification (HSEA Phase 4 Cluster I rescoping) take precedence over any conflicting claim in this spec
**Unified phase mapping:** **UP-10 Core Director Activities** (drop #62 §5): depends on UP-1 (LRR research registry) + UP-2 (HSEA foundation primitives) + UP-9 (LRR Phase 7 persona spec); ~2,500 LOC across activity primitives + ReflectiveMomentScorer + calibration + director_loop wiring; ~3 sessions serial

---

## 1. Phase goal

Extend the director loop's `ACTIVITY_CAPABILITIES` taxonomy from 6 activities to 13 by adding the drafting, reflective, and synthesis activities that make the director a self-programming content generator on the livestream. Phase 2 is the infrastructure layer for every subsequent HSEA phase that produces text content — drafting drops (Phase 4 Cluster I narrators), synthesizing research (Phase 3 Cluster C), reviewing exemplars (Phase 7), and composing reflective moments.

**What this phase is:** 7 new activity modes (`draft`, `reflect`, `critique`, `patch` stub, `compose_drop`, `synthesize`, `exemplar_review`), the `ReflectiveMomentScorer` gate with a 7-day calibration window, and the `ACTIVITY_CAPABILITIES` taxonomy extension that plumbs the new activities through the director loop + reactor log + content scheduler + preset reactor.

**What this phase is NOT:** this phase does not ship the drop #58 Cluster I code-drafter full implementations (Phase 4), does not ship the Phase 7 exemplar pool population (LRR Phase 7 persona), does not wire the spawn pipeline that produces multi-agent findings (Phase 7), and does not ship the full `patch` activity implementation (Phase 4). Phase 2 ships the activity INFRASTRUCTURE — the taxonomy, the scorer, the schemas, and the director loop wiring. Deliverable 2.4 `patch` is a stub that returns "no patches available" until Phase 4 lands.

**Key drop #62 downstream dependency** (Q3 ratification 2026-04-15T05:35Z): HSEA Phase 4 Cluster I drafters I1/I2/I3/I4/I5 are demoted to narration-only spectator agents. They compose/subclass **deliverable 2.5 `compose_drop`** as their research-drop output stream. This makes 2.5 the load-bearing activity for the rescoped Phase 4 instead of a Phase-4-internal drafter base class. Phase 2 must ship 2.5 with enough structure that Phase 4 narrator drafters can plug in without re-authoring the compose pipeline.

---

## 2. Dependencies + preconditions

**Cross-epic (from drop #62):**

1. **LRR UP-0 (verification) closed** — standard HSEA phase precondition.
2. **LRR UP-1 (research registry) closed** — Phase 2 activities tag reactor log entries with `condition_id` (via the research marker established by LRR Phase 1 item 3). Deliverables 2.2 reflect, 2.3 critique, and 2.5 compose_drop all emit reactor log entries that must carry the current condition_id.
3. **HSEA UP-2 (foundation primitives) closed** — Phase 2 consumes multiple Phase 0 deliverables:
   - **0.2 governance queue**: deliverable 2.1 `draft` and 2.5 `compose_drop` write governance queue entries at completion time for operator review (the drafts become governance-queue items rather than direct commits).
   - **0.3 spawn budget**: all 7 new activities go through `SpawnBudgetLedger.check_can_spawn("<touch_point>")` before any LLM call. Phase 2 registers 7 new touch points in the budget configuration.
   - **0.4 promote scripts**: `scripts/promote-drop.sh` is the ratification vehicle for drafts produced by 2.1 + 2.5.
4. **LRR UP-9 (persona spec) closed** — Phase 2 activity prompts consume the persona spec (`axioms/persona/hapax-livestream.yaml` per LRR Phase 7). The persona is the voice/register that the new activities speak in. Per drop #62 §3 row 9, LRR Phase 7 owns the persona spec and Phase 2 reads it.
5. **HSEA UP-4 (visibility surfaces) closed** (desirable, not strict) — Phase 2 benefits from the HUD + governance queue overlay + glass-box prompt rendering that HSEA Phase 1 ships. Strictly speaking Phase 2 can ship without the surfaces, but without the glass-box prompt (HSEA Phase 1 deliverable 1.3), the new activities' prompt construction is unverifiable on stream. Recommend opening Phase 2 after Phase 1 closes, not before.

**Intra-epic:** all earlier HSEA phases (0 + 1) closed. This is the first HSEA phase that touches the director loop proper, not just primitives.

**Infrastructure:**

1. `agents/hapax_daimonion/director_loop.py` or equivalent — the existing director loop that hosts `ACTIVITY_CAPABILITIES` (verify exact file at open time).
2. `ACTIVITY_CAPABILITIES` taxonomy (existing, 6 entries) — Phase 2 extends to 13.
3. `agents/hapax_daimonion/persona.py` — existing persona prompt assembly; Phase 2 extends to describe each new activity.
4. Response schema (pydantic-ai `output_type`) — existing, Phase 2 extends with activity-specific fields (`noticed`, `intend`, `patch_target`, etc.).
5. `shared/atomic_io.atomic_write_json` (existing) — used for writing draft buffer partials.
6. `shared/research_marker.read_marker()` (LRR Phase 1 deliverable) — used to tag reactor log entries with condition_id.
7. `shared/governance_queue.py::GovernanceQueue` (HSEA Phase 0 deliverable 0.2) — receives draft and compose_drop entries.
8. `shared/spawn_budget.py::SpawnBudgetLedger` (HSEA Phase 0 deliverable 0.3) — gates all LLM calls.
9. `shared/config.py` model routes (`balanced`, `fast`, `coding`, `reasoning`) — Phase 2 activities use `balanced` for drafting by default, `fast` for reflect/critique, per the routing patterns established in the existing director loop.
10. `/dev/shm/hapax-compositor/draft-buffer/` directory (operator's workspace, created by Phase 0 0.4 inbox convention).
11. `reactor-log-YYYY-MM.jsonl` (existing; Phase 2 extends entry schema with `noticed` + `intend` fields for reflect/critique activities per LRR Phase 1 item 2 extension).
12. pydantic-ai agents using `output_type` + `result.output` per council conventions.

---

## 3. Deliverables

Each deliverable maps to an epic spec §5 Phase 2 item.

### 3.1 Activity taxonomy extension (item 2.8)

**Scope:**
- Extend `ACTIVITY_CAPABILITIES` from 6 entries to 13 by adding:
  - `draft` — compose research drops live (deliverable 3.2)
  - `reflect` — self-reflect on last 8 reactions (deliverable 3.3)
  - `critique` — self-critique recent activity with explicit pattern naming (deliverable 3.4)
  - `patch` — patch-proposal stub (deliverable 3.5; full impl in Phase 4)
  - `compose_drop` — synthesize multi-source findings into drop draft (deliverable 3.6)
  - `synthesize` — 30-word multi-agent consensus synthesis (deliverable 3.7)
  - `exemplar_review` — review own outputs against operator-flagged exemplars (deliverable 3.9)
- Update `agents/hapax_daimonion/persona.py` (or wherever the persona prompt is assembled) with per-activity description paragraphs
- Update the pydantic-ai response schema (`class DirectorActivityResponse(BaseModel)` or equivalent `output_type`) with activity-specific fields:
  - `activity: Literal["react", "draft", "reflect", "critique", "patch", "compose_drop", "synthesize", "exemplar_review", ...]`
  - `noticed: int | None` (required for reflect, critique)
  - `intend: str | None` (required for reflect, critique)
  - `draft_slug: str | None` (required for draft, compose_drop)
  - `patch_target: str | None` (placeholder for patch stub)
  - `synthesis_sources: list[str] | None` (required for synthesize)
  - `exemplar_id: str | None` (required for exemplar_review)
- Update downstream consumers to comprehend new types:
  - **Reactor log writer** — append new fields; backward compatible (missing fields → null)
  - **Content scheduler** — recognize new activity types for Cairo source activation (e.g., `DraftStreamCairoSource` activates when activity == "draft")
  - **Preset reactor** (`agents/studio_compositor/chat_reactor.py::PresetReactor`) — no changes needed; preset triggers are chat-driven, not activity-driven
- **Target files:**
  - `agents/hapax_daimonion/persona.py` or `director_loop.py` (extend `ACTIVITY_CAPABILITIES`)
  - `agents/hapax_daimonion/director_schema.py` (or wherever response schema lives; extend pydantic model)
  - `agents/hapax_daimonion/reactor_log_writer.py` (~30 LOC extension)
  - `agents/hapax_daimonion/content_scheduler.py` (~40 LOC extension)
  - `tests/hapax_daimonion/test_activity_taxonomy.py` (~150 LOC)
- **Deliverable size:** ~350 LOC, 0.5 day serial work

**Why this ships FIRST:** all other deliverables (3.2–3.9) depend on the `ACTIVITY_CAPABILITIES` list being extended. The extension itself is mechanical (add enum values, extend schema, update consumers). Once it's shipped, the individual activities can ship in any order without the "what activity type am I?" question being unresolvable.

### 3.2 `draft` activity (item 2.1 / A1)

**Scope:**
- New activity mode for composing research drops live
- Each tick extends `/dev/shm/hapax-compositor/draft-buffer/<slug>.partial.md` with ~300-600 additional characters
- LLM call via the `balanced` route (Claude Sonnet) with a 1-shot exemplar drawn from the existing `docs/research/` directory (pick a recent drop of similar scope)
- Prompt structure: persona header + current condition + recent reactions context + exemplar + "continue the drop, ~400 characters"
- Response schema: `DirectorActivityResponse(activity="draft", draft_slug="<slug>", ...)`; the drop text itself comes back in a free-text `content` field that gets appended to the partial
- Buffer promotion: when the operator approves via `promote-drop.sh <slug>` (HSEA Phase 0 0.4), the partial is moved to `docs/research/<date>-<slug>.md`
- **`DraftStreamCairoSource` character-reveal** (referenced in epic spec but ships as part of THIS deliverable since there's no separate slot for it):
  - New Cairo source that tails `<slug>.partial.md` and renders characters at a tuned rate
  - Rate: 80-240 chars/sec, modulated by stimmung `intensity` dimension (higher intensity → faster reveal)
  - Zone: center-stage content area (same zone as Phase 1's glass-box prompt if not already occupied)
  - Graceful handling: if the file is empty or missing, render a placeholder "composing..."
- **Spawn budget touch point:** `draft_activity` with per-call estimated cost ~$0.05 at `balanced` tier; max_concurrent=1
- **Governance queue entry:** when a draft reaches a completion threshold (~2000 characters OR operator manual flag OR director decides "done"), the activity writes a governance queue entry via `GovernanceQueue.append(type="research-drop", drafted_by="hapax-draft-activity", location="/dev/shm/hapax-compositor/draft-buffer/<slug>.partial.md", approval_path="operator inbox")`
- **Target files:**
  - `agents/hapax_daimonion/activities/draft.py` (~200 LOC activity handler)
  - `agents/studio_compositor/draft_stream_source.py` (~180 LOC Cairo reveal source)
  - `tests/hapax_daimonion/test_activity_draft.py` (~150 LOC)
  - `tests/studio_compositor/test_draft_stream_source.py` (~100 LOC)

**Size:** ~630 LOC, ~1 day serial work

### 3.3 `reflect` activity (item 2.2 / F2)

**Scope:**
- New activity reading the last 8 reactions + stimmung trajectory + current 9-dim state
- Prompt structure: enumerated reaction list (each with an explicit index 1-8) + stimmung delta over the window + current dimension values + persona header + "reflect on one of the enumerated reactions; you MUST specify the index"
- **Anti-slop constraint:** schema requires `noticed: int` in range [1, 8]. If the LLM returns a response without `noticed` set OR with `noticed` out of range, the response is REJECTED and the activity re-rolls (up to 3 retries before aborting)
- Response schema: `DirectorActivityResponse(activity="reflect", noticed=<int>, intend="<string>", ...)`
- The `intend` field describes the reflective response ("I notice I leaned on the same metaphor; I intend to try a different one next time")
- Reactor log entry: appends with the new `noticed` + `intend` fields
- **Spawn budget touch point:** `reflect_activity` at `fast` tier (~$0.01/call), max_concurrent=1
- **Gating:** 2.2 `reflect` is GATED by the `ReflectiveMomentScorer` (deliverable 3.8). Reflect calls are only allowed when the scorer returns `should_reflect=True`. Without the gate, reflect would fire too often and drown the stream.
- **Target files:**
  - `agents/hapax_daimonion/activities/reflect.py` (~180 LOC)
  - `tests/hapax_daimonion/test_activity_reflect.py` (~180 LOC)

**Size:** ~360 LOC, 0.5 day serial work

### 3.4 `critique` activity (item 2.3 / B4)

**Scope:**
- New activity reading the last 5-10 reactions and critiquing patterns
- Output constraint: the critique MUST name crutches by name ("reliance on metaphor X", "circular phrasing Y") — not generic "I was repetitive"
- Response schema: `DirectorActivityResponse(activity="critique", react=<int>, noticed=<int>, intend="<string>", ...)` with BOTH `noticed` and `intend` required
- Appends `noticed` + `intend` to the reactor log entry for audit and for the ReflectiveMomentScorer's `pattern_density` input (see deliverable 3.8)
- **Anti-slop constraint:** same as reflect (activity 2.2) — must include concrete index + concrete pattern name; re-roll on vague output
- **Gating:** same `ReflectiveMomentScorer` gate as reflect; critique is more expensive (reads 10 reactions vs 8) so the threshold may be slightly higher at phase tuning time
- **Spawn budget touch point:** `critique_activity` at `balanced` tier (~$0.03/call), max_concurrent=1
- **Target files:**
  - `agents/hapax_daimonion/activities/critique.py` (~200 LOC)
  - `tests/hapax_daimonion/test_activity_critique.py` (~180 LOC)

**Size:** ~380 LOC, 0.5 day serial work

### 3.5 `patch` activity (item 2.4 / D5 preview)

**Scope:**
- Phase 2 ships this as a STUB that returns "no patches available" — it's a placeholder for the Phase 4 Cluster I drafters
- Signature: `patch_activity() -> DirectorActivityResponse(activity="patch", patch_target=None, notes="no patches available (stub)")`
- Registered in `ACTIVITY_CAPABILITIES` so the director loop's activity selection can consider it (but it always returns no-op)
- **Rationale for shipping the stub:** the `ACTIVITY_CAPABILITIES` taxonomy in deliverable 3.1 registers all 13 activity types. Leaving `patch` unregistered would mean the director loop has an inconsistent taxonomy vs the phase plan. Shipping a stub preserves the consistency + makes Phase 4's full implementation a drop-in replacement.
- **Full implementation lands in Phase 4** (Cluster I drafters, per drop #62 §10 Q3 rescoping: I1-I5 are narration-only, so the "patch" is NOT delta-patching code but rather producing a governance-queue entry describing what a patch WOULD be if it were approved).
- **Target files:**
  - `agents/hapax_daimonion/activities/patch.py` (~40 LOC stub)
  - `tests/hapax_daimonion/test_activity_patch_stub.py` (~40 LOC)

**Size:** ~80 LOC, 0.1 day serial work

### 3.6 `compose_drop` activity (item 2.5 / G4 foundation)

**Scope:**
- Synthesizes findings from ≥3 sub-agent outputs into a research drop draft
- **Critical role per drop #62 Q3 ratification (2026-04-15T05:35Z):** this is the base for HSEA Phase 4 Cluster I narrator drafters (I1-I5). Each narrator spawns sub-agents (e.g., a PyMC-BEST-code-watcher, a test-output-reader, a LRR-commit-diff-reader) whose findings get composed into a research drop via this activity. Phase 4 I1-I5 narrators all subclass or compose this activity.
- **Phase 2 scope:** ship the activity handler + the prompt construction pattern + governance queue integration. Phase 2 does NOT ship the spawn pipeline that produces the findings — that's HSEA Phase 7 + HSEA Phase 11 G-cluster.
- Placeholder sub-agent output for Phase 2 testing: a stub `findings.jsonl` at `/dev/shm/hapax-compositor/compose-stubs/<slug>.findings.jsonl` with 3 synthetic finding entries
- Prompt structure: persona header + condition + N finding summaries + exemplar drop + "compose a drop synthesizing these findings; include all N citations"
- Response schema: `DirectorActivityResponse(activity="compose_drop", draft_slug="<slug>", ...)` with the drop text in a `content` field (same pattern as 3.2 draft)
- Writes to `/dev/shm/hapax-compositor/draft-buffer/<slug>.partial.md` (same buffer as 3.2 draft)
- Writes to governance queue via `GovernanceQueue.append(type="research-drop", drafted_by="hapax-compose-drop-activity", ...)`
- **Narrator base class export:** for Phase 4's benefit, deliverable 3.6 exports a public API:
  ```python
  class ComposeDropActivity:
      def __init__(self, findings_reader: Callable[[], list[dict]], drop_slug: str, exemplar_path: Path)
      def run(self) -> DirectorActivityResponse: ...
      def promote(self) -> None: ...  # moves partial to final location via promote-drop.sh
  ```
  Phase 4 narrator drafters construct instances with their own `findings_reader` closures that watch LRR Phase 1 commits (for I1 PyMC BEST narrator) or similar upstream signals.
- **Spawn budget touch point:** `compose_drop_activity` at `balanced` tier (~$0.10/call, higher than draft because the synthesis prompt is larger), max_concurrent=1
- **Target files:**
  - `agents/hapax_daimonion/activities/compose_drop.py` (~300 LOC including ComposeDropActivity class)
  - `tests/hapax_daimonion/test_activity_compose_drop.py` (~200 LOC)

**Size:** ~500 LOC, 0.8 day serial work

### 3.7 `synthesize` activity (item 2.6 / G9)

**Scope:**
- Takes multiple recent sub-agent findings and composes a 30-word synthesis (distinct from `compose_drop`'s drop-length output)
- Target output: a Cairo overlay caption — "the most compact multi-agent consensus surface"
- Use case: when several sub-agents converge on a finding, the synthesize activity produces a single-sentence stream-ready summary that becomes a brief on-stream caption
- Response schema: `DirectorActivityResponse(activity="synthesize", synthesis_sources=["agent-a", "agent-b", "agent-c"], content="<30 word synthesis>")`
- Cairo overlay integration: the synthesize activity writes to `/dev/shm/hapax-compositor/synthesis.json`; a new `SynthesisBannerSource` Cairo source reads that file and renders the synthesis as a temporary caption (3-5 seconds, then fades)
- **Spawn budget touch point:** `synthesize_activity` at `fast` tier (~$0.005/call — very short), max_concurrent=1
- **Target files:**
  - `agents/hapax_daimonion/activities/synthesize.py` (~150 LOC)
  - `agents/studio_compositor/synthesis_banner_source.py` (~120 LOC Cairo source)
  - `tests/hapax_daimonion/test_activity_synthesize.py` (~100 LOC)

**Size:** ~370 LOC, 0.5 day serial work

### 3.8 `ReflectiveMomentScorer` gate (item 2.7 / F3) + calibration

**Scope:**
- Gate function that decides whether the director loop SHOULD execute a reflect or critique activity at the current tick
- Score formula:
  - `score = 0.3 · pattern_density + 0.25 · stance_specificity + 0.2 · time_since_last_reflect/30min + 0.15 · chat_quietness + 0.1 · condition_change_recency`
- Input components:
  - `pattern_density` — from reactor log's recent `noticed` fields (how often the director has been noticing self-patterns)
  - `stance_specificity` — from the last N reactions' stance fields (how concretely the director's stance has been articulated)
  - `time_since_last_reflect` — seconds since the last `reflect` or `critique` activity fired
  - `chat_quietness` — how quiet chat has been in the last window (a quiet chat is a good time to reflect)
  - `condition_change_recency` — how recently the research-marker condition_id changed (new conditions invite reflection)
- Threshold: 0.65; cooldown floor 12 ticks (minimum 12 ticks between consecutive reflect/critique activities regardless of score)
- **7-day calibration window:** per epic spec item 2.7, Phase 2 instruments the scorer with a metrics capture BEFORE enabling the gate. Calibration phase:
  1. Ship the scorer with `enabled=False` (metrics collection only, no gating effect)
  2. Metrics exported to Prometheus: `hapax_reflective_moment_score` histogram, `hapax_reflective_moment_score_components_{pattern_density,stance_specificity,...}` gauges
  3. Run for 7 days collecting empirical distribution
  4. At day 7, analyze: what is the empirical frequency of scores > 0.65? Target is "~1 in 20 ticks" (~5% of ticks) per drop #59 Finding
  5. Tune threshold if empirical frequency diverges from target (drop the threshold if 1 in 50, raise it if 1 in 5)
  6. Enable gating (`enabled=True`) after calibration
- **Drop #59 Finding addressed:** drop #59 flagged "1 in 20" as an untested claim. Phase 2's calibration task converts the claim from "hoped" to "empirically tuned"
- **Target files:**
  - `agents/hapax_daimonion/reflective_moment_scorer.py` (~250 LOC scorer + metrics + enabled flag)
  - `tests/hapax_daimonion/test_reflective_moment_scorer.py` (~200 LOC)
  - `docs/research/protocols/reflective-moment-calibration.md` (~100 lines: calibration protocol + analysis template)

**Size:** ~550 LOC + 7-day wall-clock calibration window, 0.5 day implementation + 7 days observation + 0.1 day tuning

**Note on calibration:** the 7-day window is not "7 days of delta's time" — it's a wall-clock observation period where the scorer emits metrics while gating is disabled. The Phase 2 close gate DOES NOT wait for the full 7 days; the calibration happens in the background and the scorer can be toggled to `enabled=True` at the end of the 7-day window even if Phase 2 has already closed. This is the one Phase 2 deliverable that has a temporal component beyond the session duration.

### 3.9 `exemplar_review` activity (item 2.8 taxonomy, listed separately for clarity)

**Scope:**
- New activity mode that reads the director's own recent outputs (last N reactions or the most recent drop) and compares them to operator-flagged exemplars
- Exemplar source: `shared/exemplars.yaml` (empty shell created by HSEA Phase 0 0.4 per the drop #62 fold-in; populated by LRR Phase 7 persona work)
- Per Phase 0 0.4: `shared/exemplars.yaml` is an empty shell at Phase 2 open time; the review activity SHOULD gracefully handle the empty case ("no exemplars available; skipping review")
- Response schema: `DirectorActivityResponse(activity="exemplar_review", exemplar_id="<id>", noticed="<comparison>", intend="<adjustment>")`
- **Spawn budget touch point:** `exemplar_review_activity` at `balanced` tier (~$0.02/call), max_concurrent=1
- **Target files:**
  - `agents/hapax_daimonion/activities/exemplar_review.py` (~150 LOC)
  - `tests/hapax_daimonion/test_activity_exemplar_review.py` (~120 LOC)

**Size:** ~270 LOC, 0.3 day serial work

---

## 4. Phase-specific decisions since epic authored

Drop #62 fold-in (2026-04-14) + operator batch ratification (2026-04-15T05:35Z) + this extraction (2026-04-15) introduce the following corrections/decisions relative to the original HSEA epic spec §5 Phase 2.

1. **Deliverable 2.5 `compose_drop` is the base for HSEA Phase 4 Cluster I narrator drafters** (drop #62 §10 Q3 ratification). The ComposeDropActivity class exported from 2.5 is the public API that Phase 4 narrator drafters (I1-I5) compose. This is a Phase 2 → Phase 4 dependency that did not exist in the original epic spec (which assumed Phase 4 had its own code-drafting base class). Phase 2 must design 2.5's interface with Phase 4's narrator use case in mind.

2. **Deliverable 2.4 `patch` ships as a stub, not a full implementation** (drop #62 §10 Q3 ratification). The original epic spec item 2.4 says "In Phase 2 the activity is a stub that calls a placeholder 'no patches available'" — this extraction preserves that framing. Phase 4's full implementation of `patch` is ALSO narration-only per Q3: the Phase 4 Cluster I narrators compose governance-queue entries describing what patches WOULD be if they were approved; they do NOT apply code patches directly.

3. **Deliverable 3.9 `exemplar_review` handles empty `shared/exemplars.yaml` gracefully.** HSEA Phase 0 0.4 ships `shared/exemplars.yaml` as an empty shell (`schema_version: 1` + empty `exemplars: []` list). LRR Phase 7 populates it. Phase 2 must not crash or error when the exemplars list is empty; it logs a warning and returns a no-op response.

4. **`ReflectiveMomentScorer` ships with `enabled=False` initially** (per the 7-day calibration window). Phase 2 close does NOT gate on calibration completing — the scorer emits metrics during calibration while the gate is disabled, and enabling happens asynchronously after the 7-day window.

5. **All drop #62 §10 open questions are closed** as of 2026-04-15T05:35Z. No Phase 2 deliverable is gated on a pending operator decision.

6. **`DraftStreamCairoSource` is bundled into deliverable 3.2 `draft`**, not a separate deliverable. The epic spec mentioned it inline in deliverable 2.1; this extraction keeps the bundling since the Cairo source is ~180 LOC and tightly coupled to the draft buffer format.

7. **`SynthesisBannerSource` is bundled into deliverable 3.7 `synthesize`**, same reasoning.

8. **Activity selection model (alpha's 06:20Z inflection mentioned 2.9):** the HSEA epic spec §5 Phase 2 does NOT list "activity selection model update" as a discrete deliverable. It is implicit in the existing director loop's activity selection logic (which Phase 2 extends via the taxonomy update in deliverable 3.1). This extraction does NOT create a separate 2.9 deliverable; the taxonomy extension in 3.1 is sufficient to plumb the 7 new activities into the existing selection mechanism. If alpha or the Phase 2 opener wants stimmung-aware activity bias as a separate deliverable, it can be added as 3.10 during phase execution without re-authoring the spec.

---

## 5. Exit criteria

Phase 2 closes when ALL of the following are verified:

1. **`ACTIVITY_CAPABILITIES` extended from 6 to 13 entries.** Verify: `grep -c "ACTIVITY_CAPABILITIES" <persona.py>` shows the extension; unit test asserts all 13 entries present.

2. **All 7 new activity handlers registered.** Director loop can dispatch to each activity by name. Smoke test: invoke each activity 1-2x against a mocked LLM and assert the response parses correctly.

3. **Director loop successfully alternates between old + new activities in production.** Verify: tail the reactor log for 5 minutes of production operation; observe at least 3 different activity types appearing (including at least one new Phase 2 activity).

4. **Reactor log captures new activity types with schema validation.** Verify: `jq '.activity' reactor-log-YYYY-MM.jsonl | sort -u` shows at least one new activity type. Each entry with activity=reflect or critique has non-null `noticed` + `intend` fields.

5. **`ReflectiveMomentScorer` instrumented with metrics capture.** Verify: Prometheus shows `hapax_reflective_moment_score` histogram with non-zero counts. `enabled=False` initially so no actual gating occurs.

6. **Calibration protocol documented** at `docs/research/protocols/reflective-moment-calibration.md` with the 7-day analysis template.

7. **Regression tests for each new activity against a mocked LLM fixture.** Each activity has ≥5 test cases: happy path, anti-slop rejection (where applicable), empty-input graceful degradation, spawn-budget-denied graceful failure, governance-queue-write verification.

8. **`compose_drop` narrator base class exported** with a public API that Phase 4 narrator drafters can compose. Verify: import `ComposeDropActivity` from `agents.hapax_daimonion.activities.compose_drop`; instantiate with a stub findings_reader; call `run()`; assert success.

9. **Spawn budget touch points registered** for all 7 new activities in `~/hapax-state/spawn-budget-caps.yaml`. Verify: `yq '.per_touch_point | keys' ~/hapax-state/spawn-budget-caps.yaml` includes `draft_activity`, `reflect_activity`, `critique_activity`, `compose_drop_activity`, `synthesize_activity`, `exemplar_review_activity`, `patch_activity` (even the stub gets a budget entry for consistency).

10. **`DraftStreamCairoSource` + `SynthesisBannerSource` registered** via HSEA Phase 1 `SourceRegistry` pattern; visible in production compositor during a smoke test that triggers each activity.

11. **Governance queue integration verified:** after a successful `draft` or `compose_drop` run, a governance queue entry appears in `~/hapax-state/governance-queue.jsonl` pointing at the draft buffer file.

12. **`hsea-state.yaml::phase_statuses[2].status == closed`** at phase close; `research-stream-state.yaml::unified_sequence[UP-10].status == closed` if the shared index has landed.

13. **Phase 2 handoff doc written** at `docs/superpowers/handoff/2026-04-15-hsea-phase-2-complete.md` with the 13 activity list, links to PRs/commits, and Phase 4 narrator compatibility verification.

14. **Phase 4 dry-run compatibility check:** construct a stub Phase 4 narrator drafter (just a skeleton that composes `ComposeDropActivity` with a trivial findings_reader) and verify it runs successfully under Phase 2's infrastructure. This is the acceptance test that Phase 2 is actually ready to support the Phase 4 Cluster I rescoping.

---

## 6. Risks + mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| LRR Phase 7 (persona spec) not closed when Phase 2 opens | HIGH | Phase 2 activities' prompt construction references the persona, which doesn't exist yet | Phase 2 onboarding MUST verify LRR UP-9 closed; otherwise phase blocks. Alternative: ship Phase 2 with a stub persona and hot-swap when LRR Phase 7 lands (adds complexity, recommend blocking instead) |
| `compose_drop` interface is not rich enough for Phase 4 narrator drafters | MEDIUM | Phase 4 has to retrofit 2.5 with additional parameters | Phase 2 designs 2.5 with Phase 4 in mind per §4 decision 1; Phase 2 opener should coordinate with whoever will open Phase 4 before locking the interface |
| 7-day calibration window is incompatible with operator's cadence | LOW | Calibration never completes; scorer stays disabled indefinitely | Calibration protocol documents that the 7-day window is wall-clock, not active-session time; if the operator chooses not to calibrate, the scorer remains disabled and the reflect/critique activities are manually triggered |
| Anti-slop re-roll on reflect/critique exceeds spawn budget | MEDIUM | Three retries × per-activity cost can push daily budget over the hysteresis threshold | Re-rolls count against the same spawn budget touch point; if 3 retries fail, the activity aborts and logs a `budget_exhausted_reroll` impingement. Prevents unbounded spend. |
| `draft` activity produces low-quality research drops that clog the governance queue | MEDIUM | Operator inbox drowns in bad drafts | Spawn budget cap on `draft_activity` (e.g., max 3/day); governance queue TTL (14-day expiry from Phase 0 0.2); operator can reject drafts via inbox frontmatter `status: rejected` |
| `ReflectiveMomentScorer` calibration reveals the 1-in-20 target is wrong | MEDIUM | Threshold tuning diverges significantly from 0.65 | This is the WHOLE POINT of the calibration window; tuning the threshold based on empirical data is the correct response. Drop #59 Finding: "1 in 20" was untested; Phase 2 is the test. |
| `exemplar_review` fails gracefully but never produces useful output until LRR Phase 7 populates exemplars | MEDIUM | Phase 2 ships a no-op activity | Expected behavior per §4 decision 3; deliverable 3.9 tests explicitly verify graceful empty-exemplars handling |
| Existing director loop's activity selection doesn't handle 13 activities as gracefully as 6 | MEDIUM | Selection bias + some activities never fire | Include a regression test that fires each activity at least once per 100 ticks under synthetic conditions; tune selection if needed |
| `DraftStreamCairoSource` character-reveal rate collides with other Cairo sources for zone space | LOW | Zone contention, visible glitches | Use the zone registry pattern from HSEA Phase 1 / LRR Phase 2; declare the draft zone explicitly in `config/compositor-zones.yaml` |
| Phase 2 ships before HSEA Phase 1 (visibility surfaces) | LOW | Glass-box prompt rendering not available to verify activity prompts on stream | Phase 2 opener blocks on UP-4 closed (preferred) OR accepts that activity prompts are only verifiable via direct JSON read during the calibration window |

---

## 7. Open questions

All drop #62 §10 open questions are resolved. Phase 2 has no remaining operator-pending decisions from the cross-epic fold-in.

Phase-2-specific design questions (operator or Phase 2 opener can decide at open time; not blocking):

1. **Activity selection model (alpha's 06:20Z inflection 2.9 suggestion).** Alpha proposed a separate deliverable for "stimmung-aware activity bias, plumbed into director_loop activity selection." This extraction does NOT include it as a discrete deliverable per §4 decision 8. If the Phase 2 opener wants this, it can be added as deliverable 3.10 during execution.

2. **Draft completion detection heuristic.** Deliverable 3.2 mentions "~2000 characters OR operator manual flag OR director decides 'done'" as the completion threshold. The exact heuristic is opener's choice at implementation time.

3. **ReflectiveMomentScorer threshold calibration target.** Drop #59 said "1 in 20 ticks" (5%). Operator can override at tuning time if 5% is too frequent or too rare in practice.

4. **`compose_drop` narrator base class — composition vs subclassing.** The spec says "subclass or compose." Phase 2 opener picks the pattern that feels cleanest for the Phase 4 narrator use case. Composition is usually cleaner (pydantic + callable injection), subclassing is usually simpler for straightforward cases.

5. **Exemplar pool population timing.** Deliverable 3.9 runs empty-pool until LRR Phase 7 populates `shared/exemplars.yaml`. The operator may want to manually seed 3-5 exemplars during Phase 2 to give the review activity something to test against; this is an operator choice, not a Phase 2 scope item.

6. **`patch` stub messaging on stream.** The stub returns "no patches available". If the director loop narrates this on stream, the message appears frequently (every time selection picks `patch`). Opener decides whether to suppress stream output for the stub or to include it as low-salience filler.

---

## 8. Companion plan doc

TDD checkbox task breakdown at `docs/superpowers/plans/2026-04-15-hsea-phase-2-core-director-activities-plan.md`.

Execution order inside Phase 2 (serial, single-session-per-deliverable-cluster model):

1. **3.1 Activity taxonomy extension** — ships FIRST; all other deliverables depend on the extended `ACTIVITY_CAPABILITIES`
2. **3.2 `draft` activity + DraftStreamCairoSource** — ships SECOND; foundational pattern for subsequent activities, exercises governance queue integration + spawn budget + Cairo source registration
3. **3.6 `compose_drop` activity + ComposeDropActivity class** — ships THIRD; load-bearing for Phase 4 narrators per §4 decision 1; designed with Phase 4 in mind
4. **3.7 `synthesize` activity + SynthesisBannerSource** — ships FOURTH; simpler than compose_drop, exercises Cairo caption pattern
5. **3.8 `ReflectiveMomentScorer` + calibration scaffolding** — ships FIFTH; required before 3.3 reflect and 3.4 critique since those are gated by it
6. **3.3 `reflect` activity** — ships SIXTH; depends on 3.8 gate
7. **3.4 `critique` activity** — ships SEVENTH; same dependency on 3.8
8. **3.9 `exemplar_review` activity** — ships EIGHTH; independent but lower priority
9. **3.5 `patch` stub** — ships LAST; trivial stub, no dependencies

Each deliverable is a separate PR (or a single multi-commit PR with reviewer pass per deliverable). Phase 2 closes when all 9 deliverables are merged, all 14 exit criteria pass, and the Phase 4 dry-run compatibility check succeeds.

**7-day calibration window is parallel**, not serial: ReflectiveMomentScorer metrics collection runs in the background during and after Phase 2 execution. Gate enablement happens asynchronously after the 7-day window; Phase 2 close does not wait for it.

---

## 9. End

This is the standalone per-phase design spec for HSEA Phase 2. It extracts the Phase 2 section of the HSEA epic spec (drop #60, §5) and incorporates:

- Drop #62 fold-in corrections (§10 Q3 HSEA Phase 4 rescoping — deliverable 3.6 `compose_drop` is the narrator base)
- Drop #62 §5 row UP-10 unified sequence mapping
- Operator batch ratification 2026-04-15T05:35Z (all 10 §10 questions closed)
- Resolution of alpha's 06:20Z 2.9 suggestion (activity selection model — not adopted as a discrete deliverable; left as §7 open question 1)

This spec is pre-staging. It does not open Phase 2. Phase 2 opens only when:

- LRR UP-0 + UP-1 + UP-9 are closed (verification + research registry + persona)
- HSEA UP-2 (Phase 0) is closed and all 6 deliverables merged
- HSEA UP-4 (Phase 1) is closed (preferred) for on-stream verification of activity prompts
- A session claims the phase via `hsea-state.yaml::phase_statuses[2].status: open`

Pre-staging authored by delta per alpha's 06:20Z delegation of the operator directive "activities extraction, always be working" (2026-04-15T06:20Z terminal message).

— delta, 2026-04-15
