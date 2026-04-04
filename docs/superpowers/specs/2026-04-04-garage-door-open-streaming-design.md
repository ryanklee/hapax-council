# Garage Door Open — Live Streaming Design

## Goal

Ship a nightly live stream of all R&D and music production work using the existing studio compositor, node graph effect system, and multi-camera infrastructure. YouTube Live as primary platform. First stream tonight.

## Architecture

```
GStreamer Compositor (30fps, 1920x1080)
  6 cameras → cudacompositor → cairooverlay (HUD) → FX chain (8 glfeedback slots)
    → v4l2sink /dev/video42

OBS Studio (thin RTMP shipper)
  V4L2 Source: /dev/video42 (1920x1080@30 YUY2)
  Audio 1: mixer_master (PipeWire — Zoom L-12 output: beats, turntables, synths)
  Audio 2: echo_cancel_source (PipeWire — AEC-cleaned Blue Yeti voice)
  Output: NVENC H.264 CBR 6000kbps → RTMP → YouTube Live
```

OBS does zero visual processing. No OBS filters, no OBS overlays, no scene switching. The compositor IS the production. OBS is a mux-and-ship layer.

### Why not native GStreamer RTMP?

Could add `rtmp2sink` branch to the compositor pipeline, eliminating OBS entirely. Deferred because:
- Audio mixing (two PipeWire sources → single stereo stream) requires `audiomixer` plumbing
- RTMP reconnection/health monitoring must be built from scratch
- OBS handles both trivially and is already installed
- Native RTMP is a future optimization, not a blocker

### Why not OBS effects?

The node graph system is categorically more powerful than OBS's linear filter stack:
- DAG topology with multi-input nodes (blend, content_layer, diff)
- Per-node temporal accumulation buffers (trail, ghost, feedback, reaction-diffusion)
- Continuous perceptual signal modulation (bass → bloom, heartrate → breathing)
- Governance-driven automatic preset selection with axiom vetoes

OBS cannot replicate any of these. The 28 presets and 54 shaders stay in the compositor.

## Technical Changes

### 1. Framerate: 10fps → 30fps

**File:** `agents/studio_compositor/models.py` line 73

The compositor was throttled to 10fps to save CPU when no consumer needed more. Streaming needs 30fps.

Change: `framerate: int = 10` → `framerate: int = 30`

Also check `agents/studio_compositor/smooth_delay.py` for any hardcoded fps values.

Impact: ~3x more GPU compositor work. The 3090 is at 70% VRAM with NVENC idle — no capacity issue. CPU load will increase but the compositor was previously at 30fps before the optimization.

### 2. OBS Configuration

**Scene: "Studio Live"**
- Source 1: V4L2 Video Capture Device → `/dev/video42`, 1920x1080, YUY2
- Source 2: Audio Input Capture (PipeWire) → `mixer_master` (music)
- Source 3: Audio Input Capture (PipeWire) → `echo_cancel_source` (voice)

**Output Settings:**
- Encoder: NVENC H.264 (hardware)
- Rate Control: CBR 6000 kbps
- Keyframe Interval: 2 seconds
- Preset: p5 (quality)
- Profile: high
- Look-ahead: off
- B-frames: 2

**Audio Settings:**
- Sample Rate: 48 kHz
- Channels: Stereo
- Audio Bitrate: 160 kbps AAC

**Stream Settings:**
- Service: YouTube - RTMPS
- Server: Primary YouTube ingest
- Stream Key: from YouTube Studio → Go Live → Stream

**Advanced:**
- Color Format: NV12
- Color Space: 709
- Color Range: Partial

### 3. YouTube Channel Setup

- Go to YouTube Studio → Go Live → Stream
- Title: "[something descriptive] — building AI + making beats"
- Category: Science & Technology (or Music, depending on session)
- Visibility: Public
- Enable DVR (lets viewers rewind)
- Enable live chat
- Copy stream key to OBS

### 4. Audio Levels

- `mixer_master` (music): -6dB to -3dB (dominant but not clipping)
- `echo_cancel_source` (voice): 0dB (clear over music)
- OBS audio mixer balances these two. Monitor with VU meters.
- The AEC source already suppresses speaker bleed from monitors.

## Operational

### Stream Schedule

- **Nightly, 4-6 hours.** Consistent time slot (e.g., 8PM-2AM CDT) builds audience.
- **No performance pressure.** This is "garage door open" — work normally, stream catches it.
- **Content mix:** R&D coding, music production, gear exploration, thinking, wandering. All of it.

### What viewers see

The compositor's existing output: 6-camera tile with perception HUD overlay, whatever shader preset is active (switched via Logos API, keyboard, or governance autopilot). Audio is the full studio mix plus voice.

The effect switching (28 presets, perceptual modulation, governance-driven) happens live on stream. This is the differentiator — the AI system autonomously changes the visual aesthetic based on what you're doing.

### Stream hygiene

- Start stream, say hello, describe what you're working on
- Work normally — don't perform
- End stream when done, no formal sign-off needed
- YouTube automatically generates VOD from the stream

### Content safety

- No employer work visible (corporate_boundary axiom)
- Consent overlay on compositor handles recording consent state
- The perception HUD shows system state — review what's visible to ensure no sensitive data
- The management governance axiom prevents any team member names/feedback from appearing

## Future Enhancements (not tonight)

### Week 2: Simulcast
Add Twitch + Kick via Restream.io or OBS multistream plugin. Same single OBS output, fan-out to 3 platforms.

### Week 2: Chat-reactive effects
Wire YouTube Live chat → Logos API → compositor preset switching. Viewers vote on effects. obs-websocket not needed — the Logos command relay at `:8052` already accepts preset switch commands.

### Week 3: Stream overlay in compositor
Add stream-specific info to the cairooverlay: current preset name, viewer count, chat messages. Rendered by the compositor, not OBS.

### Month 2: Native GStreamer RTMP
Eliminate OBS entirely. Add RTMP branch to compositor pipeline:
```
output_tee → queue → audiomixer(pipewiresrc×2) → flvmux → rtmp2sink
```
Handles audio mixing and RTMP in-process. Reconnection logic via GStreamer bus messages.

### Month 2: TikTok clip pipeline
Automated clip extraction from VODs. Key moments (effect switches, beat drops, interesting code) identified by the DMN and exported as vertical clips for TikTok/Shorts/Reels.

### Month 3: Stream as affordance
The stream itself becomes a registered affordance in the recruitment pipeline. The DMN can decide to "go live" based on activity patterns, or suggest going live via voice.

## Success Criteria

**Tonight:** Video and audio reach YouTube Live. Stream is watchable. Effects are visible.

**Week 1:** 5+ hours streamed across 3+ nights. At least one VOD with >100 views.

**Month 1:** Consistent nightly schedule. Affiliate/monetization application submitted. Clips posted to Shorts.

**Month 3:** 100+ concurrent viewers during peak. Revenue from Super Chat/memberships. Second platform active.
