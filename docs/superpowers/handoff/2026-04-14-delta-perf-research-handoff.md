# Delta perf-research session handoff — 2026-04-14

**Session role:** delta (beta role — performance research support)
**Session window:** 2026-04-14 09:00Z → this handoff
**Scope:** Livestream smoothness + LRR research support via
performance research drops and small infrastructure fixes
**Drops shipped:** 24 (22 research + 2 errata)
**Code shipped:** 1 PR-free commit to `main` (hapax-logos
frontend perf fix) + 2 live docker container config changes
**Status at handoff:** not retiring — operator mandate is
"keep going", this handoff is a checkpoint for alpha / the
next delta rotation

## How to read this handoff

Delta's research register is terse, neutral, scientific,
with each drop as a self-contained investigation. The drops
fall into three classes:

- **Ring 1 — drop-everything**: a live regression or
  severely wasteful state with a one-line or few-line fix.
  Ship these first.
- **Ring 2 — alpha-sprint-sized**: concrete fix candidates
  that need code review but are well-scoped.
- **Ring 3 — research groundwork**: observability gaps,
  metric census, design observations that inform future
  sprints.

The rollup at the bottom of this handoff groups every drop
by ring + by subsystem.

## Immediate action items for the next session

If alpha (or delta rotation) starts a session tomorrow,
these are the five things to land first, in order:

1. **Enable the 14 dormant systemd timers** (drop #22,
   `5db43ee95`). One `systemctl --user enable --now` sweep.
   Unblocks langfuse-sync, rag-ingest, obsidian-sync,
   av-correlator, flow-journal, and 9 others. Zero risk.
   **Sequencing caveat:** before running the enable,
   reset `~/.cache/gdrive-sync/state.json` per drop #21 to
   avoid repeatedly firing a known-broken service.
2. **Enable the HLS archive rotation timer** (drop #20,
   `9e0fbf3d4`). Separate from drop #22 because this timer
   isn't even `linked` — it needs a symlink in
   `~/.config/systemd/user/` first. LRR Phase 2's "Archive
   + Replay as Research Instrument" premise is blocked on
   this single step.
3. **Fix `gdrive-sync` state** (drop #21, `f798d110a`).
   Reset `start_page_token` from the literal string 'def'
   to `None` so next sync refetches. Preserves the 209k
   file fingerprints already cached.
4. **Ship glfeedback diff check** (drop #5, `a3fc43eef`).
   4 LoC across Rust + Python. Eliminates ~224 wasted
   shader recompiles/hour and the visible accumulation-
   buffer clear that happens every ~4 minutes when plans
   activate.
5. **Confirm Hermes 3 quantization path with operator**
   (drop #15, `79d4f53a5`). Beta's 3.0bpw quant is
   currently in flight on GPU 1; drop #15 shows only
   Q2_K fits single-GPU and larger quants require
   TP2 which evicts the compositor. Before the quant
   finishes and alpha/beta starts wiring, confirm
   which of drop #15's four paths is being committed.

## Drops, grouped by ring and subsystem

### Ring 1 — drop-everything

| # | commit | drop title | subsystem | fix effort |
|---|---|---|---|---|
| 20 | `9e0fbf3d4` | LRR Phase 2 HLS archive is dormant | HLS / systemd | 3 lines (symlink + enable) |
| 21 | `f798d110a` | gdrive-sync broken by corrupted start_page_token='def' | gdrive / state file | 1 python one-liner |
| 22 | `5db43ee95` | Systemd timer enablement gap — 14 of 51 timers dead | systemd / install pattern | one enable sweep |

### Ring 2 — alpha-sprint-sized

| # | commit | drop title | subsystem | fix effort |
|---|---|---|---|---|
| 5 | `a3fc43eef` | glfeedback shader-recompile storm root cause | Rust GL + Python effect graph | 4 LoC |
| 6 | `874d36c45` | studio_fx CPU load — OpenCV GPU path silently disabled | OpenCV package | pacman diagnose + reinstall |
| 8 | `86c0383e0` | director_loop LLM cost — Anthropic prompt cache unused | LLM routing | 3 JSON keys per caller |
| 9 | `6bbb39535` | Prompt-cache audit across all council LLM callers | LLM routing | 5 callers, batched PR |
| 17 | `b3e540a42` | TabbyAPI config audit — context window + Phase 5 readiness | local inference | 2 yaml lines |
| 18 | `50be4841d` | Qdrant payload-index gap — system-wide | qdrant / schema | ~20 LoC registry extension |
| 19 | `759f0b4f7` | LiteLLM gateway config audit | gateway / routing | ~8 yaml edits |
| 23 | `ea8a39394` | Chronicle query is a full JSONL linear scan | logos API / shared | 20 LoC (option C) |
| 24 | `0b738bcaa` | predictions_metrics inlines a second chronicle full-scan | logos API / predictions | caller swap after #23 |

### Ring 3 — research groundwork

| # | commit | drop title | subsystem |
|---|---|---|---|
| 1 | `0ae2a9868` | Compositor frame budget forensics | compositor telemetry |
| 1e | `f502bc541` | Erratum — corrected metric count | compositor telemetry |
| 2 | `b90f0599e` | brio-operator producer deficit root-cause probe | camera capture |
| 3 | `fdfe7ecda` | overlay_zones cairo invalid-size call-chain analysis | compositor rendering |
| 4 | `2c86ac537` | Sprint-5 delta audit — output/encoding reconciliation | RTMP / HLS |
| 7 | `f8d2b678f` | Perf findings rollup + priority ranking | cross-cutting |
| 11 | `a89170f9b` | Audio path baseline — PipeWire, DSP, TTS | audio / PipeWire |
| 11e | `2665c2218` | Erratum to audio path baseline — BRIO audio present | audio / PipeWire |
| 13 | `d71eb2385` | Logos build-time audit | build / cargo / vite |
| 14 | `684ff7ca7` | Metric coverage gaps — consolidated observability backlog | observability |
| 15 | `79d4f53a5` | Hermes-3-70B VRAM sizing pre-flight | GPU / inference |
| 16 | `cf7a9e877` | LRR Phase 9 integration pre-flight | LRR chat classifier |

Plus the infrastructure changes shipped outside the research
drops:

| commit | what | where |
|---|---|---|
| `ac927debc` | perf(logos): fix webview CPU hotspots (DetectionOverlay rAF leak + AmbientShader FPS mismatch) | hapax-logos/src/components/ |
| (no commit, live) | redis container: mem 768m→2g, cpus 0.25→1.0 | ~/llm-stack/docker-compose.yml |
| (no commit, live) | minio container: mem 2g→4g | ~/llm-stack/docker-compose.yml |

Measured impact: redis CPU 83.9 % → 1.9 % (99.7 % reduction).
WebKit webview CPU 85.6 % → ~74 % (13 % reduction, mostly
stable). Detailed before/after in the rollup drop.

## Themes across drops

Three patterns repeat across the 24-drop set. Worth
internalizing because they are the likeliest classes of
regression in future sessions.

### Theme A — "Fire on any change" instead of "fire on actual change"

- Drop #5: glfeedback shader-dirty fires on every
  `set_property("fragment", ...)` even when the fragment
  is byte-identical to the previous value
- Drop #14 (A3) / drop #2: v4l2 kernel-drops detector fires
  never because sequence-gap logic doesn't work for MJPG —
  but the metric advertises itself as a drop counter
- Drop #1 + errata: partial hyphen-fix for per-camera
  freshness gauge registration — 2 of 8 cairo sources
  fixed, 6 camera sources still missing
- Drop #14 (C11): Anthropic prompt cache headers are
  available in the response but not parsed by any caller

The fix pattern is the same: `if old != new { mark_dirty }`
or, at the observability layer, explicit drift detection.
Worth considering a `DirtyFlag<T>` helper or a linter rule.

### Theme B — "Code exists, runtime disables it"

- Drop #1: Phase 7 BudgetTracker is installed but never
  instantiated in the compositor runtime
- Drop #6: GpuAccel is wired in studio_fx with full CUDA
  code paths — disabled at runtime because cv2 CUDA
  module isn't available
- Drop #15: Hermes 3 70B weights downloaded — but no
  quant, no TabbyAPI config, no routing (alpha/beta is
  addressing this live)
- Drop #20: HLS archive rotation timer file exists in
  the repo but is not installed, not symlinked, not
  enabled
- Drop #22: 14 of 51 timers are symlinked (`linked`
  state) but never enabled (`~/.config/systemd/user/
  timers.target.wants/` entry missing)

The fix pattern is the same: **between shipping the
code and shipping the runtime state, there is always a
second step that gets forgotten.** The install convention
for systemd units specifically needs to be one step
longer than it currently is.

### Theme C — "No counter, no data"

- Drop #1: no per-source frame-time histogram — can't
  attribute compositor CPU to specific cairo sources
- Drop #2: no reliable kernel-drops counter — can't
  attribute brio-operator's 7 % frame deficit
- Drop #14: no alertmanager — health monitor FAILs
  route to journald instead of ntfy
- Drops #20, #21, #22: same alertmanager gap. All three
  regressions were only surfaced by delta manually
  walking the systemd state, not by any alerting path.

The observability backlog (drop #14) enumerates 12 missing
metrics and 4 diagnostic log-line additions that would
close the highest-leverage subset of this theme.

## What delta intentionally did not do

- **Did not write code beyond the one perf-fix commit
  (`ac927debc`) + two live docker config changes**. Per
  operator instruction: "research role only: look at
  beta's research drops for examples." The drops are
  investigation artifacts, not shipping patches.
- **Did not interrupt beta's Hermes 3 quantization**. Beta
  was running `hf download` then the 3.0bpw quant on
  GPU 1 throughout the session. Delta's drop #15 is the
  sizing pre-flight for exactly that work — the concerns
  in § 4 of that drop are relevant to beta's in-flight
  decision but delta did not DM beta or block the quant.
- **Did not `systemctl --user enable` the 14 dead timers**
  (drop #22). That's an installer-level operation and
  delta stayed in research lane.
- **Did not bypass the LiteLLM gateway** to benchmark
  TabbyAPI directly (drop #17 § 3 would benefit from such
  a test). The benchmark script exists at
  `scripts/benchmark_prompt_compression_b6.py` but running
  it during a session with other LLM traffic would
  pollute the measurements.
- **Did not verify the `glfeedback` recompile cluster
  settles after process warmup** (drop #5). Sampled once
  during live runtime, showed sustained bursts.
  Would benefit from a 60-second sustained measurement
  window.

## Open questions / follow-ups

Ordered by "would unblock the most future work":

1. **Run the enable sweep from drop #22 first, then
   measure.** Many of the other ring-1 and ring-2 drops
   have effects that only become visible once the
   underlying timers are active. Particularly
   `langfuse-sync.timer` — LRR Phase 1 traces need to
   catch up 81 h of backlog, and the first run's behavior
   is worth watching.
2. **Close drop #2 H3 (v4l2-ctl streaming diagnostic)**
   to distinguish brio-operator's 45 k missing frames
   from a kernel-layer drop vs a producer-thread stall.
   Operator + alpha in the loop; delta cannot do this
   non-invasively against the live camera.
3. **Close drop #3 H1/H2/H3 (overlay_zones cairo
   invalid-size input capture)** by shipping the
   minimal diagnostic patch at `text_render.py:188`.
   One burst after the diagnostic lands = root cause
   known.
4. **Ship drop #23's option C** (reverse scan + orjson)
   which closes both drop #23 and drop #24. 20 LoC.
5. **Decide the Hermes 3 path** (drop #15) before
   TabbyAPI config gets rewritten.

## Relay / session coordination

The operator's peer-awareness notes during the session
established that beta is running the Hermes 3 quant in
parallel and consumed the same research drops delta was
producing. Alpha retired earlier today (PR #800,
`04e4fe641`) crediting delta's work as "Phase 10
observability pre-staging."

At handoff time:

- **alpha**: retired. Next alpha session will start fresh.
- **beta**: running Hermes 3 70B → EXL3 3.0bpw quant on
  GPU 1, in flight. Expected to complete within hours
  given the current quant process has been running for
  ~30 minutes at ~12 GB VRAM footprint.
- **delta (me)**: continuing per operator mandate; this
  handoff is a checkpoint, not a retirement.

## References — commit hashes for everything delta shipped today

Research drops and code commits, in chronological order:

- `ac927debc` perf(logos): DetectionOverlay + AmbientShader fixes
- `0ae2a9868` docs(research): compositor frame budget forensics
- `f502bc541` docs(research): erratum to compositor frame budget forensics
- `b90f0599e` docs(research): brio-operator producer deficit
- `fdfe7ecda` docs(research): overlay_zones cairo invalid-size
- `2c86ac537` docs(research): sprint-5 delta audit
- `a3fc43eef` docs(research): glfeedback shader-recompile storm
- `874d36c45` docs(research): studio_fx OpenCV GPU gap
- `f8d2b678f` docs(research): perf findings rollup
- `86c0383e0` docs(research): director_loop LLM cost
- `6bbb39535` docs(research): prompt-cache audit
- `a89170f9b` docs(research): audio path baseline
- `2665c2218` docs(research): audio path baseline erratum
- `d71eb2385` docs(research): logos build-time audit
- `684ff7ca7` docs(research): metric coverage gaps
- `79d4f53a5` docs(research): Hermes-3-70B VRAM sizing
- `cf7a9e877` docs(research): LRR Phase 9 integration pre-flight
- `b3e540a42` docs(research): TabbyAPI config audit
- `50be4841d` docs(research): Qdrant payload-index gap
- `759f0b4f7` docs(research): LiteLLM gateway config audit
- `9e0fbf3d4` docs(research): LRR Phase 2 HLS archive dormant
- `f798d110a` docs(research): gdrive-sync corrupted state
- `5db43ee95` docs(research): systemd timer enablement gap
- `ea8a39394` docs(research): chronicle query linear scan
- `0b738bcaa` docs(research): predictions_metrics inlines chronicle scan
- (this file) docs(handoff): delta perf-research session handoff

All files are under `docs/research/2026-04-14-*.md`. The
rollup at `f8d2b678f` is the original priority index (drops
#1–#7 only); this handoff updates it with drops #8–#24.
