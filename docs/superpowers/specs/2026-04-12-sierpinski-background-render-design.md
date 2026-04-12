# Sierpinski Background Render — Design Spec

**Status:** Draft
**Author:** alpha session
**Date:** 2026-04-12
**Blocking:** PR #644 merge (Stage 2 of Garage Door Phase 2 epic)

## Problem

The Sierpinski renderer (`sierpinski_renderer.py`) performs JPEG decode and full Cairo rendering synchronously inside the GStreamer `cairooverlay` draw callback. This callback runs in the GStreamer streaming thread at 30fps and must complete before the next buffer can be processed.

### Root Cause

`youtube-player.py` writes JPEG snapshots at 10fps per slot (`ffmpeg -r 10 -update 1`). Three slots = 30 JPEG writes/sec. Each write changes the file mtime, which causes `_load_frame()` to re-decode via GdkPixbuf on the next draw callback invocation.

**Measured costs:**
- GdkPixbuf JPEG decode (384×216): **8.4ms** per decode
- Full Cairo render (lines + video compositing): **2.9ms** per frame
- Combined worst case: 3 × 8.4ms + 2.9ms = **28.1ms** per callback

At 30fps, each callback has a 33ms budget. A 28ms callback consumes **85% of the budget**, leaving only 5ms for the rest of the GStreamer pipeline work on that thread (compositor blitting, format conversion, glupload). Under contention with MJPEG decode threads, this causes pipeline stalls and system freezes.

### Constraint

The `on_draw` callback MUST be fast (<2ms). It runs in the GStreamer streaming thread alongside camera MJPEG decode, compositor tile blitting, and GL upload. Any blocking work in this callback causes back-pressure that propagates to camera capture pipelines.

## Solution: Background Render Thread

### Architecture

```
Background Thread (10fps)              GStreamer Pipeline Thread (30fps)
┌──────────────────────────┐            ┌────────────────────────────────┐
│ 1. Poll yt-frame-{0,1,2}.jpg        │ on_draw callback:             │
│ 2. Decode JPEG → Cairo surface      │   1. Read _output_surface     │
│ 3. Render full Sierpinski frame:     │   2. cr.set_source_surface()  │
│    - Video frames in corners         │   3. cr.paint()               │
│    - Triangle line work              │   4. Return (<0.5ms)          │
│    - Waveform bars                   │                                │
│ 4. Write to _output_surface (lock)   │                                │
│ 5. Sleep until next tick             │                                │
└──────────────────────────┘            └────────────────────────────────┘
        ▲                                       │
        │         threading.Lock                 │
        └───── _output_lock ────────────────────┘
```

### Design Decisions

1. **Render at 10fps, not 30fps.** The content updates at 10fps (ffmpeg snapshot rate). Rendering faster wastes CPU. The pipeline blits the cached surface at 30fps — visual smoothness comes from the shader effects applied AFTER the cairooverlay, not from the overlay frame rate.

2. **Single output surface with a lock.** The background thread writes a complete ARGB32 surface. The draw callback reads it under a lock. Lock contention is near-zero because the draw callback holds the lock for <0.5ms (single surface blit) and the background thread holds it for <1ms (surface swap).

3. **No partial updates.** The entire frame is re-rendered on each tick. At 10fps with 2.9ms render time, the background thread uses ~3% of one core. Partial update logic (dirty rectangles) adds complexity for negligible gain.

4. **Audio energy via atomic float.** The draw callback does NOT render the waveform. The background thread reads `_audio_energy` (set by the compositor's audio capture) and renders the waveform into the cached surface. The 10fps update rate is sufficient for visual waveform animation.

### Implementation

**Modified files:**
- `agents/studio_compositor/sierpinski_renderer.py` — refactor to background thread model

**Key changes:**

1. `__init__()`: Start background render thread, create output surface and lock
2. `_render_loop()`: New method — 10fps loop that decodes, renders, swaps surface
3. `draw()`: Now just blits `_output_surface` under lock (<0.5ms)
4. `_load_frame()`: Unchanged (called from background thread now)
5. `stop()`: Signal background thread to exit

**Thread safety:**
- `_output_surface`: protected by `_output_lock` (threading.Lock)
- `_audio_energy`: plain float, set from main thread, read from background — atomic on CPython (GIL)
- `_active_slot`: plain int, same GIL guarantee

### Performance Budget

| Component | Before (per frame) | After (per frame) |
|-----------|--------------------|--------------------|
| Draw callback | 8-28ms | <0.5ms |
| Background thread | — | 11.3ms @ 10fps |
| CPU (draw callback @ 30fps) | 25-85% core | ~1.5% core |
| CPU (background @ 10fps) | — | ~3% core |
| **Total CPU** | **25-85% core** | **~4.5% core** |

### Acceptance Criteria

- [ ] Draw callback completes in <2ms (measured via timestamp delta)
- [ ] No visible frame drops in OBS output during Sierpinski rendering
- [ ] Compositor total CPU stays below 400% with Sierpinski active
- [ ] Video frames update within 200ms of youtube-player writing new snapshot
- [ ] Waveform animates smoothly at 10fps (visually acceptable)
- [ ] Active slot opacity change visible within 100ms of director switch
- [ ] No threading deadlocks during start/stop lifecycle

### Risk

**Low.** The approach is a standard double-buffer pattern. The only risk is lock contention if the background render takes longer than expected, but at 2.9ms render + 8.4ms decode = 11.3ms per tick, the background thread is idle 88% of the time at 10fps.

## Alternatives Considered

### GStreamer-native triangle layout (rejected)
Position cameras as GStreamer compositor tiles in triangular arrangement. Eliminates Cairo entirely for video content. **Rejected** because GStreamer compositor only supports rectangular tiles — can't achieve triangular clipping. Would require completely different visual design.

### Camera reduction when Sierpinski active (deferred)
Reduce to 3 cameras when triangle layout is active. Saves MJPEG decode CPU but doesn't address the rendering overhead. **Deferred** to Stage 3 (Dynamic Camera Resolution) where it can be designed properly as part of the camera profile system.

### Reduce rendering quality (rejected)
Remove glow effects, reduce subdivision levels. Would cut rendering cost but defeats the visual design intent (synthwave aesthetic, fractal detail). The background thread approach achieves full quality at negligible cost.
