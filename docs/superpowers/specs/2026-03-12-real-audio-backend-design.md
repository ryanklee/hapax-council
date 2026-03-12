# Real Audio Energy Backend — Design Spec

> **Status:** Proposed
> **Date:** 2026-03-12
> **Scope:** `agents/hapax_voice/backends/audio_energy.py` — first real backend replacing a stub
> **Builds on:** [Perception Primitives](2026-03-11-perception-primitives-design.md), [North Star](2026-03-11-backup-mc-north-star-design.md)

## Problem

The AudioEnergyBackend is a stub with `available() → False` and an empty `contribute()`. Both governance chains (MC and OBS) depend on `audio_energy_rms` as a load-bearing signal — MC uses it for the energy_sufficient veto and FallbackChain intensity selection, OBS uses it for scene selection and transition style. Without real audio data, the entire perception-to-actuation pipeline is untestable against real-world conditions.

The operator's DAWless rig has 6+ audio sources (OXI One, dual SP-404s, MPC Live, Digitakt, Digitone) plus a monitor mix and room mic. The backend must support multi-source operation via source-qualified behavior names, already implemented in the wiring layer.

## Goal

Replace the AudioEnergyBackend stub with a real implementation that:

1. Captures audio from a specific PipeWire node via `pw-record` subprocess
2. Computes RMS energy in 50ms windows using numpy
3. Detects transient onsets via spectral flux
4. Writes source-qualified Behaviors (`audio_energy_rms:<source_id>`, `audio_onset:<source_id>`)
5. Reports `available() → True` when `pw-record` is installed and the target node exists

## Design Decisions

### D1: `pw-record` subprocess over PyAudio

**Decision:** Use `pw-record --target <node_id> --format f32 --rate 48000 --channels 1 -` piping raw float32 PCM to stdout.

**Rationale:**
- The existing PyAudio path (`audio_input.py`) manipulates the PipeWire default source — one source at a time, racy, global state mutation. The multi-source North Star requires simultaneous capture from 8+ sources.
- `pw-record --target <node_id>` directly targets a specific PipeWire node without touching global state.
- Multiple `pw-record` instances can run simultaneously — one per source.
- `pw-record` ships with `pipewire-bin` (already installed). Zero new pip dependencies.
- float32 output feeds directly into numpy with no conversion.

**Trade-off:** Subprocess overhead (~5-10ms pipe latency). Acceptable for energy analysis — we need 50ms windows, not sub-millisecond.

### D2: Computation in a reader thread, not in `contribute()`

**Decision:** A background thread reads `pw-record` stdout, computes RMS + onset per chunk, and stores the latest values. `contribute()` just reads the stored values and writes to Behaviors.

**Rationale:**
- `contribute()` is called by the CadenceGroup on the main asyncio thread. It must not block.
- Audio analysis (numpy on 2048 samples) takes <1ms — fast, but the pipe read could block if no data is ready.
- The reader thread runs continuously, independent of the perception cadence. `contribute()` samples the most recent result.

### D3: EMA smoothing with adaptive normalization

**Decision:** Exponential moving average (alpha=0.2) on raw RMS. Normalize to 0.0-1.0 via running max over the last 10 seconds.

**Rationale:**
- Raw RMS from different sources has wildly different absolute levels depending on gain staging. The SP-404 output is hotter than the Digitone output.
- Running-max normalization adapts to each source's dynamic range automatically.
- EMA smoothing prevents single-frame spikes from dominating. Alpha=0.2 gives ~250ms effective response time — fast enough to track beat-level dynamics at 90 BPM (beat = 667ms).

### D4: Node discovery via `pw-dump`

**Decision:** `available()` shells out to `pw-dump`, parses JSON, checks if a node matching the target exists.

**Rationale:**
- `pw-dump` produces full JSON of all PipeWire objects. Filter for `Audio/Source` or `Audio/Sink` nodes.
- Node identification by `node.name`, `node.description`, or numeric ID — configurable per source.
- One-time check at registration. If the node doesn't exist, the backend reports unavailable and the engine skips it (existing behavior).

### D5: Onset detection via spectral flux

**Decision:** Compare consecutive magnitude spectra (from `np.fft.rfft`). Sum positive differences. Threshold-detect peaks. No external library (no aubio).

**Rationale:**
- Aubio has Python 3.12+ / numpy 2.x build issues. Not worth the dependency risk.
- Spectral flux is ~15 lines of numpy. Well-understood, reliable for percussive transients (kicks, snares — exactly the boom bap context).
- Threshold can be tuned per source (kick drum input needs different sensitivity than hi-hat input).

## Architecture

```
pw-record --target <node_id> --format f32 --rate 48000 --channels 1 -
  │
  │ stdout: raw float32 PCM (2048 samples per read = ~43ms)
  │
  ▼
ReaderThread (per source)
  ├─ np.frombuffer(chunk, dtype=np.float32)
  ├─ RMS: np.sqrt(np.mean(samples**2))
  ├─ EMA smooth: smoothed = alpha * raw + (1-alpha) * smoothed
  ├─ Normalize: smoothed / running_max_10s
  ├─ Onset: spectral_flux > threshold
  └─ Store to thread-safe attributes
      │
      ▼
contribute() (called by CadenceGroup on main thread)
  ├─ Read latest rms, onset from attributes
  ├─ behaviors["audio_energy_rms:<source>"].update(rms, now)
  └─ behaviors["audio_onset:<source>"].update(onset, now)
```

### Node Discovery

```python
def _discover_node(target: str) -> int | None:
    """Find a PipeWire node by name or description.

    Runs pw-dump, parses JSON, returns node ID or None.
    """
```

The `target` parameter accepts:
- A numeric node ID (e.g., `"42"`)
- A node name (e.g., `"alsa_input.usb-Roland_SP-404MKII"`)
- A substring match on `node.description` (e.g., `"SP-404"`)

### Lifecycle

- `__init__(source_id, target)` — validate source_id, store target
- `available()` — check `pw-record` exists + target node discoverable
- `start()` — launch `pw-record` subprocess + reader thread
- `contribute()` — read latest values, write to Behaviors
- `stop()` — terminate subprocess, join thread

### Failure Modes

| Failure | Behavior |
|---------|----------|
| `pw-record` not installed | `available() → False`, backend skipped |
| Target node not found | `available() → False`, backend skipped |
| `pw-record` crashes mid-session | Reader thread detects EOF, logs error, sets values to stale (watermark stops advancing → FreshnessGuard rejects) |
| Audio silence (no signal) | RMS → 0.0, onset → False. Governance chains handle gracefully (energy_sufficient veto blocks MC throws) |
| Pipe buffer overflow | Reader thread drains continuously. If it falls behind, old frames are consumed — latency increases but no data loss |

## Signals Produced

| Behavior | Type | Range | Update Rate |
|----------|------|-------|-------------|
| `audio_energy_rms:<source>` | float | 0.0-1.0 (normalized) | ~20Hz (every 50ms window) |
| `audio_onset:<source>` | bool | True on transient | ~20Hz |

## Dependencies

- `pw-record` (system binary, part of `pipewire-bin`)
- `numpy` (already in deps via torchaudio)
- No new pip dependencies

## Testing Strategy

Unit tests mock the subprocess — no real audio hardware needed in CI:

- **Reader thread tests**: Feed synthetic float32 PCM via a pipe, verify RMS computation, EMA smoothing, onset detection
- **Node discovery tests**: Mock `pw-dump` JSON output, verify node matching
- **Lifecycle tests**: Start/stop, subprocess cleanup, crash recovery
- **Integration with wiring**: Verify source-qualified Behaviors land in the correct governance chain alias
- **Property tests**: RMS is always 0.0-1.0, onset is always bool, watermarks are monotonic
