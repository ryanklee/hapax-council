# Governance Enforcement Hardening

**Date**: 2026-03-24
**Session**: beta
**Scope**: `shared/governance/`, `logos/api/routes/`, `agents/ingest.py`, `agents/retroactive_label.py`
**Axioms**: interpersonal_transparency (88), corporate_boundary (90)
**Prior art**: `2026-03-13-enforcement-gaps.md`, `2026-03-13-computational-constitutional-governance.md`

Comprehensive audit of the consent-based data classification system found the algebraic
core (consent_label, provenance, labeled, principal) to be sound and well-tested. The
enforcement wiring layer has systematic gaps. This document specifies fixes organized by
severity and dependency order.

---

## Problem Statement

The governance system claims two structural properties:

1. **Write chokepoint**: All person-adjacent persistent writes pass through ConsentGatedWriter
2. **Read chokepoint**: All person-adjacent data reaching the LLM passes through ConsentGatedReader

Neither property holds for the full system. The write gate covers filesystem writes only;
Qdrant upserts bypass it entirely. The read gate covers voice pipeline tool results only;
the Logos REST API returns unfiltered data to the frontend. Additionally, the corporate
boundary axiom has zero runtime enforcement due to an attribute access bug.

---

## Findings Summary

### Correctness Bugs

| ID | File | Description | Severity |
|----|------|-------------|----------|
| C1 | `agent_governor.py:71` | Corporate boundary policy checks `data.metadata` which doesn't exist on `Labeled[T]`; policy is always permissive | **High** |
| C2 | `agent_governor.py:88-91` | Dead `_AXIOM_POLICY_BUILDERS` dict, never populated | Low |
| C3 | `consent.py:102` | `contract_check` matches operator as party, semantically imprecise | Low |

### Enforcement Gaps

| ID | Scope | Description | Severity |
|----|-------|-------------|----------|
| G1 | Qdrant writes | `ingest.py`, `retroactive_label.py`, `dossier.py` write person-adjacent data to Qdrant without consent check | **Critical** |
| G2 | Qdrant revocation | `RevocationPropagator` has no handler for Qdrant collections; revocation cascade doesn't reach primary persistence | **Critical** |
| G3 | REST API reads | Logos API routes (`/api/studio/*`, `/api/flow/state`, `/api/briefing`) return person-adjacent data without ConsentGatedReader | **High** |
| G4 | GateToken | `require_token()` defined but never called; no write path demands proof of gate passage | Medium |
| G5 | Child principal | Contract YAML has `principal_class: child` / `guardian`; neither parsed by `_parse_contract()` nor used at runtime | **High** |

### Consistency Issues

| ID | Scope | Description | Severity |
|----|-------|-------------|----------|
| S1 | Temporal | `ConsentInterval` / `TemporalConsent` fully implemented, zero runtime callers; contracts are indefinite-only | Medium |
| S2 | Says monad | Created in voice pipeline, stored as `_last_says`, never consumed downstream | Low |
| S3 | Package exports | 9 of 16 governance modules not exported from `__init__.py` | Low |
| S4 | Carrier purge | `purge_by_provenance` uses flat set check, not semiring evaluation | Low |
| S5 | Context threading | `consent_scope()` used only in voice; other agents pass registries explicitly | Low |

---

## Architecture Decisions

### AD-1: Qdrant consent gate as a wrapper, not middleware

**Decision**: Create `ConsentGatedQdrant` — a thin wrapper around `QdrantClient` that
intercepts `upsert()` and `set_payload()` calls, checks consent for any person IDs in
the payload, and either permits or curtails the write.

**Rationale**: Middleware on the Qdrant client itself would require modifying every call
site. A wrapper follows the same pattern as `ConsentGatedWriter` (chokepoint) and can be
injected at construction time. Agents that write operator-only data (profile_store,
episodic_memory, axiom_precedents) can use the raw client; agents that MAY write
person-adjacent data (ingest, retroactive_label, dossier) MUST use the gated client.

**What it checks**:
1. Extract person IDs from payload (using `person_extract.extract_person_ids()`)
2. For each non-operator person ID: `registry.contract_check(person_id, collection_name)`
3. If any person lacks consent: curtail the write, log the decision, return structured denial
4. If all consented: delegate to inner `QdrantClient.upsert()`

**Collection → data category mapping**: Each Qdrant collection maps to a consent data
category. Collections with only operator data are exempt.

```
documents      → "document"    (emails, calendar, drive — person-adjacent)
studio-moments → "perception"  (anonymized counts — EXEMPT, no person IDs)
profile-facts  → EXEMPT        (operator-only)
operator-*     → EXEMPT        (operator-only by name)
axiom-*        → EXEMPT        (governance data)
```

### AD-2: Qdrant revocation handler

**Decision**: Register a Qdrant purge handler with `RevocationPropagator` that, on
contract revocation, scans the `documents` collection for points whose `people` payload
field contains the revoked person ID, and deletes them.

**Rationale**: Qdrant supports filtering by payload fields. The `people` field is already
populated by `retroactive_label.py`. Scanning by person ID is O(collection_size) but
revocation is rare and correctness is paramount.

**Implementation**:
- New function `purge_qdrant_by_person(contract_id: str) -> int` in `revocation_wiring.py`
- Queries `documents` collection with `must: [{key: "people", match: {any: [person_id]}}]`
- Deletes matching points
- Returns count of purged points

### AD-3: Logos API consent middleware as FastAPI dependency

**Decision**: Create a `ConsentGatedReader` FastAPI dependency that wraps route responses
for person-adjacent routes. Routes opt in via `Depends(consent_filter)`.

**Rationale**: Not all routes need filtering (system status, governance introspection,
game state). A dependency is explicit, testable, and doesn't require response middleware
that would process every response.

**Which routes get the dependency**:
- `/api/briefing` — briefing text may mention persons
- `/api/studio/consent` — exposes guest presence (governance introspection, exempt)
- `/api/studio/stream/*` — live video feeds (requires separate handling — image data
  can't be text-filtered; instead, gate on guest consent status before streaming)
- `/api/flow/state` — expose `face_count` and `consent_phase` only if active consent exists

**Video feed gating**: For camera streams, the gate checks whether ALL detected guests
have active consent for "video" scope. If not, the stream endpoint returns 451
(Unavailable For Legal Reasons) with a structured JSON body explaining the curtailment.
This is coarser than text degradation but appropriate for binary video streams.

### AD-4: Fix corporate boundary policy

**Decision**: Replace the broken `data.metadata` check with a proper data-category-aware
check. Since `Labeled[T]` doesn't carry data category metadata, the policy must receive
the category through the governor check interface.

**Approach**: Add an optional `data_category: str` field to the governor check context.
The simplest change: since `GovernorPolicy.check` signature is
`Callable[[str, Labeled[Any]], bool]`, and we can't change it without breaking all
policies, instead: the corporate boundary check should operate at the **agent manifest
level** (static binding) rather than the per-datum level (runtime check).

The axiom's intent is: agents that handle work data must route through sanctioned
providers and not persist to the home system. This is a deployment topology constraint,
not a per-datum label check. The runtime policy was always the wrong abstraction.

**Revised enforcement**:
1. Remove the broken `_corporate_boundary_policies` runtime check
2. Strengthen the static binding validation in `axiom_bindings.py` to BLOCK (not just
   warn) when work-handling agents lack the binding
3. Ensure `obsidian_sync` gets its missing binding
4. Document that corporate boundary is enforced statically (manifest bindings + SDLC
   hooks), not at runtime per-datum

### AD-5: Child principal detection

**Decision**: Parse `principal_class` and `guardian` from contract YAML into
`ConsentContract`. When resolving guest identity, check against
`REGISTERED_CHILD_PRINCIPALS` and automatically set `GuestContext.is_child = True`.

**Changes**:
1. Add `principal_class: str = ""` and `guardian: str | None = None` to `ConsentContract`
2. Parse these fields in `_parse_contract()`
3. In `guest_detection.py:check_guest_consent()`, if person_id is in
   `REGISTERED_CHILD_PRINCIPALS`, populate `GuestContext(is_child=True,
   guardian_present=True)` (guardian is always operator in this household)
4. Channel selection then correctly restricts to operator-mediated consent

### AD-6: Clean up dead code and package exports

**Decision**: Remove `_AXIOM_POLICY_BUILDERS` dead dict. Add missing modules to
`__init__.py` exports where they're part of the public API. Modules that are internal
implementation details (person_extract, guest_detection) stay unexported.

**Export additions**:
- `ConsentGatedReader`, `RetrievedDatum`, `ReaderDecision` (read gate is public API)
- `GateToken`, `require_token` (token discipline is public API)
- `ConsentChannel`, `ChannelMenu`, `build_channel_menu` (channel selection is public API)
- `TemporalConsent`, `ConsentInterval` (temporal is public API, even if unused)
- `Says` (public formalism API)
- `consent_scope`, `current_registry`, `current_principal` (context threading is public API)
- `degrade` (degradation dispatch is public API)

---

## Scope Exclusions

The following are **not addressed** in this spec:

- **Temporal consent integration** (S1): Contracts are indefinite-only by design for current
  principals (family members). Time-limited contracts are a future feature when guest
  visitors arrive. The temporal module is correctly positioned as deferred formalism.

- **Says monad wiring** (S2): The voice pipeline creates Says but doesn't thread it.
  This requires redesigning the message history to carry principal attribution, which is
  a separate effort orthogonal to enforcement hardening.

- **GateToken structural enforcement** (G4): Making write functions demand GateToken
  parameters requires refactoring all write call sites. This is deferred to a future
  phase once the Qdrant gate (AD-1) is proven. The token minting continues as audit trail.

- **Carrier purge semiring** (S4): Carrier facts are never created with structured
  provenance expressions. The flat check is correct for current usage. If structured
  provenance is introduced for carriers, the purge method should be updated then.

---

## Dependency Graph

```
AD-4 (fix corporate boundary) ──────────────────────────────────┐
AD-6 (clean up dead code + exports) ────────────────────────────┤
AD-5 (child principal detection) ───────────────────────────────┤── independent
                                                                │
AD-1 (Qdrant consent gate) ─────────┬───► AD-2 (Qdrant revocation handler)
                                    │
AD-3 (API consent middleware) ──────┘── both depend on ConsentGatedReader existing
```

AD-1, AD-3, AD-4, AD-5, AD-6 are independent of each other.
AD-2 depends on AD-1 (needs the collection→category mapping).

---

## Test Strategy

Each AD gets:
1. **Unit tests**: Test the new module/function in isolation with mock registries
2. **Integration test**: Test with real contract YAML files and Qdrant test collection
3. **E2E scenario**: Full lifecycle — create contract, write data, revoke, verify purge

Specific test cases:
- AD-1: Upsert with consented person passes; upsert with unconsented person is curtailed
- AD-2: Revoke contract → Qdrant points with that person purged; other points untouched
- AD-3: API route returns degraded content for unconsented persons
- AD-4: Agent with missing corporate_boundary binding fails validation
- AD-5: Child detected → only operator-mediated channel offered

---

## Research Phase 2 Refinements

### Qdrant Client Topology

The codebase has **two** Qdrant client factories:

1. **`shared/config.py:get_qdrant()`** — LRU-cached singleton, used by ~48 files.
   The ConsentGatedQdrant wrapper replaces the return value of this factory.
   All consumers automatically get the gated version.

2. **`agents/ingest.py:get_qdrant()`** — Isolated singleton in separate venv (docling
   conflicts prevent importing shared.config). Must be wrapped independently. Since
   ingest.py is the **most critical** consent gap (emails, calendar, drive documents),
   the wrapper must be duplicated or extracted to a dependency-free module.

**Decision**: Create `shared/governance/qdrant_gate.py` with zero pydantic-ai dependency.
Import it in both `shared/config.py` and `agents/ingest.py`. The gate module depends only
on `qdrant-client` and `pyyaml` (both available in the ingest venv).

### Dossier Collection Correction

The dossier writes to `profile-facts` (not a dynamic collection). Person identifiers are
in `audience_key` and `audience_name` payload fields. The gate must check these fields in
addition to the standard `people`/`attendees`/`from`/`to` fields.

### Logos API Dependency Pattern

No existing `Depends()` usage. Routes use module-level singletons and lazy imports.
The consent dependency will be the first `Depends()` in the API. Pattern:

```python
# logos/api/deps/consent.py
from shared.governance.consent_reader import ConsentGatedReader

_reader: ConsentGatedReader | None = None

def get_consent_reader() -> ConsentGatedReader:
    global _reader
    if _reader is None:
        _reader = ConsentGatedReader.create()
    return _reader

# In route:
@router.get("/api/briefing")
async def get_briefing(reader: ConsentGatedReader = Depends(get_consent_reader)):
    ...
```

### Binding Validation Enforcement

`validate_bindings()` is currently test-only. To make it blocking:
- Call in `logos/api/app.py:lifespan()` at startup
- Log binding gaps at WARNING level
- Do NOT block startup (would brick the system if a manifest is wrong)
- Add to health monitor checks (already runs every 5 minutes)

---

## Affected Files

### New files
- `shared/governance/qdrant_gate.py` — ConsentGatedQdrant wrapper (AD-1, AD-2)
- `logos/api/deps/__init__.py` — Package init
- `logos/api/deps/consent.py` — FastAPI consent dependency (AD-3)

### Modified files
- `shared/config.py` — Wrap `get_qdrant()` return with ConsentGatedQdrant (AD-1)
- `shared/governance/consent.py` — Add `principal_class`, `guardian` fields (AD-5)
- `shared/governance/agent_governor.py` — Remove broken corporate boundary policy, remove dead dict (AD-4, C2)
- `shared/governance/revocation_wiring.py` — Register Qdrant purge handler (AD-2)
- `shared/governance/__init__.py` — Add missing exports (AD-6)
- `shared/governance/guest_detection.py` — Auto-detect child principals (AD-5)
- `agents/ingest.py` — Wrap isolated Qdrant client with consent gate (AD-1)
- `agents/retroactive_label.py` — Use gated client (AD-1)
- `agents/demo_pipeline/dossier.py` — Use gated client for profile-facts writes (AD-1)
- `logos/api/routes/flow.py` — Add consent dependency for face_count (AD-3)
- `logos/api/routes/studio.py` — Add consent gating for video streams (AD-3)
- `logos/api/routes/data.py` — Add consent filtering for briefing (AD-3)
- `logos/api/app.py` — Call validate_bindings() at startup (AD-4)
- `shared/axiom_bindings.py` — Strengthen corporate_boundary validation (AD-4)

### Test files (new)
- `tests/test_qdrant_gate.py`
- `tests/test_api_consent_middleware.py`
- `tests/test_child_principal_detection.py`
- `tests/test_corporate_boundary_static.py`
