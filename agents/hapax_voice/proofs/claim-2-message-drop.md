# Claim 2: Simple Message Drop Maintains Reference Accuracy

## Prediction
Replacing LLMLingua-2 lossy compression with simple message dropping
(keep system + last 5 turns) will maintain `reference_accuracy` ≥0.8
on sessions with 10+ turns, while the conversation thread compensates
for dropped context.

## Null Hypothesis
`reference_accuracy` degrades significantly (≤0.6) when older messages
are dropped without compression.

## Metric
- Primary: `reference_accuracy` (Langfuse, per-turn, float 0-1)
- Secondary: operator clarification requests (CLARIFY acceptance type)

## Design
SCED A-B with ≥10 sessions exceeding 10 turns each.

## Pre-Registration Date
2026-03-19
