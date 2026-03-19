# Claim 4: Sentinel Fact Survives System Prompt Rebuilds

## Prediction
A sentinel number injected at session start will be correctly retrieved
when the operator asks a probe question ("what's my favorite number?")
at any point during the session, with ≥90% accuracy.

## Null Hypothesis
System prompt rebuilds (environment/policy/salience refresh) cause the
sentinel to be lost or overwritten.

## Metric
- Primary: `sentinel_retrieval` (Langfuse, per-probe, binary 0/1)

## Design
5+ sessions with probe questions at turns 2, 5, and 10+.

## Pre-Registration Date
2026-03-19
