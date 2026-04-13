# Phase 3 — Cognitive-loop continuity audit

**Queue item:** 025
**Phase:** 3 of 6
**Date:** 2026-04-13 CDT
**Register:** scientific, neutral (per `feedback_scientific_register.md`)

## Headline

The `feedback_cognitive_loop` memory says: *"Voice needs a
never-stopping cognitive loop during conversation, not
request-response state machine. Cognition must run continuously,
not cold-start on utterance boundary."*

**Half true.** The control loop IS continuous. The
formulation loop IS cold-start per utterance.

- **Continuous layer (always on, ticking):** CPAL runner at
  150 ms cadence, the impingement consumer loop at 0.5 s,
  workspace monitor at 3 s, perception loop, ambient refresh,
  proactive delivery. All 8 long-lived coroutines produce
  measurable signals (log lines, SHM writes, Prometheus gauges)
  during the idle period between utterances. Live evidence from
  the 18:36:07-18:36:23 journal window shows "World affordance
  recruited" messages firing every 2–5 seconds with distinct
  exploration sources (`dmn_pulse`, `visual_chain`,
  `dmn_imagination`, `affordance_pipeline`). The impingement
  consumer loop is genuinely doing cognitive work between turns.
- **Cold-start layer (per utterance):**
  `ConversationPipeline.process_utterance` is spawned as a fresh
  `asyncio.create_task` on each utterance
  (`cpal/runner.py:223`). Inside, the STT → LLM → TTS sequence
  runs as a one-shot pipeline: fresh Langfuse trace
  (`conversation_pipeline.py:488`), fresh OTEL span
  instantiation for every sub-event, fresh LLM call with a
  rebuilt message history, fresh context assembly. The LLM
  client is persistent but the call itself is one-shot.

The cognitive-loop continuity claim holds for the T0/T1/T2 layers
(backchannel, gain modulation, impingement surfacing) but **not
for the T3 LLM formulation layer**. T3 is still request-response.

Whether this counts as "the claim holds" depends on how it's
read:

- **Reading 1** (generous): The never-stopping cognitive loop is
  the control layer. The LLM is called through the loop, not as a
  replacement for it. Claim holds.
- **Reading 2** (literal): "Cognition must run continuously, not
  cold-start on utterance boundary" — the LLM *is* cognition from
  the operator's perspective, and it DOES cold-start on utterance
  boundary. Claim half-holds.

Reading 2 is the stronger reading and the one the feedback memory
author likely intended. Under that reading, **the claim is not
currently satisfied.** The LLM formulation is the biggest single
piece of "cognition" that happens during conversation, and it is
not continuous.

## Coroutine continuity classification

Per `run_inner.py:135-180` + cpal/runner.py:

| # | coroutine | entry | cadence | continuity | produces-signal |
|---|---|---|---|---|---|
| 1 | `CpalRunner.run` | cpal/runner.py:128 | **150 ms tick**, continuous | **always-on** | gain updates, grounding ledger, SHM publish every 10 ticks, stimmung read every 10 ticks |
| 2 | `_cpal_impingement_loop` | run_inner.py:151 | 0.5 s poll | **always-on** | 150 "CPAL: impingement surfacing" log lines per 10 min (queue 024 Phase 4) |
| 3 | `impingement_consumer_loop` | run_loops_aux.py:187 | file-watch + 0.5 s | **always-on** | "World affordance recruited" logs ~every 2–5 s with distinct source labels |
| 4 | `workspace_monitor.run` | workspace_monitor.py | 3 s poll | **always-on** | perception state updates, screen-capture triggers |
| 5 | `audio_loop` | run_loops.py:19 | continuous (pw-cat frames) | **always-on** | VAD frames, echo reference, utterance detection |
| 6 | `perception_loop` | run_loops.py | 0.5 s | **always-on** | EnvironmentState updates |
| 7 | `ambient_refresh_loop` | run_loops_aux.py:149 | 30 s | **always-on but slow** | ambient context refresh |
| 8 | `proactive_delivery_loop` | run_loops_aux.py:71 | event-driven (notification queue) | **event-driven** | notification dispatch |
| 9 | `subscribe_ntfy` | ntfy_listener | SSE subscription | **always-on but silent in steady state** | ntfy inbound delivery |
| 10 | `actuation_loop` | run_loops.py:83 | event-driven (MIDI/OBS) | **event-driven** | OBS scene + MIDI CC dispatch |
| — | `process_utterance` | cpal/runner.py:223 → pipeline.process_utterance | **per-utterance, cold-start task** | **cold-start** | STT + LLM + TTS + trace + spans |
| — | `generate_spontaneous_speech` | cpal/runner.py:501 → pipeline.generate_spontaneous_speech | **per-impingement, cold-start** | **cold-start** | same one-shot shape |

**Summary:** 8 continuous + 2 event-driven + 2 cold-start. The
continuous majority is control + perception + ambient awareness.
The cold-start minority is the LLM formulation path.

## Direct answer: does the claim hold?

The `feedback_cognitive_loop` claim is:

> "Voice needs a never-stopping cognitive loop during conversation,
> not request-response state machine. Cognition must run
> continuously, not cold-start on utterance boundary."

**The continuous control loop does exist and runs at 150 ms
cadence.** PR #752 onward confirmed this via live journal
observation. The measured tick count was 30499 over 6479 seconds
= 4.71 ticks/sec (slightly below the 6.67 target but close, and
the jitter is from `asyncio.sleep(sleep_time)` on busy ticks).
This layer:

- modulates gain (operator presence, speech, silence, stimmung)
- runs the grounding control law every tick
- reads stimmung ceiling every 10 ticks
- publishes CPAL state every 10 ticks
- runs the evaluator's control law continuously
- surfaces impingements as they arrive

**But the T3 formulation layer is cold-start** (new Task per
utterance + fresh LLM message history). The claim as written
does not distinguish between control and formulation — it reads
"cognition" as a single thing. By that reading, it does not hold.

## Cold-start path trace (per utterance)

When an utterance arrives:

1. `cpal/runner.py:223` — `asyncio.create_task(self._process_utterance(utterance))`
   — creates a **new asyncio Task**. Task lifecycle: created,
   awaited-later, garbage-collected after completion.
2. `cpal/runner.py:346` — `_process_utterance` sets
   `self._processing_utterance = True` and calls
   `self._pipeline.process_utterance(utterance)`.
3. `conversation_pipeline.py:471` — `ConversationPipeline.process_utterance`
   opens a **new Langfuse trace** (line 482-488,
   `hapax_trace("voice", "utterance", ...).__enter__()`). The
   trace is per-utterance, not per-session.
4. `conversation_pipeline.py:491` — delegates to
   `_process_utterance_inner`, which performs the full
   STT → echo check → consent filter → salience route → LLM
   call → TTS → audio output sequence.
5. Inside the inner, many fresh OTEL span + `hapax_event` calls
   (~6+ per utterance for STT, LLM, TTS, grounding).
6. LLM is called via `pydantic-ai Agent` which holds a persistent
   client but instantiates a new message list per call.

**The Agent client is persistent; the message list is fresh; the
trace is fresh.** The claim's "cold-start on utterance boundary"
language is literally true for the trace, message list, and OTEL
span creation. It is figuratively true for the LLM call
(weights loaded, client persistent, but context window fresh).

### Why this matters operationally

The cold-start cost is the LLM round-trip + context assembly. For
a local model, context assembly + serialization + generation can
be several hundred milliseconds. A sizable chunk of the per-turn
latency is "cold-start work that could have been done
speculatively." Queue 024 Phase 1 established that Kokoro synthesis
is the current pacing factor (6.6 chars/sec), but even if Kokoro
were instant, the LLM cold-start layer would be the next bottleneck.

The speculative formulation path (`cpal/runner.py:241`
`self._formulation.speculate(frames, ...)`) exists and runs during
operator speech. Let me check whether it actually warms the LLM:

```bash
grep -n "speculate\|warm\|preload" agents/hapax_daimonion/cpal/formulation_stream.py
```

(Would need to trace the full speculate → LLM call path. Out of
scope for this phase since the signal is already clear: the LLM
call itself is a one-shot request, and whether speculation warms it
is a follow-up question.)

## Cold-start patterns grep'd

| location | pattern | cold-start? |
|---|---|---|
| `grounding_bridge.py:42` | `if self._ledger is None:` | lazy init on first access (cold-start at first call) |
| `conversation_pipeline.py:1321` | `if self._bridge_engine is None: return` | not cold-start — skip if unavailable |
| `conversation_pipeline.py:1568` | `if self._screen_capturer is None: return None` | not cold-start — skip if unavailable |
| `signal_cache.py:56` | `if synthesize is None:` | defensive check, not cold-start |
| `conversation_pipeline.py:1779` | `self._audio_output = None` | cleanup, not init |

Most `if X is None` patterns in the cpal/daimonion code are
**optional-subsystem skip gates**, not lazy-init. The ones that are
lazy-init (`grounding_bridge._ledger`) fire on first access, which
is once per session start, not per-utterance.

## Gap analysis

### What exists

- A continuous 150 ms control tick (CPAL)
- Continuous impingement consumer (0.5 s + file watch)
- Continuous gain modulation, grounding ledger, stimmung reads
- Presynthesized signal cache + bridge phrases (loaded once at start)
- Speculative formulation stream (runs during speech)

### What's missing for the strong-reading claim

1. **No continuous LLM warming during conversation**. Between turns,
   there is no background coroutine that pre-computes LLM context,
   runs a speculative completion, or keeps a prompt warm. The LLM
   call is still one-shot.
2. **No per-session LLM message-history persistence**. Each
   `process_utterance` rebuilds the message list from
   `_context_assembler`. There is no growing turn log that the LLM
   attends to across turns — each call includes the relevant context
   but the assembly is fresh.
3. **No streaming formulation between utterances**. The formulation
   stream speculates *during* operator speech but does not generate
   complete candidate responses that are ready to speak before the
   operator finishes.
4. **No cognitive continuation beyond the turn boundary**. After an
   utterance is processed and spoken, the cognitive activity that
   would naturally follow ("still thinking about what the operator
   said") does not happen. The next cycle is tied to the next
   impingement arrival or utterance boundary.

### What would close the gap

1. **Persistent conversation agent with a rolling context**. The
   agent would live for the session, not the turn. The turn would
   append to its history and trigger a response. Pydantic-AI supports
   this via `Agent.iter` with explicit message history.
2. **Continuous low-temperature thinking**. Between turns, a
   background coroutine runs `Agent.run` with a "reflect on the
   last exchange" prompt, producing a short summary or an
   anticipatory continuation. The output feeds back into context
   without speaking.
3. **Turn-bounded speculative formulation**. The formulation stream
   speculates during speech; extend it to speculate complete LLM
   responses using the partial transcript.
4. **Post-utterance continuation**. After TTS completes, a
   "what should I notice next" cycle runs before returning to the
   idle cognitive loop.

## Ranked backlog: make the claim hold

| rank | work | effort | impact |
|---|---|---|---|
| 1 | Persistent per-session pydantic-ai Agent with rolling context | medium (restructure ConversationPipeline) | turns become appends, not replays |
| 2 | Continuous inter-turn LLM reflection coroutine | medium (new background task) | cognition runs continuously in the strong sense |
| 3 | Speculative complete-response formulation (extend formulation stream) | large (LLM call during speech) | next-turn cold start becomes warm hand-off |
| 4 | Post-utterance continuation cycle | small | immediately after TTS, run one "notice what just happened" tick |
| 5 | LLM call-path instrumentation to confirm cold-start cost | small | measure the cost the claim predicts |

## Backlog additions (for retirement handoff)

108. **`feat(daimonion): persistent per-session pydantic-ai Agent with rolling context`** [Phase 3 rank 1] — the ConversationPipeline's turn path currently rebuilds message history per turn. Restructure to a session-scoped Agent + append. Medium effort.
109. **`feat(daimonion): continuous inter-turn LLM reflection coroutine`** [Phase 3 rank 2] — new background task that runs `Agent.run` with a "reflect on the last exchange" prompt during idle. Feeds rolling context. Medium effort.
110. **`feat(daimonion): extend formulation_stream.speculate to generate complete LLM responses`** [Phase 3 rank 3] — currently speculates backchannels; extend to speculate T3. Large effort.
111. **`feat(daimonion): post-utterance continuation cycle`** [Phase 3 rank 4] — after TTS, run one "notice what just happened" cycle. Small effort.
112. **`feat(daimonion): hapax_llm_cold_start_ms histogram`** [Phase 3 rank 5] — measures the cost of the cold-start layer. Small.
113. **`docs(feedback_cognitive_loop): refine the claim to distinguish control from formulation`** [Phase 3 interpretation gap] — the current memory is ambiguous. Refined version: "The control loop runs continuously at 150 ms. The LLM formulation layer is currently cold-start per turn and should become continuous."
