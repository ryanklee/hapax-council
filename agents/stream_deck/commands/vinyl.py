"""Vinyl rate preset handler for the Stream Deck (task #142, PR C).

Wires the ``VINYL 45`` / ``VINYL 33`` keys on the shipped #140 manifest
(and the ``vinyl <preset>`` KDEConnect grammar from #141) to the
compositor's vinyl playback rate SHM file at
``/dev/shm/hapax-compositor/vinyl-playback-rate.txt``. Writes are
atomic (tmp + rename) so concurrent readers never observe a partial
value.

Presets:
    ``45-on-33`` → 0.741  (45 RPM disc on 33⅓ setting)
    ``33``      → 1.0    (standard 33⅓ playback)
    ``45``      → 1.0    (standard 45 playback — the deck's own pitch)
    ``custom:<float>`` → ``float(<float>)``, bounded to [0.25, 2.0]

Invalid presets (unknown name, unparseable custom float, out-of-range
custom float) raise :class:`VinylRatePresetError`, which the adapter's
error path converts into a structured log entry — the SHM file is
left untouched so the previous rate stays authoritative.
"""

from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path
from typing import Any

from shared.telemetry import hapax_event, hapax_span

log = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────

VINYL_RATE_COMMAND = "audio.vinyl.rate_preset"
"""Command-registry name the manifest + KDEConnect grammar dispatch under."""

RATE_FILE: Path = Path("/dev/shm/hapax-compositor/vinyl-playback-rate.txt")
"""Canonical SHM authority for the vinyl playback rate.

Kept in sync with :data:`shared.vinyl_rate._RATE_FILE`; readers consult
``shared.vinyl_rate.read_vinyl_playback_rate()`` rather than reading
this path directly.
"""

# Fixed presets. The operator's Korg Handytrax-PLAY has three positions;
# 45-on-33 is the only non-unit playback we ship bindings for today.
# Additional discrete presets can be added here without touching
# callers, the test suite, or the manifest.
_PRESET_RATES: dict[str, float] = {
    "45-on-33": 0.741,
    "33": 1.0,
    "45": 1.0,
}

_CUSTOM_PREFIX = "custom:"
_MIN_RATE = 0.25
_MAX_RATE = 2.0


# ── Errors ─────────────────────────────────────────────────────────────────


class VinylRatePresetError(ValueError):
    """Raised when a preset string cannot be resolved to a valid rate."""


# ── Preset resolution ──────────────────────────────────────────────────────


def resolve_rate(preset: str) -> float:
    """Return the numeric playback rate for ``preset``.

    Raises :class:`VinylRatePresetError` on unknown preset names,
    unparseable ``custom:<float>`` payloads, and out-of-range custom
    floats. Callers that persist the rate (e.g. :func:`handle_vinyl_rate_preset`)
    rely on this function to reject bad input before any SHM write.
    """
    if not isinstance(preset, str) or not preset:
        raise VinylRatePresetError(f"preset must be a non-empty string: {preset!r}")

    if preset in _PRESET_RATES:
        return _PRESET_RATES[preset]

    if preset.startswith(_CUSTOM_PREFIX):
        payload = preset[len(_CUSTOM_PREFIX) :].strip()
        try:
            rate = float(payload)
        except ValueError as exc:
            raise VinylRatePresetError(f"custom vinyl rate is not a float: {payload!r}") from exc
        if not (_MIN_RATE <= rate <= _MAX_RATE):
            raise VinylRatePresetError(
                f"custom vinyl rate {rate} outside bounds [{_MIN_RATE}, {_MAX_RATE}]"
            )
        return rate

    raise VinylRatePresetError(f"unknown vinyl preset: {preset!r}")


# ── Handler ────────────────────────────────────────────────────────────────


def handle_vinyl_rate_preset(
    args: dict[str, Any],
    *,
    rate_file: Path | None = None,
) -> float:
    """Dispatch target for ``audio.vinyl.rate_preset`` commands.

    Resolves ``args["preset"]`` to a numeric rate via :func:`resolve_rate`
    and atomically writes it to the compositor's SHM rate authority.
    Returns the persisted rate so callers can log / telemetry.

    Invalid presets raise :class:`VinylRatePresetError`; the SHM file
    is left untouched in that case (previous rate stays authoritative).

    ``rate_file`` override lets the test suite redirect writes into
    ``tmp_path``; production callers pass ``None`` to use :data:`RATE_FILE`.
    """
    preset = args.get("preset")
    if not isinstance(preset, str):
        raise VinylRatePresetError(
            f"audio.vinyl.rate_preset requires 'preset' str arg; got {args!r}"
        )

    with hapax_span(
        "control",
        "stream_deck.vinyl_preset",
        metadata={"preset": preset},
    ):
        try:
            rate = resolve_rate(preset)
        except VinylRatePresetError as exc:
            log.error(
                "stream-deck vinyl preset rejected: preset=%s reason=%s",
                preset,
                exc,
            )
            hapax_event(
                "control",
                "stream_deck.vinyl_preset.rejected",
                metadata={"preset": preset, "reason": str(exc)},
            )
            raise

        target = rate_file if rate_file is not None else RATE_FILE
        _atomic_write_rate(target, rate)
        log.info(
            "stream-deck vinyl preset: preset=%s rate=%.4f file=%s",
            preset,
            rate,
            target,
        )
        hapax_event(
            "control",
            "stream_deck.vinyl_preset.applied",
            metadata={"preset": preset, "rate": f"{rate:.4f}"},
        )
        return rate


def _atomic_write_rate(path: Path, rate: float) -> None:
    """Write ``rate`` to ``path`` via a sibling tmp file + ``os.replace``.

    The compositor polls the file from a different process; partial
    writes would corrupt its cached rate. ``os.replace`` on the same
    filesystem is atomic per POSIX, so readers see either the old or
    the new contents, never a half-written value.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_fd, tmp_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
    )
    try:
        with os.fdopen(tmp_fd, "w") as fh:
            fh.write(f"{rate:.6f}\n")
        os.replace(tmp_name, path)
    except Exception:
        # Tmp file may or may not exist depending on where we failed;
        # best-effort cleanup so we don't leak SHM tmpfs space.
        Path(tmp_name).unlink(missing_ok=True)
        raise
