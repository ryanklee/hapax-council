# Research-to-Plan Triage — 2026-04-20

**Author:** delta
**Scope:** inventory every 2026-04-20 research drop against the
spec→plan→implement queue. Flag gaps. Surface the next action per item.

## Method

1. Enumerate `docs/research/2026-04-20-*.md` (46 docs).
2. Check each for an existing plan at `docs/superpowers/plans/*.md` or
   spec at `docs/superpowers/specs/*.md`.
3. Cross-reference against TaskList (as of this commit, tasks
   #164–#191 for April 20 work).
4. Categorise: **Shipped**, **In flight**, **Queued (plan exists,
   implementation pending)**, **Unqueued (plan-stub needed)**,
   **Deferred / operator-driven**, **Reference only**.

Ownership uses the alpha/delta split from
`~/.cache/hapax/relay/alpha-to-delta-queue-ack-20260420.yaml`:
alpha = compositor/wards/HARDM, delta = daimonion/voice/audio/research.

---

## §1. Delta-zone research

| # | Research doc | State | Plan reference | Next action |
|---|---|---|---|---|
| 1 | voice-transformation-tier-spectrum | **In flight** | 2026-04-19-voice-modulation-phase-1-plan | Phase 5 queued |
| 2 | voice-tier-director-integration | **In flight** | (same) | Phase 3b (director_loop wire) pending alpha zone |
| 3 | mode-d-voice-tier-mutex | **In flight** | Phase 1 + Phase 2 shipped (b27758c79, e1da54fae) | Phase 3 (director_loop counters) queued |
| 4 | unified-audio-architecture-design | **Unqueued** | — | **Ship stub plan `2026-04-20-unified-audio-architecture-plan.md`** |
| 5 | dual-fx-routing-design | **Unqueued** | — | **Ship stub plan `2026-04-20-dual-fx-routing-plan.md`** |
| 6 | evil-pet-factory-presets-midi | **Unqueued** | — | **Ship stub plan `2026-04-20-evil-pet-preset-pack-plan.md`** |
| 7 | fx-firmware-upgrade-procedures | **Deferred** | (doc is the plan; operator-driven) | Operator runs per research doc steps |
| 8 | audio-normalization-ducking-strategy | **Blocked** | — | Unblock LADSPA syntax research first; then plan |
| 9 | evil-pet-cc-exhaustive-map | **Reference** | — | Keep as lookup |
| 10 | vinyl-broadcast-signal-chain-topology | **Unqueued** | — | Plan (operator-owned signal chain; delta wires the software side) |

## §2. Alpha-zone research (noted — plans belong to alpha)

| # | Research doc | State | Next action per alpha ACK |
|---|---|---|---|
| 11 | livestream-halt-investigation | Partial (Phase 1 watchdog 9b85da3e6 shipped) | Alpha Phase 2 pending |
| 12 | dead-bridge-modules-audit (11+6) | Inventory only | Alpha remediation plan missing |
| 13 | cbip-1-name-cultural-lineage | Pending operator decision | CBIP branding plan |
| 14 | v4l2sink-stall-prevention | Phase 1 shipped (df6629f43 watchdog) | Phase 2+ plan missing |
| 15 | homage-scrim-1-algorithmic-intelligence | Unqueued | **Alpha scrim framework plan missing — 6 docs, substantial** |
| 16 | homage-scrim-2-disorientation-aesthetics | Unqueued | (same) |
| 17 | homage-scrim-3-nebulous-scrim-architecture | Unqueued | (same) |
| 18 | homage-scrim-4-fishbowl-spatial-conceit | Unqueued | (same) |
| 19 | homage-scrim-5-choreographer-audio-coupled-motion | Unqueued | (same) |
| 20 | homage-scrim-6-ward-inventory-integration | Unqueued | (same) |
| 21 | nebulous-scrim-design | Unqueued (task #174) | Alpha plan |
| 22 | chat-keywords-ward-design (task #180) | Queued via orphan-ward-producers-plan | Alpha |
| 23 | notification-loopback-leak-fix | Shipped (task #187) | — |
| 24 | retire-effect-shuffle-design (task #175) | Unqueued | Alpha plan |
| 25 | self-censorship-aesthetic-design (task #173) | Shipped | — |
| 26 | prompt-level-slur-prohibition-design | Unqueued | Alpha plan |
| 27 | mixquality-skeleton-design | Unqueued | Alpha plan |
| 28 | grounding-provenance-invariant-fix | Unqueued | Alpha plan |
| 29 | tauri-decommission-freed-resources | Likely-deferred | Alpha check |
| 30 | logos-output-quality-design (tasks #176/177) | Unqueued | Alpha plan |

Alpha's ack queue covers items 11–14 through the current HARDM+notif+Wave-B
sequence; items 15–30 need alpha's own plan-creation sweep. This triage
surfaces the gap — alpha picks the sequencing.

## §3. Shared / vinyl-broadcast family (operator-authored context)

| # | Research doc | Zone | Action |
|---|---|---|---|
| 31 | vinyl-broadcast-calibration-telemetry | alpha (compositor telemetry) | Plan TBD |
| 32 | vinyl-broadcast-ethics-scene-norms | both (governance) | Feeds into consent/monetization gate — already wired via `monetization_safety.py` |
| 33 | vinyl-broadcast-mode-b-turntablist-craft | operator-authored | Reference |
| 34 | vinyl-broadcast-mode-d-granular-instrument | delta + alpha | Covered by mode-d-voice-tier-mutex plan |
| 35 | vinyl-broadcast-programme-splattribution | alpha (ward system) | Shipped (task #127) |
| 36 | vinyl-broadcast-signal-chain-topology | delta | See §1 entry |
| 37 | vinyl-collection-livestream-broadcast-safety | governance | Feeds MonetizationRiskGate |

## §4. Audit-family research (covered by audit-closeout-plan)

| # | Research doc | Consumed by |
|---|---|---|
| 38 | audit-synthesis-final | 2026-04-20-audit-closeout-plan |
| 39 | audit-synthesis | 2026-04-20-audit-closeout-plan |
| 40 | dynamic-audit-synthesis-final | 2026-04-20-audit-closeout-plan |
| 41 | dynamic-livestream-audit-catalog | 2026-04-20-audit-closeout-plan |
| 42 | livestream-audit-catalog | 2026-04-20-audit-closeout-plan |
| 43 | wiring-audit-alpha | 2026-04-20-audit-closeout-plan |
| 44 | wiring-audit-findings | 2026-04-20-audit-closeout-plan |
| 45 | ward-full-audit-alpha | 2026-04-20-audit-closeout-plan |
| 46 | hardm-aesthetic-rehab | Shipped (task #181) |
| 47 | finding-v-deploy-status | In flight (task #178 producers plan) |

---

## §5. Delta's outstanding plan stubs shipped alongside this triage

- `2026-04-20-unified-audio-architecture-plan.md` — topology CLI + validator + migration
- `2026-04-20-dual-fx-routing-plan.md` — S-4 USB-direct path + DSP assignability
- `2026-04-20-evil-pet-preset-pack-plan.md` — SD-card `.evl` pack with `midi_receive_cc: true`

Each stub names the research references, the implementation phases,
and the blocking dependencies (firmware, operator decisions) so the
next delta-owned work cycle can pick up a concrete next action
without re-deriving scope.

## §6. Recommendation to alpha

Create a single alpha triage pass over items 15–30 in §2 above. The
HOMAGE-SCRIM family (items 15–20, 6 research docs) is the largest
unplanned cluster in the workspace. Without a scrim-framework plan
it risks sitting as "research only" for another session cycle.

## §7. Tracking

Add-to-queue tasks to create after shipping this triage:

- delta: Unified audio topology CLI implementation (research #4)
- delta: Dual-FX S-4 USB-direct PipeWire retarget (research #5)
- delta: Evil Pet `.evl` preset pack + loader (research #6)
- delta: Vinyl broadcast signal-chain software wiring (research #36)

These are added as TaskCreate entries with the delta owner tag.
