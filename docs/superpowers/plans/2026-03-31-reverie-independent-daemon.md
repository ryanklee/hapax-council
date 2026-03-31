# Reverie Independent Daemon Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Decouple Reverie mixer and vision observation from DMN into independent systemd services.

**Architecture:** Three extractions from DMN: (1) Reverie daemon — owns mixer lifecycle and impingement consumption via shared `ImpingementConsumer`, (2) Vision observer — standalone timer that calls gemini-flash to describe the rendered frame, writes to SHM, (3) DMN cleanup — remove all Reverie imports/init/tick and vision generation, read observation from SHM instead.

**Tech Stack:** Python 3.12, asyncio, systemd user units, shared ImpingementConsumer, LiteLLM gateway

**Spec:** `docs/superpowers/specs/2026-03-31-reverie-independent-daemon-design.md`

**Note:** systemd units use absolute paths (matching existing units like `hapax-dmn.service`). Copy path conventions from existing units verbatim.

---

### Task 1: Vision observer module

**Files:**
- Create: `agents/vision_observer/__init__.py`
- Create: `agents/vision_observer/__main__.py`
- Create: `tests/test_vision_observer.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_vision_observer.py
"""Tests for the standalone vision observer."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.asyncio
async def test_observe_writes_observation(tmp_path: Path):
    """Observer reads frame, calls LLM, writes observation to SHM."""
    frame_dir = tmp_path / "hapax-visual"
    frame_dir.mkdir()
    (frame_dir / "frame.jpg").write_bytes(b"\xff\xd8\xff\xe0fake-jpeg")

    imagination_dir = tmp_path / "hapax-dmn"
    imagination_dir.mkdir()
    (imagination_dir / "imagination-current.json").write_text(
        json.dumps({"narrative": "warm drifting colors"})
    )

    output_dir = tmp_path / "hapax-vision"

    with patch(
        "agents.vision_observer.__main__._call_vision_model",
        new_callable=AsyncMock,
        return_value="soft amber gradients with gentle movement",
    ):
        from agents.vision_observer.__main__ import observe

        await observe(
            frame_path=frame_dir / "frame.jpg",
            imagination_path=imagination_dir / "imagination-current.json",
            output_dir=output_dir,
        )

    assert (output_dir / "observation.txt").exists()
    assert "amber" in (output_dir / "observation.txt").read_text()
    status = json.loads((output_dir / "status.json").read_text())
    assert "timestamp" in status


@pytest.mark.asyncio
async def test_observe_skips_missing_frame(tmp_path: Path):
    """Observer does nothing when frame.jpg is missing."""
    output_dir = tmp_path / "hapax-vision"

    from agents.vision_observer.__main__ import observe

    await observe(
        frame_path=tmp_path / "nonexistent.jpg",
        imagination_path=tmp_path / "also-missing.json",
        output_dir=output_dir,
    )

    assert not output_dir.exists() or not (output_dir / "observation.txt").exists()


@pytest.mark.asyncio
async def test_observe_tolerates_missing_imagination(tmp_path: Path):
    """Observer works with no imagination context — passes empty narrative."""
    frame_dir = tmp_path / "hapax-visual"
    frame_dir.mkdir()
    (frame_dir / "frame.jpg").write_bytes(b"\xff\xd8\xff\xe0fake-jpeg")

    output_dir = tmp_path / "hapax-vision"

    with patch(
        "agents.vision_observer.__main__._call_vision_model",
        new_callable=AsyncMock,
        return_value="dark surface with faint noise",
    ) as mock_call:
        from agents.vision_observer.__main__ import observe

        await observe(
            frame_path=frame_dir / "frame.jpg",
            imagination_path=tmp_path / "nonexistent.json",
            output_dir=output_dir,
        )

    # Should have been called with empty narrative
    _, kwargs = mock_call.call_args
    assert kwargs.get("narrative") == "" or mock_call.call_args[0][1] == ""
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_vision_observer.py -v`
Expected: FAIL (module not found)

- [ ] **Step 3: Create the vision observer module**

```python
# agents/vision_observer/__init__.py
```

```python
# agents/vision_observer/__main__.py
"""Vision observer — standalone visual surface description sensor.

Reads the rendered frame from hapax-imagination, calls gemini-flash
to produce a one-sentence description, writes to SHM. Any consumer
(DMN reverberation, VLA, etc.) reads the output file.

Usage:
    uv run python -m agents.vision_observer
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import time
from pathlib import Path

log = logging.getLogger("vision_observer")

FRAME_PATH = Path("/dev/shm/hapax-visual/frame.jpg")
IMAGINATION_PATH = Path("/dev/shm/hapax-dmn/imagination-current.json")
OUTPUT_DIR = Path("/dev/shm/hapax-vision")

SYSTEM_PROMPT = (
    "You are observing a visual display surface. Describe what you see "
    "in one concrete sentence: colors, shapes, motion, text fragments, "
    "spatial arrangement. Do not evaluate quality. Do not describe system "
    "health. Only describe visual appearance."
)


async def _call_vision_model(frame_b64: str, narrative: str) -> str:
    """Call gemini-flash via LiteLLM to describe the visual surface."""
    from openai import AsyncOpenAI

    client = AsyncOpenAI(
        base_url="http://localhost:4000",
        api_key=os.environ.get("LITELLM_API_KEY", "sk-dummy"),
    )
    user_content: list[dict] = [
        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{frame_b64}"}},
    ]
    if narrative:
        user_content.append(
            {"type": "text", "text": f"The system intended to show: {narrative}"}
        )
    resp = await client.chat.completions.create(
        model="gemini-flash",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        temperature=0.1,
        max_tokens=100,
    )
    return resp.choices[0].message.content.strip()


async def observe(
    frame_path: Path = FRAME_PATH,
    imagination_path: Path = IMAGINATION_PATH,
    output_dir: Path = OUTPUT_DIR,
) -> None:
    """One observation cycle: read frame, call LLM, write result."""
    if not frame_path.exists():
        log.debug("No frame at %s, skipping", frame_path)
        return

    try:
        frame_b64 = base64.b64encode(frame_path.read_bytes()).decode()
    except OSError:
        log.debug("Failed to read frame", exc_info=True)
        return

    narrative = ""
    try:
        if imagination_path.exists():
            data = json.loads(imagination_path.read_text(encoding="utf-8"))
            narrative = data.get("narrative", "")
    except (OSError, json.JSONDecodeError):
        pass

    try:
        result = await _call_vision_model(frame_b64, narrative)
    except Exception:
        log.warning("Vision model call failed", exc_info=True)
        return

    if not result:
        return

    output_dir.mkdir(parents=True, exist_ok=True)
    obs_path = output_dir / "observation.txt"
    status_path = output_dir / "status.json"

    try:
        tmp = obs_path.with_suffix(".tmp")
        tmp.write_text(result, encoding="utf-8")
        tmp.rename(obs_path)

        status = {"timestamp": time.time(), "length": len(result)}
        tmp_s = status_path.with_suffix(".tmp")
        tmp_s.write_text(json.dumps(status), encoding="utf-8")
        tmp_s.rename(status_path)
        log.info("Observation written (%d chars)", len(result))
    except OSError:
        log.warning("Failed to write observation", exc_info=True)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    asyncio.run(observe())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_vision_observer.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add agents/vision_observer/__init__.py agents/vision_observer/__main__.py tests/test_vision_observer.py
git commit -m "feat: standalone vision observer module"
```

---

### Task 2: Reverie daemon entrypoint

**Files:**
- Create: `agents/reverie/__main__.py`
- Create: `tests/test_reverie_daemon.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_reverie_daemon.py
"""Tests for the standalone Reverie daemon entrypoint."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.mark.asyncio
async def test_daemon_tick_consumes_impingements(tmp_path: Path):
    """Daemon reads impingements from JSONL and dispatches to mixer."""
    imp_file = tmp_path / "impingements.jsonl"
    imp_data = {
        "id": "test-001",
        "timestamp": 1000.0,
        "source": "dmn.evaluative",
        "type": "salience_integration",
        "strength": 0.7,
        "content": {"metric": "tension", "dimensions": {"intensity": 0.5}},
    }
    imp_file.write_text(json.dumps(imp_data) + "\n")

    mock_mixer = MagicMock()
    mock_mixer.tick = AsyncMock()
    mock_mixer.dispatch_impingement = MagicMock()

    from agents.reverie.__main__ import ReverieDaemon

    daemon = ReverieDaemon(
        impingement_path=imp_file,
        mixer=mock_mixer,
        skip_bootstrap=True,
    )

    await daemon.tick()

    mock_mixer.dispatch_impingement.assert_called_once()
    mock_mixer.tick.assert_awaited_once()


@pytest.mark.asyncio
async def test_daemon_tick_tolerates_missing_impingement_file(tmp_path: Path):
    """Daemon handles missing impingement file gracefully."""
    mock_mixer = MagicMock()
    mock_mixer.tick = AsyncMock()

    from agents.reverie.__main__ import ReverieDaemon

    daemon = ReverieDaemon(
        impingement_path=tmp_path / "nonexistent.jsonl",
        mixer=mock_mixer,
        skip_bootstrap=True,
    )

    await daemon.tick()  # Should not raise

    mock_mixer.tick.assert_awaited_once()
    mock_mixer.dispatch_impingement.assert_not_called()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_reverie_daemon.py -v`
Expected: FAIL (module not found)

- [ ] **Step 3: Create the Reverie daemon entrypoint**

```python
# agents/reverie/__main__.py
"""Reverie daemon — independent visual expression service.

Owns the ReverieMixer lifecycle, consumes impingements from DMN via
ImpingementConsumer, and ticks the mixer on a 1s governance cadence.

Usage:
    uv run python -m agents.reverie
"""

from __future__ import annotations

import asyncio
import logging
import signal
from pathlib import Path

from shared.impingement_consumer import ImpingementConsumer

log = logging.getLogger("reverie")

IMPINGEMENT_PATH = Path("/dev/shm/hapax-dmn/impingements.jsonl")
TICK_INTERVAL_S = 1.0


class ReverieDaemon:
    """Standalone Reverie visual expression daemon."""

    def __init__(
        self,
        impingement_path: Path = IMPINGEMENT_PATH,
        mixer: object | None = None,
        skip_bootstrap: bool = False,
    ) -> None:
        self._consumer = ImpingementConsumer(impingement_path)
        self._running = True

        if not skip_bootstrap:
            from agents.reverie.bootstrap import write_vocabulary_plan

            try:
                if write_vocabulary_plan():
                    log.info("Reverie vocabulary written")
            except Exception:
                log.warning("Reverie vocabulary write failed", exc_info=True)

        if mixer is not None:
            self._mixer = mixer
        elif not skip_bootstrap:
            from agents.reverie.mixer import ReverieMixer

            self._mixer = ReverieMixer()
        else:
            self._mixer = None

    async def tick(self) -> None:
        """One daemon cycle: consume impingements, tick mixer."""
        impingements = self._consumer.read_new()
        for imp in impingements:
            if self._mixer is not None:
                self._mixer.dispatch_impingement(imp)

        if self._mixer is not None:
            await self._mixer.tick()

    async def run(self) -> None:
        """Main loop — never stops unless signalled."""
        log.info("Reverie daemon starting")
        while self._running:
            try:
                await self.tick()
            except Exception:
                log.exception("Reverie tick failed")
            await asyncio.sleep(TICK_INTERVAL_S)
        log.info("Reverie daemon stopped")

    def stop(self) -> None:
        self._running = False


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    daemon = ReverieDaemon()

    def handle_signal(sig: int, frame: object) -> None:
        log.info("Signal %d received, stopping", sig)
        daemon.stop()

    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    await daemon.run()


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_reverie_daemon.py -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add agents/reverie/__main__.py tests/test_reverie_daemon.py
git commit -m "feat: standalone Reverie daemon entrypoint"
```

---

### Task 3: DMN cleanup — remove Reverie coupling

**Files:**
- Modify: `agents/dmn/__main__.py`
- Test: existing DMN tests still pass

- [ ] **Step 1: Remove Reverie TYPE_CHECKING import and instance variable**

In `agents/dmn/__main__.py`, remove lines 24-25:
```python
if TYPE_CHECKING:
    from agents.reverie.mixer import ReverieMixer
```

Also remove the now-unused `TYPE_CHECKING` import from line 22 (only if nothing else uses it — check first).

Remove from `__init__` (line 73):
```python
        self._reverie: ReverieMixer | None = None  # initialized in run()
```

- [ ] **Step 2: Remove vocabulary write and mixer init from run()**

In `agents/dmn/__main__.py`, remove lines 84-101:
```python
        # Write the permanent visual vocabulary (graph structure never changes).
        # There is no idle state — params are driven by imagination fragments.
        try:
            from agents.reverie.bootstrap import write_vocabulary_plan

            if write_vocabulary_plan():
                log.info("Reverie vocabulary written")
        except Exception:
            log.warning("Reverie vocabulary write failed", exc_info=True)

        # Initialize Reverie mixer — visual peer of Daimonion
        try:
            from agents.reverie.mixer import ReverieMixer

            self._reverie = ReverieMixer()
            log.info("Reverie mixer initialized")
        except Exception:
            log.warning("Reverie actuation init failed", exc_info=True)
```

- [ ] **Step 3: Remove Reverie tick from main loop**

In `agents/dmn/__main__.py`, remove lines 124-126:
```python
                # Reverie actuation tick (1s cadence, same as main loop)
                if self._reverie is not None:
                    await self._reverie.tick()
```

- [ ] **Step 4: Remove impingement routing to Reverie**

In `agents/dmn/__main__.py`, remove lines 219-222:
```python
            # Feed impingements to Reverie via mixer's affordance pipeline
            if self._reverie is not None:
                for imp in impingements:
                    self._reverie.dispatch_impingement(imp)
```

- [ ] **Step 5: Run existing DMN tests**

Run: `uv run pytest tests/ -k "dmn" -v`
Expected: all pass (no test depends on Reverie coupling)

- [ ] **Step 6: Commit**

```bash
git add agents/dmn/__main__.py
git commit -m "refactor(dmn): remove Reverie mixer coupling"
```

---

### Task 4: DMN cleanup — remove vision observation

**Files:**
- Modify: `agents/dmn/pulse.py`
- Modify: `agents/imagination.py` (update observation path)
- Delete: `agents/dmn/vision.py`
- Test: existing tests still pass

- [ ] **Step 1: Update observation path constant**

In `agents/imagination.py`, change line 33:
```python
# Old:
VISUAL_OBSERVATION_PATH = Path("/dev/shm/hapax-dmn/visual-observation.txt")
# New:
VISUAL_OBSERVATION_PATH = Path("/dev/shm/hapax-vision/observation.txt")
```

This propagates to `imagination_loop.py` line 87 which reads this constant — no change needed there.

- [ ] **Step 2: Remove vision generation from pulse.py**

In `agents/dmn/pulse.py`:

Remove line 20:
```python
from agents.dmn.vision import _generate_visual_observation
```

Remove line 22:
```python
VISUAL_OBSERVATION_PATH = Path("/dev/shm/hapax-dmn/visual-observation.txt")
```

Remove the entire `_write_visual_observation` method (lines 198-214).

Remove the call to it in `_evaluative_tick` (line 248):
```python
            await self._write_visual_observation(snapshot)
```

- [ ] **Step 3: Delete agents/dmn/vision.py**

```bash
git rm agents/dmn/vision.py
```

- [ ] **Step 4: Run tests to verify nothing broke**

Run: `uv run pytest tests/ -k "dmn or imagination or vision" -v`
Expected: all pass

- [ ] **Step 5: Commit**

```bash
git add agents/dmn/pulse.py agents/imagination.py
git commit -m "refactor(dmn): extract vision observation to standalone service"
```

---

### Task 5: systemd units

**Files:**
- Create: `systemd/units/hapax-reverie.service`
- Create: `systemd/units/hapax-vision-observer.service`
- Create: `systemd/units/hapax-vision-observer.timer`
- Modify: `systemd/units/hapax-visual-stack.target`

- [ ] **Step 1: Create hapax-reverie.service**

Copy path conventions from `systemd/units/hapax-dmn.service` verbatim (ExecStart prefix, WorkingDirectory, EnvironmentFile, PATH). Change ExecStart module to `agents.reverie`, set MemoryMax=1G, set After/Wants/PartOf as specified in the design spec.

- [ ] **Step 2: Create hapax-vision-observer.service**

Type=oneshot. Copy path conventions from `hapax-dmn.service`. ExecStart module: `agents.vision_observer`. TimeoutStartSec=30.

- [ ] **Step 3: Create hapax-vision-observer.timer**

OnBootSec=30, OnUnitActiveSec=10, AccuracySec=1. WantedBy=timers.target.

- [ ] **Step 4: Update hapax-visual-stack.target**

Add `hapax-reverie.service` to the `Wants=` line.

- [ ] **Step 5: Commit**

```bash
git add systemd/units/hapax-reverie.service systemd/units/hapax-vision-observer.service systemd/units/hapax-vision-observer.timer systemd/units/hapax-visual-stack.target
git commit -m "feat: systemd units for Reverie daemon and vision observer"
```

---

### Task 6: Integration verification

- [ ] **Step 1: Run full test suite**

Run: `uv run pytest tests/ -q --timeout=30`
Expected: no regressions

- [ ] **Step 2: Run linting and type check**

Run: `uv run ruff check agents/reverie/__main__.py agents/vision_observer/__main__.py agents/dmn/__main__.py agents/dmn/pulse.py && uv run ruff format --check agents/reverie/ agents/vision_observer/ agents/dmn/`
Expected: clean

- [ ] **Step 3: Verify DMN starts without Reverie imports**

Run: `uv run python -c "from agents.dmn.__main__ import DMNDaemon; print('DMN imports clean')"`
Expected: prints "DMN imports clean" with no import of reverie.mixer

- [ ] **Step 4: Verify Reverie daemon starts independently**

Run: `uv run python -c "from agents.reverie.__main__ import ReverieDaemon; print('Reverie imports clean')"`
Expected: prints "Reverie imports clean"

- [ ] **Step 5: Final commit if any lint fixes were needed**

```bash
git add -u
git commit -m "fix: lint and type fixes for daemon extraction"
```
