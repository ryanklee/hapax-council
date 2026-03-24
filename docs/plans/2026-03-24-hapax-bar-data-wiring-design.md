# Hapax Bar — Data Wiring Design

**Date:** 2026-03-24
**Status:** Design
**Scope:** Wire missing data sources into the dual-bar architecture

## Problem

The bars render but are data-blind beyond stimmung stance. They ignore activity, flow, engine health, governance, nudges, drift, and biometric connectivity. The horizon shows static text; it should reflect temporal urgency and pending actions.

## New Data: Stimmung Reader

Already-read files, just extract more fields:

| Field | Source | Type |
|-------|--------|------|
| `activity_label` | visual-layer-state | str ("idle"/"coding"/"creative"/"reading") |
| `flow_score` | perception-state | float 0-1 |
| `interruptibility` | perception-state | float 0-1 |
| `activity_mode` | perception-state | str |

## New Data: API Polls

| Endpoint | Key Fields | Poll Rate |
|----------|-----------|-----------|
| `/api/engine/status` | `errors: int` | 30s |
| `/api/governance/heartbeat` | `score: float`, `label: str` | 60s |
| `/api/nudges` | `len(): int` | 60s |
| `/api/drift` | `drift_count: int` | 300s |

## Horizon Additions

1. **Activity label** — dim text after window title ("· coding"). Hidden when idle.
2. **Nudge badge** — colored dot + count (●3). Hidden when 0. Green 1-5, amber 6-10, red 11+.
3. **Flow → temporal ribbon** — flow_score modulates ribbon brightness (preattentive, no number).

## Bedrock Additions

1. **Engine errors → gradient** — errors > 0 warms health region of stimmung field.
2. **Governance → gradient** — new position at 0.85 (fuchsia §3.3). Low score = fuchsia tint.
3. **Drift → gradient** — count > 10 = amber at system_state position.
4. **Watch indicator** — 4px green dot bottom-right of stimmung field when biometrics flowing.

## Seam Additions

**Horizon seam**: nudge list (top 7, act/dismiss), readiness summary, briefing age.
**Bedrock seam**: engine panel (events/errors/uptime), governance panel (score/issues), drift summary.

## Scope

~260 new lines across ~10 files. No new widgets except NudgeBadge (35 lines) and 3 seam panels (~50 lines each).
