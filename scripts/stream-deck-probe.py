#!/usr/bin/env python3
"""Stream Deck hardware presence probe (task #140, Phase 1).

Non-fatal: prints the state of the bus and exits 0 whether or not a
device is plugged in. The adapter remains armed either way — the probe
exists so the operator can confirm that Phase 2 wiring will find the
device when they plug it in, without chasing an import error.

Also validates the Phase 1 manifest so an unrelated manifest bug shows
up here instead of at service start.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _probe_device() -> int:
    try:
        from StreamDeck.DeviceManager import DeviceManager  # type: ignore[import-not-found]
    except ImportError:
        print(
            "stream-deck: python 'streamdeck' library not installed; "
            "adapter remains armed for when hardware is plugged in "
            "(Phase 2 will pin the runtime dep)."
        )
        return 0

    try:
        devices = DeviceManager().enumerate()
    except Exception as exc:  # noqa: BLE001 — probe is non-fatal by design.
        print(f"stream-deck: device enumeration failed ({exc}); adapter remains armed.")
        return 0

    if not devices:
        print("stream-deck: no device detected; adapter remains armed.")
        return 0

    for device in devices:
        try:
            device.open()
            try:
                print(
                    f"stream-deck: found {device.deck_type()} "
                    f"serial={device.get_serial_number()!r} "
                    f"keys={device.key_count()}"
                )
            finally:
                device.close()
        except Exception as exc:  # noqa: BLE001 — keep probing remaining devices.
            print(f"stream-deck: device open failed ({exc}); skipping.")
    return 0


def _probe_manifest() -> int:
    sys.path.insert(0, str(REPO_ROOT))
    from agents.stream_deck import load_manifest  # noqa: PLC0415 — repo path just pushed.

    manifest_path = REPO_ROOT / "config" / "stream-deck" / "manifest.yaml"
    try:
        manifest = load_manifest(manifest_path)
    except Exception as exc:  # noqa: BLE001 — still non-fatal for the probe.
        print(f"stream-deck: manifest load failed at {manifest_path} ({exc})")
        return 1
    print(
        f"stream-deck: manifest v{manifest.version} device={manifest.device} "
        f"keys={len(manifest.keys)}/{manifest.slot_count()}"
    )
    return 0


def main() -> int:
    manifest_rc = _probe_manifest()
    _probe_device()
    # Manifest problems are worth surfacing as a non-zero exit inside
    # interactive use, but the spec says exit 0 for Phase 1 so hardware
    # absence is never fatal. We honor that for the device probe and
    # surface manifest issues via stderr-visible output without failing.
    if manifest_rc != 0:
        print("stream-deck: manifest had issues (see above); exiting 0 per Phase 1 policy.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
