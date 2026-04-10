# Activity Selector — Hapax Autonomous Livestream Behavior

**Date:** 2026-04-10
**Amends:** `2026-04-10-spirograph-reactor-design.md`
**Status:** Draft

---

## Problem

The director loop runs a fixed four-beat rotation (V1 → React → V2 → React → V3 → React). Hapax has one behavior: react to videos. But the stream is 36 hours. Hapax should autonomously choose what to do based on what's happening: react to videos, engage chat, comment on music, be silent, or study its own research.

## Design

### Activities

| Activity | Trigger signals | Perception input |
|----------|----------------|-----------------|
| `react` | Video playing, content changing | Video frame + compositor snapshot |
| `chat` | Messages in chat-recent.json | Recent messages + chat state |
| `vinyl` | Track change in album-state.json | Album metadata + audio signals |
| `study` | Low activity, late hour, SEEKING stance | Research document excerpt |
| `observe` | Camera scene change, hand activity | Camera snapshot + IR signals |
| `silence` | Low energy, no chat, late hour, between tracks | Nothing (no LLM call) |

### Activity Selection

Every perception tick (~8s during video, ~15s otherwise), the director reads all available signals and scores each activity:

```
score(activity) = signal_strength × stimmung_modifier × circadian_bias × inertia
```

- **signal_strength**: is there something for this activity to respond to? (chat messages → chat score high; track change → vinyl score high; nothing happening → silence score high)
- **stimmung_modifier**: stance affects thresholds (SEEKING explores, cautious stays)
- **circadian_bias**: 4am → silence/study preferred; peak hours → react/chat preferred
- **inertia**: current activity gets a bonus to prevent thrashing. Minimum 15s per activity.

Highest score wins. If it's the same activity, continue. If different, transition.

### Transitions

Transitions are simple: stop speaking (if speaking), update the overlay header, switch the prompt. The spirograph, videos, music, and shader effects continue uninterrupted — they're structural, not activity-dependent.

The overlay header changes from "REACTOR" to the activity name (or nothing for silence).

### Prompt Structure

All activities share one prompt builder. The core identity block (what Hapax is, what it's working toward, grounding context) stays constant. The activity-specific block changes:

- **react**: "Two images. The video up close. The composed surface. What caught you?"
- **chat**: "Someone asked: '{message}'. Answer from what you know."
- **vinyl**: "New track: {title} by {artist}. What do you hear?"
- **study**: "You're reading: '{excerpt}'. What does this illuminate right now?"
- **observe**: "Camera shows: [image]. What's happening in the space?"
- **silence**: No LLM call. Just wait.

### No Affordance Pipeline Integration (Yet)

The full vision registers activities as affordances and lets the recruitment pipeline select them via imagination intent. That's architecturally correct but too much machinery for launch. The initial implementation is a simple signal-scoring function in the director loop. The affordance registration is a Phase 2 upgrade.

### Output

All activities share: TTS synthesis, Pango overlay, waveform visualization, Obsidian log. The overlay header dynamically shows the current activity. The Obsidian log tags entries with the activity name.

## What Doesn't Change

- Spirograph path rendering and animation
- Video slot orbiting and frame capture
- Shader preset cycling (random_mode.py)
- Album identification and splattributions
- Token pole and bouncing text overlays
- Chat monitor ingestion (when live)
