# Engagement-Based Activation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace wake word detection with a 3-stage engagement classifier so the system activates when the operator speaks to it, not when summoned.

**Architecture:** EngagementClassifier replaces WakeWordDetector in the audio loop. Same callback interface (fires `on_engagement_detected` instead of `on_wake_word`). Three stages: VAD gate, directed-speech classifier (context window + gaze + exclusions), semantic confirmation (speculative STT + salience). Proactive gate already exists — tune cooldown.

**Tech Stack:** Python 3.12, asyncio, Silero VAD (existing), faster-whisper STT (existing), salience router (existing)

**Spec:** `docs/superpowers/specs/2026-03-31-engagement-activation-design.md`

---

### Task 1: Create EngagementClassifier

**Files:**
- Create: `agents/hapax_daimonion/engagement.py`
- Create: `tests/hapax_daimonion/test_engagement.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/hapax_daimonion/test_engagement.py
"""Tests for the engagement-based activation classifier."""

from __future__ import annotations

import time
from unittest.mock import MagicMock

import pytest

from agents.hapax_daimonion.engagement import EngagementClassifier


class TestStage2ContextWindow:
    def test_recent_system_speech_activates(self):
        """Within 30s of system speech, any operator speech = directed."""
        ec = EngagementClassifier(on_engaged=MagicMock())
        ec._last_system_speech = time.monotonic() - 10.0  # 10s ago
        assert ec._check_context_window() >= 0.9

    def test_old_system_speech_does_not_activate(self):
        """After 30s, context window closes."""
        ec = EngagementClassifier(on_engaged=MagicMock())
        ec._last_system_speech = time.monotonic() - 60.0  # 60s ago
        assert ec._check_context_window() < 0.1

    def test_no_system_speech_returns_zero(self):
        """No prior system speech = no context window."""
        ec = EngagementClassifier(on_engaged=MagicMock())
        ec._last_system_speech = 0.0
        assert ec._check_context_window() == 0.0


class TestStage2Exclusions:
    def test_phone_call_suppresses(self):
        """Active phone call suppresses engagement."""
        ec = EngagementClassifier(on_engaged=MagicMock())
        behaviors = {"phone_call_active": MagicMock(value=True)}
        assert ec._check_exclusions(behaviors) < 0.1

    def test_no_phone_call_allows(self):
        """No phone call allows engagement."""
        ec = EngagementClassifier(on_engaged=MagicMock())
        behaviors = {"phone_call_active": MagicMock(value=False)}
        assert ec._check_exclusions(behaviors) >= 0.9

    def test_meeting_activity_suppresses(self):
        """Meeting activity mode suppresses engagement."""
        ec = EngagementClassifier(on_engaged=MagicMock())
        behaviors = {
            "phone_call_active": MagicMock(value=False),
            "activity_mode": MagicMock(value="meeting"),
        }
        assert ec._check_exclusions(behaviors) < 0.1


class TestStage2Gaze:
    def test_desk_gaze_activates(self):
        """Operator facing desk = directed."""
        ec = EngagementClassifier(on_engaged=MagicMock())
        behaviors = {
            "ir_gaze_zone": MagicMock(value="desk", timestamp=time.monotonic()),
        }
        assert ec._check_gaze(behaviors) >= 0.7

    def test_away_gaze_does_not_activate(self):
        """Operator facing away = not directed."""
        ec = EngagementClassifier(on_engaged=MagicMock())
        behaviors = {
            "ir_gaze_zone": MagicMock(value="away", timestamp=time.monotonic()),
        }
        assert ec._check_gaze(behaviors) < 0.3

    def test_stale_gaze_returns_neutral(self):
        """Gaze data older than 5s = neutral (don't block, don't confirm)."""
        ec = EngagementClassifier(on_engaged=MagicMock())
        behaviors = {
            "ir_gaze_zone": MagicMock(value="desk", timestamp=time.monotonic() - 10.0),
        }
        assert ec._check_gaze(behaviors) == 0.5


class TestStage2Fusion:
    def test_context_window_alone_activates(self):
        """Context window is sufficient for activation."""
        ec = EngagementClassifier(on_engaged=MagicMock())
        ec._last_system_speech = time.monotonic() - 5.0
        behaviors = {"phone_call_active": MagicMock(value=False)}
        score = ec.evaluate(behaviors)
        assert score >= 0.4

    def test_phone_call_blocks_even_with_context(self):
        """Phone call blocks even within context window."""
        ec = EngagementClassifier(on_engaged=MagicMock())
        ec._last_system_speech = time.monotonic() - 5.0
        behaviors = {"phone_call_active": MagicMock(value=True)}
        score = ec.evaluate(behaviors)
        assert score < 0.2


class TestFollowUpWindow:
    def test_follow_up_lowers_threshold(self):
        """During follow-up window, threshold is lowered."""
        ec = EngagementClassifier(on_engaged=MagicMock())
        ec._follow_up_until = time.monotonic() + 30.0
        assert ec._in_follow_up_window()

    def test_expired_follow_up(self):
        """After follow-up window expires, normal threshold."""
        ec = EngagementClassifier(on_engaged=MagicMock())
        ec._follow_up_until = time.monotonic() - 5.0
        assert not ec._in_follow_up_window()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/hapax_daimonion/test_engagement.py -v`
Expected: FAIL (module not found)

- [ ] **Step 3: Create the EngagementClassifier**

```python
# agents/hapax_daimonion/engagement.py
"""Engagement classifier — replaces wake word detection.

Three-stage pipeline:
  Stage 1: VAD gate (speech detected, operator present)
  Stage 2: Directed-speech classifier (context window, gaze, exclusions)
  Stage 3: Semantic confirmation (speculative STT + salience, only when ambiguous)
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from agents.hapax_daimonion.perception import Behavior

log = logging.getLogger("engagement")

CONTEXT_WINDOW_S = 30.0
GAZE_STALE_S = 5.0
ACTIVATE_THRESHOLD = 0.4
SUPPRESS_THRESHOLD = 0.2
FOLLOW_UP_THRESHOLD = 0.1
FOLLOW_UP_WINDOW_S = 30.0
MEETING_ACTIVITIES = frozenset({"meeting", "phone_call"})
DESK_GAZE_ZONES = frozenset({"desk", "screen", "monitor"})


class EngagementClassifier:
    """Determines whether operator speech is directed at the system."""

    def __init__(self, on_engaged: Callable[[], None]) -> None:
        self._on_engaged = on_engaged
        self._last_system_speech: float = 0.0
        self._follow_up_until: float = 0.0
        self._last_activation: float = 0.0
        self._debounce_s: float = 2.0

    def notify_system_spoke(self) -> None:
        """Called when TTS playback finishes."""
        self._last_system_speech = time.monotonic()

    def notify_session_closed(self) -> None:
        """Called when a session closes — opens follow-up window."""
        self._follow_up_until = time.monotonic() + FOLLOW_UP_WINDOW_S

    def on_speech_detected(self, behaviors: dict[str, Behavior]) -> None:
        """Called from audio loop when VAD detects speech and operator is present.

        Runs Stage 2 evaluation. If ambiguous, Stage 3 would run async
        (deferred to v2 — for now, ambiguous = suppress).
        """
        now = time.monotonic()
        if now - self._last_activation < self._debounce_s:
            return

        score = self.evaluate(behaviors)
        threshold = FOLLOW_UP_THRESHOLD if self._in_follow_up_window() else ACTIVATE_THRESHOLD

        if score >= threshold:
            self._last_activation = now
            log.info(
                "Engagement detected: score=%.2f threshold=%.2f",
                score, threshold,
            )
            self._on_engaged()

    def evaluate(self, behaviors: dict[str, Behavior]) -> float:
        """Stage 2: compute engagement score from available signals."""
        context = self._check_context_window()
        gaze = self._check_gaze(behaviors)
        exclusion = self._check_exclusions(behaviors)

        # Weighted OR: best positive signal, gated by exclusions
        positive = max(context, gaze)
        return positive * exclusion

    def _check_context_window(self) -> float:
        """Stage 2a: recent system speech implies follow-up."""
        if self._last_system_speech == 0.0:
            return 0.0
        age = time.monotonic() - self._last_system_speech
        if age < CONTEXT_WINDOW_S:
            return max(0.0, 1.0 - (age / CONTEXT_WINDOW_S))
        return 0.0

    def _check_gaze(self, behaviors: dict[str, Behavior]) -> float:
        """Stage 2c: head orientation from IR presence."""
        gaze_b = behaviors.get("ir_gaze_zone")
        if gaze_b is None:
            return 0.5  # neutral — no data, don't block

        age = time.monotonic() - getattr(gaze_b, "timestamp", 0.0)
        if age > GAZE_STALE_S:
            return 0.5  # stale — neutral

        zone = getattr(gaze_b, "value", "")
        if zone in DESK_GAZE_ZONES:
            return 0.8
        return 0.2

    def _check_exclusions(self, behaviors: dict[str, Behavior]) -> float:
        """Stage 2b/2d: phone call and meeting activity suppress."""
        phone = behaviors.get("phone_call_active")
        if phone is not None and getattr(phone, "value", False):
            return 0.0

        activity = behaviors.get("activity_mode")
        if activity is not None and getattr(activity, "value", "") in MEETING_ACTIVITIES:
            return 0.0

        return 1.0

    def _in_follow_up_window(self) -> bool:
        """Check if we're in the post-session follow-up window."""
        return time.monotonic() < self._follow_up_until
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/hapax_daimonion/test_engagement.py -v`
Expected: 12 passed

- [ ] **Step 5: Commit**

```bash
git add agents/hapax_daimonion/engagement.py tests/hapax_daimonion/test_engagement.py
git commit -m "feat(voice): engagement classifier — replaces wake word"
```

---

### Task 2: Wire EngagementClassifier into audio loop and session events

**Files:**
- Modify: `agents/hapax_daimonion/daemon.py` — replace `wake_word` with `engagement`
- Modify: `agents/hapax_daimonion/run_inner.py` — replace wake word init with engagement init
- Modify: `agents/hapax_daimonion/run_loops.py` — replace wake word frame distribution
- Modify: `agents/hapax_daimonion/session_events.py` — replace `on_wake_word`/`wake_word_processor`

- [ ] **Step 1: Update daemon.py — replace wake_word attribute**

In `daemon.py`, find `self._wake_word_signal = asyncio.Event()` (line ~170) and replace with:

```python
self._engagement_signal = asyncio.Event()
```

Find `self.wake_word` assignment and replace with engagement classifier init (will be done in run_inner.py, just remove wake_word references).

- [ ] **Step 2: Update session_events.py — replace on_wake_word with on_engagement_detected**

Replace `on_wake_word` function (lines 55-59):

```python
def on_engagement_detected(daemon: VoiceDaemon) -> None:
    """Called from audio loop when engagement classifier fires."""
    daemon.wake_word_event.emit(time.monotonic(), None)  # keep event for telemetry
    if not daemon.session.is_active:
        daemon._engagement_signal.set()
```

Replace `wake_word_processor` function (lines 62-86):

```python
async def engagement_processor(daemon: VoiceDaemon) -> None:
    """Await engagement signal, then atomically set up session + pipeline."""
    while daemon._running:
        await daemon._engagement_signal.wait()
        daemon._engagement_signal.clear()

        if daemon.session.is_active:
            continue

        state = daemon.perception.tick()
        veto = daemon.governor._veto_chain.evaluate(state)
        if not veto.allowed and "axiom_compliance" in veto.denied_by:
            log.warning("Engagement blocked by axiom compliance: %s", veto.denied_by)
            acknowledge(daemon, "denied")
            continue

        acknowledge(daemon, "activation")
        daemon.governor.wake_word_active = True
        daemon._frame_gate.set_directive("process")
        daemon.session.open(trigger="engagement")
        daemon.session.set_speaker("operator", confidence=1.0)
        log.info("Session opened via engagement detection")
        daemon.event_log.set_session_id(daemon.session.session_id)
        daemon.event_log.emit("session_lifecycle", action="opened", trigger="engagement")
        await daemon._start_pipeline()
```

- [ ] **Step 3: Update run_inner.py — replace wake word init**

Find wake word loading block (lines ~49-52) and replace:

```python
    # Initialize engagement classifier (replaces wake word)
    from agents.hapax_daimonion.engagement import EngagementClassifier
    from agents.hapax_daimonion.session_events import on_engagement_detected

    daemon._engagement = EngagementClassifier(
        on_engaged=lambda: on_engagement_detected(daemon),
    )
```

Find `wake_word_processor` import and background task creation (lines ~35, ~141) and replace:

```python
    from agents.hapax_daimonion.session_events import close_session, engagement_processor
    # ...
    daemon._background_tasks.append(asyncio.create_task(engagement_processor(daemon)))
```

- [ ] **Step 4: Update run_loops.py — replace wake word frame distribution**

In `audio_loop`, find the wake word processing block (lines ~79-86):

```python
        while len(_wake_buf) >= _WAKE_CHUNK:
            chunk = bytes(_wake_buf[:_WAKE_CHUNK])
            del _wake_buf[:_WAKE_CHUNK]
            try:
                audio_np = np.frombuffer(chunk, dtype=np.int16)
                daemon.wake_word.process_audio(audio_np)
            except Exception as exc:
                log.warning("Wake word consumer error: %s", exc)
```

Replace with engagement evaluation triggered by VAD:

```python
        # Engagement detection: when VAD detects speech and operator is present,
        # evaluate whether to open a session
        if (
            not daemon.session.is_active
            and daemon.presence._latest_vad_confidence >= 0.5
            and hasattr(daemon, "_engagement")
        ):
            try:
                behaviors = daemon.perception.latest_behaviors()
                presence_state = behaviors.get("presence_state")
                if presence_state is not None and getattr(presence_state, "value", "") == "PRESENT":
                    daemon._engagement.on_speech_detected(behaviors)
            except Exception as exc:
                log.debug("Engagement evaluation error: %s", exc)
```

Also remove the `_wake_buf` and `_WAKE_CHUNK` variables and the WhisperWakeWord import if no longer needed.

- [ ] **Step 5: Wire notify_system_spoke and notify_session_closed**

In `session_events.py`, in the `close_session` function, add:

```python
    if hasattr(daemon, "_engagement"):
        daemon._engagement.notify_session_closed()
```

In `conversation_pipeline.py` (or wherever TTS playback completes), add notification. Since this file is frozen, instead wire it in `session_events.py` or `cognitive_loop.py` where speaking state transitions are tracked. The cognitive loop already tracks HAPAX_SPEAKING → MUTUAL_SILENCE transition. Add:

```python
# In cognitive_loop.py, when transitioning OUT of HAPAX_SPEAKING:
if hasattr(self._daemon, "_engagement"):
    self._daemon._engagement.notify_system_spoke()
```

- [ ] **Step 6: Run all affected tests**

Run: `uv run pytest tests/hapax_daimonion/test_engagement.py tests/hapax_daimonion/test_salience_router.py -q`
Expected: All pass

- [ ] **Step 7: Commit**

```bash
git add agents/hapax_daimonion/daemon.py agents/hapax_daimonion/run_inner.py agents/hapax_daimonion/run_loops.py agents/hapax_daimonion/session_events.py agents/hapax_daimonion/cognitive_loop.py
git commit -m "feat(voice): wire engagement classifier into audio loop and session events"
```

---

### Task 3: Delete wake word code

**Files:**
- Delete: `agents/hapax_daimonion/wake_word.py`
- Delete: `agents/hapax_daimonion/wake_word_whisper.py`
- Delete: `agents/hapax_daimonion/wake_word_porcupine.py`
- Modify: `agents/hapax_daimonion/config.py` — remove `wake_word_engine`

- [ ] **Step 1: Delete wake word files**

```bash
git rm agents/hapax_daimonion/wake_word.py
git rm agents/hapax_daimonion/wake_word_whisper.py
git rm agents/hapax_daimonion/wake_word_porcupine.py
```

- [ ] **Step 2: Remove wake_word_engine from config**

In `config.py`, remove:

```python
    wake_word_engine: str = "whisper"  # "whisper", "porcupine", or "oww"
```

- [ ] **Step 3: Remove any remaining wake word imports**

Search for and remove any remaining imports of wake word modules:

```bash
grep -rn "wake_word\|WakeWord\|WhisperWakeWord\|PorcupineWakeWord" agents/hapax_daimonion/ --include="*.py" | grep -v __pycache__ | grep -v test_
```

Fix each occurrence — replace with engagement equivalent or remove.

- [ ] **Step 4: Verify no import errors**

Run: `uv run python -c "from agents.hapax_daimonion.run_inner import run_inner; print('clean')"`
Expected: `clean`

- [ ] **Step 5: Run full daimonion test suite**

Run: `uv run pytest tests/hapax_daimonion/ -q --ignore=tests/hapax_daimonion/test_type_system_matrix_l8.py --ignore=tests/hapax_daimonion/test_type_system_matrix_l9.py`
Expected: All pass (L8/L9 tests have pre-existing wake word debounce failures — those tests should now be deleted or updated since wake word is gone)

- [ ] **Step 6: Commit**

```bash
git add -u
git commit -m "refactor(voice): delete wake word detection — replaced by engagement classifier"
```

---

### Task 4: Tune proactive gate

**Files:**
- Modify: `agents/proactive_gate.py`

- [ ] **Step 1: Reduce proactive cooldown**

The spec says 5 minutes between proactive utterances. Current default is 120s (2 minutes). The existing value is already close. Verify and adjust if needed.

In `agents/proactive_gate.py`, check `DEFAULT_COOLDOWN_S`:

```python
# Current: DEFAULT_COOLDOWN_S = 120.0
# Change to 300.0 (5 minutes) per spec
DEFAULT_COOLDOWN_S = 300.0
```

- [ ] **Step 2: Add presence check to proactive gate**

The spec requires presence check. Current gate checks `perception_activity` but not explicit presence state. Add:

In `should_speak`, after the activity check:

```python
        if state.get("presence_state", "AWAY") != "PRESENT":
            return False
```

- [ ] **Step 3: Add stimmung check**

The spec requires stimmung not critical. Add:

```python
        if state.get("stimmung_stance", "nominal") == "critical":
            return False
```

- [ ] **Step 4: Add session-active check**

The spec requires no active voice session. Add:

```python
        if state.get("session_active", False):
            return False
```

- [ ] **Step 5: Update run_loops_aux.py to pass new state fields**

In `run_loops_aux.py`, find where `gate_state` dict is built for `should_speak()` call. Add the new fields:

```python
gate_state = {
    # ... existing fields ...
    "presence_state": behaviors.get("presence_state", Behavior("AWAY")).value,
    "stimmung_stance": _read_stimmung_stance(),
    "session_active": daemon.session.is_active,
}
```

- [ ] **Step 6: Run proactive gate tests**

Run: `uv run pytest tests/ -k "proactive" -q`
Expected: All pass (may need to update test fixtures for new state fields)

- [ ] **Step 7: Commit**

```bash
git add agents/proactive_gate.py agents/hapax_daimonion/run_loops_aux.py
git commit -m "feat(voice): tune proactive gate — 5min cooldown, presence/stimmung/session checks"
```

---

### Task 5: Integration verification

- [ ] **Step 1: Verify daemon starts with engagement classifier**

```bash
systemctl --user restart hapax-daimonion.service
sleep 20
journalctl --user -u hapax-daimonion.service --since "25 sec ago" --no-pager | grep -i "engagement\|wake"
```

Expected: No wake word references. Engagement classifier initialized.

- [ ] **Step 2: Verify hotkey still works**

```bash
echo "toggle" | nc -U /run/user/1000/hapax-daimonion.sock
```

Expected: Session opens (or closes if already open).

- [ ] **Step 3: Run full test suite**

```bash
uv run pytest tests/hapax_daimonion/ -q
```

Expected: All pass (minus any pre-existing L8/L9 failures that were wake-word-specific and should now be gone).

- [ ] **Step 4: Commit any fixes**

```bash
git add -u
git commit -m "fix(voice): integration fixes for engagement activation"
```
