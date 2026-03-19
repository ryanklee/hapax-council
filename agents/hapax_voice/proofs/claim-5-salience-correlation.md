# Claim 5: Salience Activation Correlates with Response Properties

## Prediction
Higher `activation_score` from the salience router correlates positively
(r ≥ 0.3) with response length and `context_anchor_success`.

## Null Hypothesis
r ≈ 0 — activation score has no measurable effect on response behavior.
If confirmed, the HOPE claim that salience injection modulates responses
is falsified.

## Metric
- Primary: Pearson r between activation_score and response token count
- Secondary: Pearson r between activation_score and context_anchor_success

## Design
Correlation analysis across ≥50 turns with valid activation scores.
Run via `eval_grounding.py` after sufficient data collection.

## Pre-Registration Date
2026-03-19
