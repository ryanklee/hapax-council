"""Vendored apperception tick for the agents package.

Copied from shared/apperception_tick.py. Standalone self-observation loop.
Reads events from shm-based subsystems (temporal bands, corrections,
stimmung) and feeds them through the ApperceptionCascade.

All inputs come from the filesystem — no in-process state dependencies.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path

from agents._apperception import ApperceptionCascade, CascadeEvent, SelfModel

log = logging.getLogger("apperception_tick")

# ── Paths ────────────────────────────────────────────────────────────────────

TEMPORAL_FILE = Path("/dev/shm/hapax-temporal/bands.json")
STIMMUNG_FILE = Path("/dev/shm/hapax-stimmung/state.json")
CORRECTION_FILE = Path("/dev/shm/hapax-compositor/activity-correction.json")
APPERCEPTION_DIR = Path("/dev/shm/hapax-apperception")
APPERCEPTION_FILE = APPERCEPTION_DIR / "self-band.json"
APPERCEPTION_CACHE_DIR = Path.home() / ".cache" / "hapax-apperception"
APPERCEPTION_CACHE_FILE = APPERCEPTION_CACHE_DIR / "self-model.json"


class ApperceptionTick:
    """Standalone apperception tick — reads shm, runs cascade, writes shm.

    All inputs from the filesystem. No in-process state dependencies.
    Can be driven by any tick loop (aggregator, daemon, or standalone).
    """

    def __init__(self) -> None:
        self._cascade = self._load_model()
        self._prev_stimmung_stance: str = "nominal"
        self._last_save: float = 0.0
        self._last_correction_ts: float = 0.0  # dedup corrections

    def tick(self) -> None:
        """Run one apperception cycle. Call this every 3-5 seconds."""
        stance = self._read_stimmung_stance()
        events = self._collect_events(stance)

        pending_actions: list[str] = []
        for event in events:
            result = self._cascade.process(event, stimmung_stance=stance)
            if result and result.action:
                pending_actions.append(result.action)

        self._write_shm(pending_actions)

        now = time.monotonic()
        if now - self._last_save >= 300.0:
            self.save_model()
            self._last_save = now

    def save_model(self) -> None:
        """Persist self-model to cache. Call on shutdown."""
        try:
            APPERCEPTION_CACHE_DIR.mkdir(parents=True, exist_ok=True)
            data = self._cascade.model.to_dict()
            tmp = APPERCEPTION_CACHE_FILE.with_suffix(".tmp")
            tmp.write_text(json.dumps(data), encoding="utf-8")
            tmp.rename(APPERCEPTION_CACHE_FILE)
        except OSError:
            log.debug("Failed to persist self-model", exc_info=True)

    @property
    def model(self) -> SelfModel:
        return self._cascade.model

    # ── Event collection (all from filesystem) ───────────────────────

    def _collect_events(self, stance: str) -> list[CascadeEvent]:
        events: list[CascadeEvent] = []

        # Read temporal file ONCE (C6: prevent contradictory events)
        temporal_data = None
        try:
            temporal_data = json.loads(TEMPORAL_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass

        # 1. Surprise from temporal bands
        if temporal_data is not None:
            ts = temporal_data.get("timestamp", 0)
            if (time.time() - ts) <= 30:
                surprise = temporal_data.get("max_surprise", 0.0)
                if surprise > 0.3:
                    events.append(
                        CascadeEvent(
                            source="prediction_error",
                            text=f"temporal surprise {surprise:.2f}",
                            magnitude=min(surprise, 1.0),
                        )
                    )

        # 2. Operator corrections (dedup by timestamp)
        try:
            corr = json.loads(CORRECTION_FILE.read_text(encoding="utf-8"))
            corr_ts = corr.get("timestamp", 0)
            elapsed = time.time() - corr_ts
            if elapsed < 10 and corr_ts > self._last_correction_ts:
                self._last_correction_ts = corr_ts
                events.append(
                    CascadeEvent(
                        source="correction",
                        text=f"operator corrected: {corr.get('label', 'unknown')}",
                        magnitude=0.7,
                    )
                )
        except Exception:
            pass

        # 3. Stimmung transition
        if stance != self._prev_stimmung_stance:
            stances = ["nominal", "cautious", "degraded", "critical"]
            try:
                improving = stances.index(stance) < stances.index(self._prev_stimmung_stance)
            except ValueError:
                improving = False
            events.append(
                CascadeEvent(
                    source="stimmung_event",
                    text=f"stance: {self._prev_stimmung_stance} → {stance}",
                    magnitude=0.5,
                    metadata={"direction": "improving" if improving else "degrading"},
                )
            )
            self._prev_stimmung_stance = stance

        # 4. Perception staleness (reuse temporal_data — mutually exclusive with surprise)
        if temporal_data is not None:
            perception_age = time.time() - temporal_data.get("timestamp", 0)
            if perception_age > 30.0:
                events.append(
                    CascadeEvent(
                        source="absence",
                        text=f"perception stale ({perception_age:.0f}s)",
                        magnitude=min(perception_age / 120.0, 1.0),
                    )
                )

        return events

    # ── Filesystem I/O ───────────────────────────────────────────────

    def _read_stimmung_stance(self) -> str:
        try:
            raw = json.loads(STIMMUNG_FILE.read_text(encoding="utf-8"))
            return raw.get("overall_stance", "nominal")
        except Exception:
            return "nominal"

    def _write_shm(self, pending_actions: list[str]) -> None:
        try:
            payload = {
                "self_model": self._cascade.model.to_dict(),
                "pending_actions": pending_actions,
                "timestamp": time.time(),
            }
            APPERCEPTION_DIR.mkdir(parents=True, exist_ok=True)
            tmp = APPERCEPTION_FILE.with_suffix(".tmp")
            tmp.write_text(json.dumps(payload), encoding="utf-8")
            tmp.rename(APPERCEPTION_FILE)
        except OSError:
            log.debug("Failed to write apperception state", exc_info=True)

    def _load_model(self) -> ApperceptionCascade:
        model = SelfModel()
        try:
            if APPERCEPTION_CACHE_FILE.exists():
                data = json.loads(APPERCEPTION_CACHE_FILE.read_text(encoding="utf-8"))
                model = SelfModel.from_dict(data)
                log.info("Loaded self-model from cache (%d dimensions)", len(model.dimensions))
        except Exception:
            log.debug("Failed to load self-model cache, starting fresh", exc_info=True)
        return ApperceptionCascade(self_model=model)
