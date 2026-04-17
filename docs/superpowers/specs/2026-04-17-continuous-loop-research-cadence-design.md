# Continuous-Loop Research Cadence — Design Spec

**Date:** 2026-04-17
**Status:** draft (post-LRR, pre-operator-ratification)
**Predecessor:** LRR (closed 2026-04-17, see `docs/superpowers/handoff/2026-04-17-lrr-epic-closure.md`)

---

## 1. Epic goal

Close the loop that LRR left half-wired. LRR shipped every module required
for the audience → stimmung → activity → output → audience path, and
landed most of them as standalone units with injection seams. This epic
*promotes the wiring from observational telemetry to actual behaviour*
so the system's response to its audience is a measurable feedback
loop — not a bundle of independent modules connected by logs.

**What this epic is:** seven items that convert the Phase 9 modules
from "reachable from the call site" to "exercising real control
authority." After this epic, a five-minute chat lull deterministically
biases the director-loop toward `study`; a burst of on-topic chat
biases it toward `chat`; the stimmung 12th dimension carries
`audience_engagement` and is visible in dashboards alongside the other
11; captions draw in scientific register when the stream is in
`public_research` mode without a manual layout edit.

**What this epic is NOT:** it is not another research-artefact epic
(LRR was); it is not an overhaul of the affordance pipeline (that is
USR Phase 4+5 territory, scoped separately); it is not a new substrate
migration (scenario 1+2 is settled).

**Theoretical grounding:** FEP/active-inference prediction→action loops.
The Phase 9 modules already provide the prediction side (engagement
score, emphasis recommendation, attention bid). This epic wires the
*action* side: stimmung update, activity-score promotion, surface
emphasis, audio duck engagement.

---

## 2. Dependencies + preconditions

Every precondition is satisfied as of 2026-04-17:

1. **Phase 9 full set merged.** `chat_monitor.structural_analyzer` + `.sink` (#997, #998), `studio_compositor.activity_scoring` (#999), `agents.hapax_daimonion.chat_queue` (#1001), `studio_compositor.captions_source` (#1002), `chat_reactor.RESEARCH_MODE_SENSITIVITY` (#996), `agents.code_narration.producer` (#977), PipeWire `hapax-ytube-ducked` (#1000).
2. **Production wire-ups merged** (#1003). Telemetry-only integrations for `activity_scoring` in director-loop and `chat_queue` producer in chat-monitor; registry registration for `CaptionsCairoSource`.
3. **Phase 7 persona-document composer active in production** (#1004, daimonion restarted 2026-04-17T13:58Z).
4. **Phase A data-collection window open** (`cond-phase-a-persona-doc-qwen-001`). Sessions accumulate as the epic runs; tuning data is a by-product, not a prerequisite.

---

## 3. Deliverables (7 items)

### 3.1 Stimmung 12th dimension — `audience_engagement` (item 1)

Add the twelfth dimension to `shared/stimmung.py::SystemStimmung`:

- Field: `audience_engagement: DimensionReading = Field(default_factory=DimensionReading)`
- Weight class: cognitive (`0.3×`) per existing `_COGNITIVE_DIMENSION_NAMES`
- Stimmung collector populates from `/dev/shm/hapax-chat-signals.json` via the `engagement_from_chat_signals()` reducer in `activity_scoring.py`. Reuse that function — do not recompute from raw metrics.
- `StimmungCollector` staleness cutoff: 90 s (one full `chat-monitor` batch cycle + margin; aligns with the 120s structural-signals publish cadence).
- No new Prometheus scrape; the existing stimmung exporter picks up the new dimension automatically once added to the model.

**Target files:** `shared/stimmung.py` (+40 LOC), `shared/stimmung_collector.py` or equivalent (+20 LOC), tests (~150 LOC: backfill, staleness, weight-class assertion).

**Downstream sweep:** every consumer that iterates `_DIMENSION_NAMES` inherits the new dim for free. Explicit readers: readiness gate, stance computation, Grafana dashboard JSON, prompt-compression benchmark. Each gets one line of validation test.

**Size:** ~210 LOC.

---

### 3.2 Promote activity-scoring from telemetry to selection (item 2)

Today the director-loop logs `activity_score activity=<a> stimmung_term=<x> composite=<y>` after the LLM has already chosen. Promote to selection:

- Score the LLM's proposed activity plus the three strongest alternates (`react` / `chat` / `study`).
- Override the LLM choice iff the top-scored alternate beats the proposed choice by ≥ `OVERRIDE_MARGIN` (default 0.08) AND the proposed choice's composite is ≤ `PROPOSAL_FLOOR` (default 0.55). Both defaults tunable in `config/director_scoring.yaml`.
- Log an `activity_override` event when it fires; Phase 10 §3.1 Prometheus per-condition slicing picks it up automatically via the existing director-loop span.

Guard rails:
- Never override to `silence` — that must stay the operator's prerogative (Stream Deck, consent).
- Never override when the scored stimmung term is stale (the 90 s staleness gate applies here too).
- Hysteresis: after an override, cool down for 60 s before another override can fire on the same slot.

**Target files:** `agents/studio_compositor/director_loop.py` (~60 LOC), `config/director_scoring.yaml` (new file, ~20 lines), tests (~180 LOC).

**Size:** ~260 LOC.

---

### 3.3 Chat-queue drain in daimonion (item 3)

The FIFO-20 queue shipped in #1001 is producer-only today; `chat-monitor.py` pushes, nobody drains. Wire the drain side into the daimonion's director-like activity loop:

- When the director-loop (or its daimonion equivalent) selects `chat`, call `chat_queue.drain()` and pass the resulting list into the existing operator-speech composition path as context.
- The queue is in-process to the *chat-monitor*, which is a separate service. Cross-service messaging: the producer atomically writes a snapshot to `/dev/shm/hapax-chat-queue-snapshot.json` every push (bounded by the FIFO-20), and the drainer reads + atomic-rename-deletes the file. File-backed drain keeps the consent guarantee (author_ids are stripped before write; only `text + ts` land on disk).
- Spec: the snapshot file is ephemeral — deleted on drain, recreated on next push.

**Target files:** `agents/hapax_daimonion/chat_queue.py` (+50 LOC for snapshot/drain IO), `scripts/chat-monitor.py` (+10 LOC at push site), `agents/hapax_daimonion/director_loop.py` or whichever file composes chat-mode utterances (+30 LOC drain call), tests (~200 LOC).

**Size:** ~290 LOC.

---

### 3.4 Captions surface in the default layout (item 4)

#1002 registered `CaptionsCairoSource` but no layout declares it. This item:

- Adds a `captions` zone to `config/compositor-layouts/default.json` — horizontal strip, bottom 12% of the 1920×1080 canvas, below the main active camera surface.
- Adds a layout-declared `SourceRegistry` entry pointing to `CaptionsCairoSource` with no extra params.
- STT consumer side: the daimonion's STT post-processing writes the most recent transcript line to `/dev/shm/hapax-daimonion/stt-recent.txt` (atomic write). ~15 LOC hook in `agents/hapax_daimonion/conversation_pipeline.py` after STT settles.
- Stream-mode reader: `stream_mode_reader` kwarg wired to `logos._governance.stream_mode.current()` (or the canonical reader — one grep).

**Target files:** `config/compositor-layouts/default.json` (+zone), `agents/hapax_daimonion/conversation_pipeline.py` (+stt-recent writer), `agents/studio_compositor/captions_source.py` (+ stream-mode reader wire), tests (~80 LOC).

**Size:** ~140 LOC.

---

### 3.5 Attention-bid delivery dispatcher call-site (item 5)

#991 shipped the dispatcher standalone. Nobody calls it today. Wire the
call site: whenever the attention-bid scorer (`agents/attention_bids/
bidder.py::select_winner`) returns a winner, the accepting caller
invokes `dispatch_bid(winner)`. The caller is whichever subsystem
generates the bids — today that's the daimonion's director-loop +
background daemon impingement producers.

- Add a `dispatch_accepted` boolean to the `select_winner` call sites so callers can opt in to delivery without a config change.
- Daimonion wire-up: existing `impingement_consumer_loop` already has per-source logic; after it calls `select_winner` for the current tick, if a winner exists and `dispatch_accepted=True`, dispatch via the Phase 8 dispatcher.
- Throttling: the dispatcher's per-channel hysteresis (default 15 min) governs the actual delivery cadence; the caller doesn't need to track.

**Target files:** `agents/hapax_daimonion/run_loops_aux.py` or equivalent (+20 LOC), tests (~60 LOC).

**Size:** ~80 LOC.

---

### 3.6 Environmental-salience emphasis promotion (item 6)

#990 shipped `recommend_emphasis()` standalone. Wire it:

- A new systemd timer unit `hapax-environmental-emphasis.timer` (30 s cadence) runs a tiny driver script that calls `recommend_emphasis()` and, if a recommendation returns, invokes the `objective_hero_switcher` to flip hero mode to the recommended camera role.
- Driver persists `last_emphasis_at` across ticks in `/dev/shm/hapax-environmental-emphasis/state.json` so the hysteresis survives timer restarts.
- Hero-mode switch uses the existing compositor command path — no new integration surface.

**Target files:** `systemd/units/hapax-environmental-emphasis.service` + `.timer` (new), `scripts/environmental-emphasis-tick.py` (~80 LOC), tests (~80 LOC).

**Size:** ~180 LOC.

---

### 3.7 Closed-loop validation drill (item 7)

A new operational drill that exercises the full loop end-to-end:

- Synthesize a chat-signals snapshot claiming high engagement + many threads
- Assert: stimmung 12th dim reads > 0.7 within one cycle
- Assert: director-loop's next activity score for `chat` is raised
- Assert: the activity-override triggers (or at least the composite score is within a configurable band)
- Assert: the same cycle the chat-queue snapshot is drained and contents are logged (contents not enforced — consent)

Adds `closed-loop-validation` as the seventh drill in `scripts/run_drill.py`, with a result doc at `docs/drills/<date>-closed-loop-validation.md` on execution.

**Target files:** `scripts/run_drill.py` (+1 drill class, ~80 LOC), tests (~60 LOC).

**Size:** ~140 LOC.

---

## 4. Exit criteria

Closed when every item in §3 is shipped AND:

1. A session run with live chat shows the `audience_engagement` gauge moving in Grafana and the director-loop emitting `activity_override` events when expected.
2. Captions zone renders transcripts on stream without a layout edit.
3. Attention bid dispatch is observed in `~/hapax-state/attention-bids.jsonl` with real `delivered` channels.
4. Environmental emphasis timer is running and the `last_emphasis_at` state file has advanced.
5. The closed-loop-validation drill passes in live mode at least once.

---

## 5. Open questions

1. **Stimmung 12th-dim weight class.** Cognitive (0.3×) matches the existing `grounding_quality` + `exploration_deficit`. Biometric (0.5×) would give audience engagement more weight on stance. Ratify cognitive (epistemic state about the audience) unless operator wants audience to push stance more forcefully.
2. **Override margin + floor defaults.** 0.08 and 0.55 are first guesses. Tunable in config; expect adjustment after ≥ 3 live sessions.
3. **Captions stream-mode redaction interaction.** Phase 6 §4.B transcript firewall already redacts impingements; does the captions surface need an additional redaction pass at draw time, or does the STT-recent file upstream already pass through the firewall? Confirm before wiring.
4. **Chat-queue snapshot consent.** We strip `author_id` before the file write; verify the Phase 6 §4.B transcript firewall treats the snapshot as transcript-adjacent (probably should). Add to deny-list if not already.

---

## 6. Risks + mitigations

| Risk | Mitigation |
|---|---|
| Activity-override causes oscillation between LLM choice and score pick | Hysteresis (§3.2); start defaults conservative; monitor `activity_override` rate; back off if > 1 per 5 min |
| Captions surface creates a persistent privacy liability | STT-recent file is atomic-written + single-line; goes through Phase 6 §4.B firewall by path; captions source already knows about stream-mode and would render in scientific register even if accidentally public |
| Chat-queue file-backed IPC fails silently | File mtime is a freshness proxy; if producer is silent but consumer keeps reading stale, log the age |
| Environmental emphasis timer triggers too often during active streams | 30 s cadence + 30 s hysteresis inside `recommend_emphasis()`; effective cap ≈ 2/min max |
| 12th dim breaks downstream prompt-compression benchmark | The benchmark reads dimensions by name; add `audience_engagement` to its expected-dims list |

---

## 7. Sequencing

The seven items have one hard dependency chain (3.1 before 3.2; every
other item is independent):

1. **3.1 Stimmung 12th dim** — foundation, everything downstream reads the new reading
2. **3.2 Activity-scoring override** — depends on 3.1
3. **3.3 Chat-queue drain** — parallel with 3.2
4. **3.4 Captions surface** — parallel, independent
5. **3.5 Attention-bid dispatch wire-up** — parallel, independent
6. **3.6 Environmental-emphasis timer** — parallel, independent
7. **3.7 Closed-loop drill** — last; validates everything

Estimated effort: **~1,300 LOC across 7 PRs**. One strict serial dependency
(3.1 → 3.2); the other five can ship in any order. At the session
cadence this epic has been shipping, this is 3-5 days real-time.

---

## 8. Authorship note

This spec was drafted by the alpha session on 2026-04-17 immediately
after LRR closure. It is an operator-facing draft; operator ratifies
before opening the first PR against the epic.

The spec deliberately keeps scope tight: it does not try to extend
into USR Phase 4 / SCM Phase 2 territory, both of which have their
own scoping docs (see `docs/superpowers/specs/2026-04-17-next-epics-scoping.md`).
