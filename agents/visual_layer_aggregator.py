"""Visual layer signal aggregator — polls cockpit API, computes display state.

Standalone daemon. Dual-cadence polling:
  - Fast (15s): health, GPU, infrastructure
  - Slow (60s): nudges, briefing, drift, goals

Writes VisualLayerState atomically to /dev/shm/hapax-compositor/visual-layer-state.json.

Usage:
    uv run python -m agents.visual_layer_aggregator
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import time
from pathlib import Path

import httpx

from agents.visual_layer_state import (
    DisplayStateMachine,
    SignalCategory,
    SignalEntry,
    VisualLayerState,
)

log = logging.getLogger(__name__)

COCKPIT_BASE = "http://localhost:8051"
OUTPUT_DIR = Path("/dev/shm/hapax-compositor")
OUTPUT_FILE = OUTPUT_DIR / "visual-layer-state.json"
PERCEPTION_STATE_PATH = Path.home() / ".cache" / "hapax-voice" / "perception-state.json"

FAST_INTERVAL = 15  # seconds
SLOW_INTERVAL = 60  # seconds


# ── Signal Mappers ──────────────────────────────────────────────────────────


def _map_health(data: dict) -> list[SignalEntry]:
    """Map health API response to signals."""
    signals = []
    status = data.get("overall_status", "healthy")
    if status != "healthy":
        failed = data.get("failed_checks", [])
        severity = min(1.0, 0.5 + 0.1 * len(failed))
        title = f"System {status}"
        detail = ", ".join(failed[:3]) if failed else ""
        signals.append(
            SignalEntry(
                category=SignalCategory.HEALTH_INFRA,
                severity=severity,
                title=title,
                detail=detail,
                source_id="health-status",
            )
        )
    return signals


def _map_gpu(data: dict) -> list[SignalEntry]:
    """Map GPU/VRAM response to signals."""
    if not data:
        return []
    used = data.get("vram_used_mib", 0)
    total = data.get("vram_total_mib", 1)
    ratio = used / total if total > 0 else 0
    if ratio > 0.85:
        return [
            SignalEntry(
                category=SignalCategory.HEALTH_INFRA,
                severity=min(1.0, 0.6 + (ratio - 0.85) * 3),
                title=f"VRAM {ratio:.0%}",
                detail=f"{used}/{total} MiB",
                source_id="gpu-vram",
            )
        ]
    return []


def _map_nudges(data: list) -> list[SignalEntry]:
    """Map top nudges to work task signals."""
    signals = []
    for nudge in data[:3]:
        priority = nudge.get("priority", "low")
        severity_map = {"critical": 0.85, "high": 0.7, "medium": 0.4, "low": 0.2}
        signals.append(
            SignalEntry(
                category=SignalCategory.WORK_TASKS,
                severity=severity_map.get(priority, 0.3),
                title=nudge.get("title", "Nudge")[:50],
                detail=nudge.get("reason", "")[:80],
                source_id=f"nudge-{nudge.get('id', '')}",
            )
        )
    return signals


def _map_briefing(data: dict) -> list[SignalEntry]:
    """Map briefing headline to context signal."""
    if not data:
        return []
    headline = data.get("headline", "") or data.get("summary", "")
    if not headline:
        return []
    return [
        SignalEntry(
            category=SignalCategory.CONTEXT_TIME,
            severity=0.15,
            title=headline[:60],
            source_id="briefing-headline",
        )
    ]


def _map_drift(data: dict) -> list[SignalEntry]:
    """Map high-severity drift items to governance signals."""
    if not data:
        return []
    signals = []
    items = data.get("items", [])
    high_items = [i for i in items if i.get("severity", "") in ("high", "critical")]
    for item in high_items[:2]:
        signals.append(
            SignalEntry(
                category=SignalCategory.GOVERNANCE,
                severity=0.7 if item.get("severity") == "high" else 0.85,
                title=item.get("title", "Drift")[:50],
                detail=item.get("detail", "")[:80],
                source_id=f"drift-{item.get('id', '')}",
            )
        )
    return signals


def _map_goals(data: dict) -> list[SignalEntry]:
    """Map stale goals to work task signals."""
    if not data:
        return []
    signals = []
    goals = data.get("goals", [])
    stale = [g for g in goals if g.get("stale", False)]
    for goal in stale[:2]:
        signals.append(
            SignalEntry(
                category=SignalCategory.WORK_TASKS,
                severity=0.35,
                title=f"Stale: {goal.get('title', 'goal')[:40]}",
                source_id=f"goal-{goal.get('id', '')}",
            )
        )
    return signals


def _read_perception() -> dict:
    """Read perception state from filesystem."""
    try:
        if PERCEPTION_STATE_PATH.exists():
            raw = PERCEPTION_STATE_PATH.read_text()
            data = json.loads(raw)
            if time.time() - data.get("timestamp", 0) < 15:
                return data
    except (json.JSONDecodeError, OSError):
        pass
    return {}


# ── Aggregator ──────────────────────────────────────────────────────────────


class SignalAggregator:
    """Polls cockpit API, runs state machine, writes visual layer state."""

    def __init__(self, base_url: str = COCKPIT_BASE) -> None:
        self.base_url = base_url
        self.state_machine = DisplayStateMachine()
        self._fast_signals: list[SignalEntry] = []
        self._slow_signals: list[SignalEntry] = []
        self._client: httpx.AsyncClient | None = None

    async def _get(self, path: str) -> dict | list | None:
        """GET from cockpit API with error tolerance."""
        if self._client is None:
            return None
        try:
            resp = await self._client.get(f"{self.base_url}{path}", timeout=5.0)
            if resp.status_code == 200:
                return resp.json()
        except (httpx.HTTPError, json.JSONDecodeError) as exc:
            log.debug("API request failed %s: %s", path, exc)
        return None

    async def poll_fast(self) -> None:
        """Fast-cadence: health, GPU."""
        signals: list[SignalEntry] = []

        health = await self._get("/api/health")
        if isinstance(health, dict):
            signals.extend(_map_health(health))

        gpu = await self._get("/api/gpu")
        if isinstance(gpu, dict):
            signals.extend(_map_gpu(gpu))

        self._fast_signals = signals

    async def poll_slow(self) -> None:
        """Slow-cadence: nudges, briefing, drift, goals."""
        signals: list[SignalEntry] = []

        nudges = await self._get("/api/nudges")
        if isinstance(nudges, list):
            signals.extend(_map_nudges(nudges))

        briefing = await self._get("/api/briefing")
        if isinstance(briefing, dict):
            signals.extend(_map_briefing(briefing))

        drift = await self._get("/api/drift")
        if isinstance(drift, dict):
            signals.extend(_map_drift(drift))

        goals = await self._get("/api/goals")
        if isinstance(goals, dict):
            signals.extend(_map_goals(goals))

        self._slow_signals = signals

    def compute_and_write(self) -> VisualLayerState:
        """Run state machine and write output atomically."""
        all_signals = self._fast_signals + self._slow_signals
        perception = _read_perception()

        flow_score = float(perception.get("flow_score", 0.0))
        audio_energy = float(perception.get("audio_energy_rms", 0.0))
        production = perception.get("production_activity", "")
        production_active = production != "" and production != "idle"

        # Check for guest/consent signals from perception
        if perception.get("guest_present", False):
            phase = perception.get("consent_phase", "")
            severity = 0.6 if phase == "consent_pending" else 0.45
            all_signals.append(
                SignalEntry(
                    category=SignalCategory.GOVERNANCE,
                    severity=severity,
                    title=f"Guest: {phase.replace('_', ' ')}",
                    source_id="consent-guest",
                )
            )

        state = self.state_machine.tick(
            signals=all_signals,
            flow_score=flow_score,
            audio_energy=audio_energy,
            production_active=production_active,
        )

        # Atomic write
        try:
            OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            tmp = OUTPUT_FILE.with_suffix(".tmp")
            tmp.write_text(state.model_dump_json(indent=2), encoding="utf-8")
            tmp.rename(OUTPUT_FILE)
        except OSError as exc:
            log.warning("Failed to write visual layer state: %s", exc)

        return state

    async def run(self) -> None:
        """Main loop with dual-cadence polling."""
        async with httpx.AsyncClient() as client:
            self._client = client
            log.info(
                "Visual layer aggregator started (fast=%ds, slow=%ds)",
                FAST_INTERVAL,
                SLOW_INTERVAL,
            )

            slow_counter = 0
            while True:
                try:
                    await self.poll_fast()

                    if slow_counter == 0:
                        await self.poll_slow()

                    state = self.compute_and_write()
                    log.debug(
                        "State: %s, signals: %d, opacities: %s",
                        state.display_state,
                        sum(len(s) for s in state.signals.values()),
                        {k: f"{v:.2f}" for k, v in state.zone_opacities.items() if v > 0},
                    )

                    slow_counter = (slow_counter + 1) % (SLOW_INTERVAL // FAST_INTERVAL)
                    await asyncio.sleep(FAST_INTERVAL)
                except asyncio.CancelledError:
                    break
                except Exception:
                    log.exception("Aggregator tick failed")
                    await asyncio.sleep(FAST_INTERVAL)

            self._client = None


# ── Entry point ─────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(description="Visual layer signal aggregator")
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--base-url", default=COCKPIT_BASE)
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

    aggregator = SignalAggregator(base_url=args.base_url)
    try:
        asyncio.run(aggregator.run())
    except KeyboardInterrupt:
        log.info("Aggregator stopped")


if __name__ == "__main__":
    main()
