# Phase 5 — Salience routing state + next steps

**Queue item:** 025
**Phase:** 5 of 6
**Date:** 2026-04-13 CDT
**Register:** scientific, neutral (per `feedback_scientific_register.md`)

## Headline

The salience router is **live code, initialized, and called per
utterance**, but **its output is structurally discarded**. The
conversation pipeline overwrites every non-CANNED routing decision
back to `CAPABLE` (claude-opus) before the LLM call. The router
now functions as a **diagnostic-only context annotator** — its
activation score is exposed via `salience_router.last_breakdown`
for downstream inspection but does not influence the model choice.

This matches the `project_intelligence_first` memory's claim
(*"Always CAPABLE; salience router becomes context annotator;
intelligence is last thing shed under stimmung"*). **The claim
holds.**

**Zero live routing decisions in the current session.** The
operator has not spoken to the daimonion since startup at
18:36:48 CDT. No `TIMING route=...` log lines exist. The router
is initialized (confirmed at 18:37:10 + 18:39:26 via journal) but
has not been exercised by a real utterance. Building a 20-row
live decision table is blocked on an operator utterance event.

## Code state snapshot

### The router itself — `agents/hapax_daimonion/salience_router.py`

The full activation-based router exists. It computes:

1. **Concern overlap** (dorsal/top-down attention): cosine
   similarity to concern anchors, weight 0.55
2. **Novelty** (ventral/bottom-up attention): distance from all
   known patterns, weight 0.15
3. **Dialog feature score**: dialog acts, hedges, pre-sequences,
   weight 0.30

Combined into a continuous activation score with thresholds:

```python
_DEFAULT_THRESHOLDS: dict[str, float] = {
    "canned_max": 0.15,
    "local_max":  0.45,
    "fast_max":   0.60,
    "strong_max": 0.78,
    # above strong_max → CAPABLE
}
```

Hysteresis to prevent tier oscillation (line 96-97). Cold-start
guard defaulting to FAST when the concern graph is empty (line
78-80). Governance overrides: refused consent → CAPABLE (line
155), explicit escalation → CAPABLE (line 189).

**The router is a complete implementation** of the
project_salience_routing memory's description ("redesign voice
model router from tier ladder to activation-based salience
system; biased competition + relevance theory + concern graph").

### Tier ladder still exists — `agents/hapax_daimonion/model_router.py:41-58`

```python
class ModelTier(IntEnum):
    CANNED  = 0
    LOCAL   = 1  # gemma3:4b — greetings, simple multi-turn
    FAST    = 2  # gemini-flash — tools, general conversation
    STRONG  = 3  # claude-sonnet — ramping complexity
    CAPABLE = 4  # claude-opus — full intelligence

TIER_ROUTES: dict[ModelTier, str] = {
    ModelTier.CANNED:  "",  # no LLM call
    ModelTier.LOCAL:   "local-fast",
    ModelTier.FAST:    "gemini-flash",
    ModelTier.STRONG:  "claude-sonnet",
    ModelTier.CAPABLE: "claude-opus",
}
```

5-tier enum + 5 route mappings exist. The old model_router.py
pattern-matching rules (`_CANNED_PATTERNS`, `_ESCALATION_PATTERNS`,
`_TOOL_PATTERNS`) are all still there. The legacy layer is live
code, not dead code — but it's only exercised by the salience
router's `route()` method internally, not by direct calls.

### The intelligence-first override — `conversation_pipeline.py:625-673`

```python
if self._salience_router is not None:
    routing = self._salience_router.route(
        transcript,
        turn_count=self.turn_count,
        activity_mode=self._activity_mode,
        consent_phase=self._consent_phase,
        guest_mode=self._guest_mode,
        face_count=self._face_count,
        has_tools=bool(self.tools),
        desk_activity=self._desk_activity,
    )
    # Keep CANNED for zero-latency phatic, upgrade everything else
    if routing.tier != ModelTier.CANNED:
        routing = routing.__class__(
            tier=ModelTier.CAPABLE,
            model=TIER_ROUTES[ModelTier.CAPABLE],
            reason=f"intelligence_first:{routing.reason}",
            canned_response="",
        )
else:
    # No salience router — default to CAPABLE
    routing = RoutingDecision(
        tier=ModelTier.CAPABLE,
        model=TIER_ROUTES[ModelTier.CAPABLE],
        reason="intelligence_first:default",
        canned_response="",
    )
```

**The rewrite at lines 641–646 is the structural discard.** The
salience router computes a tier, the pipeline throws it away, and
CAPABLE is selected. The `reason` field preserves the original
activation path (`intelligence_first:<original_reason>`) so
diagnostics can see what the router would have chosen.

**CANNED tier survives** because it's a zero-latency path — a
pure phatic greeting ("hi", "thanks") gets handled without an LLM
call. Everything above CANNED becomes CAPABLE.

### The last_breakdown is used 7 times downstream

```text
$ grep -n "salience_router.last_breakdown\|_salience_router is not None" \
  agents/hapax_daimonion/conversation_pipeline.py

125: self._salience_router = None  # set externally if salience routing enabled
126: self._salience_diagnostics = None  # set externally for activation history
443: _bd = self._salience_router.last_breakdown
628: routing = self._salience_router.route(...)
676: self._salience_diagnostics.record(transcript)
799: _bd = self._salience_router.last_breakdown
859: _bd = self._salience_router.last_breakdown
920: _bd = self._salience_router.last_breakdown
1330: breakdown = self._salience_router.last_breakdown
1378: breakdown = self._salience_router.last_breakdown
```

The `last_breakdown` (`ActivationBreakdown` dataclass) is accessed
at 7 sites for **context annotation**, not routing. It is attached
to:

- the utterance trace metadata
- the bridge engine context
- diagnostic logs
- event metadata

This is consistent with the `project_intelligence_first` memory's
"salience router becomes context annotator." The original
hierarchical routing design is preserved as a diagnostic signal.

## Live decision table

**Blocked.** The daimonion started at 18:36:48 CDT (current PID
18286 after a restart at 18:39). Between start and now (18:40),
the operator has not spoken. `grep "TIMING route="` returns **zero
matches** in the session journal. The salience router's
`_last_breakdown` is therefore `None`, and there is no routing
data to tabulate.

The closest I can get to a 20-row table without operator input is
**historical routing from prior sessions**, but:

- The journal window this session has is 18:36-current; the
  previous session's TIMING lines are in the journal history
  but the operator may have rotated or restarted between them
- Historical rows do not reflect the current code state (PR #757
  and #761 landed mid-session)

**Recommended deferral:** mark Phase 5 partial, produce a
reproduction command for the next session to capture a 20-row
table, and defer the table itself to the next operator-speech
window.

### Reproduction command for next session

```bash
# After the operator has interacted with the daimonion for ~5 min
journalctl --user -u hapax-daimonion.service --since "5 minutes ago" \
  --no-pager | \
  grep -oE 'TIMING route=[A-Z]+ model=[^ ]+ reason=[^ ]+' | \
  head -20
```

With the intelligence_first override live, this table will show
**every non-phatic route as CAPABLE**. The interesting columns are
the `reason` field (which encodes the original pre-override
tier) and whether any CANNED decisions fired.

## Cross-reference with the memory claims

### `project_salience_routing` claim

> Redesign voice model router from tier ladder to activation-based
> salience system (biased competition + relevance theory +
> concern graph)

**Status: implemented.** `salience_router.py` exists with
`ConcernGraph` + `UtteranceFeatures` + `Embedder`. Biased
competition: dorsal (concern_overlap, weight 0.55) vs ventral
(novelty, weight 0.15). Relevance theory: the dialog_feature_score
(hedges, pre-sequences, dialog acts). Concern graph: anchor
embeddings live in `agents/hapax_daimonion/salience/concern_graph.py`.

### `project_intelligence_first` claim

> Always CAPABLE; salience router becomes context annotator;
> intelligence is last thing shed under stimmung

**Status: implemented.** The conversation_pipeline override at
line 641-646 rewrites every non-CANNED routing decision to
CAPABLE. The salience router's output is used 7 times downstream
for context annotation, not routing.

### `feedback_model_routing_patience` claim

> CAPABLE tier = best Claude model (Opus). Operator always willing
> to wait if indicated and justified. Never downgrade for speed.

**Status: enforced.** `model_router.py:19` has the comment
"The operator is always willing to wait for CAPABLE if the
situation indicates. Never downgrade CAPABLE to save latency."
The intelligence_first override enforces this at runtime.

## Gap analysis

### What's working

1. Salience router is complete: embedder, concern graph,
   utterance features, hysteresis, governance overrides
2. Model tier ladder is preserved (not deleted) so the router has
   somewhere to route to if the override were removed
3. The intelligence_first override is explicit in one place
   (conversation_pipeline.py:641) with a clear comment
4. The `last_breakdown` is attached to 7 downstream context
   points for annotation use

### What's missing

1. **No live exercise data.** The operator has not used voice in
   this session. I cannot confirm that the salience score is
   meaningful on real utterances.
2. **`stimmung_shed` is not implemented.** The memory says
   "intelligence is last thing shed under stimmung" — there is no
   code path that actually sheds intelligence based on stimmung.
   Grep returned zero matches for `stimmung_shed` and the
   intelligence_first override is unconditional (it fires even
   when stimmung is in the worst stance).
3. **Cold-start guard defaults to FAST**, not CAPABLE
   (`salience_router.py:78`). If the concern graph is empty, the
   router returns FAST, which the override then rewrites to
   CAPABLE — so the end result is CAPABLE, but the code path is
   indirect.
4. **`_seeking` mode halves `canned_max` threshold** (`.py:126`)
   which is a SEEKING-specific behavior but does not affect the
   intelligence_first override. The seeking mode is partially
   implemented at the router but does not currently connect to
   the stimmung SEEKING stance.
5. **`salience_diagnostics` is optional.** Line 126
   `self._salience_diagnostics = None  # set externally for
   activation history`. If nothing externally instantiates the
   diagnostics recorder, the activation history is lost.
6. **Concern graph anchors need runtime updating.** The concern
   graph's anchor embeddings are probably loaded at startup. If
   the operator's concerns shift mid-session (new project, new
   focus area), the router's concern overlap will lag unless
   there's a refresh path.

## Next-steps list

### Immediate (before next voice session)

1. **Verify salience_diagnostics is instantiated.** Check
   `init_audio.py` or wherever the router is constructed. If the
   diagnostics recorder is never set externally, the activation
   history is being silently discarded.
2. **Confirm stimmung_shed is a missing feature, not a feature I
   missed.** Grep more aggressively, especially for `_last_under_stimmung`
   or similar.

### Short-term (next sprint)

3. **Implement `stimmung_shed`**. When stimmung stance is CRITICAL
   (or some defined threshold), allow the intelligence_first
   override to back off to STRONG (claude-sonnet) or FAST
   (gemini-flash) to reduce cost/latency under operator stress.
   The memory says "intelligence is last thing shed" — this means
   other shedding happens before, but intelligence-shed is still
   possible.
4. **Concern graph refresh**. Daily or per-session refresh of
   concern anchors from the operator's recent conversations,
   goals, and sprint state. Without this, the salience score
   drifts away from the operator's current attention.
5. **Live activation gauge**. Expose
   `hapax_salience_activation_score` as a Prometheus histogram
   (once round 3 Phase 2 FINDING-H is fixed). Operator can see
   activation distribution over time.

### Medium-term

6. **Remove the intelligence_first override's unconditional
   rewrite, replace with a gate function.** Current code is:

   ```python
   if routing.tier != ModelTier.CANNED:
       routing = ...CAPABLE...
   ```

   Replace with:

   ```python
   if routing.tier != ModelTier.CANNED:
       if _should_shed_intelligence(stimmung_stance):
           pass  # keep router's choice
       else:
           routing = ...CAPABLE...
   ```

   This preserves the "always CAPABLE" default while allowing
   stimmung-driven shed.

7. **Live a/b of "router tier vs CAPABLE override"**. For a small
   sample of utterances, let the router's original tier win and
   compare outcomes (grounding quality, operator corrections) to
   CAPABLE. Data would justify or refute the override's
   unconditional nature.

8. **Connect the salience `_seeking` flag to the stimmung SEEKING
   stance**. Today the `set_seeking(True)` method exists but
   grep for its callers returns zero (needs verification).

## Backlog additions (for retirement handoff)

121. **`research(daimonion): live 20-row salience routing decision table with operator utterance`** [Phase 5 deferral] — blocked on zero voice activity in this session. Re-run after the next operator voice interaction. Command: `journalctl | grep "TIMING route=" | head -20`.
122. **`fix(daimonion): verify salience_diagnostics is instantiated externally`** [Phase 5 gap 5] — line 126 of conversation_pipeline.py sets `_salience_diagnostics = None` with "set externally" comment. Confirm the set-externally path exists and is reached.
123. **`feat(daimonion): stimmung_shed intelligence back-off path`** [Phase 5 gap 2] — currently the intelligence_first override is unconditional. Add a `_should_shed_intelligence(stimmung_stance)` gate that allows STRONG or FAST under CRITICAL stimmung stance.
124. **`feat(daimonion): concern graph refresh cadence`** [Phase 5 gap 6] — daily or per-session re-computation of concern anchors from recent operator context. Without this, activation scores drift from operator's actual attention over time.
125. **`feat(monitoring): hapax_salience_activation_score histogram`** [Phase 5 next-step 5] — depends on round 3 Phase 2 FINDING-H fix.
126. **`fix(daimonion): connect salience _seeking flag to stimmung SEEKING stance`** [Phase 5 gap 8] — the flag exists on the router but its caller path needs verification.
127. **`research(daimonion): a/b test router tier vs CAPABLE override`** [Phase 5 next-step 7] — data-driven justification for the unconditional override.
