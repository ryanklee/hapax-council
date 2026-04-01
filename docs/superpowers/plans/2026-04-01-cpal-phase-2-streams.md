# CPAL Phase 2: Three Concurrent Streams

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the serial conversation pipeline (LISTEN->TRANSCRIBE->THINK->SPEAK) and 5-phase cognitive loop with three concurrent streams (perception, formulation, production) orchestrated by the CPAL control law evaluator.

**Architecture:** New stream modules in `agents/hapax_daimonion/cpal/`. Existing components (AudioInputStream, ConversationBuffer, ResidentSTT, SalienceRouter, TTSManager, PwAudioOutput) are reused as-is. The streams are new orchestration over existing components. A new `CpalEvaluator` replaces `CognitiveLoop` as the main daemon tick.

**Tech Stack:** Python 3.12, asyncio, existing daemon infrastructure. Phase 1 CPAL types (LoopGainController, ConversationControlLaw, ErrorSignal).

**Spec:** `docs/superpowers/specs/2026-04-01-conversational-perception-action-loop-design.md` sections 7, 6, 5

**Depends on:** Phase 1 (merged)

---

### File Structure

| File | Responsibility |
|---|---|
| `agents/hapax_daimonion/cpal/perception_stream.py` | Continuous audio analysis: VAD confidence, prosodic contour, TRP projection |
| `agents/hapax_daimonion/cpal/formulation_stream.py` | Speculative STT, salience pre-routing, LLM call preparation, backchannel selection |
| `agents/hapax_daimonion/cpal/production_stream.py` | Tier-composed output (T0-T3), interruptible, barge-in handling |
| `agents/hapax_daimonion/cpal/evaluator.py` | Control law evaluator tick: reads streams, updates gain, computes error, selects action |
| `tests/hapax_daimonion/test_perception_stream.py` | VAD signal, prosodic extraction, TRP projection |
| `tests/hapax_daimonion/test_formulation_stream.py` | Speculative STT gating, backchannel selection, commit/discard |
| `tests/hapax_daimonion/test_production_stream.py` | Tier composition, interruption, barge-in yield |
| `tests/hapax_daimonion/test_evaluator.py` | End-to-end tick: gain update, error computation, action dispatch |

---

### Task 1: Perception Stream

**Files:**
- Create: `agents/hapax_daimonion/cpal/perception_stream.py`
- Create: `tests/hapax_daimonion/test_perception_stream.py`

The perception stream wraps the existing ConversationBuffer and adds continuous signal extraction. It runs at ~30ms resolution (one audio frame) and publishes:

- `vad_confidence`: float 0.0-1.0 (from ConversationBuffer's VAD)
- `speech_active`: bool (from ConversationBuffer)
- `speech_duration_s`: float (from ConversationBuffer)
- `is_speaking`: bool (Hapax TTS active)
- `energy_rms`: float (computed from raw PCM frame)
- `trp_probability`: float 0.0-1.0 (turn completion estimate)

TRP projection is the key new capability. Initial implementation: rising-edge detector on silence after speech. When speech_active transitions false, trp_probability jumps to 0.7 and decays. This will be refined in later phases with prosodic analysis.

- [ ] **Step 1: Write failing tests**

```python
# tests/hapax_daimonion/test_perception_stream.py
"""Tests for CPAL perception stream."""

import struct
from unittest.mock import MagicMock

from agents.hapax_daimonion.cpal.perception_stream import PerceptionSignals, PerceptionStream


class TestPerceptionSignals:
    def test_default_signals(self):
        s = PerceptionSignals()
        assert s.vad_confidence == 0.0
        assert s.speech_active is False
        assert s.speech_duration_s == 0.0
        assert s.is_speaking is False
        assert s.energy_rms == 0.0
        assert s.trp_probability == 0.0

    def test_signals_are_frozen(self):
        s = PerceptionSignals()
        try:
            s.vad_confidence = 0.5
            assert False, "Should be frozen"
        except (AttributeError, TypeError):
            pass


class TestPerceptionStream:
    def _make_stream(self):
        buffer = MagicMock()
        buffer.speech_active = False
        buffer.speech_duration_s = 0.0
        buffer.is_speaking = False
        return PerceptionStream(buffer=buffer), buffer

    def test_initial_signals(self):
        stream, _ = self._make_stream()
        s = stream.signals
        assert s.vad_confidence == 0.0
        assert s.trp_probability == 0.0

    def test_update_reads_buffer(self):
        stream, buf = self._make_stream()
        buf.speech_active = True
        buf.speech_duration_s = 2.5
        buf.is_speaking = False
        silence_frame = b"\x00\x00" * 480
        stream.update(silence_frame, vad_prob=0.8)
        s = stream.signals
        assert s.vad_confidence == 0.8
        assert s.speech_active is True
        assert s.speech_duration_s == 2.5

    def test_energy_from_pcm(self):
        stream, buf = self._make_stream()
        # Frame of moderate energy
        samples = [1000] * 480
        frame = struct.pack(f"<{len(samples)}h", *samples)
        stream.update(frame, vad_prob=0.0)
        assert stream.signals.energy_rms > 0.0

    def test_trp_rises_on_speech_end(self):
        stream, buf = self._make_stream()
        # Simulate speech active
        buf.speech_active = True
        stream.update(b"\x00\x00" * 480, vad_prob=0.8)
        assert stream.signals.trp_probability == 0.0

        # Speech ends
        buf.speech_active = False
        stream.update(b"\x00\x00" * 480, vad_prob=0.05)
        assert stream.signals.trp_probability >= 0.5

    def test_trp_decays_in_silence(self):
        stream, buf = self._make_stream()
        buf.speech_active = True
        stream.update(b"\x00\x00" * 480, vad_prob=0.8)
        buf.speech_active = False
        stream.update(b"\x00\x00" * 480, vad_prob=0.05)
        trp_initial = stream.signals.trp_probability

        # Several more silent frames
        for _ in range(10):
            stream.update(b"\x00\x00" * 480, vad_prob=0.02)
        assert stream.signals.trp_probability < trp_initial

    def test_trp_resets_on_new_speech(self):
        stream, buf = self._make_stream()
        buf.speech_active = True
        stream.update(b"\x00\x00" * 480, vad_prob=0.8)
        buf.speech_active = False
        stream.update(b"\x00\x00" * 480, vad_prob=0.05)
        assert stream.signals.trp_probability > 0.0

        # New speech starts
        buf.speech_active = True
        stream.update(b"\x00\x00" * 480, vad_prob=0.7)
        assert stream.signals.trp_probability == 0.0

    def test_utterance_passthrough(self):
        stream, buf = self._make_stream()
        buf.get_utterance.return_value = b"\x01\x02" * 100
        assert stream.get_utterance() == b"\x01\x02" * 100

    def test_utterance_none_when_empty(self):
        stream, buf = self._make_stream()
        buf.get_utterance.return_value = None
        assert stream.get_utterance() is None
```

- [ ] **Step 2: Run tests, verify fail**

Run: `uv run pytest tests/hapax_daimonion/test_perception_stream.py -v`

- [ ] **Step 3: Write implementation**

```python
# agents/hapax_daimonion/cpal/perception_stream.py
"""Perception stream -- continuous audio analysis at ~30ms resolution.

Wraps the existing ConversationBuffer and adds continuous signal
extraction: VAD confidence, energy, and TRP (transition relevance
place) projection. Published signals drive the control law evaluator.

Stream 1 of 3 in the CPAL temporal architecture.
"""

from __future__ import annotations

import math
import struct
from dataclasses import dataclass


@dataclass(frozen=True)
class PerceptionSignals:
    """Snapshot of perception stream state. Immutable."""

    vad_confidence: float = 0.0
    speech_active: bool = False
    speech_duration_s: float = 0.0
    is_speaking: bool = False
    energy_rms: float = 0.0
    trp_probability: float = 0.0


_TRP_ONSET = 0.7  # initial TRP probability when speech ends
_TRP_DECAY = 0.85  # per-frame multiplicative decay


class PerceptionStream:
    """Continuous audio perception at frame resolution.

    Called once per audio frame (~30ms). Reads ConversationBuffer
    state and computes derived signals (energy, TRP projection).
    Does not own the buffer -- receives it from the daemon.
    """

    def __init__(self, buffer: object) -> None:
        self._buffer = buffer
        self._signals = PerceptionSignals()
        self._prev_speech_active = False
        self._trp = 0.0

    @property
    def signals(self) -> PerceptionSignals:
        return self._signals

    def update(self, frame: bytes, *, vad_prob: float) -> None:
        """Update perception from one audio frame.

        Args:
            frame: Raw int16 mono PCM (960 bytes = 480 samples @ 16kHz).
            vad_prob: VAD probability for this frame (0.0-1.0).
        """
        speech_active = self._buffer.speech_active
        speech_duration_s = self._buffer.speech_duration_s
        is_speaking = self._buffer.is_speaking

        # Energy RMS from PCM
        n_samples = len(frame) // 2
        if n_samples > 0:
            samples = struct.unpack(f"<{n_samples}h", frame)
            rms = math.sqrt(sum(s * s for s in samples) / n_samples) / 32768.0
        else:
            rms = 0.0

        # TRP projection: rising edge on speech->silence transition
        if self._prev_speech_active and not speech_active:
            self._trp = _TRP_ONSET
        elif speech_active:
            self._trp = 0.0
        else:
            self._trp *= _TRP_DECAY
            if self._trp < 0.01:
                self._trp = 0.0

        self._prev_speech_active = speech_active

        self._signals = PerceptionSignals(
            vad_confidence=vad_prob,
            speech_active=speech_active,
            speech_duration_s=speech_duration_s,
            is_speaking=is_speaking,
            energy_rms=rms,
            trp_probability=self._trp,
        )

    def get_utterance(self) -> bytes | None:
        """Pass through to buffer's utterance queue."""
        return self._buffer.get_utterance()
```

- [ ] **Step 4: Run tests, verify pass**
- [ ] **Step 5: Lint and commit**

```bash
git add agents/hapax_daimonion/cpal/perception_stream.py tests/hapax_daimonion/test_perception_stream.py
git commit -m "feat(cpal): perception stream -- continuous VAD, energy, TRP projection"
```

---

### Task 2: Formulation Stream

**Files:**
- Create: `agents/hapax_daimonion/cpal/formulation_stream.py`
- Create: `tests/hapax_daimonion/test_formulation_stream.py`

The formulation stream manages speculative processing: partial STT during operator speech, salience pre-routing, and backchannel selection. It runs independently of the perception stream and can begin LLM preparation before the operator finishes speaking.

Key design: formulation state is SPECULATIVE until committed. The evaluator decides when to commit (TRP high + salience warrants response). Uncommitted formulation can be discarded if the operator continues speaking and changes the meaning.

- [ ] **Step 1: Write failing tests**

```python
# tests/hapax_daimonion/test_formulation_stream.py
"""Tests for CPAL formulation stream."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from agents.hapax_daimonion.cpal.formulation_stream import (
    BackchannelDecision,
    FormulationState,
    FormulationStream,
)
from agents.hapax_daimonion.cpal.types import ConversationalRegion, CorrectionTier


class TestFormulationState:
    def test_initial_state_idle(self):
        fs = FormulationStream(stt=MagicMock(), salience_router=MagicMock())
        assert fs.state == FormulationState.IDLE

    def test_states_defined(self):
        assert len(FormulationState) == 4  # IDLE, SPECULATING, COMMITTED, PRODUCING


class TestBackchannelSelection:
    def test_no_backchannel_at_ambient(self):
        fs = FormulationStream(stt=MagicMock(), salience_router=MagicMock())
        decision = fs.select_backchannel(
            region=ConversationalRegion.AMBIENT,
            speech_active=True,
            speech_duration_s=3.0,
            trp_probability=0.0,
        )
        assert decision is None

    def test_backchannel_at_attentive_with_speech(self):
        fs = FormulationStream(stt=MagicMock(), salience_router=MagicMock())
        decision = fs.select_backchannel(
            region=ConversationalRegion.ATTENTIVE,
            speech_active=True,
            speech_duration_s=4.0,
            trp_probability=0.0,
        )
        # May or may not produce backchannel depending on timing
        assert decision is None or isinstance(decision, BackchannelDecision)

    def test_acknowledgment_after_speech_end(self):
        fs = FormulationStream(stt=MagicMock(), salience_router=MagicMock())
        decision = fs.select_backchannel(
            region=ConversationalRegion.CONVERSATIONAL,
            speech_active=False,
            speech_duration_s=0.0,
            trp_probability=0.6,
        )
        # High TRP + conversational = acknowledgment likely
        if decision is not None:
            assert decision.tier in (CorrectionTier.T0_VISUAL, CorrectionTier.T1_PRESYNTHESIZED)

    def test_no_backchannel_while_hapax_speaking(self):
        fs = FormulationStream(stt=MagicMock(), salience_router=MagicMock())
        fs._hapax_speaking = True
        decision = fs.select_backchannel(
            region=ConversationalRegion.INTENSIVE,
            speech_active=True,
            speech_duration_s=5.0,
            trp_probability=0.0,
        )
        assert decision is None


class TestSpeculativeFormulation:
    @pytest.mark.asyncio
    async def test_begin_speculation_on_speech(self):
        stt = MagicMock()
        stt.transcribe = AsyncMock(return_value="hello how are")
        router = MagicMock()
        router.route.return_value = MagicMock(tier="CAPABLE", activation_score=0.5)

        fs = FormulationStream(stt=stt, salience_router=router)
        frames = [b"\x00\x00" * 480] * 50  # ~1.5s of audio

        await fs.speculate(frames, speech_duration_s=1.5)
        assert fs.state == FormulationState.SPECULATING
        assert fs.partial_transcript is not None

    @pytest.mark.asyncio
    async def test_no_speculation_if_too_short(self):
        stt = MagicMock()
        fs = FormulationStream(stt=stt, salience_router=MagicMock())
        frames = [b"\x00\x00" * 480] * 10  # ~0.3s

        await fs.speculate(frames, speech_duration_s=0.3)
        assert fs.state == FormulationState.IDLE
        stt.transcribe.assert_not_called()

    @pytest.mark.asyncio
    async def test_commit_transitions_state(self):
        stt = MagicMock()
        stt.transcribe = AsyncMock(return_value="hello")
        fs = FormulationStream(stt=stt, salience_router=MagicMock())
        frames = [b"\x00\x00" * 480] * 50

        await fs.speculate(frames, speech_duration_s=1.5)
        fs.commit()
        assert fs.state == FormulationState.COMMITTED

    def test_discard_resets_state(self):
        fs = FormulationStream(stt=MagicMock(), salience_router=MagicMock())
        fs._state = FormulationState.SPECULATING
        fs._partial_transcript = "hello"
        fs.discard()
        assert fs.state == FormulationState.IDLE
        assert fs.partial_transcript is None

    def test_cannot_commit_from_idle(self):
        fs = FormulationStream(stt=MagicMock(), salience_router=MagicMock())
        fs.commit()  # no-op
        assert fs.state == FormulationState.IDLE
```

- [ ] **Step 2: Run tests, verify fail**
- [ ] **Step 3: Write implementation**

```python
# agents/hapax_daimonion/cpal/formulation_stream.py
"""Formulation stream -- speculative response preparation.

Begins processing while the operator is still speaking. Manages
speculative STT, salience pre-routing, and backchannel selection.
All formulation is speculative until the evaluator commits it.

Stream 2 of 3 in the CPAL temporal architecture.
"""

from __future__ import annotations

import enum
import logging
import time
from dataclasses import dataclass

from agents.hapax_daimonion.cpal.types import ConversationalRegion, CorrectionTier

log = logging.getLogger(__name__)

_MIN_SPEECH_FOR_SPECULATION_S = 1.0
_SPECULATION_INTERVAL_S = 1.2
_BACKCHANNEL_MIN_SPEECH_S = 3.0
_BACKCHANNEL_COOLDOWN_S = 5.0

# Regions that permit backchannel production
_BACKCHANNEL_REGIONS = frozenset({
    ConversationalRegion.ATTENTIVE,
    ConversationalRegion.CONVERSATIONAL,
    ConversationalRegion.INTENSIVE,
})


class FormulationState(enum.Enum):
    """State of the formulation stream."""

    IDLE = "idle"  # no active formulation
    SPECULATING = "speculating"  # partial STT + routing in progress
    COMMITTED = "committed"  # evaluator committed this formulation
    PRODUCING = "producing"  # handed off to production stream


@dataclass(frozen=True)
class BackchannelDecision:
    """A decision to produce a backchannel signal."""

    tier: CorrectionTier
    signal_type: str  # "visual", "vocal_backchannel", "acknowledgment"


class FormulationStream:
    """Speculative response preparation.

    Called by the evaluator each tick. Manages speculation lifecycle
    (idle -> speculating -> committed -> producing) and parallel
    backchannel selection.
    """

    def __init__(self, stt: object, salience_router: object) -> None:
        self._stt = stt
        self._salience_router = salience_router
        self._state = FormulationState.IDLE
        self._partial_transcript: str | None = None
        self._routing_result: object | None = None
        self._last_speculation_at: float = 0.0
        self._last_backchannel_at: float = 0.0
        self._hapax_speaking: bool = False
        self._speculating: bool = False  # in-flight guard

    @property
    def state(self) -> FormulationState:
        return self._state

    @property
    def partial_transcript(self) -> str | None:
        return self._partial_transcript

    @property
    def routing_result(self) -> object | None:
        return self._routing_result

    def set_hapax_speaking(self, speaking: bool) -> None:
        """Update Hapax speaking state (suppresses backchannels)."""
        self._hapax_speaking = speaking

    async def speculate(
        self, frames: list[bytes], *, speech_duration_s: float
    ) -> None:
        """Run speculative STT on accumulated speech frames.

        No-op if speech is too short, speculation is already in-flight,
        or insufficient time since last speculation.
        """
        if speech_duration_s < _MIN_SPEECH_FOR_SPECULATION_S:
            return
        if self._speculating:
            return
        now = time.monotonic()
        if now - self._last_speculation_at < _SPECULATION_INTERVAL_S:
            return

        self._speculating = True
        try:
            audio = b"".join(frames)
            transcript = await self._stt.transcribe(audio, _speculative=True)
            if transcript:
                self._partial_transcript = transcript
                self._state = FormulationState.SPECULATING
                # Pre-route for predicted tier
                try:
                    self._routing_result = self._salience_router.route(transcript)
                except Exception:
                    pass
            self._last_speculation_at = now
        finally:
            self._speculating = False

    def commit(self) -> None:
        """Commit current speculation for production."""
        if self._state == FormulationState.SPECULATING:
            self._state = FormulationState.COMMITTED
            log.info("Formulation committed: %s", (self._partial_transcript or "")[:50])

    def discard(self) -> None:
        """Discard current speculation (operator continued speaking)."""
        self._state = FormulationState.IDLE
        self._partial_transcript = None
        self._routing_result = None

    def mark_producing(self) -> None:
        """Mark formulation as handed off to production."""
        self._state = FormulationState.PRODUCING

    def reset(self) -> None:
        """Full reset for new conversational segment."""
        self._state = FormulationState.IDLE
        self._partial_transcript = None
        self._routing_result = None
        self._speculating = False

    def select_backchannel(
        self,
        *,
        region: ConversationalRegion,
        speech_active: bool,
        speech_duration_s: float,
        trp_probability: float,
    ) -> BackchannelDecision | None:
        """Select a backchannel signal if appropriate.

        Independent of formulation state -- backchannels are reactive
        signals, not planned utterances.
        """
        if self._hapax_speaking:
            return None

        if region not in _BACKCHANNEL_REGIONS:
            return None

        now = time.monotonic()
        if now - self._last_backchannel_at < _BACKCHANNEL_COOLDOWN_S:
            return None

        # Vocal backchannel during sustained operator speech
        if speech_active and speech_duration_s >= _BACKCHANNEL_MIN_SPEECH_S:
            if region in (ConversationalRegion.CONVERSATIONAL, ConversationalRegion.INTENSIVE):
                self._last_backchannel_at = now
                return BackchannelDecision(
                    tier=CorrectionTier.T1_PRESYNTHESIZED,
                    signal_type="vocal_backchannel",
                )

        # Acknowledgment at TRP (speech just ended)
        if not speech_active and trp_probability >= 0.5:
            if region in (ConversationalRegion.CONVERSATIONAL, ConversationalRegion.INTENSIVE):
                self._last_backchannel_at = now
                return BackchannelDecision(
                    tier=CorrectionTier.T1_PRESYNTHESIZED,
                    signal_type="acknowledgment",
                )

        # Visual signal at lower regions
        if not speech_active and trp_probability >= 0.3:
            self._last_backchannel_at = now
            return BackchannelDecision(
                tier=CorrectionTier.T0_VISUAL,
                signal_type="visual",
            )

        return None
```

- [ ] **Step 4: Run tests, verify pass**
- [ ] **Step 5: Lint and commit**

```bash
git add agents/hapax_daimonion/cpal/formulation_stream.py tests/hapax_daimonion/test_formulation_stream.py
git commit -m "feat(cpal): formulation stream -- speculative STT, backchannel selection"
```

---

### Task 3: Production Stream

**Files:**
- Create: `agents/hapax_daimonion/cpal/production_stream.py`
- Create: `tests/hapax_daimonion/test_production_stream.py`

The production stream handles tier-composed output. It receives action decisions from the evaluator and produces the appropriate signal (T0 visual, T1 presynthesized, T2 lightweight, T3 full LLM). Production is interruptible at tier boundaries -- if the operator resumes speaking, production yields immediately.

- [ ] **Step 1: Write failing tests**

```python
# tests/hapax_daimonion/test_production_stream.py
"""Tests for CPAL production stream."""

from unittest.mock import MagicMock

from agents.hapax_daimonion.cpal.production_stream import ProductionStream
from agents.hapax_daimonion.cpal.types import CorrectionTier


class TestProductionStream:
    def _make_stream(self):
        audio_output = MagicMock()
        shm_writer = MagicMock()
        return ProductionStream(audio_output=audio_output, shm_writer=shm_writer), audio_output, shm_writer

    def test_initial_state(self):
        ps, _, _ = self._make_stream()
        assert not ps.is_producing
        assert ps.current_tier is None

    def test_produce_t0_visual(self):
        ps, _, shm = self._make_stream()
        ps.produce_t0(signal_type="attentional_shift", intensity=0.7)
        shm.assert_called_once()
        assert not ps.is_producing  # T0 is instant, non-blocking

    def test_produce_t1_writes_audio(self):
        ps, audio, _ = self._make_stream()
        pcm = b"\x00\x01" * 500
        ps.produce_t1(pcm_data=pcm)
        audio.write.assert_called_once_with(pcm)

    def test_interrupt_stops_production(self):
        ps, _, _ = self._make_stream()
        ps._producing = True
        ps._current_tier = CorrectionTier.T3_FULL_FORMULATION
        ps.interrupt()
        assert not ps.is_producing
        assert ps.current_tier is None

    def test_interrupt_when_idle_is_noop(self):
        ps, _, _ = self._make_stream()
        ps.interrupt()  # should not raise
        assert not ps.is_producing

    def test_yield_to_operator(self):
        ps, _, _ = self._make_stream()
        ps._producing = True
        ps.yield_to_operator()
        assert not ps.is_producing
```

- [ ] **Step 2: Run tests, verify fail**
- [ ] **Step 3: Write implementation**

```python
# agents/hapax_daimonion/cpal/production_stream.py
"""Production stream -- tier-composed, interruptible output.

Receives action decisions from the evaluator and produces signals
at the appropriate tier. Production is interruptible at tier boundaries:
if the operator resumes speaking, production yields immediately.

Stream 3 of 3 in the CPAL temporal architecture.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path

from agents.hapax_daimonion.cpal.types import CorrectionTier

log = logging.getLogger(__name__)

_DEFAULT_VISUAL_PATH = Path("/dev/shm/hapax-conversation/visual-signal.json")


class ProductionStream:
    """Tier-composed output with interruption support.

    T0: Visual state change (instant, non-blocking)
    T1: Presynthesized audio playback
    T2: Lightweight computed response
    T3: Full LLM formulation (managed externally via pipeline)

    Operator always wins -- any tier can be interrupted.
    """

    def __init__(
        self,
        audio_output: object | None = None,
        shm_writer: object | None = None,
    ) -> None:
        self._audio_output = audio_output
        self._shm_writer = shm_writer or self._default_shm_write
        self._producing = False
        self._current_tier: CorrectionTier | None = None
        self._interrupted = False

    @property
    def is_producing(self) -> bool:
        return self._producing

    @property
    def current_tier(self) -> CorrectionTier | None:
        return self._current_tier

    @property
    def was_interrupted(self) -> bool:
        return self._interrupted

    def produce_t0(self, *, signal_type: str, intensity: float = 0.5) -> None:
        """Produce a T0 visual signal (instant, non-blocking).

        Writes to /dev/shm for Reverie and other visual surfaces.
        """
        signal = {
            "type": signal_type,
            "intensity": intensity,
            "timestamp": time.time(),
        }
        self._shm_writer(signal)

    def produce_t1(self, *, pcm_data: bytes) -> None:
        """Produce a T1 presynthesized audio signal.

        Plays cached audio (backchannel, acknowledgment, formulation onset).
        Blocking for audio duration via PwAudioOutput.write().
        """
        self._producing = True
        self._current_tier = CorrectionTier.T1_PRESYNTHESIZED
        self._interrupted = False
        try:
            if self._audio_output is not None:
                self._audio_output.write(pcm_data)
        finally:
            if not self._interrupted:
                self._producing = False
                self._current_tier = None

    def produce_t2(self, *, text: str) -> None:
        """Produce a T2 lightweight response (echo/rephrase, discourse marker).

        Requires TTS synthesis but no LLM call. Blocking.
        """
        self._producing = True
        self._current_tier = CorrectionTier.T2_LIGHTWEIGHT
        self._interrupted = False
        log.info("T2 production: %s", text[:50])
        # T2 synthesis delegated to caller (evaluator provides synthesized PCM)
        self._producing = False
        self._current_tier = None

    def mark_t3_start(self) -> None:
        """Mark the start of T3 full formulation (managed externally)."""
        self._producing = True
        self._current_tier = CorrectionTier.T3_FULL_FORMULATION
        self._interrupted = False

    def mark_t3_end(self) -> None:
        """Mark the end of T3 formulation."""
        self._producing = False
        self._current_tier = None

    def interrupt(self) -> None:
        """Interrupt current production at tier boundary."""
        if self._producing:
            log.info("Production interrupted at %s", self._current_tier)
            self._interrupted = True
        self._producing = False
        self._current_tier = None

    def yield_to_operator(self) -> None:
        """Yield the floor to the operator. Same as interrupt."""
        self.interrupt()

    @staticmethod
    def _default_shm_write(signal: dict) -> None:
        """Default SHM writer for T0 visual signals."""
        try:
            path = _DEFAULT_VISUAL_PATH
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix(".tmp")
            tmp.write_text(json.dumps(signal), encoding="utf-8")
            tmp.rename(path)
        except Exception:
            pass
```

- [ ] **Step 4: Run tests, verify pass**
- [ ] **Step 5: Lint and commit**

```bash
git add agents/hapax_daimonion/cpal/production_stream.py tests/hapax_daimonion/test_production_stream.py
git commit -m "feat(cpal): production stream -- tier-composed, interruptible output"
```

---

### Task 4: Control Law Evaluator

**Files:**
- Create: `agents/hapax_daimonion/cpal/evaluator.py`
- Create: `tests/hapax_daimonion/test_evaluator.py`

The evaluator replaces the CognitiveLoop. It ticks at ~150ms, reads all three streams, runs the control law, and dispatches actions. This is the orchestrator.

- [ ] **Step 1: Write failing tests**

```python
# tests/hapax_daimonion/test_evaluator.py
"""Tests for CPAL control law evaluator."""

from unittest.mock import MagicMock

from agents.hapax_daimonion.cpal.evaluator import CpalEvaluator
from agents.hapax_daimonion.cpal.types import ConversationalRegion, CorrectionTier, GainUpdate


class TestEvaluatorGainUpdates:
    def _make_evaluator(self):
        perception = MagicMock()
        perception.signals = MagicMock(
            vad_confidence=0.0,
            speech_active=False,
            speech_duration_s=0.0,
            is_speaking=False,
            energy_rms=0.0,
            trp_probability=0.0,
        )
        formulation = MagicMock()
        formulation.state = MagicMock(value="idle")
        production = MagicMock()
        production.is_producing = False
        return CpalEvaluator(
            perception=perception,
            formulation=formulation,
            production=production,
        )

    def test_initial_gain_ambient(self):
        ev = self._make_evaluator()
        assert ev.gain_controller.region == ConversationalRegion.AMBIENT

    def test_operator_speech_drives_gain(self):
        ev = self._make_evaluator()
        ev.perception.signals.speech_active = True
        ev.perception.signals.vad_confidence = 0.8
        ev.tick(dt=0.15)
        assert ev.gain_controller.gain > 0.0

    def test_silence_decays_gain(self):
        ev = self._make_evaluator()
        ev.gain_controller.apply(GainUpdate(delta=0.5, source="test"))
        ev.perception.signals.speech_active = False
        ev.tick(dt=5.0)
        assert ev.gain_controller.gain < 0.5

    def test_tick_returns_action(self):
        ev = self._make_evaluator()
        ev.gain_controller.apply(GainUpdate(delta=0.6, source="test"))
        ev.perception.signals.speech_active = False
        ev.perception.signals.trp_probability = 0.7
        result = ev.tick(dt=0.15)
        assert result is not None
        assert result.action_tier is not None
        assert result.region is not None


class TestEvaluatorActionDispatch:
    def _make_evaluator(self):
        perception = MagicMock()
        perception.signals = MagicMock(
            vad_confidence=0.0,
            speech_active=False,
            speech_duration_s=0.0,
            is_speaking=False,
            energy_rms=0.0,
            trp_probability=0.0,
        )
        formulation = MagicMock()
        formulation.state = MagicMock(value="idle")
        formulation.select_backchannel.return_value = None
        production = MagicMock()
        production.is_producing = False
        return CpalEvaluator(
            perception=perception,
            formulation=formulation,
            production=production,
        )

    def test_ambient_produces_no_vocal(self):
        ev = self._make_evaluator()
        result = ev.tick(dt=0.15)
        # At ambient, max action is T0
        assert result.action_tier == CorrectionTier.T0_VISUAL

    def test_barge_in_interrupts_production(self):
        ev = self._make_evaluator()
        ev.production.is_producing = True
        ev.perception.signals.speech_active = True
        ev.perception.signals.vad_confidence = 0.95
        ev.tick(dt=0.15)
        ev.production.interrupt.assert_called()
```

- [ ] **Step 2: Run tests, verify fail**
- [ ] **Step 3: Write implementation**

```python
# agents/hapax_daimonion/cpal/evaluator.py
"""CPAL control law evaluator -- the cognitive tick.

Replaces CognitiveLoop. Ticks at ~150ms, reads all three streams,
runs the control law, and dispatches actions. This is the single
point of coordination for the CPAL architecture.

The evaluator does NOT run the streams -- they run independently.
It reads their state, evaluates the control law, and tells them
what to do.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from agents.hapax_daimonion.cpal.control_law import ConversationControlLaw, ControlLawResult
from agents.hapax_daimonion.cpal.loop_gain import LoopGainController
from agents.hapax_daimonion.cpal.types import CorrectionTier, GainUpdate

log = logging.getLogger(__name__)

_SPEECH_GAIN_DELTA = 0.05  # gain increase per tick during operator speech
_BARGE_IN_VAD_THRESHOLD = 0.9


@dataclass(frozen=True)
class EvaluatorResult:
    """Result of a single evaluator tick."""

    action_tier: CorrectionTier
    region: object  # ConversationalRegion
    error_magnitude: float
    gain: float


class CpalEvaluator:
    """Control law evaluator -- the cognitive tick.

    Reads perception, formulation, and production streams.
    Runs the control law. Dispatches actions.
    """

    def __init__(
        self,
        perception: object,
        formulation: object,
        production: object,
        control_law: ConversationControlLaw | None = None,
    ) -> None:
        self.perception = perception
        self.formulation = formulation
        self.production = production
        self._control_law = control_law or ConversationControlLaw()
        self._gain_controller = LoopGainController()

    @property
    def gain_controller(self) -> LoopGainController:
        return self._gain_controller

    def tick(self, dt: float) -> EvaluatorResult:
        """Run one evaluator tick.

        Args:
            dt: Time since last tick (seconds).

        Returns:
            EvaluatorResult with selected action tier and state.
        """
        signals = self.perception.signals

        # 1. Gain updates
        if signals.speech_active and signals.vad_confidence > 0.3:
            self._gain_controller.apply(
                GainUpdate(delta=_SPEECH_GAIN_DELTA, source="operator_speech")
            )
        else:
            self._gain_controller.decay(dt)

        # 2. Barge-in detection
        if (
            self.production.is_producing
            and signals.speech_active
            and signals.vad_confidence > _BARGE_IN_VAD_THRESHOLD
        ):
            self.production.interrupt()
            log.info("Barge-in: operator speech interrupted production")

        # 3. Control law evaluation
        result = self._control_law.evaluate(
            gain=self._gain_controller.gain,
            ungrounded_du_count=0,  # Phase 4 will wire grounding ledger
            repair_rate=0.0,
            gqi=0.8,  # Phase 4 will wire GQI
            silence_s=0.0 if signals.speech_active else dt,
        )

        # 4. Backchannel check (independent of formulation)
        bc = self.formulation.select_backchannel(
            region=result.region,
            speech_active=signals.speech_active,
            speech_duration_s=signals.speech_duration_s,
            trp_probability=signals.trp_probability,
        )
        if bc is not None:
            log.debug("Backchannel selected: %s (%s)", bc.signal_type, bc.tier)

        return EvaluatorResult(
            action_tier=result.action_tier,
            region=result.region,
            error_magnitude=result.error.magnitude,
            gain=self._gain_controller.gain,
        )
```

- [ ] **Step 4: Run tests, verify pass**
- [ ] **Step 5: Lint and commit**

```bash
git add agents/hapax_daimonion/cpal/evaluator.py tests/hapax_daimonion/test_evaluator.py
git commit -m "feat(cpal): control law evaluator -- cognitive tick reads streams, dispatches actions"
```

---

### Task 5: Update Package Exports + Full Test Suite

**Files:**
- Modify: `agents/hapax_daimonion/cpal/__init__.py`

- [ ] **Step 1: Update exports to include all Phase 2 modules**

Add imports for PerceptionStream, PerceptionSignals, FormulationStream, FormulationState, BackchannelDecision, ProductionStream, CpalEvaluator, EvaluatorResult.

- [ ] **Step 2: Run all CPAL tests (Phase 1 + Phase 2)**

Run: `uv run pytest tests/hapax_daimonion/test_cpal_*.py tests/hapax_daimonion/test_perception_stream.py tests/hapax_daimonion/test_formulation_stream.py tests/hapax_daimonion/test_production_stream.py tests/hapax_daimonion/test_evaluator.py -v`

- [ ] **Step 3: Lint and format check**
- [ ] **Step 4: Commit and push**

```bash
git add agents/hapax_daimonion/cpal/__init__.py
git commit -m "feat(cpal): complete Phase 2 -- three concurrent streams + evaluator"
git push origin HEAD
```
