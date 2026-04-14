# Studio Cable Inventory

**Purpose:** LRR Phase 3 item 10 — cable hygiene pass. Identifies which cables are known-good and which are damaged/suspect. Operator fills in actual inspection data during the X670E install window (~2026-04-16).

**Status:** template / stub. This file is a placeholder that the operator completes during the physical install.

## USB cables (cameras)

| Cable | Camera | Type | Length | Known-good? | Notes |
|---|---|---|---|---|---|
| USB-A → Type-C | brio-operator | Logitech-supplied | ? | ? | Flagged by delta drop #2 H4; may be signal-integrity source of the 27.94 fps deficit |
| USB-A → Type-C | brio-room | Logitech-supplied | ? | ? | |
| USB-A → Type-C | brio-synths | Logitech-supplied | ? | ? | |
| USB-A → USB-A | c920-desk | Logitech-supplied | ? | ? | |
| USB-A → USB-A | c920-room | Logitech-supplied | ? | ? | |
| USB-A → USB-A | c920-overhead | Logitech-supplied | ? | ? | |

**Inspection checklist per cable:**

- [ ] Visual inspection: no cuts, crushed sections, exposed shielding
- [ ] Connector wiggle test: no intermittent connection
- [ ] Ferrite bead present (if original)
- [ ] Length matches run distance (no excess coil-induced noise)
- [ ] Routed away from power cables (PSU, monitor power)
- [ ] If failing: flag for replacement with known-good equivalent

## DisplayPort cables (monitors)

| Cable | From | To | Type | Known-good? | Notes |
|---|---|---|---|---|---|
| DP 1.4 | GPU 0 (5060 Ti) | Dell S2721DGF primary | ? | ? | Per `feedback_vrr_flicker.md`: vrr=0, fixed 120Hz |
| DP 1.4 | GPU 1 (3090) | Dell S2721DGF secondary | ? | ? | |

## Audio cables (studio rig)

| Cable | From | To | Type | Known-good? | Notes |
|---|---|---|---|---|---|
| XLR | Contact mic (Cortado MKIII) | PreSonus Studio 24c input 2 | Balanced 48V phantom | ? | Per Bayesian presence detection; phantom power required |
| XLR | Blue Yeti | Studio 24c input 1 | Balanced | ? | |
| TRS | Studio 24c outputs | Monitors | 1/4" balanced | ? | |

## Known-good cable inventory (spares)

| Spec | Quantity | Source | Last verified |
|---|---|---|---|
| USB 3.2 Gen 1 5Gbps A-to-C 1m | ? | ? | ? |
| USB 3.2 Gen 1 5Gbps A-to-C 2m | ? | ? | ? |
| DP 1.4 1m | ? | ? | ? |
| XLR balanced 3m | ? | ? | ? |

## References

- `~/.cache/hapax/relay/context/2026-04-14-beta-brio-operator-deep-research.md` — brio-operator deficit deep dive (H4 cable/port hypothesis)
- `docs/research/2026-04-14-brio-operator-producer-deficit.md` — delta drop #2
- LRR Phase 3 spec §"Item 10 — Cable hygiene pass"
- `livestream-performance-map` Sprint 7 F8 — original cable hygiene work item
