# LRR Phase 8 — Hapax Content Programming via Research Objectives (I-3) — Design Spec

**Date:** 2026-04-15
**Author:** delta (pre-staging extraction; LRR execution remains alpha/beta workstream)
**Status:** DRAFT pre-staging — awaiting LRR UP-9 (persona) close before Phase 8 open
**Epic reference:** `docs/superpowers/specs/2026-04-14-livestream-research-ready-epic-design.md` §5 Phase 8 (canonical source)
**Plan reference:** `docs/superpowers/plans/2026-04-15-lrr-phase-8-content-programming-via-objectives-plan.md`
**Branch target:** `feat/lrr-phase-8-content-programming-via-objectives`
**Cross-epic authority:** drop #62 §5 row UP-11 (co-ships with LRR Phase 9 + HSEA Phase 3) + §3 row 20 (LRR Phase 8 surfaces distinct from HSEA Phase 1 surfaces)
**Unified phase mapping:** **UP-11 Content programming + objectives + closed loop** (drop #62 §5 line 146): LRR Phases 8 + 9 own infrastructure; HSEA Phase 3 owns C-cluster narration on top. Phase 8 portion: ~2,500 LOC. ~5-7 sessions for UP-11 total.

> **2026-04-15T07:30Z note:** LRR Phase 8 depends on Phase 7 (persona) per epic spec. Phase 7's Hermes framing is SUPERSEDED per drop #62 §14 — Phase 8 opener should read §14 before starting because Phase 8's objectives reference the persona authored under whichever post-Hermes substrate the operator ratifies.

---

## 1. Phase goal

Give Hapax a set of **research objectives** it holds and updates over time. Wire the director loop's activity selector to score against objective advancement so that what Hapax does at each tick is measurably connected to what it's trying to learn. Build the visibility surface (objective-overlay tile). Wire hero-mode camera switching (GDO Phase 2 Stage 3, never specced). Add Stream Deck integration, YouTube description auto-update, three research-mode tiles (Logos studio view, terminal capture with secret obscuration, PR/CI status), attention-bid mechanism for Hapax-initiated operator interaction, environmental perception → surface emphasis wiring, and formalize the existing overlay content system as a Phase 8 primitive.

**Phase 8 is the I-3 workstream landing.** After Phase 8, Hapax is a continual research programmer in the concrete sense — not just architecturally.

**What this phase is:** 12 items spanning objectives data structure + registry CLI + director scoring extension + objective overlay Cairo source + hero-mode camera switching + Stream Deck adapter + YouTube description auto-update + stream-as-affordance reconciliation + 3 research-mode compositor tiles + attention-bid mechanism + environmental salience → surface emphasis + overlay content system formalization.

**What this phase is NOT:** does not ship Phase 9 closed-loop feedback (chat → stimmung → activity → output feedback; that's the next phase), does not ship the HSEA C-cluster narrators that watch Phase 8 commits (HSEA Phase 3, also in UP-11), does not modify the persona spec (Phase 7), does not ship the observability layer (Phase 10).

**Theoretical grounding:** I-3 (Hapax content programming via research objectives) + P-5 (content primitives are already built; objectives are the missing layer).

---

## 2. Dependencies + preconditions

**Cross-epic (from drop #62):**

1. **LRR UP-0 + UP-1 closed.**
2. **LRR UP-3 (Phase 2 archive instrument) closed.** Phase 8 item 9 tiles register via `SourceRegistry`/`OutputRouter` pattern that LRR Phase 2 item 10 ships.
3. **LRR UP-9 (Phase 7 persona) closed.** The persona is "the stance from which objectives are pursued" per epic spec; without a persona, the objective register cannot frame the stance each objective is being pursued FROM. Note per drop #62 §14: Phase 7 is pre-staged but the Hermes framing is superseded; Phase 8 opener reframes to whichever substrate the operator ratifies.
4. **HSEA UP-2 (Phase 0) closed.** Phase 8 item 4 Cairo source uses the zone registry; item 9 tiles also use SourceRegistry.
5. **HSEA UP-4 (Phase 1 visibility surfaces) closed.** Phase 8's new Cairo sources live alongside HSEA Phase 1's; they share `CairoSource` protocol + zone registry.
6. **HSEA UP-10 (Phase 2 core director activities) closed.** Phase 8 item 3 director-loop scoring extension modifies `_call_activity_llm` — the same code path HSEA Phase 2 activities plug into.
7. **HSEA Phase 3 (UP-11, co-ships)** depends on Phase 8 artifacts for its C-cluster narrator findings_readers. In particular:
   - HSEA Phase 3 C2 voice session spectator reads research-marker + condition_id (LRR Phase 1)
   - HSEA Phase 3 C4 Phase 4 PR drafter reads beta worktree (no Phase 8 coupling)
   - HSEA Phase 3 C10 milestone drop generator watches Phase 8 objective opens/closes as milestones
   - So Phase 8 unblocks C10 directly

**Intra-epic:** Phase 0, 1, 2, 3, 6, 7 closed. (Phase 4, 5 may or may not be closed — Phase 8 does not strictly require them.)

**Infrastructure:**

1. `~/Documents/Personal/30-areas/` directory (operator's vault, existing) — Phase 8 item 1 creates `hapax-objectives/` subfolder.
2. Obsidian Local REST API (existing, used by `agents/vault_context_writer.py` etc.) — Phase 8 item 1 reads objective markdown via this API.
3. `agents/hapax_daimonion/director_loop.py` or `_call_activity_llm` (existing) — Phase 8 item 3 extends scoring.
4. `agents/studio_compositor/cairo_source.py::CairoSource` + `CairoSourceRunner` (existing) — Phase 8 items 4, 9 implement new subclasses.
5. `config/compositor-layouts/default.json` + `config/compositor-zones.yaml` (LRR Phase 2 deliverables) — Phase 8 adds zone declarations for its 4 new surfaces (objective overlay + 3 research-mode tiles).
6. `agents/studio_compositor/chat_reactor.py::PresetReactor` (existing) — unchanged by Phase 8, extended by Phase 9.
7. GDO's `LivestreamDescriptionUpdater` class in `agents/studio_compositor/youtube_player.py` or similar (existing) — Phase 8 item 7 extends.
8. `shared/command_registry.py` + WS relay on `:8052` (existing command registry) — Phase 8 item 6 Stream Deck integration dispatches through this.
9. `agents/hapax_daimonion/voice_session/` + `shared/notify.py` + PipeWire sinks (existing) — Phase 8 item 10 attention-bid channels.
10. Pi NoIR perception fleet SHM + VLA stimmung JSON (existing) — Phase 8 item 11 consumes salience signals.

---

## 3. Deliverables (12 items)

### 3.1 Objectives data structure (item 1)

- Location: `~/Documents/Personal/30-areas/hapax-objectives/` in Obsidian vault; markdown per objective
- Frontmatter schema: `objective_id`, `title`, `status` (active/closed/deferred), `priority`, `opened_at`, `linked_claims[]`, `linked_conditions[]`, `success_criteria[]`, `activities_that_advance[]`
- Body: interleaved operator + Hapax notes
- **Target files:** `~/Documents/Personal/30-areas/hapax-objectives/obj-001.md` (+ at least 3 seed objectives), `shared/objective_schema.py` (~150 LOC Pydantic model)
- **Size:** ~200 LOC

### 3.2 Objectives registry CLI (item 2)

- `scripts/hapax-objectives.py` with subcommands: `open`, `close`, `list`, `current`, `advance <objective_id> <activity>`
- Reads/writes the markdown files in `~/Documents/Personal/30-areas/hapax-objectives/` via `shared/frontmatter.py`
- Hapax can autonomously invoke `advance` when the `study` activity completes in a way that measurably furthers an objective (measurement logic is item 3)
- **Target files:** `scripts/hapax-objectives.py` (~250 LOC), `tests/scripts/test_hapax_objectives.py` (~150 LOC)
- **Size:** ~400 LOC

### 3.3 Director loop scoring extension (item 3)

- Extend `director_loop._call_activity_llm` activity scoring function:
  ```
  activity_score(a) = (old_score * 0.7) + (objective_advancement_score(a) * 0.3)
  objective_advancement_score(a) = sum(
    1.0 if objective.activities_that_advance contains a else 0
    for objective in current_active_objectives
  ) / len(current_active_objectives)
  ```
- 0.7/0.3 split is tunable in `config/director_scoring.yaml`
- **Target files:** `agents/hapax_daimonion/director_loop.py` (~60 LOC edit), `config/director_scoring.yaml` (new), `tests/hapax_daimonion/test_objective_scoring.py` (~120 LOC)
- **Size:** ~180 LOC

### 3.4 Objective visibility overlay (item 4)

- New `ObjectiveOverlaySource(CairoSource)` in `agents/studio_compositor/objective_overlay_source.py`
- Renders: current top objective title (truncated), activities advancing it, sub-experiment/condition_id, sprint day, claim state
- Zone: lower-right quadrant (registered via HSEA Phase 0 0.2 / LRR Phase 2 item 10 zones registry)
- Refresh: 1 Hz via `WatchedQueryPool`-equivalent polling (reads objective markdown files via `shared/frontmatter.py`)
- **Target files:** `agents/studio_compositor/objective_overlay_source.py` (~180 LOC), tests (~100 LOC)
- **Size:** ~280 LOC

### 3.5 Hero-mode camera switching (item 5)

- Camera profile presets: `hero_operator`, `hero_turntable`, `hero_screen`, `balanced`, `sierpinski`
- Pipeline branch restart mechanism for V4L2 framerate changes (200-500ms blackout)
- Display-side scaling via compositor pad properties (instant, no blackout)
- Runtime switching via command registry: `studio.camera_profile.set`
- Director selects profile based on activity: `vinyl → hero_turntable`, `study → hero_screen`, `react → hero_operator`
- **Target files:**
  - `agents/studio_compositor/camera_profiles.py` (~300 LOC profile manager + pipeline restart)
  - `config/compositor-camera-profiles.yaml` (new)
  - `hapax-logos/src/lib/commands/studio.ts` extension for `camera_profile.set` command
  - Tests (~200 LOC)
- **Size:** ~550 LOC

### 3.6 Stream Deck integration (item 6)

- `streamdeck-linux` Python library OR WebSocket relay to `:8052` command registry
- Key map: preset selection, camera profile, stream-mode toggle, manual activity override, auto-private override, research-registry open/close
- `config/streamdeck.yaml` operator-editable key map
- `systemd/user/hapax-streamdeck-adapter.service` new unit
- **Target files:** `agents/streamdeck_adapter/__init__.py` (~300 LOC), systemd unit, config file, tests
- **Size:** ~400 LOC

### 3.7 YouTube description auto-update (item 7)

- Extend GDO's `LivestreamDescriptionUpdater` class in `youtube_player.py` (or wherever it lives)
- Description template fields: condition_id, claim_id, current_objective.title, sub_experiment_id, reaction_count, substrate.model
- Updates on condition change (via research-registry event hook) + objective change
- OAuth scope: `youtube.force-ssl` (operator re-consent required per GDO 2026-04-09 handoff §5.1)
- Quota: 50 units/update × 200 updates/day cap (well under 10000/day YouTube quota)
- **Target files:** `agents/studio_compositor/youtube_player.py` extension (~100 LOC), tests (~80 LOC)
- **Size:** ~180 LOC

### 3.8 Stream-as-affordance reconciliation (item 8)

- `studio.toggle_livestream` affordance already exists (PR #730); Phase 8 extends with Hapax-autonomous recruitment when an objective requires it
- Affordance pipeline integration is already there; the new work is the recruitment logic in the objective scorer
- **Target files:** `agents/hapax_daimonion/objective_affordance_recruiter.py` (~150 LOC), tests (~80 LOC)
- **Size:** ~230 LOC

### 3.9 Research-mode surface inventory — 3 additional tiles (item 9)

Three new Cairo sources registered in `SourceRegistry`:

- **Logos studio view tile** — renders Logos fullscreen (or subset region) as a tile source. Stream-mode-aware redaction via Phase 6 API gates. Source ID: `logos_studio_view`.
- **Terminal capture tile with secret obscuration** — captures a terminal/IDE region via `wf-recorder` or equivalent. Pre-compositor regex-based blur on known secret patterns (`pass show`, `LITELLM_*`, `*_API_KEY`, `Authorization: Bearer`, etc.). Only active in `public_research` mode. Source ID: `terminal_capture`.
- **PR / CI status overlay** — polls git + GitHub Actions state for current branch; renders branch + CI status + open PR URL + test counts + latest commit SHA. Updates on push/CI event. Data source: git + `gh` CLI + SHM cache. Source ID: `pr_ci_status`.

- **Target files:**
  - `agents/studio_compositor/logos_studio_view_source.py` (~250 LOC)
  - `agents/studio_compositor/terminal_capture_source.py` (~300 LOC — includes regex obscuration)
  - `agents/studio_compositor/pr_ci_status_source.py` (~200 LOC)
  - Tests (~300 LOC across 3 files)
- **Size:** ~1,050 LOC total

### 3.10 Attention bid mechanism (item 10)

- Hapax-initiates-interaction primitive: when activity selector scores `chat` or `study` with strong operator-attention hypothesis, Hapax generates an attention bid rather than speaking
- Delivery channels (operator-configurable via `config/attention-bids.yaml`):
  - ntfy notification
  - TTS via daimonion on a DEDICATED operator-only audio sink (NOT `mixer_master`, so bid never reaches stream audio)
  - Visual flash on Logos sidebar
  - Optional: Stream Deck LED cue
- Logs to `~/hapax-state/attention-bids.jsonl`
- Respects `executive_function` axiom: hysteresis gate (max 1/15min), stimmung-gate (suppressed in critical/degraded stimmung), operator override ("not now" voice command OR Stream Deck button)
- **Target files:**
  - `agents/hapax_daimonion/attention_bid.py` (~250 LOC)
  - PipeWire sink config for `hapax-attention-bids` (~20 lines)
  - `config/attention-bids.yaml` (operator-editable)
  - Tests (~200 LOC)
- **Size:** ~500 LOC

### 3.11 Environmental perception → content highlighting (item 11)

- Wire existing salience signals (Pi NoIR IR hand activity, motion delta, audio onset, imagination fragment salience) as surface-emphasis inputs to the objective selector
- When high-salience environmental signal co-occurs with active objective having `observe` or `react` in `activities_that_advance`, compositor briefly emphasizes the relevant surface:
  - Hero mode on the appropriate camera
  - Overlay highlight on active object
  - Audio duck on competing sources
- Distinct from hero mode (activity-driven) + attention bids (operator-facing) — audience-facing environmental foregrounding
- **Target files:**
  - `agents/hapax_daimonion/environmental_salience_emphasis.py` (~200 LOC)
  - Tests (~120 LOC)
- **Size:** ~320 LOC

### 3.12 Overlay content system formalization (item 12)

- Existing `agents/studio_compositor/overlay_zones.py` already cycles 85 documents from `~/Documents/Personal/30-areas/stream-overlays/`
- Phase 8 formalizes by adding `stream-overlays/research/` subfolder for research-mode content (claim summaries, citation cards, methodology notes)
- Objective selector cycles research content when `study` activity active
- Reuses existing Pango rendering, DVD-screensaver bounce, IBM VGA font stack
- No new infrastructure — content authoring + a new zone in `overlay_zones.py` config
- **Target files:**
  - `~/Documents/Personal/30-areas/stream-overlays/research/` (operator creates 3+ seed cards)
  - `agents/studio_compositor/overlay_zones.py` (~20 LOC edit to add research zone)
- **Size:** ~50 LOC (mostly content, operator-authored)

---

## 4. Phase-specific decisions since epic authored

1. **Phase 7 Hermes framing is SUPERSEDED per drop #62 §14** (2026-04-15T06:35Z operator Hermes abandonment). Phase 8 opener reads §14 before starting; the persona that Phase 8 references is the one authored under the post-Hermes substrate.

2. **No direct drop #62 §10 open questions affect Phase 8.** All 10 ratifications substrate-independent except Q1 (now practically reopened but ratified historically).

3. **HSEA Phase 3 C10 milestone drop generator depends on Phase 8 objective open/close events.** Phase 8 item 2 CLI must emit events to a location HSEA Phase 3 C10 can watch (e.g., `~/hapax-state/hapax-objectives/events.jsonl`).

4. **LRR Phase 9 (closed-loop feedback) depends on this phase**, not vice versa. Phase 9 modulates the objective scorer with chat signals; Phase 8 ships the scorer Phase 9 modulates.

5. **Drop #62 §3 row 20 distinguishes Phase 8 surfaces from HSEA Phase 1 surfaces.** Phase 8 ships `objective-overlay` + Logos studio view + terminal capture + PR/CI status. HSEA Phase 1 ships HUD + research state broadcaster + glass-box prompt + orchestration strip + governance queue overlay. These are DISTINCT surfaces with different zone ownerships; naming must stay distinct to prevent re-implementation drift.

---

## 5. Exit criteria

Phase 8 closes when ALL 14 exit criteria pass (matching epic spec §5 Phase 8 exit criteria):

1. `~/Documents/Personal/30-areas/hapax-objectives/` exists with ≥3 authored objectives
2. `hapax-objectives.py` CLI operational (all 5 subcommands)
3. Director loop's activity selector scores against objective advancement (verify via LLM prompt logs)
4. Objective visibility overlay renders in lower-right quadrant
5. Camera profile switching works: manual `studio.camera_profile.set hero_operator` moves compositor to hero mode with <1 frame latency (display-side scaling) or <500ms (v4l2 framerate change)
6. Director selects camera profile based on activity (verified via journal logs)
7. Stream Deck maps keys to actions; operator can trigger 5 common actions without leaving physical control surface
8. YouTube description auto-updates on condition change (verify via YouTube Studio)
9. At least one autonomous "stream as affordance" recruitment logged
10. Three research-mode tiles registered in `SourceRegistry`; each renders in `public_research` layout; each redacts correctly when tested against a sample secret-laden terminal frame
11. Attention bid mechanism triggers on synthetic high-score activity; lands on at least one channel; hysteresis prevents second bid within 15-min window; critical stimmung suppresses
12. Environmental perception emphasis demonstrated: induce high-salience IR hand-activity signal with active objective having `observe`/`react` in `activities_that_advance`; relevant camera promoted to hero mode briefly
13. Overlay content system has `stream-overlays/research/` with ≥3 research-mode cards; cycles when `study` activity active
14. `lrr-state.yaml::phase_statuses[8].status == closed` + handoff doc written

---

## 6. Risks + mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Objectives data structure needs revision after Hapax starts pursuing | Iteration cost | 70/30 split + scoring math are tunable via `config/director_scoring.yaml`; iterate in place |
| Camera profile switching V4L2 framerate blackout | Visible stream break | Switch only during activity transitions, not mid-activity |
| Stream Deck hardware dependency | Phase 8 blocked if hardware unavailable | Integration is optional at phase close; deliverable 3.6 ships the adapter code even if operator hasn't connected hardware |
| YouTube OAuth re-consent required | Manual operator browser step | Phase 8 opener surfaces the re-consent requirement early; operator can complete before Phase 8 close |
| Terminal capture regex obscuration misses edge cases (e.g., `tree ~/.password-store/`) | Secret leak on stream | Paired with Phase 6 C3 filesystem-level visibility block as belt-and-suspenders |
| Attention bid channels surprise operator | Bad UX | Operator-configurable in `config/attention-bids.yaml`; default to ntfy only until operator approves other channels |
| Environmental salience emphasis fires too often | Visual jitter | Hysteresis + cooldown in deliverable 3.11; minimum 30s between emphasis events |
| Phase 8 opens before Phase 7 persona landed | Objectives reference a non-existent persona stance | Phase 8 onboarding verifies UP-9 closed before opening |

---

## 7. Open questions

All drop #62 §10 resolved except Q1 practical reopening per §14.

Phase-8-specific:

1. **70/30 scoring split default.** Tunable; start at 70% momentary + 30% objective-driven per epic spec recommendation.
2. **Attention bid rate limit.** Default: max 1 per 15 min per channel; tunable.
3. **Camera profile presets for post-Hermes substrate.** The 5 presets (hero_operator, hero_turntable, hero_screen, balanced, sierpinski) are substrate-independent — no change needed.
4. **Objective file location** (`~/Documents/Personal/30-areas/hapax-objectives/` vs alternative). Default per epic spec; operator can relocate.
5. **Stream Deck device model.** Operator-hardware-dependent; phase 8 opener asks which device is in use.

---

## 8. Companion plan doc

`docs/superpowers/plans/2026-04-15-lrr-phase-8-content-programming-via-objectives-plan.md`.

Execution order:

1. **Item 1 Objectives data structure** — foundational; needed by items 2, 3
2. **Item 2 Objectives registry CLI** — depends on item 1 schema
3. **Item 3 Director scoring extension** — depends on item 1 + 2; unblocks items 5, 8, 10, 11
4. **Item 4 Objective overlay Cairo source** — depends on items 1, 2, 3
5. **Item 12 Overlay content system formalization** — trivial edit to existing system
6. **Item 7 YouTube description updater** — independent; can ship any time
7. **Item 9 Research-mode tiles (3 Cairo sources)** — independent; can ship in parallel with items 4-8
8. **Item 5 Hero-mode camera switching** — depends on item 3 for activity-driven selection
9. **Item 6 Stream Deck integration** — depends on item 5 for camera_profile.set command
10. **Item 8 Stream-as-affordance reconciliation** — depends on items 1, 3
11. **Item 11 Environmental salience emphasis** — depends on items 1, 3, 5
12. **Item 10 Attention bid mechanism** — ships last; depends on items 1, 3 + operator configuration of channels

---

## 9. End

Standalone per-phase design spec for LRR Phase 8 Hapax Content Programming via Research Objectives. 12 items extracted from epic spec §5 Phase 8 verbatim. Pre-staging; Phase 8 opens only when:
- LRR UP-0/UP-1/UP-3/UP-9 closed
- HSEA UP-2/UP-4/UP-10 closed (preferred; Phase 8 scorer extends director loop that HSEA Phase 2 activities plug into)
- Phase 7 persona authored under post-Hermes substrate per drop #62 §14
- A session claims the phase via `lrr-state.yaml::phase_statuses[8].status: open`

Tenth complete extraction in delta's pre-staging queue this session. LRR execution remains alpha/beta workstream.

— delta, 2026-04-15
