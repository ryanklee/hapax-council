#!/usr/bin/env python3
"""LRR Phase 0 item 10: capture Kokoro 82M TTS latency baseline.

Phase 5 (Hermes 3 substrate swap) needs a baseline number to compare
against when evaluating StyleTTS 2 and other GPU TTS candidates as
latency mitigation alternatives. This script captures cold-synth +
warm-synth + per-phrase timing for the Kokoro 82M CPU backend currently
in use by hapax-daimonion.

Output: ~/hapax-state/benchmarks/kokoro-latency/baseline.json

Usage:
    uv run python scripts/kokoro-baseline.py

Schema:
    {
      "timestamp": "2026-04-14T...Z",
      "git_sha": "...",
      "voice_id": "af_heart",
      "device": "cpu",
      "phrases": [
        {"text": "...", "char_count": N, "synth_ms": F, "audio_seconds": F, "rtf": F},
        ...
      ],
      "summary": {
        "phrase_count": N,
        "cold_synth_ms": F,    # first-call wall clock incl. model load
        "warm_synth_p50_ms": F,
        "warm_synth_p95_ms": F,
        "warm_synth_max_ms": F,
        "warm_rtf_p50": F,     # warm real-time factor (synth_ms / audio_ms)
        "total_audio_seconds": F
      }
    }
"""

from __future__ import annotations

import json
import statistics
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

# Fixed test phrases. Mix of short / medium / long to capture per-character
# scaling. Stable set so future runs are comparable.
_PHRASES: list[str] = [
    "Hello.",
    "The quick brown fox jumps over the lazy dog.",
    "Hapax is now running on Kokoro eighty two million for text to speech synthesis.",
    "Recursion is constitutive: the experiment is the experimenter is the instrument.",
    "Phase zero verification establishes the baseline against which Phase five will be measured.",
]

_OUTPUT_DIR = Path.home() / "hapax-state" / "benchmarks" / "kokoro-latency"
_OUTPUT_FILE = _OUTPUT_DIR / "baseline.json"
_SAMPLE_RATE_HZ = 24_000  # Kokoro 82M default output rate


def _git_sha() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except subprocess.CalledProcessError:
        return "unknown"


def _audio_seconds(pcm_bytes: bytes) -> float:
    # int16 mono → 2 bytes per sample
    return len(pcm_bytes) / 2 / _SAMPLE_RATE_HZ


def main() -> int:
    print("=== Kokoro 82M baseline ===", file=sys.stderr)
    print("Importing TTSManager...", file=sys.stderr)
    from agents.hapax_daimonion.tts import TTSManager

    # Phase 1: cold synth — fresh manager, no preload, time the first call
    # (includes model load).
    print("Cold synth (first call, includes model load)...", file=sys.stderr)
    cold_manager = TTSManager()
    t0 = time.perf_counter()
    cold_pcm = cold_manager.synthesize(_PHRASES[0])
    cold_ms = (time.perf_counter() - t0) * 1000.0
    if not cold_pcm:
        print("ERROR: Kokoro returned empty audio on cold call", file=sys.stderr)
        return 1
    print(f"  cold synth: {cold_ms:.1f} ms", file=sys.stderr)

    # Phase 2: warm synth — same manager (model loaded), measure per phrase.
    print("Warm synth (5 phrases via preloaded manager)...", file=sys.stderr)
    warm_manager = TTSManager()
    warm_manager.preload()  # explicit model load

    phrase_records: list[dict[str, object]] = []
    for phrase in _PHRASES:
        t_start = time.perf_counter()
        pcm = warm_manager.synthesize(phrase)
        synth_ms = (time.perf_counter() - t_start) * 1000.0
        audio_s = _audio_seconds(pcm)
        rtf = (synth_ms / 1000.0) / audio_s if audio_s > 0 else float("inf")
        phrase_records.append(
            {
                "text": phrase,
                "char_count": len(phrase),
                "synth_ms": round(synth_ms, 1),
                "audio_seconds": round(audio_s, 3),
                "rtf": round(rtf, 3),
            }
        )
        print(
            f"  {len(phrase):3d} chars → {synth_ms:6.1f} ms synth, {audio_s:.2f}s audio, rtf={rtf:.2f}",
            file=sys.stderr,
        )

    warm_ms_values = [float(r["synth_ms"]) for r in phrase_records]
    rtf_values = [float(r["rtf"]) for r in phrase_records if r["rtf"] != float("inf")]
    summary = {
        "phrase_count": len(phrase_records),
        "cold_synth_ms": round(cold_ms, 1),
        "warm_synth_p50_ms": round(statistics.median(warm_ms_values), 1),
        "warm_synth_p95_ms": round(
            statistics.quantiles(warm_ms_values, n=20)[18]
            if len(warm_ms_values) >= 5
            else max(warm_ms_values),
            1,
        ),
        "warm_synth_max_ms": round(max(warm_ms_values), 1),
        "warm_rtf_p50": round(statistics.median(rtf_values), 3) if rtf_values else None,
        "total_audio_seconds": round(sum(float(r["audio_seconds"]) for r in phrase_records), 3),
    }

    out = {
        "timestamp": datetime.now(UTC).isoformat(),
        "git_sha": _git_sha(),
        "voice_id": "af_heart",
        "device": "cpu",
        "backend": "kokoro-82m",
        "lrr_phase": 0,
        "lrr_phase_item": 10,
        "purpose": (
            "Phase 5 substrate swap latency baseline. Kokoro 82M CPU. Compare "
            "future GPU TTS candidates (StyleTTS 2, Bark, ChatTTS, etc.) "
            "against this number when evaluating latency mitigation."
        ),
        "phrases": phrase_records,
        "summary": summary,
    }

    _OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    _OUTPUT_FILE.write_text(json.dumps(out, indent=2) + "\n")
    print(f"\nWritten: {_OUTPUT_FILE}", file=sys.stderr)
    print(
        f"\nSummary: cold={summary['cold_synth_ms']}ms, "
        f"warm p50={summary['warm_synth_p50_ms']}ms, "
        f"warm rtf p50={summary['warm_rtf_p50']}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
