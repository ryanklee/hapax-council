# Echo Cancellation Calibration Methodology

Measurement and calibration procedure for the three-layer echo discrimination stack (speexdsp AEC, energy-ratio classifier, adaptive VAD thresholds) operating in a studio environment with Blue Yeti USB mic, PreSonus Studio 24c → studio monitors, no headphones.

## 1. Signal Environment Model

The mic signal during TTS playback contains three components, each with distinct energy characteristics:

```
mic_signal = acoustic_echo + room_reverb_tail + ambient_noise
```

After speexdsp AEC:
```
aec_output = attenuated_echo + reverb_residual + ambient_noise
```

The energy classifier and adaptive VAD operate on `aec_output`. Their thresholds must separate:
- **Echo frames**: `aec_output` where attenuated echo dominates (reject)
- **Speech frames**: operator speech (accept, even during TTS)
- **Silent frames**: ambient noise floor (pass through, VAD handles)

## 2. Instrumentation: Per-Frame Metrics

### 2.1 What to Log

Add a passive telemetry logger to `audio_loop` that records per-frame metrics without altering behavior. Each row = one 30ms frame (480 samples at 16kHz).

| Field | Type | Source | Purpose |
|-------|------|--------|---------|
| `ts` | float | `time.monotonic()` | Temporal ordering |
| `mic_rms_raw` | float | `_rms_int16(frame)` before AEC | Raw echo energy |
| `mic_rms_aec` | float | `_rms_int16(frame)` after AEC | Attenuated echo energy |
| `aec_attenuation_db` | float | `20*log10(raw/aec)` | AEC effectiveness per frame |
| `tts_ref_rms` | float | `tracker.expected_energy()` | TTS playback energy (resampled to 16k) |
| `vad_prob` | float | Silero output | VAD score on this frame |
| `energy_class` | str | `classifier.classify()` | Current classification (speech/echo/silent) |
| `system_speaking` | bool | `tracker.is_active()` | TTS active or in decay window |
| `tts_ended_ago_ms` | float | `(now - last_record_at) * 1000` | Time since TTS stopped |
| `operator_speaking` | bool | `conversation_buffer.speech_active` | VAD-detected operator speech |

### 2.2 Logger Implementation

```python
"""Echo calibration telemetry — passive, zero-behavior-change instrumentation."""

import csv
import logging
import math
import os
import time
from pathlib import Path

log = logging.getLogger(__name__)

_CALIBRATION_DIR = Path.home() / "hapax-state" / "echo-calibration"
_FIELDS = [
    "ts", "mic_rms_raw", "mic_rms_aec", "aec_attenuation_db",
    "tts_ref_rms", "vad_prob", "energy_class", "system_speaking",
    "tts_ended_ago_ms", "operator_speaking",
]


class EchoCalibrationLogger:
    """Append-only CSV logger for echo calibration data.

    Creates one file per session. Writes are buffered (flush every 100 rows).
    Enable via env var: HAPAX_ECHO_CALIBRATION=1
    """

    def __init__(self) -> None:
        self._enabled = os.environ.get("HAPAX_ECHO_CALIBRATION", "") == "1"
        self._writer: csv.DictWriter | None = None
        self._file = None
        self._row_count = 0
        if self._enabled:
            _CALIBRATION_DIR.mkdir(parents=True, exist_ok=True)
            path = _CALIBRATION_DIR / f"session-{int(time.time())}.csv"
            self._file = open(path, "w", newline="")
            self._writer = csv.DictWriter(self._file, fieldnames=_FIELDS)
            self._writer.writeheader()
            log.info("Echo calibration logging to %s", path)

    def record(
        self,
        mic_rms_raw: float,
        mic_rms_aec: float,
        tts_ref_rms: float,
        vad_prob: float,
        energy_class: str,
        system_speaking: bool,
        tts_ended_ago_ms: float,
        operator_speaking: bool,
    ) -> None:
        if not self._enabled or self._writer is None:
            return
        if mic_rms_raw > 0 and mic_rms_aec > 0:
            atten = 20 * math.log10(mic_rms_raw / mic_rms_aec)
        else:
            atten = 0.0
        self._writer.writerow({
            "ts": f"{time.monotonic():.4f}",
            "mic_rms_raw": f"{mic_rms_raw:.1f}",
            "mic_rms_aec": f"{mic_rms_aec:.1f}",
            "aec_attenuation_db": f"{atten:.1f}",
            "tts_ref_rms": f"{tts_ref_rms:.1f}",
            "vad_prob": f"{vad_prob:.4f}",
            "energy_class": energy_class,
            "system_speaking": system_speaking,
            "tts_ended_ago_ms": f"{tts_ended_ago_ms:.0f}",
            "operator_speaking": operator_speaking,
        })
        self._row_count += 1
        if self._row_count % 100 == 0:
            self._file.flush()

    def close(self) -> None:
        if self._file:
            self._file.close()
```

### 2.3 Integration Point

In `run_loops.py:audio_loop`, after the AEC process step and before the energy classifier, capture both raw and AEC'd RMS. The logger call sits alongside existing code, changing no control flow:

```python
# After: frame = daemon._echo_canceller.process(frame)
# Capture both for calibration (raw was the pre-AEC frame)
if daemon._echo_cal_logger is not None:
    daemon._echo_cal_logger.record(
        mic_rms_raw=_rms_int16(raw_frame),  # frame before AEC
        mic_rms_aec=_rms_int16(frame),      # frame after AEC
        tts_ref_rms=_tts_tracker.expected_energy() if _tts_tracker else 0.0,
        vad_prob=daemon.presence._latest_vad_confidence,
        energy_class=...,  # classify result from existing code
        system_speaking=_tts_tracker.is_active() if _tts_tracker else False,
        tts_ended_ago_ms=...,
        operator_speaking=daemon._conversation_buffer.speech_active,
    )
```

This requires saving the pre-AEC frame before the `daemon._echo_canceller.process(frame)` call on line 48 of `run_loops.py`:

```python
raw_frame = frame  # snapshot before AEC
if daemon._echo_canceller is not None:
    frame = daemon._echo_canceller.process(frame)
```

## 3. Data Collection Protocol

### 3.1 Required Scenarios

Each scenario must be collected separately and labeled:

| Scenario | Duration | What it measures |
|----------|----------|-----------------|
| **A: Room silence** | 2 min | Ambient noise floor (mic_rms baseline) |
| **B: TTS only** | 5 min (multiple utterances) | Echo energy distribution (raw + attenuated) |
| **C: Operator speech only** | 3 min (natural talking) | Speech energy distribution |
| **D: Operator speech during TTS** | 3 min (talk over system) | Separation between echo and speech during overlap |
| **E: Post-TTS decay** | Captured naturally in B | Reverb tail decay after TTS stops |

### 3.2 Minimum Data Requirements

At 16kHz, 30ms frames = ~33 frames/second.

| Scenario | Frames needed | Time | Rationale |
|----------|--------------|------|-----------|
| A | 4000 | 2 min | Stable noise floor estimate (>100 independent samples after 40-frame averaging) |
| B | 10000 | 5 min | Multiple TTS utterances (>10) with varying content/loudness. Need distribution tails. |
| C | 6000 | 3 min | Capture operator speech at various volumes (quiet, normal, loud). |
| D | 6000 | 3 min | Hardest scenario. Need >5 barge-in events with clear ground truth. |

Total: ~13 minutes of active data collection across 3-5 voice sessions.

### 3.3 Ground Truth Labeling

For scenarios B and D, ground truth comes from temporal correlation:
- **Echo frames**: `system_speaking=True AND operator_speaking=False`
- **Speech-during-TTS frames**: `system_speaking=True AND operator_speaking=True` (operator must consciously speak during TTS for D)
- **Clean speech frames**: `system_speaking=False AND operator_speaking=True`
- **Silent frames**: `system_speaking=False AND operator_speaking=False`

For offline validation, the `operator_speaking` flag from VAD is imperfect (it is what we are trying to calibrate). The more reliable signal: in scenario B, the operator stays silent (all non-silent frames are echo). In scenario C, TTS is never playing (all non-silent frames are speech). Scenario D requires manual annotation or a physical push-to-talk button held during operator speech.

## 4. Analysis: Computing Calibrated Thresholds

### 4.1 Analysis Script

```python
"""Analyze echo calibration data and compute thresholds.

Usage: uv run python scripts/analyze_echo_calibration.py ~/hapax-state/echo-calibration/
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd


def load_sessions(cal_dir: Path) -> pd.DataFrame:
    frames = []
    for f in sorted(cal_dir.glob("session-*.csv")):
        df = pd.read_csv(f)
        df["session"] = f.stem
        frames.append(df)
    return pd.concat(frames, ignore_index=True)


def analyze(df: pd.DataFrame) -> dict:
    results = {}

    # --- Noise floor (ambient) ---
    silent = df[(~df["system_speaking"]) & (~df["operator_speaking"])]
    results["ambient_rms_p50"] = silent["mic_rms_aec"].quantile(0.50)
    results["ambient_rms_p95"] = silent["mic_rms_aec"].quantile(0.95)
    results["ambient_rms_p99"] = silent["mic_rms_aec"].quantile(0.99)

    # --- Echo energy (system speaking, operator silent) ---
    echo = df[(df["system_speaking"]) & (~df["operator_speaking"])]
    results["echo_rms_raw_p50"] = echo["mic_rms_raw"].quantile(0.50)
    results["echo_rms_raw_p95"] = echo["mic_rms_raw"].quantile(0.95)
    results["echo_rms_aec_p50"] = echo["mic_rms_aec"].quantile(0.50)
    results["echo_rms_aec_p95"] = echo["mic_rms_aec"].quantile(0.95)
    results["echo_rms_aec_p99"] = echo["mic_rms_aec"].quantile(0.99)
    results["echo_vad_p50"] = echo["vad_prob"].quantile(0.50)
    results["echo_vad_p95"] = echo["vad_prob"].quantile(0.95)
    results["echo_vad_p99"] = echo["vad_prob"].quantile(0.99)
    results["aec_attenuation_median_db"] = echo["aec_attenuation_db"].quantile(0.50)

    # --- Speech energy (operator speaking, system silent) ---
    speech = df[(~df["system_speaking"]) & (df["operator_speaking"])]
    results["speech_rms_p05"] = speech["mic_rms_aec"].quantile(0.05)
    results["speech_rms_p25"] = speech["mic_rms_aec"].quantile(0.25)
    results["speech_rms_p50"] = speech["mic_rms_aec"].quantile(0.50)
    results["speech_vad_p05"] = speech["vad_prob"].quantile(0.05)
    results["speech_vad_p25"] = speech["vad_prob"].quantile(0.25)

    # --- Post-TTS reverb decay ---
    post_tts = df[
        (~df["system_speaking"])
        & (~df["operator_speaking"])
        & (df["tts_ended_ago_ms"] > 0)
        & (df["tts_ended_ago_ms"] < 3000)
    ]
    if len(post_tts) > 0:
        # Group by 100ms bins and compute mean RMS
        post_tts = post_tts.copy()
        post_tts["bin_ms"] = (post_tts["tts_ended_ago_ms"] // 100) * 100
        decay = post_tts.groupby("bin_ms")["mic_rms_aec"].mean()
        results["reverb_decay_profile"] = decay.to_dict()
        # Find when energy drops below 2x ambient
        ambient_2x = results["ambient_rms_p95"] * 2
        settled_bins = decay[decay < ambient_2x]
        if len(settled_bins) > 0:
            results["reverb_settle_ms"] = int(settled_bins.index[0])
        else:
            results["reverb_settle_ms"] = 3000  # hasn't settled in 3s

    return results


def compute_thresholds(r: dict) -> dict:
    """Derive calibrated thresholds from measured distributions."""
    thresholds = {}

    # _SILENCE_THRESHOLD: must be above ambient p99 to avoid
    # classifying noise as signal, but below quiet speech p05.
    # Use ambient p99 + 20% margin.
    thresholds["_SILENCE_THRESHOLD"] = r["ambient_rms_p99"] * 1.2
    thresholds["_SILENCE_THRESHOLD_rationale"] = (
        f"ambient p99={r['ambient_rms_p99']:.0f} × 1.2"
    )

    # _ECHO_RATIO_CEILING: the ratio mic_rms/tts_rms that separates
    # echo from speech. Echo frames should have ratio < ceiling,
    # speech should have ratio > ceiling.
    # Set ceiling at echo_p95_ratio + margin so 95% of echo is caught.
    # This requires computing the ratio distribution — use raw stats as proxy.
    # Conservative: if echo_aec_p95 / tts_ref median < 2.0, then 2.0 works.
    # The current 1.5 may be too tight or too loose — data will tell.
    thresholds["_ECHO_RATIO_CEILING"] = "COMPUTE FROM RATIO DISTRIBUTION"

    # _SPEECH_FLOOR_DURING_TTS: minimum RMS for mic signal to be
    # classified as speech during TTS. Must be above echo_aec_p99
    # (reject all echo) but below speech_p05 (accept quiet speech).
    thresholds["_SPEECH_FLOOR_DURING_TTS"] = r["echo_rms_aec_p99"] * 1.1
    thresholds["_SPEECH_FLOOR_rationale"] = (
        f"echo_aec p99={r['echo_rms_aec_p99']:.0f} × 1.1, "
        f"speech p05={r.get('speech_rms_p05', 'N/A')}"
    )

    # Adaptive VAD threshold during system speech:
    # Must be above echo_vad_p99 to reject echo.
    # Current: 0.8. Data may show this can be lowered.
    thresholds["vad_during_tts"] = min(0.95, r["echo_vad_p99"] + 0.05)
    thresholds["vad_during_tts_rationale"] = (
        f"echo_vad p99={r['echo_vad_p99']:.4f} + 0.05 margin"
    )

    # Post-TTS window: how long to maintain elevated VAD threshold
    thresholds["post_tts_window_ms"] = r.get("reverb_settle_ms", 500)
    thresholds["post_tts_window_rationale"] = (
        f"energy settles to <2× ambient at {r.get('reverb_settle_ms', '?')}ms"
    )

    return thresholds


def print_report(r: dict, t: dict) -> None:
    print("=" * 60)
    print("ECHO CALIBRATION REPORT")
    print("=" * 60)

    print("\n--- Room Characteristics ---")
    print(f"  Ambient noise floor (RMS):  p50={r['ambient_rms_p50']:.0f}  p95={r['ambient_rms_p95']:.0f}  p99={r['ambient_rms_p99']:.0f}")
    print(f"  AEC attenuation:            median={r['aec_attenuation_median_db']:.1f} dB")

    print("\n--- Echo Energy (after AEC) ---")
    print(f"  RMS:   p50={r['echo_rms_aec_p50']:.0f}  p95={r['echo_rms_aec_p95']:.0f}  p99={r['echo_rms_aec_p99']:.0f}")
    print(f"  VAD:   p50={r['echo_vad_p50']:.4f}  p95={r['echo_vad_p95']:.4f}  p99={r['echo_vad_p99']:.4f}")

    print("\n--- Operator Speech Energy ---")
    print(f"  RMS:   p05={r['speech_rms_p05']:.0f}  p25={r['speech_rms_p25']:.0f}  p50={r['speech_rms_p50']:.0f}")
    print(f"  VAD:   p05={r['speech_vad_p05']:.4f}  p25={r['speech_vad_p25']:.4f}")

    sep = r.get("speech_rms_p05", 0) / max(r.get("echo_rms_aec_p99", 1), 1)
    print(f"\n--- Separation ---")
    print(f"  speech_p05 / echo_p99 = {sep:.2f}x  {'(GOOD >2x)' if sep > 2 else '(MARGINAL)' if sep > 1.2 else '(OVERLAPPING — problem)'}")

    if "reverb_settle_ms" in r:
        print(f"\n--- Reverb Decay ---")
        print(f"  Settles to <2× ambient at: {r['reverb_settle_ms']}ms after TTS ends")

    print(f"\n--- Calibrated Thresholds ---")
    for k, v in t.items():
        if not k.endswith("_rationale"):
            rationale = t.get(f"{k}_rationale", "")
            print(f"  {k} = {v}  ({rationale})")

    # Separation warning
    if sep < 1.5:
        print("\n⚠ WARNING: Echo and speech energy distributions overlap.")
        print("  Energy classifier alone cannot separate them.")
        print("  Mitigation options:")
        print("    1. Increase AEC tail_ms (currently in config)")
        print("    2. Reduce monitor volume")
        print("    3. Reposition mic (closer to operator, further from monitors)")
        print("    4. Rely more heavily on adaptive VAD threshold")


if __name__ == "__main__":
    cal_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.home() / "hapax-state" / "echo-calibration"
    df = load_sessions(cal_dir)
    print(f"Loaded {len(df)} frames from {df['session'].nunique()} sessions")
    r = analyze(df)
    t = compute_thresholds(r)
    print_report(r, t)
```

### 4.2 Threshold Derivation Method

The core statistical principle: **set each threshold at the boundary between two distributions with a safety margin**.

For the energy classifier's three thresholds:

**`_SILENCE_THRESHOLD`** (currently 300.0):
- Measure: ambient noise RMS distribution
- Threshold = `ambient_p99 × 1.2`
- Validation: >99% of ambient frames fall below; <5% of quiet speech frames fall below

**`_ECHO_RATIO_CEILING`** (currently 1.5):
- Measure: `mic_rms_aec / tts_ref_rms` during echo-only frames
- Threshold = `echo_ratio_p95 + 0.2` margin
- Validation: >95% of echo frames have ratio below ceiling; >95% of speech-during-TTS frames have ratio above ceiling

**`_SPEECH_FLOOR_DURING_TTS`** (currently 1000.0):
- Measure: echo_rms_aec distribution (upper tail) vs speech_rms_aec distribution (lower tail)
- Threshold = `echo_rms_aec_p99 × 1.1`
- Validation: >99% of echo frames fall below; check what percentage of speech frames fall above (this is the false-negative rate for barge-in detection)

**Adaptive VAD threshold** (currently 0.8):
- Measure: Silero VAD probability on echo frames
- Threshold = `echo_vad_p99 + 0.05`
- Validation: >99% of echo frames produce VAD below threshold; check operator speech VAD during TTS exceeds threshold

**Post-TTS window** (currently 500ms):
- Measure: time for post-TTS RMS to decay below `2 × ambient_p95`
- Threshold = measured decay time rounded up to nearest 100ms
- Validation: no echo frames misclassified as speech after window expires

### 4.3 Ratio Distribution Analysis

The echo ratio ceiling requires computing the actual ratio distribution, not just raw RMS stats. Add to the analysis script:

```python
def compute_ratio_distributions(df: pd.DataFrame) -> dict:
    """Compute mic_rms/tts_rms ratio distributions for echo vs speech."""
    echo = df[(df["system_speaking"]) & (~df["operator_speaking"])]
    echo_ratios = echo["mic_rms_aec"] / echo["tts_ref_rms"].clip(lower=1.0)

    speech_during = df[(df["system_speaking"]) & (df["operator_speaking"])]
    if len(speech_during) > 0:
        speech_ratios = speech_during["mic_rms_aec"] / speech_during["tts_ref_rms"].clip(lower=1.0)
    else:
        speech_ratios = pd.Series(dtype=float)

    return {
        "echo_ratio_p50": echo_ratios.quantile(0.50),
        "echo_ratio_p95": echo_ratios.quantile(0.95),
        "echo_ratio_p99": echo_ratios.quantile(0.99),
        "speech_ratio_p05": speech_ratios.quantile(0.05) if len(speech_ratios) > 0 else None,
        "speech_ratio_p25": speech_ratios.quantile(0.25) if len(speech_ratios) > 0 else None,
    }
```

The ceiling should sit between `echo_ratio_p99` and `speech_ratio_p05`. If these overlap, the ratio metric alone is insufficient and the system must rely on the absolute `_SPEECH_FLOOR_DURING_TTS` as a secondary gate (which is what the current `classify()` already does with the AND condition).

## 5. Offline Validation (Replay)

Before deploying calibrated thresholds, validate them against collected data by replaying frames through the classifier with new thresholds.

```python
def validate_thresholds(
    df: pd.DataFrame,
    silence_threshold: float,
    echo_ratio_ceiling: float,
    speech_floor: float,
    vad_threshold: float,
) -> dict:
    """Replay collected frames through classifier with proposed thresholds.

    Returns confusion matrix counts.
    """
    # Ground truth labels from scenarios
    echo_gt = df[(df["system_speaking"]) & (~df["operator_speaking"])]
    speech_gt = df[(~df["system_speaking"]) & (df["operator_speaking"])]
    speech_during_tts_gt = df[(df["system_speaking"]) & (df["operator_speaking"])]

    results = {"echo_frames": len(echo_gt), "speech_frames": len(speech_gt)}

    # Echo frames: how many are correctly classified as echo?
    echo_correct = 0
    for _, row in echo_gt.iterrows():
        rms = row["mic_rms_aec"]
        if rms < silence_threshold:
            echo_correct += 1  # silent = correctly suppressed
            continue
        tts = max(row["tts_ref_rms"], 1.0)
        ratio = rms / tts
        if ratio < echo_ratio_ceiling and rms < speech_floor:
            echo_correct += 1
    results["echo_correctly_rejected"] = echo_correct
    results["echo_rejection_rate"] = echo_correct / max(len(echo_gt), 1)

    # Echo frames: how many have VAD below threshold?
    echo_vad_ok = (echo_gt["vad_prob"] < vad_threshold).sum()
    results["echo_vad_rejection_rate"] = echo_vad_ok / max(len(echo_gt), 1)

    # Speech frames during TTS: how many are correctly passed?
    if len(speech_during_tts_gt) > 0:
        speech_passed = 0
        for _, row in speech_during_tts_gt.iterrows():
            rms = row["mic_rms_aec"]
            if rms >= silence_threshold:
                tts = max(row["tts_ref_rms"], 1.0)
                ratio = rms / tts
                if ratio >= echo_ratio_ceiling or rms >= speech_floor:
                    speech_passed += 1
        results["speech_during_tts_acceptance_rate"] = speech_passed / len(speech_during_tts_gt)

    # Clean speech: all should pass (sanity check)
    clean_passed = (speech_gt["mic_rms_aec"] >= silence_threshold).sum()
    results["clean_speech_pass_rate"] = clean_passed / max(len(speech_gt), 1)

    return results
```

### 5.1 Acceptance Criteria

Run validation against the full dataset. Thresholds are acceptable when:

| Metric | Target | Rationale |
|--------|--------|-----------|
| `echo_rejection_rate` | >0.99 | <1% of echo frames leak through energy classifier |
| `echo_vad_rejection_rate` | >0.99 | <1% of echo frames exceed adaptive VAD threshold |
| `clean_speech_pass_rate` | >0.99 | Energy classifier does not eat normal speech |
| `speech_during_tts_acceptance_rate` | >0.80 | Barge-in detection works (some loss acceptable) |

## 6. Gate-Removal Criteria

The current system has two implicit gates that suppress audio:

1. **Energy classifier gate** (run_loops.py line 67-73): Frames classified as "echo" are not fed to `conversation_buffer.feed_audio()`.
2. **Adaptive VAD gate** (conversation_buffer.py line 150-163): During system speech, VAD threshold is raised to 0.8, requiring sustained high-confidence speech detection.

These gates are the *defense* against the system hearing itself. They should remain active until calibration proves they are correctly tuned. Gate removal means: the gate is still present, but the thresholds are calibrated rather than guessed, and the data proves the gate correctly discriminates.

### 6.1 Gate Confidence Levels

| Condition | Action |
|-----------|--------|
| Validation shows `echo_rejection_rate > 0.99` AND `clean_speech_pass_rate > 0.99` | Energy classifier thresholds are calibrated. Deploy to production. |
| Validation shows `echo_vad_rejection_rate > 0.99` AND `speech_during_tts_acceptance_rate > 0.80` | Adaptive VAD threshold is calibrated. Deploy to production. |
| Echo and speech energy distributions overlap (separation < 1.5x) | Energy classifier cannot fully separate. Keep both gates AND consider: reduce monitor volume, reposition mic, increase AEC tail_ms. |
| AEC attenuation < 10dB median | speexdsp is not working effectively. Debug reference alignment (latency compensation), sample rate mismatch, or reference buffer timing before tuning downstream thresholds. |

### 6.2 Iterative Refinement

If initial thresholds do not meet acceptance criteria:

1. Check AEC attenuation first. If <15dB, the upstream canceller is not doing enough work. Tune `tail_ms` (try 200, 300, 500) and `latency_frames` (try 0, 1, 2).
2. Check if echo and speech RMS distributions overlap. If they do, energy classification alone is insufficient — the system must rely on the VAD layer.
3. If VAD echo scores are high (>0.5 on echo frames), Silero is being fooled by the attenuated echo. This means the echo still sounds like speech. Increase AEC effectiveness or add spectral features.

## 7. Post-TTS Decay Measurement

The decay profile is critical for the `_post_tts_window` in `conversation_buffer.py` (currently 500ms, with threshold 0.7).

### 7.1 Measuring RT60

RT60 (time for 60dB decay) is overkill for this application. What matters is the time for the mic signal to drop below the speech detection floor after TTS stops.

From collected data, filter frames where `tts_ended_ago_ms > 0` and `operator_speaking = False`. Bin by 50ms intervals and plot mean RMS:

```python
def decay_profile(df: pd.DataFrame) -> pd.Series:
    """Return mean RMS by 50ms bins after TTS ends."""
    mask = (
        (~df["operator_speaking"])
        & (df["tts_ended_ago_ms"] > 0)
        & (df["tts_ended_ago_ms"] < 5000)
    )
    post = df[mask].copy()
    post["bin"] = (post["tts_ended_ago_ms"] // 50) * 50
    return post.groupby("bin")["mic_rms_aec"].agg(["mean", "std", "count"])
```

The `post_tts_window` should be set to the bin where `mean + 2*std < _SILENCE_THRESHOLD`.

### 7.2 Expected Room Behavior

Blue Yeti cardioid pattern + studio monitors at desk distance (~1.5m):
- Direct path echo: ~4ms (speed of sound)
- First reflection: ~10-20ms (desk, walls)
- RT60 for a treated room: 200-400ms; untreated: 500-800ms
- Post-AEC residual: much lower, but reverb tail is harder for AEC to cancel than direct path

The current 500ms post-TTS window is likely reasonable for a studio room but may need to be 800-1000ms for an untreated room. Data will resolve this.

## 8. Implementation Sequence

1. **Implement `EchoCalibrationLogger`** as a new module in `agents/hapax_daimonion/`.
2. **Wire into `audio_loop`** with the pre-AEC frame capture. Activate via `HAPAX_ECHO_CALIBRATION=1` env var.
3. **Collect data**: Run 3-5 normal voice sessions with calibration enabled. Sessions should include both system-initiated speech and operator-initiated conversations. ~15 minutes total.
4. **Run analysis script** to compute distributions and proposed thresholds.
5. **Run validation script** on collected data with proposed thresholds.
6. **If validation passes**: Update `_SILENCE_THRESHOLD`, `_ECHO_RATIO_CEILING`, `_SPEECH_FLOOR_DURING_TTS` in `energy_classifier.py` and the adaptive VAD thresholds in `conversation_buffer.py`. Move thresholds to `DaimonionConfig` so they are tunable without code changes.
7. **If validation fails**: Diagnose per §6.2, iterate.
8. **Ongoing**: Leave calibration logger available. Re-run after hardware changes (mic position, monitor volume, room treatment).
