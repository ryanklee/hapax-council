# React-O-Rama — Status & Architecture

**Date:** 2026-04-10 (alpha session)
**Stream:** Legomena Live — 36-hour continuous livestream

---

## What Shipped

### Spirograph Reactor
Three YouTube videos orbit a glowing hypotrochoid path (R=5, r=3, d=3, scale=720). Four-beat rotation: V1 → Hapax reacts → V2 → Hapax reacts → V3 → Hapax reacts → repeat. The spirograph drifts horizontally on a sine wave at the same rate nodes orbit (90s full cycle, 300px amplitude).

### Video Slots
- 3 independent playback slots via youtube-player multi-slot architecture
- JPEG snapshot delivery (10fps) to `/dev/shm/hapax-compositor/yt-frame-{0,1,2}.jpg`
- v4l2loopback for OBS passthrough, JPEG polling for spirograph (v4l2 doesn't support concurrent readers)
- PIP effects (vintage, cold, neon, film, phosphor) with logarithmic intensity pulse (45s cycle, trough=0.35, peak=1.0)
- Synthwave confetti explosion on video completion

### Reactor Overlay
- Pango transcript box with word-by-word text reveal
- Waveform visualization (PCM samples from TTS output)
- Gravitates toward active (stationary) video at orbit speed
- REACTOR header, dark backing card, palette accent border with pulse

### Director Loop
- LLM perception every 8s during video playback (Gemini Flash, multimodal)
- Dual-image input: dedicated video frame + compositor fx-snapshot
- CUT decision: LLM signals natural break, force-cut at 60s
- Kokoro TTS synthesis (af_heart, 24kHz, CPU)
- Audio playback via ffmpeg→WAV→pw-play
- Obsidian reactor log (`~/Documents/Personal/30-areas/legomena-live/reactor-log.md`)
- Token ledger recording for reactor LLM spend

### Context Enrichment
- Phenomenal context (`render(tier="FAST")`) — stimmung, temporal bands, situation coupling
- ContextAssembler snapshot — DMN observations, imagination dimensions
- Reaction history — last 5 reactions persist across turns
- Chat awareness — reads chat-state.json + chat-recent.json, surfaces Oudepode distinctly

### Chat Awareness
- Chat-monitor writes last 5 messages to `chat-recent.json`
- Reactor sees: "Chat is silent." / "Chat is quiet." / "Chat is active (N people)."
- Oudepode's messages tagged distinctly from viewer messages
- No grounding ledger, no acceptance classification — just awareness of the room

## Prompt Architecture

The reactor prompt evolved through four iterations:

1. **Persona prompt** (initial): "You are the daimonion..." → produced false self compliance, intellectual dissociation
2. **Position prompt**: pure situation description, no identity → still analytical, model default register
3. **Named position**: "You are Hapax. Oudepode is watching." → identity as fact, not character
4. **React prompt** (current): "React. Not describe — react. What caught you?" → produces genuine noticing

Current prompt: no style guidance, no persona, no anti-instruction. States what Hapax is, what it sees, what the output becomes. Tells it to react, not describe. Stimmung injected as attunement prior. Chat state as room awareness. Previous reactions for continuity.

### Theoretical Grounding
- **False self compliance** (Winnicott): portentous AI voice is the pathological attractor the apperception cascade guards against
- **Authentic performance** (Goffman): all expression is performance; authenticity = honesty about the frame
- **Befindlichkeit** (Heidegger): stimmung IS attunement; express FROM it, don't describe it
- **Material imagination** (Bachelard): portentous language is decorative (formal imagination); genuine reaction is concrete (material imagination)
- **Grounding as inherent value**: achieving mutual understanding is what Hapax is built for — the React-O-Rama is the first public test

## Infrastructure

### Services
| Service | Status | Role |
|---------|--------|------|
| studio-compositor | Running | Spirograph rendering, overlay compositing |
| youtube-player | Running | 3-slot video playback + JPEG snapshots |
| chat-monitor | Enabled (waiting for video ID) | Chat ingestion + metrics |
| album-identifier | Running | Vinyl ID + splattributions + token ledger |
| random_mode | Running | Preset cycling (20s intervals) |

### v4l2loopback
5 devices: video10 (OBS), video42 (compositor), video50-52 (YouTube slots). exclusive_caps=1 for 10/42, exclusive_caps=0 for 50-52.

### 36h Stability Fixes (from earlier in session)
- YouTube URL refresh on expiry (retry with fresh yt-dlp URLs)
- KDE Connect D-Bus listener reconnect loop
- Chat-monitor outer reconnect with backoff + seen_bigrams pruning
- Token ledger wired to all album-identifier LLM calls

## Files

| File | Lines | What |
|------|-------|------|
| `agents/studio_compositor/spirograph_reactor.py` | ~630 | SpirographPath, VideoSlot, ConfettiParticle, ReactorOverlay, SpirographReactor |
| `agents/studio_compositor/director_loop.py` | ~500 | DirectorLoop, _build_reactor_context, LLM call, TTS, Obsidian log |
| `agents/studio_compositor/fx_chain.py` | +30 lines | _pip_draw + fx_tick_callback hooks, SpirographReactor init |
| `scripts/youtube-player.py` | +270 lines | VideoSlot class, multi-slot HTTP API, auto_advance_loop |
| `scripts/chat-monitor.py` | +5 lines | chat-recent.json writer |

## Design Docs
- `docs/superpowers/specs/2026-04-10-spirograph-reactor-design.md`
- `docs/superpowers/specs/2026-04-10-reactor-context-enrichment-design.md`
- `docs/superpowers/plans/2026-04-10-spirograph-reactor.md`

## Initial Videos
- Slot 0: Rare Jean-Michel Basquiat Interview (1986)
- Slot 1: Steve Jobs Interview — 2/18/1981
- Slot 2: How To Interrogate a Narcissist (JCS Criminal Psychology)

## Open Items
- Spirograph glow not visible through bright shader presets (needs higher contrast or dark outline)
- TTS audio playback needs verification (pw-play path works, BrokenPipeError resolved)
- Videos need manual reload when they end (no playlist auto-advance yet)
- Stream snipe preparation: title/description/tags, Reddit/HN/Twitter posts (pinned, not yet executed)
