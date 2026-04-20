#!/usr/bin/env -S uv run python
"""Torso S-4 base-scene writer — MIDI CC burst for Track 1 voice processing.

Writes S-4 Track 1 parameters to the HAPAX-VOX-BASE values from
docs/research/2026-04-19-evil-pet-s4-base-config.md §4 via MIDI CCs
on the Erica Synths MIDI Dispatch.

Hardware path (operator):
    MIDI: Dispatch OUT 2 → S-4 MIDI IN
          - Track 1/2/3/4 receive on MIDI ch 2/3/4/5
          - Sync in ON, Start/Stop ON, Program Change ON, CC Control ON
    Audio: L6 AUX 2 → S-4 L-in; S-4 L-out → L6 ch 6
          - Parallel path to Evil Pet (which lives on L6 AUX 1)

Scene goals (Track 1, voice-on-ch-5-AUX2-send processing path):
    - Material slot: Bypass (line-in passthrough, no Tape sampler)
    - Granular slot: Bypass (Mosaic off; voice stays intelligible)
    - Filter slot:   Ring active, tonal-only
    - Color slot:    Deform active, mild compression + drive
    - Space slot:    Vast active, delay + hall reverb

After this script runs, vocal_chain.py's S-4 CC mappings modulate
Track 1 live on top of the scene.

Hardware-only config that this script does NOT touch (device front panel):
    1. Audio input: Config → Audio → Input Mode = LINE
    2. Track 1 LINE IN = Mono In 1 (or Stereo if the menu lacks mono)
    3. Track 1 Material + Granular → Bypass (CTRL+MATERIAL, CTRL+GRANULAR)
    4. Save as Scene 1 / HAPAX-VOX-BASE for persistence across reboots
"""

from __future__ import annotations

import sys
import time

import mido

PORT_PREFIX = "MIDI Dispatch:MIDI Dispatch MIDI 1"
S4_TRACK1_CHANNEL = 1  # 0-indexed; MIDI channel 2 on the wire


# Per docs/research/2026-04-19-evil-pet-s4-base-config.md §4.
# CC numbers verified against midi.guide S-4 chart and the S-4 manual.
# Values are "clock-position" scaled to 0-127.
BASE_SCENE: list[tuple[int, int, str]] = [
    # Filter (Ring) — subtle tonal sculpting, no pitched-resonator effect.
    (79, 64, "Ring cutoff → 12 o'clock (all formants present)"),
    (80, 25, "Ring resonance → 9 o'clock (~20%, light)"),
    (81, 25, "Ring decay → 9 o'clock (short, no drone)"),
    (82, 64, "Ring pitch → centred (no tracking)"),
    (83, 38, "Ring slope → 10 o'clock (gentle)"),
    (84, 64, "Ring tone → neutral"),
    (86, 38, "Ring wet → 10 o'clock (~30%, flavour)"),
    (87, 13, "Ring waves → 8 o'clock (minimal osc injection)"),
    (88, 0, "Ring noise → 0 (no noise injection)"),
    # Color (Deform) — even dynamics + mild drive for broadcast consistency.
    (95, 38, "Deform drive → 10 o'clock (~30%, warm)"),
    (96, 76, "Deform compress → 1 o'clock (~60%, evens dynamics)"),
    (98, 0, "Deform crush → 0 (no bit reduction)"),
    (99, 64, "Deform tilt → neutral EQ"),
    (100, 0, "Deform noise → 0"),
    (103, 76, "Deform wet → 1 o'clock (~60%, doing real work)"),
    # Space (Vast) — hall-like reverb + rhythmic delay.
    (112, 50, "Vast delay amount → 11 o'clock (~40%, audible)"),
    (113, 76, "Vast delay time → 1/8D (~60% of range for dotted-eighth)"),
    (114, 38, "Vast reverb amount → 10 o'clock (~30%)"),
    (115, 76, "Vast reverb size → 1 o'clock (medium-large hall)"),
    (116, 38, "Vast delay feedback → 10 o'clock (~30%, 2-3 repeats)"),
    (117, 64, "Vast delay spread → centre (no ping-pong)"),
    (118, 76, "Vast reverb damp → 1 o'clock (~60%, keep consonants clear)"),
    (119, 50, "Vast reverb decay → 11 o'clock (~40%, ~2s tail)"),
    # Master.
    (47, 64, "Track 1 level → unity (0 dB)"),
]


def _resolve_port(mido_mod, configured: str) -> str | None:
    names = list(mido_mod.get_output_names())
    if configured in names:
        return configured
    for name in names:
        if name.rsplit(" ", 1)[0] == configured.rsplit(" ", 1)[0]:
            return name
    for name in names:
        if configured in name:
            return name
    return None


def main() -> int:
    resolved = _resolve_port(mido, PORT_PREFIX)
    if resolved is None:
        print(
            f"MIDI port {PORT_PREFIX!r} not found among {mido.get_output_names()}",
            file=sys.stderr,
        )
        return 1
    print(f"Opening MIDI port: {resolved}")
    print(f"Target: S-4 Track 1 on MIDI channel {S4_TRACK1_CHANNEL + 1}")
    with mido.open_output(resolved) as port:
        for cc, value, note in BASE_SCENE:
            port.send(
                mido.Message("control_change", channel=S4_TRACK1_CHANNEL, control=cc, value=value)
            )
            print(f"  CC{cc:3d} = {value:3d}  ({note})")
            time.sleep(0.02)
    print("S-4 Track 1 base scene written (HAPAX-VOX-BASE).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
