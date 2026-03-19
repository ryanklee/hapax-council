# Claim 1: Stable Frame Improves Context Anchoring

## Prediction
The conversation thread injected into the system prompt will increase
`context_anchor_success` scores from baseline by ≥0.15 on sessions with
5+ turns.

## Null Hypothesis
`context_anchor_success` scores are equal across baseline (no thread)
and intervention (thread active) conditions.

## Metric
- Primary: `context_anchor_success` (Langfuse, per-turn, float 0-1)
- Secondary: operator acceptance rate (ACCEPT/CLARIFY/IGNORE/REJECT)

## Design
SCED A-B-A with ≥10 sessions per phase. Minimum 5 turns per session.

## Pre-Registration Date
2026-03-19
