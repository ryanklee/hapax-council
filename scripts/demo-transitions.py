#!/usr/bin/env python3
"""Demo all 5 transition primitives in sequence on /dev/video42.

Phase 7 of preset-variety-plan (#166). Picks two distinct presets from
the corpus, then runs each primitive in turn from preset A → preset B
→ preset A → preset B → preset A so the operator sees each transition
applied twice (once into B, once back into A) without bias from the
preset visual differences.

Usage:
    uv run python scripts/demo-transitions.py [hold_seconds]

    hold_seconds defaults to 4 — long enough to perceive each preset
    settled before the next transition starts.

The script writes directly to /dev/shm/hapax-compositor/graph-mutation.json
via the same primitive callbacks the live ``random_mode`` loop uses, so
what you see on /dev/video42 is exactly what production will render.
"""

from __future__ import annotations

import sys
import time

from agents.studio_compositor import random_mode
from agents.studio_compositor.transition_primitives import PRIMITIVES, TRANSITION_NAMES


def main(hold_s: float = 4.0) -> int:
    presets = random_mode.get_preset_names()
    if len(presets) < 2:
        print("need at least 2 presets in the corpus to demo transitions", file=sys.stderr)
        return 2
    a_name = presets[0]
    b_name = presets[len(presets) // 2]
    a = random_mode.load_preset_graph(a_name)
    b = random_mode.load_preset_graph(b_name)
    if a is None or b is None:
        print(f"failed to load presets {a_name!r} / {b_name!r}", file=sys.stderr)
        return 2

    print(f"demo-transitions: A={a_name!r} ↔ B={b_name!r}, hold={hold_s}s")
    # Settle on A first.
    random_mode._write_mutation(a)
    time.sleep(hold_s)

    for transition_name in TRANSITION_NAMES:
        fn = PRIMITIVES[transition_name]
        print(f"  [{transition_name}] A → B")
        fn(a, b, random_mode._write_mutation)
        time.sleep(hold_s)
        print(f"  [{transition_name}] B → A")
        fn(b, a, random_mode._write_mutation)
        time.sleep(hold_s)

    print("demo-transitions: complete")
    return 0


if __name__ == "__main__":
    arg_hold = float(sys.argv[1]) if len(sys.argv) > 1 else 4.0
    sys.exit(main(arg_hold))
