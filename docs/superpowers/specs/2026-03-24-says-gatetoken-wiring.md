# Says Monad Wiring + GateToken Structural Enforcement

**Date**: 2026-03-24
**Session**: beta
**Scope**: `shared/governance/says.py`, `shared/governance/gate_token.py`, `agents/hapax_voice/conversation_pipeline.py`
**Companion to**: `2026-03-24-governance-enforcement-hardening.md`
**Prior art**: Deferred formalisms #1 (Says/DCC) and #4 (GateToken/linear discipline)

---

## Problem Statement

### Says Monad

The Says monad (`says.py`) implements principal-annotated assertions following
Abadi's DCC formalism. It records WHO authorized data, bridging to Labeled[T]
via `to_labeled()`. Currently:

- `Says.unit(speaker_principal, transcript)` is called at conversation_pipeline.py:727
- The result is stored in `self._last_says` but **never consumed**
- No tool results, screen captures, or system prompt layers carry principal attribution
- The event log has no principal/authority fields

Without Says wiring, the system cannot answer: "which principal authorized this
datum reaching the LLM?" — a question the interpersonal_transparency axiom
implicitly requires at T1 (it-backend-001: verification at ingestion boundary).

### GateToken

GateToken (`gate_token.py`) is an unforgeable proof of consent gate passage.
`require_token()` exists but is never called. Currently:

- `ConsentGatedWriter.check()` mints tokens, attaches them to `GateDecision`
- `ConsentGatedQdrant` returns inner client results, decisions are invisible to callers
- 15+ filesystem write agents write profile facts without any gate
- No code path requires a GateToken parameter for write authorization

Without token enforcement, the "single chokepoint" property is a convention,
not a structural guarantee.

---

## Constraints

1. **Voice pipeline uses plain dicts** for litellm streaming. Cannot use pydantic-ai
   message types. Says metadata cannot be embedded in message dicts sent to the LLM.

2. **Messages are bounded to 5 exchanges**. Only ThreadEntry and session digests
   persist across turns. Says metadata must attach to ThreadEntry, not messages.

3. **50+ call sites** write to Qdrant/filesystem. Changing function signatures to
   require GateToken is infeasible without cascading breakage. Context vars are the
   only non-breaking enforcement mechanism.

4. **Single-operator axiom** means the operator principal is always sovereign.
   Guest principals appear only during multi-person voice sessions.

---

## Architecture Decisions

### AD-7: Says integration via ThreadEntry + parallel metadata

**Decision**: Enrich ThreadEntry with a `principal_id: str` field to record who
made each conversational turn. Maintain a parallel `_message_attribution` list
alongside `self.messages` for per-message Says tracking within a session.

**ThreadEntry enrichment**:
```python
@dataclass
class ThreadEntry:
    turn: int
    user_text: str
    response_summary: str
    acceptance: str
    grounding_state: str
    principal_id: str = "operator"  # NEW: who made this utterance
```

ThreadEntry is the right attachment point because:
- It persists across message bounding (messages trimmed to 5, thread survives)
- It feeds session digests stored in Qdrant (cross-session memory)
- It's rendered in the system prompt (LLM sees principal context)
- It already tracks grounding_state, so principal_id is a natural peer field

**Parallel attribution list**:
```python
@dataclass(frozen=True)
class MessageAttribution:
    """Per-message Says metadata, parallel to self.messages."""
    principal_id: str
    principal_kind: str  # "sovereign" | "bound"
    authority: frozenset[str]
    data_category: str  # from tool category or "speech"
    says_created: bool  # whether Says.unit() was called

self._message_attribution: list[MessageAttribution] = []
```

This list is:
- Same length as `self.messages` (appended in parallel)
- NOT sent to the LLM (private tracking)
- Used for audit logging and consent decisions
- Discarded when messages are bounded (ephemeral)

**Where Says.unit() is called**:

| Data flow | Location | Principal | Action |
|-----------|----------|-----------|--------|
| User speech | After line 727 | `maybe_principal()` or operator | Already exists, wire to ThreadEntry |
| Tool result | Before line 1395 | Bound tool principal | Create, attribute, then filter |
| Screen capture | After line 1682 | Bound vision principal | Create for audit trail |
| System prompt layers | Not Says-wrapped | Multi-principal | Track via system prompt source map (future) |

**Tool principal creation**: Each tool gets a bound principal derived from the
operator via `delegate()`. Authority scope matches the tool's data category
from `_TOOL_CATEGORIES`.

```python
# Lazily cached per tool name
def _tool_principal(self, tool_name: str) -> Principal:
    category = _TOOL_CATEGORIES.get(tool_name, "system")
    return self._operator_principal.delegate(
        f"tool:{tool_name}",
        scope=frozenset({category}),
    )
```

Where `self._operator_principal` is the sovereign operator principal already
created in `__main__.py`.

### AD-8: GateToken enforcement via contextvars

**Decision**: Use Python `contextvars.ContextVar` to track the last gate decision
at each persistence boundary. Write sites that care about provenance can call
`last_gate_decision()` to retrieve the decision without signature changes.

**New context var** in `gate_token.py`:
```python
import contextvars

_gate_decision_var: contextvars.ContextVar[GateDecision | None] = contextvars.ContextVar(
    "gate_decision", default=None
)

def last_gate_decision() -> GateDecision | None:
    """Retrieve the most recent gate decision from context."""
    return _gate_decision_var.get()
```

**Gate sets it automatically**: ConsentGatedWriter.check() and
ConsentGatedQdrant.upsert() set the context var after every decision.
No caller changes needed.

**Audit integration**: The event log checks `last_gate_decision()` when
emitting persistence events, automatically capturing the consent trail.

**Enforcement levels**:

1. **Passive** (Phase 1): Gates set context var. Event log reads it for audit.
   No code blocks on missing tokens. This is observability.

2. **Advisory** (Phase 2): Health monitor checks that all persistence events
   have an associated gate decision in the audit log. Missing decisions produce
   drift items.

3. **Structural** (Phase 3, future): Critical write paths call
   `require_gate_decision()` which raises if no decision is in context.
   Applied incrementally to the highest-risk paths first.

This spec implements Phase 1 (passive) and Phase 2 (advisory).

### AD-9: Event log principal attribution

**Decision**: Extend the voice pipeline's EventLog to include principal and
gate decision fields on relevant events.

**Extended event fields**:
```python
# user_utterance event
{
    "type": "user_utterance",
    "principal_id": "operator",
    "principal_kind": "sovereign",
    ...
}

# tool_call event
{
    "type": "tool_call",
    "principal_id": "tool:get_calendar_today",
    "principal_kind": "bound",
    "data_category": "calendar",
    "gate_decision": "allowed",  # from context var
    ...
}
```

The event log already redacts person-adjacent data when guests lack consent.
Adding principal_id extends this to record who authorized the data flow.

---

## Scope Exclusions

- **System prompt multi-principal tracking**: The system prompt combines 6-8 context
  layers from different sources. Tracking Says per layer requires a source map that
  doesn't exist yet. Deferred to a future iteration.

- **Cross-session Says threading**: Session digests go to Qdrant. Enriching them with
  full Says metadata requires schema changes to the episodes collection. Deferred.
  Only `principal_id` (a string) travels to ThreadEntry and digests for now.

- **Filesystem write gating**: The 15+ agents that write profile facts via `open()`
  need a `ConsentGatedWriter` wrapper. This is a separate effort (filesystem-as-bus
  already has frontmatter-based consent labels; the gate should read those). Deferred.

- **Phase 3 structural enforcement**: Requiring `require_gate_decision()` at write
  sites is high-risk. Only Phase 1 (passive) and Phase 2 (advisory) are implemented.

---

## Dependency Graph

```
AD-8 (GateToken context var) ──────┐
                                    ├──► AD-9 (event log attribution)
AD-7 (Says via ThreadEntry) ───────┘
```

AD-7 and AD-8 are independent of each other.
AD-9 depends on both (event log reads principal from Says and gate decision from context var).

---

## Affected Files

### Modified files
- `shared/governance/gate_token.py` — Add context var, `last_gate_decision()`, `set_gate_decision()`
- `shared/governance/consent_gate.py` — Set context var in `check()` and `check_and_write()`
- `shared/governance/qdrant_gate.py` — Set context var in `upsert()` and `set_payload()`
- `agents/hapax_voice/conversation_pipeline.py` — ThreadEntry.principal_id, _message_attribution, tool principal creation, Says wiring at 3 data flow points
- `agents/hapax_voice/event_log.py` — Add principal_id, gate_decision fields to events

### No new files needed
All changes extend existing modules.

### Test files
- `tests/test_gate_token.py` — Test context var set/get
- `tests/test_says_monad.py` — Test tool principal delegation + to_labeled bridge
- `tests/hapax_voice/test_conversation_pipeline_says.py` — New: test Says wiring in pipeline
