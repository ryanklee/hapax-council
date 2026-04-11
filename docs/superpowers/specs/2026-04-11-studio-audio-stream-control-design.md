# Studio Audio Stream Control Redesign

**Date:** 2026-04-11
**Status:** Approved
**Scope:** Studio compositor audio management — replace SIGSTOP slot pausing with PipeWire per-stream volume control, fix director threading, separate TTS routing

## Problem

The studio compositor runs 3 YouTube video slots via ffmpeg, each outputting audio to PipeWire as `youtube-audio-{0,1,2}`. The director loop cycles through slots, choosing one as "active" for LLM perception and reaction. Non-active slots should be silent.

The current approach uses SIGSTOP/SIGCONT on ffmpeg processes to pause non-active slots. This is broken in three ways:

1. **SIGSTOP freezes everything.** Video frames, audio output, and JPEG snapshots all stop. But the spirograph renderer draws frames from all 3 slots and the LLM gathers images from all 3 for perception. The snapshot watchdog in youtube-player restarts ffmpeg after 30s of stale snapshots, undoing the pause and resuming audio.

2. **Toggle semantics cause races.** `_sync_slot_playback` checks slot status via HTTP GET, then conditionally toggles pause via HTTP POST. Multiple unsynchronized `_advance` threads can interleave these calls on a toggle endpoint, leaving all slots unpaused simultaneously.

3. **No audio separation for OBS.** All 3 YouTube streams and TTS output dump into `mixer_master` indiscriminately. OBS cannot independently balance voice and content audio. The `_duck_music` function adjusts the entire mixer volume, muting turntable/synth audio along with YouTube audio during speech.

## Design

### 1. Audio Control Layer

**New file:** `agents/studio_compositor/audio_control.py`

A `SlotAudioControl` class wrapping `wpctl` for idempotent per-node volume control. No toggle semantics.

**Interface:**

```python
class SlotAudioControl:
    def __init__(self, slot_count: int = 3) -> None: ...

    def discover_node(self, stream_name: str) -> int | None:
        """Find PipeWire node ID for a named stream via pw-dump.

        Caches results. Re-discovers on cache miss or when set_volume
        fails (node ID may change if ffmpeg restarts).
        """

    def set_volume(self, slot_id: int, level: float) -> None:
        """Set volume for youtube-audio-{slot_id}. Idempotent.

        level: 0.0 = silent, 1.0 = full volume.
        Calls: wpctl set-volume {node_id} {level}
        """

    def mute_all_except(self, active_slot: int) -> None:
        """Set active slot to 1.0, all others to 0.0.

        Single-intent operation called by director on slot transitions.
        """

    def mute_all(self) -> None:
        """Mute all YouTube audio streams. Called during TTS playback."""
```

**Node discovery:** Parse `pw-dump` JSON output, match nodes where `props.media.name == "youtube-audio-{slot_id}"`. Cache node IDs. If `wpctl set-volume` fails (node disappeared after ffmpeg restart), invalidate cache and re-discover.

**No HTTP round-trips.** Audio control goes directly through PipeWire. The youtube-player daemon is not involved in audio state management.

### 2. TTS Routing to Assistant Sink

TTS output (Kokoro 82M via `pw-cat`) moves from the default multimedia sink to the dedicated assistant role sink.

**Change in `agents/hapax_daimonion/pw_audio_output.py`:**

```
# Before
pw-cat --playback --raw --format s16 --rate 24000 --channels 1 -

# After
pw-cat --playback --target input.loopback.sink.role.assistant --raw --format s16 --rate 24000 --channels 1 -
```

The `input.loopback.sink.role.assistant` loopback already exists in the PipeWire graph (created by WirePlumber) and routes to the Studio 24c output. The operator still hears TTS through monitors. OBS captures it as a separate source from `mixer_master`, enabling independent level control.

**Ducking replaced.** `_duck_music(0.3)` / `_duck_music(1.0)` is removed. During speech, the director calls `mute_all()` to silence YouTube streams. Live instruments on the turntable/synth (which flow through `mixer_master` from the Studio 24c hardware inputs) remain audible. After speech + slot transition, `mute_all_except(active_slot)` restores the new active slot's audio.

**Future VST path.** Because TTS flows through a dedicated PipeWire node, a `filter-chain` module can be inserted between the assistant sink and the 24c output for voice effects processing. No architectural changes needed.

### 3. Director Threading Cleanup

**Problem:** `_speak_activity` sets `self._state = "SPEAKING"` synchronously, spawns a `_do_speak` thread, returns immediately. A separate `_advance_after_speak` thread polls `self._state` in a spin loop. Multiple react cycles can stack uncoordinated advance threads that race on `_active_slot`.

**Fix:** Merge speech and slot advance into a single thread, guarded by a lock.

```python
self._transition_lock = threading.Lock()

def _speak_activity(self, text: str, activity: str) -> None:
    self._state = "SPEAKING"
    self._reactor.set_text(text)
    self._reactor.set_speaking(True)
    threading.Thread(
        target=self._do_speak_and_advance,
        args=(text, activity),
        daemon=True,
    ).start()

def _do_speak_and_advance(self, text: str, activity: str) -> None:
    with self._transition_lock:
        try:
            pcm = self._synthesize(text)
            if pcm:
                self._audio_control.mute_all()
                self._reactor.feed_pcm(pcm)
                self._play_audio(pcm)
                time.sleep(0.3)
        except Exception:
            log.exception("TTS error")

        # Advance slot atomically
        if self._activity == "react":
            self._slots[self._active_slot].is_active = False
            self._active_slot = (self._active_slot + 1) % len(self._slots)
            self._slots[self._active_slot].is_active = True

        self._audio_control.mute_all_except(self._active_slot)

        # Bookkeeping
        self._log_to_obsidian(text, self._activity)
        self._reactor.set_speaking(False)
        self._reactor.set_text("")
        self._state = "IDLE"
```

**Key properties:**
- One thread per speech act (not two)
- `_transition_lock` prevents concurrent advance threads from interleaving
- Main loop already skips when `self._state == "SPEAKING"`, so no new speech starts during a transition
- `_active_slot` only changes inside the lock
- Audio mute/unmute happens atomically with the slot transition

**Removed from director_loop.py:**
- `_sync_slot_playback()` — replaced by `mute_all_except`
- `_duck_music()` and `_find_mixer_node()` — ducking replaced by per-stream muting
- `_advance()` inner function in `_loop()`
- `_advance_after_speak()` — merged into `_do_speak_and_advance`

### 4. youtube-player.py Cleanup

Pure subtraction. The youtube-player becomes a play/stop daemon with no audio state management.

**Removed:**
- `VideoSlot.toggle_pause()` — SIGSTOP/SIGCONT mechanism
- `VideoSlot.paused` field
- `POST /slot/{id}/pause` HTTP endpoint
- Legacy `POST /pause` endpoint
- `paused` field from status response dicts

**Kept unchanged:**
- `VideoSlot.play()` / `VideoSlot.stop()` — start/stop ffmpeg processes
- `_snapshot_watchdog()` — still detects ffmpeg crashes (no longer in tension with pausing since ffmpeg never gets SIGSTOP'd)
- `auto_advance_loop()` — watches for finished videos, triggers playlist reload
- KDE Connect listener, HTTP play/stop endpoints, queue logic

## File Changes

| File | Action | Summary |
|------|--------|---------|
| `agents/studio_compositor/audio_control.py` | New | `SlotAudioControl` — node discovery, `set_volume`, `mute_all_except`, `mute_all` |
| `agents/studio_compositor/director_loop.py` | Edit | Remove `_sync_slot_playback`, `_duck_music`, `_find_mixer_node`, `_advance`, `_advance_after_speak`. Add `_transition_lock`, refactor speech into `_do_speak_and_advance`. Wire `SlotAudioControl` at init |
| `scripts/youtube-player.py` | Edit | Remove `toggle_pause`, `paused` field, pause endpoints |
| `agents/hapax_daimonion/pw_audio_output.py` | Edit | Add `--target input.loopback.sink.role.assistant` to pw-cat playback command |

## Not Changed

- **PipeWire config** — assistant loopback already exists
- **`audio_capture.py`** — still captures `mixer_master` for reactivity (cleaner now: only 1 YT stream is audible in the mix)
- **`spirograph_reactor.py`** — still reads JPEG snapshots from all 3 slots
- **Systemd units** — no new services

## Testing

1. Start youtube-player with 3 slots loaded
2. Instantiate `SlotAudioControl`, call `mute_all_except(2)` — confirm only slot 2 audible through 24c
3. Call `mute_all_except(0)` — confirm hard cut, only slot 0 audible
4. Call `mute_all()` — confirm silence
5. Run director loop, confirm slot transitions produce clean hard cuts
6. Confirm TTS plays through assistant sink (`pw-dump | grep assistant` shows running node during speech)
7. Rapid slot transitions: call `mute_all_except` 10 times in tight loop — confirm no race (only final slot audible)
8. Kill and restart an ffmpeg process — confirm node re-discovery works on next `set_volume` call

## Audio Topology After Change

```
YouTube slot 0 ──► youtube-audio-0 ──┐
YouTube slot 1 ──► youtube-audio-1 ──┼──► mixer_master ──► Studio 24c ──► OBS source 1
YouTube slot 2 ──► youtube-audio-2 ──┘         ▲
Turntable/synths ─────────────────────────────┘

                                    SlotAudioControl
                                    mutes inactive slots
                                    via wpctl set-volume

Kokoro TTS ──► pw-cat --target assistant ──► assistant loopback ──► Studio 24c ──► OBS source 2
                                                    ▲
                                              future: VST filter-chain here
```
