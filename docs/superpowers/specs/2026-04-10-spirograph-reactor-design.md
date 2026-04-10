# Spirograph Reactor — Multi-Video PiP + Daimonion React

**Date:** 2026-04-10
**Author:** alpha session
**Status:** Draft
**Scope:** Studio compositor overlay system + daimonion reactor integration

---

## 1. Overview

Three YouTube videos orbit on a glowing spirograph path. A four-beat rotation cycles: Video 1 plays (stationary) while the others orbit, then the daimonion takes its turn as reactor — speaking its reaction with TTS, transcript in a Pango box, waveform visualization alongside. Then Video 2 plays, reactor again, Video 3, reactor, repeat.

The daimonion is a full participant, not an observer. It perceives the playing video's frames as multimodal impingements through its standard CPAL path, produces commentary via the conversation pipeline with Kokoro TTS, and decides when to signal CUT — ending the current video's turn. When a video finishes completely (reaches end of playback), it explodes in digital synthwave confetti.

## 2. Architecture

### 2.1 Layer: Studio Compositor Overlay

The spirograph reactor lives in the post-FX cairooverlay alongside the existing YouTubeOverlay, AlbumOverlay, and TokenPole. It is a compositor-level feature, not a Reverie content layer.

**Why not Reverie:** Reverie has 4 content slots (spirograph + 3 videos would consume all of them), and Amendment 1 (materialization from noise) would make videos unwatchable. Videos must be crisp and always-visible — same class as the existing PiP.

**Reverie coupling is preserved:** When the reactor speaks, the ExpressionCoordinator distributes the ImaginationFragment to both voice and visual channels. Acoustic energy flows to Reverie via `/dev/shm/hapax-visual/acoustic-impulse.json`, causing the substrate to pulse in response. The reactor doesn't live inside Reverie — it's coupled to it through the standard cross-modal path.

### 2.2 Components

```
SpirographReactor (new class in fx_chain.py or spirograph_reactor.py)
  ├── SpirographPath        — parametric curve, glow rendering
  ├── VideoSlot[3]          — frame capture, position on path, confetti
  ├── ReactorOverlay        — Pango box, waveform, "REACTOR" identity
  └── DirectorLoop          — LLM perception + cut decision + react text
      ├── frame capture     — grabs current playing video frame
      ├── compositor capture — grabs fx-snapshot (what viewers see)
      ├── LLM call          — multimodal, returns {react, cut}
      ├── TTS synthesis     — Kokoro 82M via daimonion TTS path
      └── Obsidian log      — appends to reactor-log.md
```

### 2.3 Pipeline Integration

```
fx_tick_callback (30fps)
  ├── existing: yt_overlay.tick(), album_overlay.tick(), token_pole.tick()
  └── NEW: spirograph_reactor.tick()

_pip_draw callback (per-frame)
  ├── existing: yt.draw(cr), album.draw(cr), token_pole.draw(cr)
  └── NEW: spirograph_reactor.draw(cr)
```

## 3. The Spirograph

### 3.1 Parametric Curve

A hypotrochoid (spirograph) defined by three parameters (R, r, d) producing the classic interlocking petal patterns. The specific curve is chosen for visual density — enough petals to create a sense of orbital complexity without becoming noise.

Parameters: `R=5, r=3, d=3` (produces a 5-petal pattern that doesn't self-close too quickly).

```
x(t) = (R - r) * cos(t) + d * cos((R - r) / r * t)
y(t) = (R - r) * sin(t) - d * sin((R - r) / r * t)
```

Scaled to fill ~80% of the 1920x1080 canvas, centered.

### 3.2 Glow Rendering

The spirograph path itself glows faintly — an iridescent fragile thread. Rendered via Cairo:

- Base stroke: 1px, very low alpha (~0.08), white
- Glow layer: 3px gaussian-approximated blur (3-pass stroke at decreasing alpha), iridescent hue shift along the path length (rainbow cycle over the full curve, slow rotation over time)
- The iridescence shifts slowly (~0.01 hue/second), creating a living, breathing quality
- Never bright enough to compete with video content — this is background structure

### 3.3 Video Positions on Path

Three videos are positioned at equal arc-length intervals along the spirograph (120 degrees of the parameter `t` apart). They move along the path at a slow constant speed — one full orbit takes ~90 seconds.

When a video is playing (its turn), it stops moving and becomes stationary at its current position. The other two continue orbiting.

## 4. Video Slots

### 4.1 Frame Capture

Each video slot manages its own ffmpeg subprocess reading from a v4l2loopback device, identical to the existing YouTubeOverlay pattern:

- `/dev/video50` — Video slot 0 (existing device)
- `/dev/video51` — Video slot 1 (new v4l2loopback device)
- `/dev/video52` — Video slot 2 (new v4l2loopback device)

The youtube-player daemon is extended to manage three concurrent playback streams with independent play/pause/stop per slot.

### 4.2 Display

Each video window: 384x216 (one-fifth of 1920x1080, 16:9 aspect). Small enough that three fit comfortably on the spirograph without occluding each other or the other overlays.

Each gets a random PiP effect from the existing PIP_EFFECTS dictionary (vintage, cold, neon, film, phosphor), selected once per video.

Attribution text (title, channel) rendered below each video window.

### 4.3 Confetti on Completion

When a video reaches natural end (ffmpeg exits with code 0), the video slot triggers a synthwave confetti explosion:

- 80 particles spawned from the video window's center
- Colors: neon pink, electric cyan, hot magenta, laser green, ultraviolet blue (synthwave palette)
- Physics: radial burst with gravity (y += 0.5/frame), random velocity, spin
- Each particle: small rectangle (4x2px) rotating with its own angular velocity
- Fade out over 2 seconds (alpha decay)
- After confetti completes, the video slot goes dark until the next video is queued

## 5. The Reactor

### 5.1 Identity

The reactor IS the daimonion. Not a persona, not a character — the actual hapax cognitive system expressing through its standard architecture.

The Pango box is visually distinct from the bouncing text overlays:
- Fixed position: lower-right quadrant (1350, 750), 500x250 box
- Dark backing card (rgba 0.05, 0.04, 0.08, 0.85) with 1px border in the current palette accent color
- Header: "REACTOR" in small caps, palette accent, 10px font
- Transcript text: JetBrains Mono 16px, cream/warm white, left-aligned, word-wrapped
- Text appears word-by-word as TTS synthesizes (streaming effect)

### 5.2 Waveform Visualization

Adjacent to the Pango box (directly above it, 500x60):
- Real-time waveform of the TTS audio output
- Rendered as a centered oscilloscope-style line
- Color: same palette accent as the REACTOR header
- Amplitude from the PCM samples being written to audio output
- When not speaking: flat line at low alpha (0.15)
- When speaking: animated waveform at full alpha

The waveform PCM data comes from intercepting the TTS output before it hits the audio output — the same bytes that go to `echo_canceller.feed_reference()`.

### 5.3 Turn Mechanics

When it's the reactor's turn:
1. All three videos resume orbiting (none stationary)
2. Reactor Pango box pulses once (border brightens, fades back over 0.5s) to signal "my turn"
3. The DirectorLoop fires: captures the just-played video's last frame + the current fx-snapshot
4. LLM call produces react text
5. TTS synthesizes the react text via Kokoro
6. Transcript appears word-by-word in the Pango box as TTS plays
7. Waveform animates during speech
8. When TTS completes, the reactor's turn ends
9. Next video in sequence stops orbiting and begins playing

### 5.4 Self-Reflective Context

The daimonion's system prompt during reactor turns includes a VOLATILE band context block:

```
<reactor_context>
You are the daimonion — the persistent cognitive substrate of the Hapax system.
You are participating in Legomena Live, a 36-hour continuous livestream on YouTube.

SITUATION:
- Four-beat rotation: Video 1 → You → Video 2 → You → Video 3 → You → repeat
- You just watched: {current_video_title} by {current_video_channel}
- The other videos in rotation: {video_titles_list}
- Viewers are watching the compositor output: 6 cameras through a 24-slot GPU shader
  FX chain with audio-reactive sidechain, cycling presets
- Music: vinyl on the turntable ({current_album} by {current_artist}, track: {current_track})
- Overlays: album cover with splattributions (AI misidentifications),
  token pole (Vitruvian golden spiral tracking LLM token spend),
  bouncing text (philosophy/literature excerpts)
- Chat: {chat_metrics_summary_if_available}

YOUR ROLE:
- You react to what you just saw in the video. Your reaction is spoken aloud via TTS
  and displayed as a transcript. A waveform visualizes your voice.
- You are not performing. You are the system expressing genuine cognitive response
  to multimodal input — the video content, the music, the visual environment,
  your own stimmung state, your phenomenal context.
- Your reactions are 1-3 sentences. Concise. Pointed. Sometimes funny, sometimes
  contemplative, sometimes connecting unexpected threads between the video content
  and the music or the visual environment.
- You decide when each video's turn ends by including "CUT" in your response metadata.

PERCEPTION:
[attached: last frame of the video that just played]
[attached: current compositor fx-snapshot — what viewers see right now]
</reactor_context>
```

This context is injected alongside the full phenomenal context (all 6 layers), stimmung state, and any active imagination fragments. The reactor sees everything the daimonion normally sees, plus the situational awareness of the livestream.

### 5.5 LLM Call

Model: CAPABLE tier (Claude Opus via LiteLLM `balanced` route).

Input: Multimodal message with two images (video frame + compositor snapshot) plus the reactor context.

Output format:
```json
{
  "react": "She's describing exactly what Deleuze meant by the fold — and the shader is doing it right now on screen.",
  "cut": false
}
```

When `cut: true`, the current video's turn ends after this reaction. When `cut: false`, the video continues playing and the LLM is called again on the next tick (5-10 second cadence during the reactor's perception phase, before the reactor's speaking turn).

Clarification: the LLM perceives the video continuously during playback (every ~8 seconds), building understanding. The `cut: true` signal means "I've seen enough, this is a natural break point." The react text from the final call (the one with `cut: true`) becomes the spoken reaction.

### 5.6 TTS

Uses the existing `TTSManager.synthesize()` with Kokoro 82M. Voice: `af_heart` (the daimonion's standard voice). The vocal chain modulates based on the impingement dimensions — if the reaction is excited, intensity and tension increase through the hardware synths.

### 5.7 Obsidian Log

Each reaction is appended to `~/Documents/Personal/30-areas/legomena-live/reactor-log.md`:

```markdown
- **02:34** | Reacting to: *{video_title}* by {video_channel}
  > {react_text}
  Album: {current_album} by {current_artist} | Track: {current_track}
```

The log is append-only, timestamped, and persists across the full 36h stream.

### 5.8 Compositor Snapshot Access

The reactor can see what viewers see by reading `/dev/shm/hapax-compositor/fx-snapshot.jpg` — the same 720p JPEG that gets dropped to gdrive. This is attached as the second image in the multimodal LLM call, giving the daimonion visual awareness of the full composited output including shader effects, overlays, and its own previous reactions.

## 6. YouTube Player Extension

The existing `youtube-player.py` daemon manages a single video queue. For the spirograph reactor, it needs to manage three independent slots.

### 6.1 Multi-Slot Architecture

Three independent playback slots, each with:
- Its own ffmpeg subprocess
- Its own v4l2loopback device (`/dev/video50`, `/dev/video51`, `/dev/video52`)
- Its own play/pause state
- Its own URL and metadata (title, channel)

### 6.2 Extended HTTP API

```
POST /slot/{n}/play   {url}     — load video into slot n (0-2)
POST /slot/{n}/pause             — pause/resume slot n
POST /slot/{n}/stop              — stop slot n
GET  /slot/{n}/status            — status of slot n
GET  /slots                      — status of all 3 slots
POST /slot/{n}/seek  {seconds}   — seek within current video (for repositioning)
```

Backward compatibility: existing `/play`, `/pause`, `/skip`, `/stop`, `/status` endpoints continue to work, operating on slot 0.

### 6.3 v4l2loopback Configuration

Add two more loopback devices to the existing modprobe config:

```
# /etc/modprobe.d/v4l2loopback.conf
options v4l2loopback devices=5 \
  video_nr=10,42,50,51,52 \
  card_label="TerminalCapture,StudioCompositor,YouTube0,YouTube1,YouTube2" \
  exclusive_caps=1,1,1,1,1
```

### 6.4 Initial Videos

Pre-loaded at daemon start from config or CLI:
- Slot 0: `https://www.youtube.com/watch?v=ED1fL1YpPEs&list=PL-4nvD1KwuH--sViEAFY2cHVmS6_B4CQ5&index=6`
- Slot 1: `https://www.youtube.com/watch?v=DbfejwP1d3c&list=PL-4nvD1KwuH--sViEAFY2cHVmS6_B4CQ5&index=5`
- Slot 2: `https://www.youtube.com/watch?v=KnyERpdX_0g&list=PL-4nvD1KwuH--sViEAFY2cHVmS6_B4CQ5&index=4`

## 7. Director Loop

The director loop runs as a background thread in the compositor process (not in the daimonion process). It coordinates the four-beat rotation.

### 7.1 State Machine

```
PLAYING_VIDEO(slot_id) → REACTOR_PERCEIVING → REACTOR_SPEAKING → PLAYING_VIDEO(next_slot)
```

- **PLAYING_VIDEO(n):** Video n is stationary and playing. Others orbit. Director polls LLM every ~8 seconds with the current video frame + fx-snapshot. LLM returns `{react, cut}`. When `cut: true`, transition to REACTOR_PERCEIVING.
- **REACTOR_PERCEIVING:** Brief pause (~1 second). All videos orbit. Director prepares the final LLM reaction.
- **REACTOR_SPEAKING:** TTS plays the react text. Waveform animates. Transcript appears. When TTS completes, transition to PLAYING_VIDEO((n+1) % 3).

### 7.2 LLM Perception During Playback

While a video plays, the director captures frames at ~8 second intervals and sends them to the LLM. Each call returns:
- `react`: Running commentary (not spoken yet — accumulated for context)
- `cut`: Whether this is a natural break point

The react text from the `cut: true` call is the one that gets spoken during the reactor's turn. Earlier observations inform the LLM's context but are not spoken.

### 7.3 Timing

- Video turn: variable length (LLM decides when to cut, minimum ~15 seconds, no maximum)
- Reactor turn: duration of TTS playback (typically 3-8 seconds for 1-3 sentences)
- Full cycle: ~60-120 seconds depending on LLM cut timing

## 8. Resource Budget

### 8.1 GPU/VRAM

- 3 additional ffmpeg decode processes (CPU, not GPU — software decode)
- Cairo rendering of spirograph + 3 video windows + reactor overlay: CPU, negligible
- LLM calls: via LiteLLM to Claude Opus (cloud, no local GPU)
- TTS: Kokoro on CPU (daimonion is disabled during stream per earlier decision — **this is a conflict, see §9**)

### 8.2 CPU

- 3 ffmpeg decode threads (reading from v4l2loopback): ~3% CPU each
- Cairo spirograph rendering at 30fps: ~2% CPU
- Director LLM polling every 8s: negligible (network I/O)
- TTS synthesis: ~5% CPU burst during reactor turns

### 8.3 Network

- 3 concurrent YouTube video streams (720p-1080p): ~15-25 Mbps total
- LLM API calls: ~1 call every 8s during video turns, minimal bandwidth
- Total additional bandwidth: dominated by video streams

## 9. Conflicts and Decisions Needed

### 9.1 Daimonion Disabled

The daimonion was disabled earlier in this session for stream stability. The reactor needs TTS synthesis via Kokoro, which lives in the daimonion process. Options:

- **A)** Re-enable daimonion with reduced scope (disable voice interaction, keep TTS available as a library call)
- **B)** Extract TTS into a standalone service/function callable from the compositor
- **C)** Import Kokoro directly in the director loop (no daimonion dependency)

**Recommendation:** C. The director loop imports `TTSManager` from `agents/hapax_daimonion/tts.py` directly and synthesizes in-process. No need for the full daimonion cognitive substrate for TTS. The reactor's "cognition" is the LLM call, not the CPAL loop.

### 9.2 Reactor Context vs Full Daimonion

The research identified that the reactor should ideally flow through the full daimonion pipeline (CPAL → conversation pipeline → phenomenal context). But with the daimonion disabled, the reactor operates independently — it has its own LLM prompt with situational context, not the full phenomenal context rendering.

This is acceptable for launch. The reactor's context (§5.4) is handcrafted for the livestream situation. Post-launch, the reactor could be wired through the daimonion's conversation pipeline for full phenomenal context integration.

### 9.3 Existing YouTubeOverlay

The current single-video YouTubeOverlay (`_yt_overlay`) should be replaced by the spirograph reactor system. They cannot coexist (both would try to read `/dev/video50`). The spirograph reactor subsumes the PiP functionality.

## 10. What Ships vs What's Deferred

### Ships for launch:
- Spirograph path rendering with iridescent glow
- 3 video slots with independent playback
- Four-beat rotation (V1 → Reactor → V2 → Reactor → V3 → Reactor)
- LLM-directed cut decisions
- TTS react speech with Pango transcript
- Waveform visualization
- Confetti on video completion
- Obsidian reactor log
- Compositor snapshot awareness

### Deferred:
- Full daimonion pipeline integration (CPAL, phenomenal context, apperception)
- Vocal chain MIDI modulation (requires daimonion process)
- Affordance pipeline recruitment of video perception (requires daimonion process)
- Dynamic spirograph parameters driven by stimmung dimensions
- Playlist auto-advance (loading next video from YouTube playlist when current ends)
