# Garage Door Open — Phase 2 Epic

> **For agentic workers:** This is a multi-stage epic, not a single implementation plan. Each stage produces one or more PRs. Stages with approved specs can be executed immediately via `superpowers:subagent-driven-development`. Stages without specs need `superpowers:brainstorming` first.

**Goal:** Complete the Garage Door Open livestream platform from working MVP (Phase 1, merged) through visual polish, research infrastructure, and autonomous behavior enrichment.

**Baseline:** Phase 1 shipped — 6 cameras → cudacompositor → cairooverlay → 24 GL shader slots → `/dev/video42` → OBS → YouTube RTMP. Director loop runs 8s perception cycles. SlotAudioControl manages per-slot PipeWire volume. JSONL logging operational. PR #643 (audio stream control) merged.

**Current blocker:** PR #644 (Sierpinski visual layout) — 12 commits with reverts, CI failing, Cairo CPU overhead at 30fps unsolved.

**Session scope:** Alpha session. Beta is on prompt compression / Hermes 3 70B migration (separate workstream, no conflicts).

---

## Stage Map

```
Stage 1: Triage & Stabilize ──────────────────────┐
  ├─ Fix CI failures (PR #644 + pre-existing)      │
  ├─ Fix failed systemd services                   │
  └─ Squash/clean PR #644 history                  │
                                                    │
Stage 2: Sierpinski Performance ◄──────────────────┘
  ├─ Solve Cairo 30fps CPU overhead
  ├─ Get Sierpinski renderer working
  └─ Merge PR #644
          │
          ├──────────────────────────────────────┐
          │                                      │
Stage 3: Dynamic Camera Resolution    Stage 4: Reactor Context Enrichment
  ├─ Spec (brainstorming)               ├─ Spec approved ✓
  ├─ Display-side scaling               ├─ Phenomenal context integration
  ├─ Hero mode presets                  ├─ TOON format ContextAssembler
  └─ V4L2 framerate switching           ├─ Dual-image input
                                        └─ Reaction memory thread
          │                                      │
          └──────────────┬───────────────────────┘
                         │
Stage 5: Stream Research Infrastructure
  ├─ Spec exists (draft) ✓
  ├─ Qdrant stream-reactions collection
  ├─ Langfuse per-reaction scoring
  └─ Monthly log rotation

Stage 6: Future Enhancements (backlog)
  ├─ VST voice effects (PipeWire filter-chain)
  ├─ Simulcast (Restream.io)
  ├─ Chat-reactive effects
  ├─ Stream overlay (viewer count, chat)
  ├─ Native GStreamer RTMP (eliminate OBS)
  ├─ TikTok clip pipeline
  └─ Stream as affordance (DMN goes live)
```

---

## Stage 1: Triage & Stabilize

**Scope:** Fix all CI failures, clean PR #644 commit history, fix failed systemd services. No new features.

**Branch:** `feat/sierpinski-visual-layout` (existing, PR #644)

**Why first:** Nothing else can merge until CI is green. The pre-existing test failures also need fixing to avoid masking future regressions.

### Task 1.1: Fix effect_graph test assertions

**Files:**
- Modify: `tests/effect_graph/test_smoke.py`
- Check: `agents/shaders/nodes/` (count all .json manifests)

**Problem:** PR #644 added `sierpinski_content` and `sierpinski_lines` shader nodes (2 new .json manifests). Four test assertions hardcode the old count of 57:
- `test_loads_all_nodes` — `assert len == 57` → should be 59
- `test_processing_nodes_have_shaders` — `sierpinski_content` has no GLSL source (WGSL-only node)
- `test_all_schemas` — `assert len == 57` → 59
- `test_schema_params_are_serializable` — `assert len == 57` → 59

**Fix:**
- [ ] Update node count assertions from 57 → 59
- [ ] Fix `test_processing_nodes_have_shaders` to skip WGSL-only nodes (nodes with `.wgsl` file but no `.glsl` source). The registry's `LoadedShaderDef.glsl_source` is None for these — the test should filter them or assert WGSL source exists instead.
- [ ] Run: `uv run pytest tests/effect_graph/test_smoke.py -v -x`
- [ ] Commit: `fix(tests): update shader registry assertions for sierpinski nodes`

### Task 1.2: Fix qdrant schema test assertions

**Files:**
- Modify: `tests/test_qdrant_schema.py`
- Check: `shared/qdrant_schema.py` (current EXPECTED_COLLECTIONS)

**Problem:** Test expects 7 collections, schema now defines 8 (a collection was added since the test was written). Three failures:
- `test_all_six_collections_defined` — 8 != 7
- `test_wrong_dimensions` — 8 != 7
- `test_wrong_distance` — 8 != 7

**Fix:**
- [ ] Read `shared/qdrant_schema.py` to find all currently defined collections
- [ ] Update test assertions to match actual schema (count + collection names)
- [ ] Rename `test_all_six_collections_defined` → `test_all_collections_defined` (name references stale count)
- [ ] Run: `uv run pytest tests/test_qdrant_schema.py -v`
- [ ] Commit: `fix(tests): update qdrant schema assertions to match current collections`

### Task 1.3: Fix experiential proofs flaky test

**Files:**
- Modify: `tests/test_experiential_proofs.py`

**Problem:** Hypothesis property test `test_unconsented_never_leaks` found that the substring `"ro"` (from a generated person name) appears in the output string `"someone sent a message about the project"`. The test checks that person name substrings don't leak into anonymized text, but 2-char substrings match common English words.

**Fix:**
- [ ] Read the test to understand the assertion logic
- [ ] Fix: either increase minimum substring length for the leak check (>=3 chars), or use whole-word matching, or filter out substrings that are common English words
- [ ] Run: `uv run pytest tests/test_experiential_proofs.py -v --count=5` (multiple runs to verify no flakiness)
- [ ] Commit: `fix(tests): prevent false positive substring leak detection in experiential proofs`

### Task 1.4: Squash PR #644 commit history

**Problem:** 12 commits including 3 reverts and 2 re-enables. The meaningful work is:
1. Sierpinski WGSL shaders (NVIDIA-compatible)
2. wgsl_compiler content slot recognition
3. SierpinskiLoader + VideoSlotStub
4. SierpinskiRenderer (Cairo pre-FX)
5. Inscribed 16:9 video containers + waveform

**Fix:**
- [ ] Interactive rebase to squash into 3-4 logical commits:
  - `feat(shaders): add Sierpinski triangle WGSL shaders` (shaders + compiler fix)
  - `feat(compositor): add SierpinskiLoader and VideoSlotStub` (loader + director compat)
  - `feat(compositor): add Cairo Sierpinski renderer` (renderer + geometry)
- [ ] Force-push to `feat/sierpinski-visual-layout`
- [ ] Verify CI passes

### Task 1.5: Fix failed systemd services

**Services:** `llm-cost-alert.service`, `vault-context-writer.service`

- [ ] Run: `systemctl --user status llm-cost-alert.service` — diagnose failure
- [ ] Run: `systemctl --user status vault-context-writer.service` — diagnose failure
- [ ] Fix root causes and restart
- [ ] Commit fixes if code changes needed, otherwise just restart

**Acceptance:** CI green on PR #644. All 8 test failures resolved. Both systemd services running.

---

## Stage 2: Sierpinski Performance

**Scope:** Solve the Cairo CPU overhead that blocks the Sierpinski renderer. Get the visual layout working at acceptable CPU cost. Merge PR #644.

**Branch:** `feat/sierpinski-visual-layout` (continuing from Stage 1)

**Spec:** `docs/superpowers/specs/2026-04-11-sierpinski-visual-layout-design.md` (approved)

**Problem:** Cairo rendering + GdkPixbuf JPEG loading at 30fps adds ~250% CPU on top of the 5-camera MJPEG baseline (~250% CPU). System hits 500%+ and freezes.

### Task 2.1: Evaluate approaches

Three options from the handoff. Evaluate before implementing:

**Option A: Background-thread texture caching**
- Cache decoded Cairo ImageSurface objects in a background thread
- Draw callback only blits pre-decoded surfaces (fast memcpy)
- Pro: minimal architecture change. Con: still paying decode cost, just moved off render thread.

**Option B: GStreamer-native triangle layout**
- Position cameras as GStreamer compositor tiles in triangular arrangement
- Use compositor pad properties (xpos, ypos, width, height, alpha) — no Cairo at all
- Pro: zero per-frame CPU overhead for video placement. Con: triangle clip paths not possible with rectangular tiles; waveform needs a different solution.

**Option C: Camera reduction when Sierpinski active**
- Reduce to 3 cameras (one per triangle corner) and lower framerate
- Pro: drops MJPEG decode baseline. Con: loses the other 3 camera views.

**Decision gate:**
- [ ] Benchmark Option A: measure per-frame decode time for 3 JPEG surfaces in a background thread
- [ ] Benchmark Option B: prototype 3-tile compositor layout, measure CPU
- [ ] Choose approach based on measurements
- [ ] Write decision in a context artifact

### Task 2.2: Implement chosen approach

- [ ] Implement the performance solution
- [ ] Verify CPU stays below 400% total with Sierpinski active (5 cameras + triangle render)
- [ ] Run compositor for 5+ minutes — no freezes, no frame drops visible in OBS
- [ ] Commit

### Task 2.3: Visual polish and verification

- [ ] Verify Sierpinski renders correctly: 3 video frames in corners, waveform in center void
- [ ] Verify GL shader effects apply on top of the triangle (effects visible in OBS)
- [ ] Verify director slot cycling changes which corner video is "active" (opacity change)
- [ ] Verify audio mute/unmute via SlotAudioControl still works
- [ ] Take a screenshot for the PR description
- [ ] Commit any polish fixes

### Task 2.4: Merge PR #644

- [ ] Push final state to `feat/sierpinski-visual-layout`
- [ ] Verify all CI checks pass
- [ ] Merge PR #644
- [ ] Delete branch
- [ ] Rebase alpha worktree: `git fetch origin main && git rebase origin/main`

**Acceptance:** Sierpinski triangle renderer live in OBS output. CPU < 400% total. No freezes. PR #644 merged.

---

## Stage 3: Dynamic Camera Resolution

**Scope:** Implement runtime camera resolution and framerate management. Hero mode (one camera emphasized), balanced mode, Sierpinski mode.

**Branch:** New feature branch (after PR #644 merged)

**Spec:** None yet — needs brainstorming.

**Depends on:** Stage 2 (Sierpinski renderer determines camera budget)

### Task 3.1: Write spec (brainstorming session)

**Research already done** (from handoff):
- C920s cap at 30fps. BRIO-room is USB 2.0 (60fps max). Two BRIOs are USB 3.0 (90fps MJPEG).
- V4L2 resolution change requires pipeline branch restart (~200-500ms blackout)
- Display-side scaling (compositor pad properties) is instant
- **Approach D recommended:** capture at max resolution, scale down non-hero cameras via compositor tile properties. Only restart v4l2src for framerate changes.

- [ ] Run `superpowers:brainstorming` with the above context
- [ ] Write spec to `docs/superpowers/specs/`
- [ ] Write implementation plan to `docs/superpowers/plans/`

### Task 3.2: Implement display-side scaling

- [ ] Add compositor pad property control (width/height scaling per camera tile)
- [ ] Camera profile presets: hero (1 camera full, others small), balanced (2 prominent, 3 small), sierpinski (3 corners only)
- [ ] Runtime switching between profiles (command registry command)

### Task 3.3: Implement V4L2 framerate switching

- [ ] Pipeline branch restart mechanism for framerate changes (v4l2src only, not full pipeline)
- [ ] Blackout handling (~200-500ms transition)
- [ ] Automatic framerate selection based on active profile

### Task 3.4: Wire to director and visual governance

- [ ] Director selects camera profile based on activity (vinyl → hero on turntable cam, study → hero on screen cam)
- [ ] Visual governance can request camera mode changes
- [ ] Commit, PR, merge

**Acceptance:** Camera layout switches at runtime. Hero mode shows one camera large. CPU budget stays within limits per profile.

---

## Stage 4: Reactor Context Enrichment

**Scope:** Enrich the director LLM prompts with phenomenal context, TOON-format ContextAssembler snapshots, dual-image input, and reaction memory threading.

**Branch:** New feature branch

**Spec:** `docs/superpowers/specs/2026-04-10-reactor-context-enrichment-design.md` (approved)

**Depends on:** Nothing (can run in parallel with Stage 3)

### Task 4.1: Write implementation plan

- [ ] Read the approved spec thoroughly
- [ ] Write implementation plan using `superpowers:writing-plans`
- [ ] Save to `docs/superpowers/plans/`

### Task 4.2: Integrate phenomenal context

- [ ] Import `phenomenal_context.render(tier="FAST")` into director loop
- [ ] ~200 tokens of environmental awareness (presence, stance, stimmung, perception)
- [ ] Verify it reads from /dev/shm only (no daimonion coupling)

### Task 4.3: Add ContextAssembler snapshot

- [ ] Wire `ContextAssembler.snapshot()` in TOON format into director prompt
- [ ] ~150 tokens of structured system state
- [ ] Verify 40% token savings over JSON

### Task 4.4: Implement dual-image input

- [ ] Send 2 images per LLM call:
  - `yt-frame-{N}.jpg` (384x216, readable video detail)
  - `fx-snapshot.jpg` (1920x1080, viewer POV with effects)
- [ ] Verify Claude Opus accepts dual-image format via LiteLLM `balanced` route

### Task 4.5: Add reaction memory threading

- [ ] Last 8 reactions injected as timestamped thread in system prompt
- [ ] Older reactions dropped (no summarization)
- [ ] Total token budget ~1,020 tokens for all context layers

### Task 4.6: PR and merge

- [ ] Verify director loop still runs within 8s perception interval (no timeout from context assembly)
- [ ] Commit, PR, CI, merge

**Acceptance:** Director LLM receives environmental awareness, system state, dual images, and recent reaction history. Responses show coherence with visible environment. Token budget under 1,100.

---

## Stage 5: Stream Research Infrastructure

**Scope:** Complete the measurement infrastructure for livestream experiments. Qdrant persistence, Langfuse scoring, monthly rotation.

**Branch:** New feature branch

**Spec:** `docs/superpowers/specs/2026-04-10-stream-research-infrastructure-design.md` (draft)

**Depends on:** Nothing (can run in parallel with Stages 3-4)

### Task 5.1: Finalize spec

- [ ] Review draft spec, promote to approved
- [ ] Write implementation plan

### Task 5.2: Qdrant stream-reactions collection

- [ ] Define schema in `shared/qdrant_schema.py` (768-dim nomic-embed vectors, payload: timestamp, activity, text, video_title, tokens, coherence, stimmung snapshot)
- [ ] Embed reaction text via nomic-embed-cpu on write
- [ ] Async persist — must not block director loop (<100ms)

### Task 5.3: Startup memory loading

- [ ] On compositor start, load last 20 reactions from Qdrant into `_reaction_history`
- [ ] Warm restart: Hapax never starts cold — always has recent memory
- [ ] Fallback: SHM snapshot if Qdrant unavailable

### Task 5.4: Langfuse per-reaction scoring

- [ ] `hapax_score()` function recording: `reaction_coherence`, `reaction_tokens`, `reaction_activity`
- [ ] Environment tag `stream-experiment` (segregated from voice experiment traces)
- [ ] Non-blocking async calls

### Task 5.5: Monthly log rotation

- [ ] JSONL rotation: `reactor-log-YYYY-MM.jsonl`
- [ ] Obsidian markdown rotation: same monthly pattern
- [ ] Systemd timer or startup check

### Task 5.6: PR and merge

- [ ] Update `tests/test_qdrant_schema.py` to include new collection
- [ ] Commit, PR, CI, merge

**Acceptance:** Every director reaction persisted to JSONL + Qdrant + Langfuse. Compositor restart loads recent memory. Monthly rotation working.

---

## Stage 6: Future Enhancements (Backlog)

**Scope:** Lower-priority items from the original Garage Door spec. Not sequenced — pick up opportunistically or when relevant.

### 6.1: VST Voice Effects
- Insert PipeWire `filter-chain` module between TTS assistant sink and 24c output
- Architectural path clear (TTS already routes to dedicated sink)
- No spec needed — small, contained work

### 6.2: Simulcast (Twitch + Kick)
- Restream.io integration or multi-RTMP output from OBS
- Needs account setup + stream key management

### 6.3: Chat-Reactive Effects
- YouTube Live chat API → Logos API → director loop → preset switching
- Needs chat polling daemon + command registry integration

### 6.4: Stream Overlay (Viewer Count, Chat)
- Additional cairooverlay zones for live data
- Needs YouTube Data API v3 polling

### 6.5: Native GStreamer RTMP (Eliminate OBS)
- Replace OBS with `rtmpsink` in GStreamer pipeline
- Removes a process from the chain, simplifies deployment
- Risk: lose OBS's NVENC quality tuning

### 6.6: TikTok Clip Pipeline
- Automated vertical clip extraction from VODs
- Needs scene detection + crop-to-vertical + upload API

### 6.7: Stream as Affordance
- Register "go live" as a recruited capability in AffordancePipeline
- DMN decides to start streaming based on environmental context
- Depends on unified semantic recruitment maturity

---

## Cross-Cutting Concerns

### CI Health
Every stage must leave CI green. Pre-existing test failures fixed in Stage 1 establish the baseline. No new test failures tolerated.

### Relay Protocol
Update `~/.cache/hapax/relay/alpha.yaml` after each stage completes. Note merged PRs so beta knows to pull. Write context artifacts for stages with >30 min of accumulated understanding.

### Performance Budget
- **CPU ceiling:** 400% total (8 cores / 16 threads on Ryzen, load ~17-20 baseline)
- **GPU:** RTX 3090, ~14% utilization currently. Shader pipeline is GPU-bound but light.
- **VRAM:** ~12.7/24.6 GB used. No new GPU allocations expected in this epic.

### Branch Discipline
One branch at a time. Each stage's PR merged before starting the next stage (except Stages 3 and 4 which can run in parallel on separate branches if needed — but only if no file conflicts).

---

## Priority Order

| Priority | Stage | Effort | Blocked By |
|----------|-------|--------|------------|
| 1 | Stage 1: Triage & Stabilize | ~1 hour | Nothing |
| 2 | Stage 2: Sierpinski Performance | ~2-4 hours | Stage 1 |
| 3 | Stage 4: Reactor Context Enrichment | ~2-3 hours | Stage 2 (branch discipline) |
| 4 | Stage 5: Stream Research Infra | ~2-3 hours | Stage 4 (branch discipline) |
| 5 | Stage 3: Dynamic Camera Resolution | ~3-4 hours | Stage 5 (branch discipline) |
| 6 | Stage 6: Future Enhancements | Ongoing | As capacity allows |

**Note:** Stages 3 and 4 are independent in content but serialized by branch discipline (one branch at a time). Stage 4 is prioritized over Stage 3 because it directly improves stream quality (richer autonomous behavior) while Stage 3 is optimization.

---

## Specs & Plans Reference

| Document | Type | Status |
|----------|------|--------|
| `specs/2026-04-04-garage-door-open-streaming-design.md` | Spec | Approved (Phase 1 done) |
| `specs/2026-04-11-sierpinski-visual-layout-design.md` | Spec | Approved |
| `specs/2026-04-10-reactor-context-enrichment-design.md` | Spec | Approved |
| `specs/2026-04-10-stream-research-infrastructure-design.md` | Spec | Draft |
| `specs/2026-04-10-activity-selector-design.md` | Spec | Draft (80% implemented) |
| `specs/2026-04-11-gpu-mjpeg-decode-design.md` | Spec | Dead end (nvjpegdec incompatible) |
| `plans/2026-04-11-sierpinski-visual-layout.md` | Plan | Exists (needs perf task added) |
| Dynamic Camera Resolution | Spec | **Needs writing** |
| Reactor Context Enrichment | Plan | **Needs writing** |
| Stream Research Infrastructure | Plan | **Needs writing** |
