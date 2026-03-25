---
id: DEVIATION-015
date: 2026-03-24
phase: baseline
paths:
  - agents/hapax_voice/grounding_ledger.py
justification: |
  Two pure code-correctness fixes from the perceptual system hardening
  batch 1 review:

  H7: The IGNORE branch contained a redundant threshold comparison
  (acceptance_score >= threshold) that was logically superseded by the
  subsequent concern_overlap < 0.3 check. The threshold comparison used
  a hardcoded acceptance_score of 0.3 for IGNORE which could never
  exceed a threshold of 0.5+, making the first branch dead code. Fix
  removes the dead branch and makes the concern_overlap check the sole
  arbiter for IGNORE — no change to grounding outcomes for any valid
  input.

  M5: The effort_calibration hysteresis counter (_effort_hold_turns)
  was incorrectly reset to 0 when new_rank == current_rank (same level).
  This caused in-progress de-escalation to stall indefinitely when a
  same-rank turn occurred between two de-escalation turns, requiring
  an extra turn to complete the 2-turn hold requirement. Fix preserves
  the counter across same-rank turns so de-escalation completes in
  exactly 2 consecutive turns regardless of intervening same-rank turns.
risk: minimal — H7 fixes dead code; M5 changes hold counter arithmetic
  but not the 2-turn de-escalation policy or any experiment variable
  (grounding acceptance signals, DU state transitions, GQI formula).
approved_by: operator
---
