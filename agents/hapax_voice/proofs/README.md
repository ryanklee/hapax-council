# Conversational Continuity Proofs

Pre-registered hypotheses and validation artifacts for the conversational
continuity design (DESIGN-conversational-continuity.md).

## Structure

Each claim gets a directory:
```
claim-N/
  hypothesis.md    — prediction, null, metric, design, date
  design.md        — detailed experiment design (after baseline)
  data/            — raw Langfuse exports and session logs
  analysis/        — scripts and results
```

## Claims

| # | Claim | Status |
|---|-------|--------|
| 1 | Stable frame improves context_anchor_success | pre-registered |
| 2 | Simple message drop maintains reference_accuracy | pre-registered |
| 3 | Cross-session memory enables recall of prior sessions | pre-registered |
| 4 | Sentinel fact survives system prompt rebuilds | pre-registered |
| 5 | Salience activation correlates with response depth | pre-registered |

## Methodology

Single-Case Experimental Design (SCED) with A-B-A reversal:
- Phase A (baseline): measurement only, no interventions
- Phase B (intervention): stable frame + compression + memory active
- Phase A' (reversal): interventions disabled, measurement continues

Use `~/.cache/hapax/voice-experiment.json` to set condition:
```json
{"name": "continuity-v1", "condition": "A", "phase": "baseline"}
```
