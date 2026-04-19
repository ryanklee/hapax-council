"""Rode Wireless Pro detection + auto-routing adapter.

Polls PipeWire's node list every 5 s for a Rode Wireless Pro receiver.
When present, becomes the authoritative voice source; on disappear,
falls back to the Blue Yeti (room mic). State is surfaced to the
daimonion STT side through ``/dev/shm/hapax-compositor/voice-source.txt``
— a single-line tag (``rode`` | ``yeti`` | ``contact-mic``) that the
``stt_source_resolver`` reads live (5 s cache). No daimonion restart is
ever required; the adapter runs as its own systemd user unit and the
resolver picks up the value on its next sample.

Task #133 follow-on to the spec 2026-04-18 audio pathways audit.
"""

from __future__ import annotations

import argparse
import logging
import re
import subprocess
import sys
import time
from pathlib import Path

log = logging.getLogger("hapax.rode_wireless_adapter")

# Voice-source tags written to the shared tag file. The stt_source_resolver
# reads and caches these live; no daimonion restart is required.
VOICE_SOURCE_RODE = "rode"
VOICE_SOURCE_YETI = "yeti"
VOICE_SOURCE_CONTACT_MIC = "contact-mic"
_VALID_TAGS = frozenset({VOICE_SOURCE_RODE, VOICE_SOURCE_YETI, VOICE_SOURCE_CONTACT_MIC})

# Shared-memory tag file. The compositor dir is the canonical SHM bus root
# for audio topology signals (see logos/api/routes/studio*.py).
VOICE_SOURCE_DIR = Path("/dev/shm/hapax-compositor")
VOICE_SOURCE_PATH = VOICE_SOURCE_DIR / "voice-source.txt"

# Polling cadence for the pw-cli probe. 5 s is fast enough for "plug in the
# lavalier and start talking" to feel responsive without thrashing PipeWire.
_POLL_INTERVAL_S = 5.0

# Match either the vendor or the product string in pw-cli output. Rode's
# PipeWire node.description / node.name varies by firmware; the two tokens
# below cover every known identifier for the Wireless Pro receiver.
_RODE_MATCH = re.compile(r"(?i)rode|wireless.?pro")


def _run_pw_cli_list() -> str:
    """Return the raw ``pw-cli list-objects`` output or empty on error."""
    try:
        result = subprocess.run(
            ["pw-cli", "list-objects"],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        log.debug("pw-cli probe failed: %s", exc)
        return ""
    if result.returncode != 0:
        log.debug("pw-cli returned %d: %s", result.returncode, result.stderr.strip())
        return ""
    return result.stdout


def detect_rode_present(pw_cli_output: str) -> bool:
    """Return True if any line of ``pw-cli list-objects`` matches a Rode receiver."""
    if not pw_cli_output:
        return False
    return any(_RODE_MATCH.search(line) for line in pw_cli_output.splitlines())


def write_voice_source(tag: str, path: Path = VOICE_SOURCE_PATH) -> None:
    """Atomically write the voice-source tag to the shared file."""
    if tag not in _VALID_TAGS:
        raise ValueError(f"invalid voice-source tag: {tag!r}")
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(tag + "\n", encoding="utf-8")
    tmp.replace(path)


def read_voice_source(path: Path = VOICE_SOURCE_PATH) -> str | None:
    """Read the current voice-source tag, or None if missing/invalid."""
    try:
        value = path.read_text(encoding="utf-8").strip()
    except (FileNotFoundError, OSError):
        return None
    if value not in _VALID_TAGS:
        return None
    return value


class _VoiceSourceMetric:
    """Prometheus ``hapax_voice_source{source}`` gauge wrapper.

    Pre-registers one child per valid tag so Grafana scrapes always see
    the full label set. Degrades to a no-op if ``prometheus_client`` is
    not importable (tests, CI) — the adapter must never crash because
    metrics are unavailable.
    """

    def __init__(self) -> None:
        self._gauge = None
        try:
            from prometheus_client import Gauge
        except ImportError:  # pragma: no cover — prometheus-client is a hard dep
            log.warning("prometheus_client unavailable; metric disabled")
            return
        try:
            self._gauge = Gauge(
                "hapax_voice_source",
                "Active voice input source (1 = current, 0 = inactive)",
                ["source"],
            )
        except ValueError:
            # Duplicate registration (e.g. test reload). Pull the existing
            # child collector out of the default registry instead.
            from prometheus_client import REGISTRY

            collector = REGISTRY._names_to_collectors.get("hapax_voice_source")  # noqa: SLF001
            self._gauge = collector
        if self._gauge is not None:
            for tag in _VALID_TAGS:
                self._gauge.labels(source=tag).set(0)

    def set_active(self, tag: str) -> None:
        if self._gauge is None:
            return
        for candidate in _VALID_TAGS:
            self._gauge.labels(source=candidate).set(1 if candidate == tag else 0)


class RodeWirelessAdapter:
    """Poll PipeWire, flip the voice-source tag when the Rode (dis)appears."""

    def __init__(
        self,
        *,
        poll_interval_s: float = _POLL_INTERVAL_S,
        voice_source_path: Path = VOICE_SOURCE_PATH,
        probe: callable = _run_pw_cli_list,
        metric: _VoiceSourceMetric | None = None,
    ) -> None:
        self._poll_interval_s = poll_interval_s
        self._voice_source_path = voice_source_path
        self._probe = probe
        self._metric = metric if metric is not None else _VoiceSourceMetric()
        self._last_tag: str | None = None

    def _apply(self, tag: str) -> None:
        """Write the tag to SHM + metric; log only on transitions."""
        if tag == self._last_tag:
            return
        write_voice_source(tag, self._voice_source_path)
        self._metric.set_active(tag)
        if self._last_tag is None:
            log.info("voice source initialized: %s", tag)
        else:
            log.info("voice source transition: %s -> %s", self._last_tag, tag)
        self._last_tag = tag

    def tick(self) -> str:
        """Run one poll cycle; return the tag applied."""
        present = detect_rode_present(self._probe())
        tag = VOICE_SOURCE_RODE if present else VOICE_SOURCE_YETI
        self._apply(tag)
        return tag

    def run(self) -> None:  # pragma: no cover — blocking loop
        log.info("rode-wireless-adapter running (poll=%.1fs)", self._poll_interval_s)
        while True:
            try:
                self.tick()
            except Exception:  # noqa: BLE001
                log.exception("rode-wireless-adapter tick failed")
            time.sleep(self._poll_interval_s)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Rode Wireless Pro detection adapter")
    parser.add_argument(
        "--poll-interval", type=float, default=_POLL_INTERVAL_S, help="poll interval in seconds"
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="run a single detection tick and exit (diagnostics)",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    adapter = RodeWirelessAdapter(poll_interval_s=args.poll_interval)
    if args.once:
        tag = adapter.tick()
        print(tag)
        return 0
    adapter.run()
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
