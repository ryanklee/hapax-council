# Session Handoff — 2026-04-11

## Open Garage Door Project — Current State

The "Garage Door Open" project is a 24/7 livestream of all R&D and music production work using the studio compositor + OBS. Original spec: `docs/superpowers/specs/2026-04-04-garage-door-open-streaming-design.md`.

### What's Working (on main)

**Core streaming pipeline:**
- 6 USB cameras (3 BRIO + 3 C920) at 720p@30fps → cudacompositor → cairooverlay → 24 glfeedback shader slots → `/dev/video42` (OBS V4L2 source)
- OBS captures compositor output + two PipeWire audio sources (mixer_master + echo_cancel_source)
- YouTube live description auto-updater with attribution logging

**Audio stream management (PR #643, merged today):**
- `SlotAudioControl` — PipeWire per-stream volume via `wpctl`. Idempotent `mute_all_except(slot)` replaces the broken SIGSTOP toggle mechanism.
- TTS (Kokoro) routed to `input.loopback.sink.role.assistant` PipeWire sink — separated from YouTube content audio. OBS can mix voice and content independently.
- Director threading fixed — speech + slot advance merged into single locked thread (`_transition_lock`). No more racy `_advance` threads.
- youtube-player is now a pure play/stop daemon — SIGSTOP/SIGCONT and pause endpoints removed.

**Performance fixes (merged today):**
- All cameras at 720p (BRIOs down from 1080p). Steady-state compositor CPU ~200-250%.
- Camera snapshot rate 1fps → 0.2fps.
- Effect pipeline uniform logging reduced from INFO to DEBUG (eliminated 558 journald writes/sec).

**Director loop (Hapax autonomous behavior):**
- Unified LLM-driven activity selector (react/chat/vinyl/study/observe/silence) every 8s
- TTS synthesis + speech → slot advance in a single locked thread
- YouTube slot cycling with audio mute/unmute via SlotAudioControl
- Reaction history persisted in SHM + Qdrant for warm restart
- JSONL structured logging to `~/Documents/Personal/30-areas/legomena-live/reactor-log.jsonl`

### What's In Progress (PR #644, not merged)

**Sierpinski Triangle Visual Layout** — replacing the spirograph reactor with a static Sierpinski triangle. PR #644 on `feat/sierpinski-visual-layout` branch.

**What's been built:**
- Two WGSL shaders (`sierpinski_content.wgsl`, `sierpinski_lines.wgsl`) — NVIDIA-compatible (flattened scalar geometry, no nested array types)
- wgsl_compiler fix — `sierpinski_content` recognized as content slot node (gets 4 texture inputs injected)
- `SierpinskiLoader` Python module — writes YouTube frames to content slot manifest for Rust ContentTextureManager
- `VideoSlotStub` — lightweight slot objects for DirectorLoop compatibility
- `SierpinskiRenderer` — Cairo renderer drawing in the pre-FX cairooverlay (correct pipeline position, before GL effects)
- Inscribed 16:9 rectangle computation for video containers within triangle corners
- Waveform visualization in center triangle void

**What's blocked:**
- Cairo rendering + GdkPixbuf JPEG loading at 30fps adds too much CPU overhead on top of the 5-camera MJPEG decode baseline. System hits 500%+ CPU and everything freezes.
- The branch has ~12 commits including multiple reverts (WGSL → Cairo pivot, NVIDIA crash fixes). Needs cleanup.

**Key architectural decisions made:**
1. Render in the GStreamer pre-FX cairooverlay (NOT the wgpu Reverie visual surface) — so GL shader effects apply
2. The WGSL approach worked technically (shaders compiled on NVIDIA after flattening) but is in the wrong pipeline — the wgpu visual surface is for Reverie, not OBS output
3. The content_layer in wgpu can be replaced with sierpinski_content, but the Rust DynamicPipeline needs the `content_slot_` prefix in input names for the extended bind group layout

**To unblock Sierpinski:**
- Cache Cairo surfaces in a background thread instead of GdkPixbuf JPEG decode per frame in the draw callback
- Or: render the Sierpinski triangle as a GStreamer compositor layout (position cameras in triangle tile arrangement) instead of Cairo overlay — eliminates the per-frame CPU overhead entirely
- Or: reduce camera count/framerate when Sierpinski is active (dynamic camera resolution system)

### What's Planned But Not Started

**Dynamic Camera Resolution/Framerate System:**
- Research complete — C920s cap at 30fps, BRIO-room is USB 2.0 (60fps max), two BRIOs are USB 3.0 (90fps MJPEG)
- Hero mode: BRIO hero 720p@60fps, others lower-res. Dual mode: both prominent cams at 720p@30fps, others small.
- V4L2 resolution change requires pipeline branch restart (~200-500ms blackout). Display-side scaling (compositor pad properties) is instant.
- Approach D recommended: capture at max resolution, scale down non-hero cameras via compositor tile properties. Only restart v4l2src for framerate changes.
- No spec or plan written yet. Was going to fold into Sierpinski design.

**VST Effects on Hapax Voice:**
- TTS already routes to dedicated assistant PipeWire sink
- A PipeWire `filter-chain` module can be inserted between the sink and the 24c output
- No work started — architectural path is clear

**From the original Garage Door spec — future enhancements not yet started:**
- Simulcast (Twitch + Kick via Restream.io)
- Chat-reactive effects (YouTube Live chat → Logos API → preset switching)
- Stream overlay in compositor (viewer count, chat messages, preset name)
- Native GStreamer RTMP (eliminate OBS)
- TikTok clip pipeline (automated vertical clip extraction)
- Stream as affordance (DMN decides to go live)

### Specs Written But Not Implemented

| Spec | Status | Notes |
|------|--------|-------|
| `2026-04-11-sierpinski-visual-layout-design.md` | Approved | Partially implemented on PR #644, blocked on perf |
| `2026-04-11-gpu-mjpeg-decode-design.md` | Approved | Dead end — nvjpegdec incompatible with USB MJPEG |
| `2026-04-10-activity-selector-design.md` | Draft | Director activity selection — partially implemented in current director loop |
| `2026-04-10-reactor-context-enrichment-design.md` | Approved | Context enrichment for director LLM prompts |
| `2026-04-10-stream-research-infrastructure-design.md` | Draft | Measurement infra for livestream (JSONL logging done, Qdrant + Langfuse scoring pending) |
| `2026-04-10-hermes3-70b-voice-architecture-design.md` | Approved | Mono-model voice architecture (beta session scope) |

### Architectural Findings

1. **CPU MJPEG decode is the performance floor.** 5 cameras x 720p@30fps = 200-250% CPU. nvjpegdec doesn't work with USB camera motion-JPEG. No GPU decode path exists for these cameras. The only levers are resolution and framerate.

2. **NVIDIA driver crashes on nested WGSL array types.** `array<array<vec2<f32>, 3>, 3>` as function return types crashes `libnvidia-glvkspirv.so` at SPIR-V compilation. Flattened scalar geometry compiles fine.

3. **The reverie daemon rewrites plan.json.** Any vocabulary preset changes need `hapax-reverie.service` restarted. The rebuild timers also recompile from whatever branch is checked out.

4. **The wgpu visual surface and GStreamer compositor are separate render paths.** Reverie (wgpu/hapax-imagination) goes to Tauri (`:8053`). GStreamer compositor goes to `/dev/video42` (OBS). Content for the stream must render in GStreamer, not wgpu.

5. **PipeWire per-stream volume works cleanly.** `wpctl set-volume {node_id} {level}` is idempotent, sub-millisecond. Node IDs change on ffmpeg restart — cache with invalidation handles this.

### System Health

- **Failed services:** `llm-cost-alert.service`, `vault-context-writer.service`
- **GPU:** RTX 3090, ~14% utilization, ~12.7/24.6 GB VRAM
- **Load:** ~17-20 steady state on main (8 cores / 16 threads)
- **Docker:** 13 containers running. ClickHouse occasionally spikes to 165% CPU (Langfuse analytics).
- **Stale branch:** `feat/sierpinski-visual-layout` (PR #644, 12 commits, not merged)

### Recommended Next Steps

1. **Clean up PR #644** — squash the reverts, decide on Cairo vs alternative renderer
2. **Solve the Sierpinski CPU problem** before re-attempting: background-thread texture caching, GStreamer-native triangle layout, or camera reduction when Sierpinski active
3. **Dynamic camera resolution** — spec and implement after Sierpinski is resolved
4. **Stream research infrastructure** — finish Qdrant persistence + Langfuse scoring
5. **Fix failed services** — `llm-cost-alert`, `vault-context-writer`
