# Reverie Independent Daemon + Vision Observer Extraction

**Date:** 2026-03-31
**Author:** beta
**Status:** Design
**Prerequisite:** Phase 4 mixer landed (PR #497)

## Problem

DMN currently owns three concerns that don't belong to it:

1. **Reverie mixer lifecycle** — DMN imports, initializes, and ticks `ReverieMixer`. DMN routes impingements to Reverie's pipeline inline. This couples DMN to Reverie internals.
2. **Visual vocabulary bootstrap** — DMN calls `write_vocabulary_plan()` at startup. This is a Reverie responsibility.
3. **Vision observation** — `agents/dmn/vision.py` calls gemini-flash to describe the rendered frame. This is a sensor, not a cognitive function. It doesn't belong to DMN or Reverie — it's an independent observer that writes to SHM for any consumer to read.

## Design

Three extractions:

### 1. Reverie daemon (`hapax-reverie.service`)

New systemd service running `agents/reverie/__main__.py`.

**Startup:**
- `write_vocabulary_plan()` — compile shader graph to SHM
- Initialize `ReverieMixer`
- Initialize `ImpingementConsumer` pointing at `/dev/shm/hapax-dmn/impingements.jsonl`

**Tick loop (1s cadence):**
- `consumer.read_new()` → impingements since last tick
- Route each impingement through `self._mixer.pipeline.select(imp)` → capability activation (same logic currently at `DMNDaemon._write_output` lines 219-229)
- `await self._mixer.tick()` — governance check, decay, uniforms, cross-modal I/O

**systemd unit:**
```ini
[Unit]
Description=Hapax Reverie — visual expression daemon
After=hapax-secrets.service hapax-dmn.service
Wants=hapax-dmn.service
PartOf=hapax-visual-stack.target

[Service]
Type=simple
ExecStart=uv run python -m agents.reverie
WorkingDirectory=<project-dir>/hapax-council
Restart=on-failure
RestartSec=10
EnvironmentFile=<runtime-dir>/hapax-secrets.env
Environment=PATH=<local-bin>:/usr/local/bin:/usr/bin
MemoryMax=1G

[Install]
WantedBy=default.target
```

(Actual paths filled from existing unit conventions at install time.)

**Impingement latency:** Current inline routing is synchronous. With JSONL consumer, up to 1s delay (tick cadence). At governance rate, this is acceptable — visual expression doesn't need sub-second impingement response.

### 2. Vision observer (`hapax-vision-observer.timer`)

New systemd timer + oneshot service running `agents/vision_observer/__main__.py`.

**What it does:**
- Read `/dev/shm/hapax-visual/frame.jpg`
- Read `/dev/shm/hapax-dmn/imagination-current.json` for narrative context
- Call gemini-flash via LiteLLM (`:4000`)
- Write observation to `/dev/shm/hapax-vision/observation.txt`
- Write timestamp + metadata to `/dev/shm/hapax-vision/status.json`

**Cadence:** 10s timer (matches current evaluative tick frequency — vision observation only fires on evaluative ticks, which run every ~10s).

**Module structure:**
```
agents/vision_observer/
  __init__.py
  __main__.py   # read frame, call LLM, write SHM (~50 lines)
```

The existing `agents/dmn/vision.py` code moves here with minimal changes: remove the `imagination_narrative` parameter dependency on DMN internals, read it from SHM instead.

**systemd units:**
```ini
# hapax-vision-observer.service
[Unit]
Description=Hapax Vision Observer — visual surface description
After=hapax-secrets.service

[Service]
Type=oneshot
ExecStart=uv run python -m agents.vision_observer
WorkingDirectory=<project-dir>/hapax-council
EnvironmentFile=<runtime-dir>/hapax-secrets.env
Environment=PATH=<local-bin>:/usr/local/bin:/usr/bin
TimeoutStartSec=30

# hapax-vision-observer.timer
[Unit]
Description=Visual observation every 10s

[Timer]
OnBootSec=30
OnUnitActiveSec=10
AccuracySec=1

[Install]
WantedBy=timers.target
```

### 3. DMN cleanup

**Remove from `agents/dmn/__main__.py`:**
- Line 24-25: `TYPE_CHECKING` import of `ReverieMixer`
- Line 73: `self._reverie` instance variable
- Lines 86-101: `write_vocabulary_plan()` call and `ReverieMixer()` init
- Lines 124-126: `self._reverie.tick()` in main loop
- Lines 219-229: Impingement routing to Reverie pipeline

**Modify `agents/dmn/pulse.py`:**
- Remove `_write_visual_observation` method (lines 198-214)
- Remove call to it from `_evaluative_tick` (line 248)
- Remove import of `_generate_visual_observation` from `vision.py` (line 20)
- Add: read `/dev/shm/hapax-vision/observation.txt` for reverberation detection (replaces inline generation with file read)

**Delete:**
- `agents/dmn/vision.py` — functionality moves to `agents/vision_observer/`

**Update `hapax-visual-stack.target`:**
- Add `hapax-reverie.service` to `Wants=`

### Data flow after decoupling

```
DMN pulse loop
  writes impingements.jsonl --> Reverie reads via ImpingementConsumer
                            --> Fortress reads via ImpingementConsumer
                            --> Daimonion reads via ImpingementConsumer
  reads observation.txt <-- Vision Observer writes (10s timer)
                               reads frame.jpg <-- hapax-imagination renders

Reverie mixer tick (1s)
  reads impingements --> pipeline select --> capability activation
  reads acoustic impulse <-- Daimonion writes
  writes visual salience --> Daimonion reads
  writes uniforms.json --> hapax-imagination reads per-frame
```

## What stays in DMN

- Pulse loop (sensory/evaluative/consolidation) — core cognitive function
- Buffer management — core cognitive function
- Imagination loop + content resolver — drives content for Reverie but runs on DMN's cadence
- `_consume_fortress_feedback()` — DMN's own feedback loop
- `_write_output()` — writes buffer.txt, status.json, impingements.jsonl
- Reverberation detection — reads observation.txt (now from SHM instead of inline call)

## Files touched

| Action | File | Lines |
|--------|------|-------|
| Create | `agents/reverie/__main__.py` | ~60 |
| Create | `agents/vision_observer/__init__.py` | 0 |
| Create | `agents/vision_observer/__main__.py` | ~50 |
| Create | `systemd/units/hapax-reverie.service` | ~15 |
| Create | `systemd/units/hapax-vision-observer.service` | ~10 |
| Create | `systemd/units/hapax-vision-observer.timer` | ~10 |
| Modify | `agents/dmn/__main__.py` | ~30 lines removed |
| Modify | `agents/dmn/pulse.py` | ~20 lines removed, ~5 added |
| Modify | `systemd/units/hapax-visual-stack.target` | 1 line added |
| Delete | `agents/dmn/vision.py` | 73 lines |
| Create | `tests/test_reverie_daemon.py` | ~40 |
| Create | `tests/test_vision_observer.py` | ~30 |

## Scope

Small. Net code change is roughly neutral (move, don't rewrite). Three new systemd units. Two new test files. The hard design work was Phase 4 (mixer) — this is the mechanical decoupling that follows.
