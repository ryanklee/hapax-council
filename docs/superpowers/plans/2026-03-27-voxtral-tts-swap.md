# Voxtral TTS Swap — Replace Kokoro + Piper with Mistral Voxtral

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace Kokoro and Piper TTS backends with Mistral Voxtral TTS via their hosted API, and cleanly excise all Piper code.

**Architecture:** Single TTS backend (`voxtral`) replaces the two-tier Kokoro/Piper system. TTSManager calls the Mistral `/v1/audio/speech` API with streaming PCM output, base64-decodes chunks, and returns raw PCM int16 bytes — same interface as today. The Pipecat wrapper, bridge engine, conversation pipeline, and vocal FX chain are unchanged (Voxtral outputs 24kHz, matching Kokoro exactly). Piper code is fully removed.

**Tech Stack:** `mistralai` Python SDK (2.1.x), Mistral API (`/v1/audio/speech`), PCM streaming (`response_format="pcm"`), 24kHz int16 mono output.

**Key constraint:** Voxtral API returns base64-encoded float32 LE PCM at 24kHz. We must decode from base64, then convert float32→int16 (reusing `_audio_to_pcm_int16`).

---

### Task 1: Add `mistralai` dependency, remove `kokoro` and `piper-tts`

**Files:**
- Modify: `pyproject.toml:17-39` (dependencies), `pyproject.toml:57-80` (audio optional deps)
- Modify: `.envrc` (add MISTRAL_API_KEY)

- [ ] **Step 1: Update pyproject.toml**

In `[project] dependencies`, replace `"kokoro>=0.9.4"` (line 34) with `"mistralai>=2.1.0"`:

```toml
    "mistralai>=2.1.0",
```

In `[project.optional-dependencies] audio`, remove `"kokoro>=0.9.0"` (line 59) and `"piper-tts>=1.2.0"` (line 64).

- [ ] **Step 2: Add MISTRAL_API_KEY to .envrc**

Append to `.envrc`:

```bash
export MISTRAL_API_KEY=$(pass show api/mistral 2>/dev/null)
```

- [ ] **Step 3: Run uv sync**

Run: `cd /home/hapax/projects/hapax-council && uv sync`
Expected: Lock file updated, mistralai installed, kokoro and piper-tts removed.

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml uv.lock .envrc
git commit -m "deps: swap kokoro+piper-tts for mistralai SDK"
```

---

### Task 2: Rewrite `tts.py` — Voxtral backend, excise Piper

**Files:**
- Modify: `agents/hapax_voice/tts.py` (full rewrite)

- [ ] **Step 1: Write the failing test — Voxtral synthesis**

Add to `tests/test_hapax_voice_tts.py` (replacing Kokoro/Piper tests — done in Task 5):

```python
def test_voxtral_synthesis_returns_pcm() -> None:
    """Voxtral synthesis decodes base64 PCM float32 to int16 bytes."""
    import base64
    import struct

    # 10 samples of float32 silence = 40 bytes raw, base64-encoded
    raw_f32 = struct.pack("<10f", *([0.0] * 10))
    b64_chunk = base64.b64encode(raw_f32).decode()

    mock_event = MagicMock()
    mock_event.event = "speech.audio.delta"
    mock_event.data.audio_data = b64_chunk

    mock_done = MagicMock()
    mock_done.event = "speech.audio.done"

    mock_client = MagicMock()
    mock_stream = MagicMock()
    mock_stream.__enter__ = MagicMock(return_value=iter([mock_event, mock_done]))
    mock_stream.__exit__ = MagicMock(return_value=False)
    mock_client.audio.speech.complete.return_value = mock_stream

    with patch("agents.hapax_voice.tts.Mistral", return_value=mock_client):
        mgr = TTSManager(voice_id="jessica")
        result = mgr.synthesize("hello", use_case="conversation")

    assert isinstance(result, bytes)
    assert len(result) == 10 * 2  # 10 samples * 2 bytes (int16)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/hapax/projects/hapax-council && uv run pytest tests/test_hapax_voice_tts.py::test_voxtral_synthesis_returns_pcm -v`
Expected: FAIL — TTSManager doesn't accept `voice_id` yet.

- [ ] **Step 3: Rewrite tts.py**

Replace `agents/hapax_voice/tts.py` entirely:

```python
"""Voxtral TTS — Mistral API streaming synthesis."""

from __future__ import annotations

import base64
import logging
import os
import struct

import numpy as np

log = logging.getLogger(__name__)

_TIER_MAP: dict[str, str] = {
    "conversation": "voxtral",
    "notification": "voxtral",
    "briefing": "voxtral",
    "proactive": "voxtral",
}

VOXTRAL_SAMPLE_RATE = 24000


def select_tier(use_case: str) -> str:
    """Select TTS tier for a given use case."""
    return _TIER_MAP.get(use_case, "voxtral")


def _audio_to_pcm_int16(audio: np.ndarray) -> bytes:
    """Convert float32 audio array to raw PCM int16 bytes."""
    audio = np.clip(audio, -1.0, 1.0)
    pcm = (audio * 32767).astype(np.int16)
    return pcm.tobytes()


def _decode_pcm_f32_b64(b64_data: str) -> np.ndarray:
    """Decode base64-encoded float32 LE PCM into a numpy array."""
    raw = base64.b64decode(b64_data)
    return np.frombuffer(raw, dtype="<f4")


class TTSManager:
    """Manages TTS synthesis via Mistral Voxtral API."""

    def __init__(
        self,
        voice_id: str = "jessica",
        ref_audio_path: str | None = None,
    ) -> None:
        self.voice_id = voice_id
        self._ref_audio_b64: str | None = None
        if ref_audio_path:
            from pathlib import Path

            self._ref_audio_b64 = base64.b64encode(
                Path(ref_audio_path).read_bytes()
            ).decode()
        self._client = None

    def _get_client(self):
        """Lazy-init the Mistral client."""
        if self._client is None:
            from mistralai import Mistral

            api_key = os.environ.get("MISTRAL_API_KEY", "")
            if not api_key:
                raise RuntimeError(
                    "MISTRAL_API_KEY is not set — TTS calls will fail. "
                    "Add to .envrc: export MISTRAL_API_KEY=$(pass show api/mistral)"
                )
            self._client = Mistral(api_key=api_key)
        return self._client

    def preload(self) -> None:
        """Validate API key at startup."""
        self._get_client()

    def synthesize(self, text: str, use_case: str = "conversation") -> bytes:
        """Synthesize text to raw PCM int16 audio bytes via Voxtral streaming API."""
        tier = select_tier(use_case)
        log.debug("TTS tier=%s for use_case=%s", tier, use_case)
        return self._synthesize_voxtral(text)

    def _synthesize_voxtral(self, text: str) -> bytes:
        """Stream synthesis from Mistral Voxtral API, return PCM int16 bytes."""
        client = self._get_client()

        kwargs: dict = {
            "model": "voxtral-mini-tts-2603",
            "input": text,
            "response_format": "pcm",
            "stream": True,
        }
        if self._ref_audio_b64:
            kwargs["ref_audio"] = self._ref_audio_b64
        else:
            kwargs["voice_id"] = self.voice_id

        chunks: list[bytes] = []
        with client.audio.speech.complete(**kwargs) as stream:
            for event in stream:
                if event.event == "speech.audio.delta":
                    f32_audio = _decode_pcm_f32_b64(event.data.audio_data)
                    chunks.append(_audio_to_pcm_int16(f32_audio))

        if not chunks:
            log.warning("Voxtral produced no audio for text: %r", text[:50])
            return b""

        return b"".join(chunks)
```

- [ ] **Step 4: Run tests**

Run: `cd /home/hapax/projects/hapax-council && uv run pytest tests/test_hapax_voice_tts.py::test_voxtral_synthesis_returns_pcm -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add agents/hapax_voice/tts.py
git commit -m "feat: replace Kokoro/Piper TTS with Voxtral streaming API"
```

---

### Task 3: Update config and Pipecat wrapper

**Files:**
- Modify: `agents/hapax_voice/config.py:81`
- Modify: `agents/hapax_voice/pipecat_tts.py` (full rewrite)
- Modify: `agents/hapax_voice/pipeline.py:32-33,116-125`

- [ ] **Step 1: Update config.py**

In `agents/hapax_voice/config.py`, replace line 81:

```python
    kokoro_voice: str = "af_heart"
```

with:

```python
    voxtral_voice_id: str = "jessica"
    voxtral_ref_audio: str = ""  # path to reference audio for voice cloning
```

- [ ] **Step 2: Rewrite pipecat_tts.py**

Replace `agents/hapax_voice/pipecat_tts.py`:

```python
"""Custom Pipecat TTS service wrapping the Voxtral TTSManager."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncGenerator

from pipecat.frames.frames import (
    Frame,
    TTSAudioRawFrame,
    TTSStartedFrame,
    TTSStoppedFrame,
)
from pipecat.services.tts_service import TTSService

from agents.hapax_voice.tts import VOXTRAL_SAMPLE_RATE, TTSManager

log = logging.getLogger(__name__)


class VoxtralTTSService(TTSService):
    """Pipecat TTS service that delegates synthesis to Voxtral via TTSManager.

    Voxtral outputs 24 kHz mono PCM, streamed and chunked for interruption
    support in the Pipecat pipeline.
    """

    def __init__(
        self,
        *,
        voice_id: str = "jessica",
        ref_audio_path: str | None = None,
        tts_manager: TTSManager | None = None,
        **kwargs,
    ) -> None:
        super().__init__(sample_rate=VOXTRAL_SAMPLE_RATE, **kwargs)
        self._tts_manager = tts_manager or TTSManager(
            voice_id=voice_id, ref_audio_path=ref_audio_path
        )

    def can_generate_metrics(self) -> bool:
        return True

    async def run_tts(self, text: str, context_id: str) -> AsyncGenerator[Frame, None]:
        """Synthesize text to audio frames using Voxtral.

        Yields:
            TTSStartedFrame, TTSAudioRawFrame(s), TTSStoppedFrame.
        """
        log.debug("VoxtralTTSService.run_tts: text=%r context_id=%s", text[:50], context_id)

        yield TTSStartedFrame()
        await self.start_ttfb_metrics()

        try:
            pcm_bytes = await asyncio.to_thread(
                self._tts_manager.synthesize, text, "conversation"
            )
        except Exception:
            log.exception("TTS synthesis failed")
            yield TTSStoppedFrame()
            return

        await self.stop_ttfb_metrics()

        if pcm_bytes:
            chunk_size = VOXTRAL_SAMPLE_RATE * 2  # 1 second of int16 audio
            for offset in range(0, len(pcm_bytes), chunk_size):
                chunk = pcm_bytes[offset : offset + chunk_size]
                yield TTSAudioRawFrame(
                    audio=chunk,
                    sample_rate=VOXTRAL_SAMPLE_RATE,
                    num_channels=1,
                )

        yield TTSStoppedFrame()
```

- [ ] **Step 3: Update pipeline.py imports and _build_tts**

In `agents/hapax_voice/pipeline.py`, replace lines 32-33:

```python
from agents.hapax_voice.pipecat_tts import VoxtralTTSService
from agents.hapax_voice.tts import VOXTRAL_SAMPLE_RATE
```

Replace `_build_tts` (lines 116-125):

```python
def _build_tts(voice: str) -> VoxtralTTSService:
    """Create the Voxtral TTS service for Pipecat.

    Args:
        voice: Voxtral voice ID.

    Returns:
        Configured VoxtralTTSService.
    """
    return VoxtralTTSService(voice_id=voice)
```

- [ ] **Step 4: Commit**

```bash
git add agents/hapax_voice/config.py agents/hapax_voice/pipecat_tts.py agents/hapax_voice/pipeline.py
git commit -m "feat: update config, Pipecat wrapper, pipeline for Voxtral"
```

---

### Task 4: Update daemon callers

**Files:**
- Modify: `agents/hapax_voice/__main__.py:121,2187`
- Modify: `agents/hapax_voice/conversation_pipeline.py:1852-1855`
- Modify: `agents/hapax_voice/vocal_fx.py:30` (comment only — sample rate already 24000)

- [ ] **Step 1: Update __main__.py TTSManager instantiation**

Find (line 121):
```python
self.tts = TTSManager(kokoro_voice=self.cfg.kokoro_voice)
```

Replace with:
```python
self.tts = TTSManager(
    voice_id=self.cfg.voxtral_voice_id,
    ref_audio_path=self.cfg.voxtral_ref_audio or None,
)
```

- [ ] **Step 2: Update conversation_pipeline.py emoji comment**

Find (lines 1852-1855):
```python
# Strip emoji before TTS — Kokoro synthesizes them as
# "smiling face with..." or silence. Keep original in
# echo detection history (already appended above).
```

Replace with:
```python
# Strip emoji before TTS — they synthesize as Unicode names
# or silence. Keep original in echo detection history.
```

- [ ] **Step 3: Commit**

```bash
git add agents/hapax_voice/__main__.py agents/hapax_voice/conversation_pipeline.py
git commit -m "feat: wire Voxtral into daemon and conversation pipeline"
```

---

### Task 5: Update demo pipeline

**Files:**
- Modify: `agents/demo_pipeline/voice.py:21-94,225-315`

- [ ] **Step 1: Replace Kokoro functions with Voxtral**

Replace the Kokoro constants, availability check, pipeline loader, and generation function (lines 21-94) with:

```python
VOXTRAL_VOICE_ID = "jessica"
VOXTRAL_SAMPLE_RATE = 24000


def check_voxtral_available() -> bool:
    """Check if Mistral API key is available for Voxtral TTS."""
    import subprocess

    try:
        result = subprocess.run(
            ["pass", "show", "api/mistral"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.returncode == 0 and bool(result.stdout.strip())
    except Exception:
        return False


def generate_voice_segment_voxtral(
    text: str,
    output_path: Path,
    voice_id: str = VOXTRAL_VOICE_ID,
) -> None:
    """Generate a single voice segment using Mistral Voxtral TTS API."""
    import base64
    import os
    import struct

    output_path.parent.mkdir(parents=True, exist_ok=True)

    from mistralai import Mistral

    api_key = os.environ.get("MISTRAL_API_KEY", "")
    if not api_key:
        raise RuntimeError("MISTRAL_API_KEY is not set")

    client = Mistral(api_key=api_key)

    chunks: list[bytes] = []
    with client.audio.speech.complete(
        model="voxtral-mini-tts-2603",
        input=text,
        voice_id=voice_id,
        response_format="pcm",
        stream=True,
    ) as stream:
        for event in stream:
            if event.event == "speech.audio.delta":
                raw = base64.b64decode(event.data.audio_data)
                f32 = np.frombuffer(raw, dtype="<f4")
                f32 = np.clip(f32, -1.0, 1.0)
                pcm = (f32 * 32767).astype(np.int16)
                chunks.append(pcm.tobytes())

    if not chunks:
        raise RuntimeError(f"Voxtral produced no audio for text: {text[:80]!r}")

    pcm_data = b"".join(chunks)
    with wave.open(str(output_path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(VOXTRAL_SAMPLE_RATE)
        wf.writeframes(pcm_data)

    log.info("Generated voice segment (voxtral): %s (%d bytes)", output_path.name, len(pcm_data))
```

Also remove the now-unused `_audio_to_pcm_int16` function (lines 61-65) and `_get_kokoro_pipeline` (lines 45-58).

- [ ] **Step 2: Update generate_all_voice_segments backend selection**

In the `backend` Literal type (line 230), replace `"kokoro"` with `"voxtral"`:

```python
backend: Literal["chatterbox", "voxtral", "elevenlabs", "auto"] = "chatterbox",
```

In auto-resolution (lines 243-254), replace the kokoro check:

```python
    if backend == "auto":
        if check_elevenlabs_available():
            resolved_backend = "elevenlabs"
        elif check_tts_available():
            resolved_backend = "chatterbox"
        elif check_voxtral_available():
            resolved_backend = "voxtral"
        else:
            raise RuntimeError(
                "No TTS backend available. Set up ElevenLabs, "
                "start Chatterbox, or set MISTRAL_API_KEY."
            )
```

In `_generate_one` (line 275-276), replace:
```python
        elif resolved_backend == "voxtral":
            generate_voice_segment_voxtral(text, output_path)
```

- [ ] **Step 3: Update module docstring**

Line 1: Replace `"Kokoro TTS"` with `"Voxtral TTS"`:
```python
"""Voice generation pipeline — Chatterbox TTS API and Voxtral TTS."""
```

- [ ] **Step 4: Commit**

```bash
git add agents/demo_pipeline/voice.py
git commit -m "feat: replace Kokoro with Voxtral in demo pipeline"
```

---

### Task 6: Rewrite all tests

**Files:**
- Modify: `tests/test_hapax_voice_tts.py` (rewrite)
- Modify: `tests/test_hapax_voice_pipecat_tts.py` (update imports/names)
- Modify: `tests/hapax_voice/test_tts_tier_cleanup.py` (update tier names)
- Modify: `tests/test_hapax_voice_pipeline.py` (update imports/mocks)

- [ ] **Step 1: Rewrite test_hapax_voice_tts.py**

```python
"""Tests for hapax_voice Voxtral TTS abstraction."""

from __future__ import annotations

import base64
import struct
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from agents.hapax_voice.tts import (
    TTSManager,
    _audio_to_pcm_int16,
    _decode_pcm_f32_b64,
    select_tier,
)

# ---------------------------------------------------------------------------
# select_tier
# ---------------------------------------------------------------------------


def test_select_tier_conversation_is_voxtral() -> None:
    assert select_tier("conversation") == "voxtral"


def test_select_tier_notification_is_voxtral() -> None:
    assert select_tier("notification") == "voxtral"


def test_select_tier_briefing_is_voxtral() -> None:
    assert select_tier("briefing") == "voxtral"


def test_select_tier_unknown_defaults_to_voxtral() -> None:
    assert select_tier("unknown_thing") == "voxtral"


# ---------------------------------------------------------------------------
# _audio_to_pcm_int16
# ---------------------------------------------------------------------------


def test_pcm_silence() -> None:
    silence = np.zeros(100, dtype=np.float32)
    pcm = _audio_to_pcm_int16(silence)
    assert len(pcm) == 200
    assert pcm == b"\x00" * 200


def test_pcm_full_scale() -> None:
    full = np.ones(1, dtype=np.float32)
    pcm = _audio_to_pcm_int16(full)
    value = struct.unpack("<h", pcm)[0]
    assert value == 32767


def test_pcm_clipping() -> None:
    over = np.array([2.0], dtype=np.float32)
    pcm = _audio_to_pcm_int16(over)
    value = struct.unpack("<h", pcm)[0]
    assert value == 32767


def test_pcm_negative() -> None:
    neg = np.array([-1.0], dtype=np.float32)
    pcm = _audio_to_pcm_int16(neg)
    value = struct.unpack("<h", pcm)[0]
    assert value == -32767


# ---------------------------------------------------------------------------
# _decode_pcm_f32_b64
# ---------------------------------------------------------------------------


def test_decode_pcm_f32_b64_roundtrip() -> None:
    original = np.array([0.5, -0.5, 1.0], dtype="<f4")
    b64 = base64.b64encode(original.tobytes()).decode()
    decoded = _decode_pcm_f32_b64(b64)
    np.testing.assert_array_almost_equal(decoded, original)


# ---------------------------------------------------------------------------
# TTSManager — init
# ---------------------------------------------------------------------------


def test_tts_manager_init_sets_voice_id() -> None:
    with patch.dict("os.environ", {"MISTRAL_API_KEY": "test-key"}):
        mgr = TTSManager(voice_id="oliver")
    assert mgr.voice_id == "oliver"


def test_tts_manager_default_voice() -> None:
    mgr = TTSManager()
    assert mgr.voice_id == "jessica"


def test_tts_manager_ref_audio(tmp_path) -> None:
    audio_file = tmp_path / "sample.wav"
    audio_file.write_bytes(b"RIFF" + b"\x00" * 40)
    mgr = TTSManager(ref_audio_path=str(audio_file))
    assert mgr._ref_audio_b64 is not None


# ---------------------------------------------------------------------------
# TTSManager — synthesis (mocked API)
# ---------------------------------------------------------------------------


def _make_stream_events(pcm_f32_samples: list[float]) -> list:
    """Create mock streaming events from float32 samples."""
    raw = struct.pack(f"<{len(pcm_f32_samples)}f", *pcm_f32_samples)
    b64 = base64.b64encode(raw).decode()

    delta = MagicMock()
    delta.event = "speech.audio.delta"
    delta.data.audio_data = b64

    done = MagicMock()
    done.event = "speech.audio.done"

    return [delta, done]


def test_voxtral_synthesis_returns_pcm() -> None:
    events = _make_stream_events([0.0] * 10)

    mock_client = MagicMock()
    mock_stream = MagicMock()
    mock_stream.__enter__ = MagicMock(return_value=iter(events))
    mock_stream.__exit__ = MagicMock(return_value=False)
    mock_client.audio.speech.complete.return_value = mock_stream

    with patch("agents.hapax_voice.tts.Mistral", return_value=mock_client):
        with patch.dict("os.environ", {"MISTRAL_API_KEY": "test-key"}):
            mgr = TTSManager(voice_id="jessica")
            result = mgr.synthesize("hello", use_case="conversation")

    assert isinstance(result, bytes)
    assert len(result) == 10 * 2  # 10 samples * int16


def test_voxtral_empty_output() -> None:
    mock_client = MagicMock()
    mock_stream = MagicMock()
    done = MagicMock()
    done.event = "speech.audio.done"
    mock_stream.__enter__ = MagicMock(return_value=iter([done]))
    mock_stream.__exit__ = MagicMock(return_value=False)
    mock_client.audio.speech.complete.return_value = mock_stream

    with patch("agents.hapax_voice.tts.Mistral", return_value=mock_client):
        with patch.dict("os.environ", {"MISTRAL_API_KEY": "test-key"}):
            mgr = TTSManager()
            result = mgr.synthesize("", use_case="conversation")

    assert result == b""


def test_voxtral_uses_ref_audio_when_set(tmp_path) -> None:
    audio_file = tmp_path / "ref.wav"
    audio_file.write_bytes(b"audio-data")

    events = _make_stream_events([0.5])
    mock_client = MagicMock()
    mock_stream = MagicMock()
    mock_stream.__enter__ = MagicMock(return_value=iter(events))
    mock_stream.__exit__ = MagicMock(return_value=False)
    mock_client.audio.speech.complete.return_value = mock_stream

    with patch("agents.hapax_voice.tts.Mistral", return_value=mock_client):
        with patch.dict("os.environ", {"MISTRAL_API_KEY": "test-key"}):
            mgr = TTSManager(ref_audio_path=str(audio_file))
            mgr.synthesize("test")

    call_kwargs = mock_client.audio.speech.complete.call_args.kwargs
    assert "ref_audio" in call_kwargs
    assert "voice_id" not in call_kwargs


def test_voxtral_missing_api_key() -> None:
    with patch.dict("os.environ", {"MISTRAL_API_KEY": ""}):
        mgr = TTSManager()
        with pytest.raises(RuntimeError, match="MISTRAL_API_KEY"):
            mgr.synthesize("hello")


def test_voxtral_client_loaded_once() -> None:
    events = _make_stream_events([0.0])
    mock_client = MagicMock()
    mock_stream = MagicMock()
    mock_stream.__enter__ = MagicMock(return_value=iter(events))
    mock_stream.__exit__ = MagicMock(return_value=False)
    mock_client.audio.speech.complete.return_value = mock_stream

    with patch("agents.hapax_voice.tts.Mistral", return_value=mock_client) as MockMistral:
        with patch.dict("os.environ", {"MISTRAL_API_KEY": "test-key"}):
            mgr = TTSManager()
            mgr.synthesize("a")
            mgr.synthesize("b")

    MockMistral.assert_called_once()
```

- [ ] **Step 2: Update test_hapax_voice_pipecat_tts.py**

Replace imports and class references. Change `KokoroTTSService` → `VoxtralTTSService`, `KOKORO_SAMPLE_RATE` → `VOXTRAL_SAMPLE_RATE`, `kokoro_voice` → `voice_id`:

```python
"""Tests for the custom Pipecat TTS service wrapping TTSManager."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from pipecat.frames.frames import TTSAudioRawFrame, TTSStartedFrame, TTSStoppedFrame

from agents.hapax_voice.pipecat_tts import VoxtralTTSService
from agents.hapax_voice.tts import VOXTRAL_SAMPLE_RATE


@pytest.fixture
def mock_tts_manager() -> MagicMock:
    mgr = MagicMock()
    mgr.synthesize.return_value = b"\x00\x01" * 100
    return mgr


class TestVoxtralTTSServiceInit:
    def test_default_sample_rate(self) -> None:
        with patch("agents.hapax_voice.pipecat_tts.TTSManager"):
            svc = VoxtralTTSService()
        assert svc._init_sample_rate == VOXTRAL_SAMPLE_RATE

    def test_custom_voice(self) -> None:
        mgr = MagicMock()
        svc = VoxtralTTSService(voice_id="oliver", tts_manager=mgr)
        assert svc._tts_manager is mgr

    def test_uses_provided_tts_manager(self, mock_tts_manager: MagicMock) -> None:
        svc = VoxtralTTSService(tts_manager=mock_tts_manager)
        assert svc._tts_manager is mock_tts_manager


class TestVoxtralTTSServiceRunTTS:
    @pytest.mark.asyncio
    async def test_yields_started_audio_stopped(self, mock_tts_manager: MagicMock) -> None:
        svc = VoxtralTTSService(tts_manager=mock_tts_manager)
        frames = []
        async for frame in svc.run_tts("hello world", "ctx-1"):
            frames.append(frame)
        assert isinstance(frames[0], TTSStartedFrame)
        assert isinstance(frames[-1], TTSStoppedFrame)
        audio_frames = [f for f in frames if isinstance(f, TTSAudioRawFrame)]
        assert len(audio_frames) >= 1
        assert audio_frames[0].sample_rate == VOXTRAL_SAMPLE_RATE
        assert audio_frames[0].num_channels == 1

    @pytest.mark.asyncio
    async def test_empty_audio_yields_no_audio_frames(self) -> None:
        mgr = MagicMock()
        mgr.synthesize.return_value = b""
        svc = VoxtralTTSService(tts_manager=mgr)
        frames = []
        async for frame in svc.run_tts("", "ctx-2"):
            frames.append(frame)
        assert isinstance(frames[0], TTSStartedFrame)
        assert isinstance(frames[-1], TTSStoppedFrame)
        audio_frames = [f for f in frames if isinstance(f, TTSAudioRawFrame)]
        assert len(audio_frames) == 0

    @pytest.mark.asyncio
    async def test_synthesis_error_yields_stopped(self) -> None:
        mgr = MagicMock()
        mgr.synthesize.side_effect = RuntimeError("API error")
        svc = VoxtralTTSService(tts_manager=mgr)
        frames = []
        async for frame in svc.run_tts("fail", "ctx-3"):
            frames.append(frame)
        assert isinstance(frames[0], TTSStartedFrame)
        assert isinstance(frames[-1], TTSStoppedFrame)
        audio_frames = [f for f in frames if isinstance(f, TTSAudioRawFrame)]
        assert len(audio_frames) == 0

    @pytest.mark.asyncio
    async def test_large_audio_chunked(self) -> None:
        mgr = MagicMock()
        mgr.synthesize.return_value = b"\x00" * (VOXTRAL_SAMPLE_RATE * 2 * 3)
        svc = VoxtralTTSService(tts_manager=mgr)
        frames = []
        async for frame in svc.run_tts("long text", "ctx-4"):
            frames.append(frame)
        audio_frames = [f for f in frames if isinstance(f, TTSAudioRawFrame)]
        assert len(audio_frames) == 3

    @pytest.mark.asyncio
    async def test_can_generate_metrics(self) -> None:
        svc = VoxtralTTSService(tts_manager=MagicMock())
        assert svc.can_generate_metrics() is True
```

- [ ] **Step 3: Update test_tts_tier_cleanup.py**

```python
"""Tests for TTS tier map after Voxtral migration."""

from agents.hapax_voice.tts import _TIER_MAP, select_tier


class TestTierMapCleanup:
    def test_no_chime_tier(self):
        assert "chime" not in _TIER_MAP

    def test_no_short_ack_tier(self):
        assert "short_ack" not in _TIER_MAP

    def test_no_confirmation_tier(self):
        assert "confirmation" not in _TIER_MAP

    def test_conversation_tier_is_voxtral(self):
        assert select_tier("conversation") == "voxtral"

    def test_notification_tier_is_voxtral(self):
        assert select_tier("notification") == "voxtral"

    def test_unknown_tier_defaults_voxtral(self):
        assert select_tier("unknown_use_case") == "voxtral"
```

- [ ] **Step 4: Update test_hapax_voice_pipeline.py**

Replace imports (lines 7-12):
```python
from agents.hapax_voice.pipeline import (
    INPUT_SAMPLE_RATE,
    _build_context,
    _build_transport,
)
from agents.hapax_voice.tts import VOXTRAL_SAMPLE_RATE
```

Replace all `KOKORO_SAMPLE_RATE` references with `VOXTRAL_SAMPLE_RATE`.

Replace `kokoro_voice="af_heart"` (line 110) with `voice_id="jessica"` in `build_pipeline_task` call.

Replace `KokoroTTSService` mock patch (line 196) with `VoxtralTTSService`.

- [ ] **Step 5: Run all tests**

Run: `cd /home/hapax/projects/hapax-council && uv run pytest tests/test_hapax_voice_tts.py tests/test_hapax_voice_pipecat_tts.py tests/hapax_voice/test_tts_tier_cleanup.py tests/test_hapax_voice_pipeline.py -v`
Expected: All PASS

- [ ] **Step 6: Commit**

```bash
git add tests/
git commit -m "test: rewrite TTS tests for Voxtral backend"
```

---

### Task 7: Update train_wake_word.py Piper flag

**Files:**
- Modify: `scripts/train_wake_word.py`

- [ ] **Step 1: Update Piper-tts usage**

The script uses `piper-tts` pip package for ~20% of wake word training samples (via `from piper import PiperVoice`). Since piper-tts is being removed:

Find the `use_piper` parameter/flag in the augmentation section and set its default to `False`, or replace the Piper TTS generation path with Voxtral. Since this is a training script run rarely:

- Comment out the piper-tts import block
- Add a note: `# piper-tts removed — use Voxtral or chatterbox for TTS augmentation`
- Ensure the script gracefully skips Piper samples when piper is unavailable (it already has a `use_piper` flag)

- [ ] **Step 2: Commit**

```bash
git add scripts/train_wake_word.py
git commit -m "chore: disable piper-tts in wake word training (removed dep)"
```

---

### Task 8: Delete Piper model file, run full test suite

**Files:**
- Delete: `~/.local/share/hapax-voice/piper-voice.onnx` (and `.onnx.json` if present)

- [ ] **Step 1: Remove Piper model files**

```bash
rm -f ~/.local/share/hapax-voice/piper-voice.onnx ~/.local/share/hapax-voice/piper-voice.onnx.json
```

- [ ] **Step 2: Run full test suite**

Run: `cd /home/hapax/projects/hapax-council && uv run pytest tests/ -q --ignore=tests/test_llm -x`
Expected: All pass. No remaining references to `piper` or `kokoro` in test imports.

- [ ] **Step 3: Run ruff**

Run: `cd /home/hapax/projects/hapax-council && uv run ruff check . && uv run ruff format --check .`
Expected: Clean

- [ ] **Step 4: Verify no stale imports**

Run: `cd /home/hapax/projects/hapax-council && grep -rn "from piper\|import piper\|import kokoro\|from kokoro" agents/ tests/ --include="*.py"`
Expected: No matches (except possibly `scripts/train_wake_word.py` which is commented out).

- [ ] **Step 5: Final commit if any cleanup needed**

```bash
git add -A
git commit -m "chore: clean up stale Piper/Kokoro references"
```
