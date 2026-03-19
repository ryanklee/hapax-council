# Claim 3: Cross-Session Memory Enables Recall

## Prediction
With session digests persisted to episodic memory and loaded at session
start, the model will correctly reference prior session content when
asked "What were we talking about last time?" in ≥80% of test cases.

## Null Hypothesis
Without cross-session memory, the model has zero recall of prior
sessions (baseline = 0%).

## Metric
- Primary: manual probe question success rate
- Secondary: `context_anchor_success` on first 2 turns of new sessions

## Design
Paired sessions: conversation A (5+ turns), gap (5+ min), conversation B
with probe question. ≥5 pairs.

## Pre-Registration Date
2026-03-19
