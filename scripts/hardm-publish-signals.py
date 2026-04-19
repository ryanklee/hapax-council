#!/usr/bin/env python3
"""HARDM signal publisher — writes cell values to SHM.

Reads each primary HARDM signal's canonical source (perception-state,
narrative-state, stimmung, consent, active homage package, etc.) and
emits a single JSON payload at
``/dev/shm/hapax-compositor/hardm-cell-signals.json`` for the HARDM
consumer (``HardmDotMatrix``) to read on each Cairo tick.

This is a stub — not every canonical source is yet plumbed. Missing
values are written as ``null`` so the consumer renders them idle
(except ``consent_gate`` which fails closed to stress, per spec §3).

Run as one-shot via systemd timer or cron. Fast, stateless, atomic
tmp+rename write.

Spec: ``docs/superpowers/specs/2026-04-18-hardm-dot-matrix-design.md``.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any

log = logging.getLogger("hardm-publish-signals")

OUT_FILE = Path("/dev/shm/hapax-compositor/hardm-cell-signals.json")

# Canonical input paths — stubbed, read best-effort.
_PERCEPTION_STATE = Path("/dev/shm/hapax-daimonion/perception-state.json")
_NARRATIVE_STATE = Path("/dev/shm/hapax-director/narrative-state.json")
_STIMMUNG_STATE = Path("/dev/shm/hapax-daimonion/stimmung-state.json")
_DEGRADED_FLAG = Path("/dev/shm/hapax-compositor/degraded.flag")
_UNIFORMS_JSON = Path("/dev/shm/hapax-imagination/uniforms.json")
_HOMAGE_ACTIVE = Path("/dev/shm/hapax-compositor/homage-active.json")


def _read_json(path: Path) -> dict[str, Any]:
    try:
        if not path.exists():
            return {}
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        log.debug("failed to read %s", path, exc_info=True)
        return {}


def _read_flag(path: Path) -> bool:
    try:
        return path.exists() and path.stat().st_size >= 0
    except Exception:
        return False


def _watch_hr_bucket(bpm: float | None) -> float | None:
    """Bucket watch HR into 0.0/0.33/0.66/1.0 bands (rest → elevated)."""
    if bpm is None:
        return None
    if bpm < 55:
        return 0.33
    if bpm < 75:
        return 0.66
    if bpm < 95:
        return 0.33
    return 1.0


def _collect_signals() -> dict[str, Any]:
    """Collect the 16 primary HARDM signals from their canonical sources."""
    perception = _read_json(_PERCEPTION_STATE)
    narrative = _read_json(_NARRATIVE_STATE)
    stimmung = _read_json(_STIMMUNG_STATE)
    uniforms = _read_json(_UNIFORMS_JSON)
    homage_active = _read_json(_HOMAGE_ACTIVE)

    signals: dict[str, Any] = {}

    # timing family
    signals["midi_active"] = bool(perception.get("midi_active"))

    # operator family
    signals["vad_speech"] = bool(perception.get("vad_speech"))
    signals["watch_hr"] = _watch_hr_bucket(perception.get("watch_hr_bpm"))
    signals["bt_phone"] = bool(perception.get("bt_phone_connected"))
    signals["kde_connect"] = bool(perception.get("phone_kde_connected"))
    signals["screen_focus"] = bool(perception.get("desktop_active"))

    # perception family
    room_count = perception.get("room_occupancy_count")
    if isinstance(room_count, (int, float)):
        # Level-3 bucketing: 0 → idle, 1 → 0.5, 2+ → 1.0.
        if room_count <= 0:
            signals["room_occupancy"] = 0.0
        elif room_count == 1:
            signals["room_occupancy"] = 0.5
        else:
            signals["room_occupancy"] = 1.0
    else:
        signals["room_occupancy"] = None

    signals["ir_person_detected"] = bool(perception.get("ir_person_detected"))

    ambient = perception.get("ambient_sound_level")
    if isinstance(ambient, (int, float)):
        signals["ambient_sound"] = float(max(0.0, min(1.0, ambient)))
    else:
        signals["ambient_sound"] = None

    # cognition family
    signals["director_stance"] = str(narrative.get("stance") or "").lower() or None
    stim_energy = stimmung.get("energy") or stimmung.get("stimmung_energy")
    if isinstance(stim_energy, (int, float)):
        signals["stimmung_energy"] = float(max(0.0, min(1.0, stim_energy)))
    else:
        signals["stimmung_energy"] = None

    shader_energy = uniforms.get("signal.homage_custom_4_0")
    if isinstance(shader_energy, (int, float)):
        signals["shader_energy"] = float(max(0.0, min(1.0, shader_energy)))
    else:
        signals["shader_energy"] = None

    reverie_pass = uniforms.get("signal.reverie_pass")
    if isinstance(reverie_pass, (int, float)):
        # Normalise: 8 passes → 0..1.
        signals["reverie_pass"] = float(max(0.0, min(1.0, reverie_pass / 8.0)))
    else:
        signals["reverie_pass"] = None

    # governance family
    consent_state = _consent_state()
    signals["consent_gate"] = consent_state

    signals["degraded_stream"] = _read_flag(_DEGRADED_FLAG)

    pkg_name = homage_active.get("package")
    signals["homage_package"] = pkg_name if isinstance(pkg_name, str) else None

    return signals


def _consent_state() -> str | None:
    """Return consent state string or ``None``. Best-effort import."""
    try:
        from shared.consent import ConsentRegistry

        registry = ConsentRegistry()
        # ConsentRegistry API varies; we just test for any active contract.
        has_active = bool(getattr(registry, "list_active", lambda: [])())
        return "ok" if has_active else "blocked"
    except Exception:
        return None


def publish(signals: dict[str, Any]) -> None:
    """Atomic tmp+rename write."""
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": time.time(),
        "signals": signals,
    }
    tmp = OUT_FILE.with_suffix(OUT_FILE.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, default=str), encoding="utf-8")
    os.replace(tmp, OUT_FILE)


def main() -> int:
    logging.basicConfig(
        level=os.environ.get("HARDM_PUBLISH_LOG_LEVEL", "WARNING"),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    signals = _collect_signals()
    publish(signals)
    return 0


if __name__ == "__main__":
    sys.exit(main())
