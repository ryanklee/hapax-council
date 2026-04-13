# Phase 1 — Axiom enforcement landscape audit

**Queue item:** 025
**Phase:** 1 of 6
**Date:** 2026-04-13 CDT
**Register:** scientific, neutral (per `feedback_scientific_register.md`)
**Depends on:** BETA-FINDING-K (PR #756 + PR #761) — the original example of the failure class this phase systematically audits.

## Headline

Four out of five axioms have silent-catch enforcement patterns
analogous to BETA-FINDING-K. Two are **Critical-or-near-Critical**
severity:

1. **`corporate_boundary` (weight 90) — `_no_work_data` fails open
   on missing metadata.** `agents/_governance/agent_governor.py:74`
   returns `True` (allow) when the data object has no `metadata`
   dict or no `data_category` key. Identical structural shape to
   BETA-FINDING-K: a weight-90 governance guarantee silently
   degrades to "proceed without enforcement" when its prerequisite
   (metadata labeling) is absent.
2. **`corporate_boundary` sufficiency not met — obsidian-hapax
   providers directory does not exist.** The sufficiency probe
   `_check_plugin_direct_api_support` at
   `shared/sufficiency_probes.py:430` checks for
   `obsidian-hapax/src/providers/{anthropic.ts, openai-compatible.ts}`;
   the directory is **missing**. The plugin therefore has **zero
   runtime enforcement** of the employer-sanctioned-provider
   requirement.

Two High findings:

3. **`management_governance` (weight 85) — runtime governor is
   pattern-match only.** `agents/hapax_daimonion/governor.py:41`
   `_RUNTIME_COMPLIANCE_RULES` uses two regex patterns to gate
   voice output. The patterns cover "feedback / coaching /
   performance review" + "draft (conversation / difficult /
   termination / pip)", but any LLM output that uses synonyms
   ("guidance," "recommendations," "one-on-one talking points")
   would pass the regex without being caught. Defense in depth is
   weak.
4. **Any axiom — `check_full` precedent store has a DEBUG-level
   silent catch.** `shared/axiom_enforcement.py:307`:

   ```python
   try:
       store = PrecedentStore()
       for axiom in axioms:
           precedents = store.search(axiom.id, situation, limit=3)
           ...
   except Exception as e:
       log.debug("Precedent store unavailable for full check: %s", e)
   ```

   If Qdrant is down / the precedents collection is missing / the
   search fails, full-path axiom checking silently drops the
   precedent layer. The static rule layer still runs, so this is
   not a full bypass — but it is the exact pattern that BETA-FINDING-K
   exploited (silent fallback at a governance-layer boundary).

One Medium finding:

5. **SDLC commit hook fails open if `jq` is missing.**
   `hooks/scripts/axiom-commit-scan.sh:11`:

   ```bash
   COMMAND="$(echo "$INPUT" | jq -r '.tool_input.command // empty' 2>/dev/null || true)"
   if [ -z "$COMMAND" ]; then
     exit 0    # ← no scan performed
   fi
   ```

   The hook is the primary commit-time defense against T0 axiom
   violations. If `jq` fails to parse the input, or if the command
   field is not a recognized pattern, the hook exits 0 (allow the
   commit). A misconfigured hook path or a malformed Claude Code
   input would silently disable commit-time axiom enforcement.

## Per-axiom enforcement-gate map

| axiom | weight | enforcement points | fail mode | analogous risk |
|---|---|---|---|---|
| `single_user` | 100 | SDLC hook regex in `axiom-patterns.sh` + runtime checks in `shared/operator.py:251` + 18 T0/T1 implications | **LOUD** — T0 violations pattern-match at commit time + raise at runtime | no runtime fail-open observed |
| `executive_function` | 95 | 19 sufficiency probes in `sufficiency_probes.py`, all T1/T2 enforcement=review or warn | **SOFT** — sufficiency only, no runtime veto | axiom is aspirational; cannot structurally "violate" executive function at runtime — LOW risk |
| `corporate_boundary` | 90 | `_corporate_boundary_policies` in `_governance/agent_governor.py:56` + 3 sufficiency probes | **FAIL-OPEN** — `_no_work_data` returns True when metadata is missing (line 74); providers dir missing | **HIGH risk** — same shape as BETA-FINDING-K |
| `interpersonal_transparency` | 88 | `ConsentGatedReader` + `init_pipeline.py:45` + PR #761 fix | **FAIL-OPEN → being fixed** by PR #761 (in flight) | known risk; fix ships |
| `management_governance` | 85 | `governor.py` VetoChain with 2 regex rules + 1 sufficiency probe | **LOUD on pattern match, SILENT on synonyms** | MEDIUM risk — pattern coverage is narrow |

## Finding 1: `_no_work_data` fail-open pattern

### Location

`agents/_governance/agent_governor.py:56–88`

### The pattern

```python
def _corporate_boundary_policies(
    role: str,
) -> tuple[list[GovernorPolicy], list[GovernorPolicy]]:
    input_policies: list[GovernorPolicy] = []
    output_policies: list[GovernorPolicy] = []

    if role in ("subject", "enforcer"):
        def _no_work_data(_agent_id: str, data: Labeled[Any]) -> bool:
            """Deny data categorized as work/employer data."""
            if hasattr(data, "metadata") and isinstance(data.metadata, dict):
                return data.metadata.get("data_category") != "work"
            return True  # No metadata = no category = allowed   ← FAIL-OPEN
        ...
```

### Why it matters

The axiom says: *"The Obsidian plugin operates across a corporate
network boundary via Obsidian Sync. When running on
employer-managed devices, all external API calls must use
employer-sanctioned providers… No localhost service dependencies
may be assumed. The system must degrade gracefully when home-only
services are unreachable."*

Weight 90.

The enforcement policy checks for a specific `data_category == "work"`
tag. If that tag is **missing**, the policy returns `True` (allow).
This inverts the axiom's intent: instead of "allow known-safe data,"
the enforcement is "deny known-unsafe data, allow everything else."
For a fail-closed governance axiom, the correct pattern is the
opposite: "allow data with `data_category == "personal"`, deny
everything else."

Any un-labeled data flowing through the agent pipeline bypasses
this check entirely. The labeling step is itself an opportunity for
silent failure (if the label extractor crashes or runs in a codepath
that doesn't know to tag).

### Fix proposal

```python
def _no_work_data(_agent_id: str, data: Labeled[Any]) -> bool:
    """Deny data categorized as work/employer data."""
    if not (hasattr(data, "metadata") and isinstance(data.metadata, dict)):
        raise GovernanceError(
            "corporate_boundary: data object has no metadata; cannot verify "
            "data_category. Label the data explicitly before routing."
        )
    category = data.metadata.get("data_category")
    if category == "work":
        return False
    if category is None:
        raise GovernanceError(
            "corporate_boundary: data has no data_category; refusing to allow "
            "(fail-closed policy)."
        )
    return True
```

**Scope**: 1 file, ~10 lines. Changes the fail-open default to
fail-closed. Downstream code that relied on unlabeled data passing
through will fail-loud at a caller boundary where the label should
have been attached — exposing all the sites that silently skipped
the labeling step.

## Finding 2: `obsidian-hapax/src/providers/` directory missing

### Location

- Sufficiency probe: `shared/sufficiency_probes.py:430+`
  (`_check_plugin_direct_api_support`)
- Expected path: `obsidian-hapax/src/providers/`
- Actual state: **directory does not exist** (`ls` returns "No such
  file or directory")

### The gap

The sufficiency probe lists the implication `cb-llm-001` which
requires the Obsidian plugin to support direct API calls to
employer-sanctioned providers. The probe checks for:

- `obsidian-hapax/src/providers/anthropic.ts`
- `obsidian-hapax/src/providers/openai-compatible.ts`
- `obsidian-hapax/src/providers/index.ts`

None of these exist. The plugin currently has only `main.ts`,
`settings.ts`, `context-panel.ts`, `context-resolver.ts`,
`logos-client.ts`, `sections.ts`, and `types.ts`. Its only
API-call path is `logos-client.ts` which calls
`http://localhost:8051` (the home workstation's Logos API), not a
provider directly.

### Why it matters

The axiom says the plugin "operates across a corporate network
boundary" and must degrade gracefully when "home-only services are
unreachable." On an employer-managed device:

- `localhost:8051` is not reachable (workstation is at home)
- The plugin has no fallback to direct Anthropic/OpenAI API calls
- So on a corporate device, the plugin is **broken**, not "degrading
  gracefully to employer-sanctioned providers"

This is not just a silent failure — it is a missing feature that
the axiom explicitly requires. The sufficiency probe would report
this, but the probe is development-time only; runtime has no
enforcement.

### Fix proposal

**Out of scope for research** — this is a missing feature, not a
code fix. File a backlog item to implement the plugin's direct API
path per the spec the probe expects.

## Finding 3: `management_governance` regex runtime coverage is narrow

### Location

`agents/hapax_daimonion/governor.py:41–62`

### The pattern

```python
_RUNTIME_COMPLIANCE_RULES: list[ComplianceRule] = [
    ComplianceRule(
        axiom_id="management_governance",
        implication_id="mg-boundary-001",
        tier="T0",
        pattern=re.compile(
            r"feedback|coaching|performance.review|1.on.1|one.on.one",
            re.IGNORECASE,
        ),
        description="Never generate feedback/coaching about individuals",
    ),
    ComplianceRule(
        axiom_id="management_governance",
        implication_id="mg-boundary-002",
        tier="T0",
        pattern=re.compile(
            r"draft.*(conversation|difficult|termination|pip\b)",
            re.IGNORECASE,
        ),
        description="Never draft language for people conversations",
    ),
]
```

Two regex patterns guard the daemon's voice output against
management-governance violations. A workspace_context string that
says "Daisy is thinking about coaching" would match. A string that
says "operator wants talking points for the Tuesday 1:1" would
match `1.on.1`. But:

- `recommendations about Alice` — no match
- `draft language for the Bob discussion` — no match (no
  keyword from the second pattern)
- `prepare guidance for the next review cycle` — no match
  (`review` alone does not match `performance.review`)
- `outline for the career conversation` — no match

An LLM that phrases its output around synonyms bypasses the regex.
The governor's `_RUNTIME_COMPLIANCE_RULES` is defense-in-depth on
top of the system prompt, but it is a narrow net.

### Fix proposal

Broaden the regex patterns OR switch to an LLM-based classifier
with a distinct cheap model (e.g., haiku) that evaluates the
workspace_context + proposed output against the axiom text. The
embedding-based similarity check would catch synonyms at the cost
of an API call per evaluation.

Medium severity because the primary defense is the system prompt
(which is harder to classify as broken) and this is a fallback
layer. Still worth strengthening.

## Finding 4: `check_full` precedent store silent catch

### Location

`shared/axiom_enforcement.py:296–308`

### The pattern

```python
precedent_violations: list[str] = []
precedent_axioms: list[str] = []
try:
    from shared.axiom_precedents import PrecedentStore
    store = PrecedentStore()
    for axiom in axioms:
        precedents = store.search(axiom.id, situation, limit=3)
        for p in precedents:
            if p.decision == "violation":
                precedent_violations.append(f"Precedent {p.id}: ...")
                ...
except Exception as e:
    log.debug("Precedent store unavailable for full check: %s", e)
```

### Why it matters

If the precedent store is down, `check_full` silently drops its
precedent layer. The function still returns a `ComplianceResult`,
now based only on the static rules. There is no signal to the
caller that the check was partial.

Currently the precedent store is Qdrant-backed. If Qdrant goes down
(which did happen during sessions this week per PR #752 findings),
the governance layer silently weakens without any operator-visible
indication.

This is less severe than BETA-FINDING-K because the static fast
rules still run. But it is the exact shape: a silent catch at a
governance-layer boundary that degrades enforcement.

### Fix proposal

Upgrade to `log.warning` + expose a counter
`hapax_check_full_precedent_errors_total`. Consider adding a
`partial=True` flag to `ComplianceResult` so callers can see that
the check was degraded, without hard-failing the call.

Alternatively, add a periodic health probe on `PrecedentStore` at
daemon startup so a missing store surfaces at boot rather than at
evaluation time.

## Finding 5: SDLC commit hook fail-open on input parse

### Location

`hooks/scripts/axiom-commit-scan.sh:11–17`

### The pattern

```bash
COMMAND="$(echo "$INPUT" | jq -r '.tool_input.command // empty' 2>/dev/null || true)"
if [ -z "$COMMAND" ]; then
  exit 0    # ← allow the commit without scanning
fi
```

If `jq` returns empty (or `jq` is not installed, or the input is
not JSON, or the input has no `tool_input.command` field), the hook
silently exits 0. The commit proceeds without axiom scanning.

Similar pattern for `git diff --cached 2>/dev/null || true` — if
diff fails, the hook exits 0.

### Why it matters

This hook is one of the primary commit-time enforcement paths. A
misconfigured Claude Code hook input (e.g., a schema change between
versions), a missing `jq` binary, or a `git diff` permission
failure all silently disable the scan. Commits go through, T0
violations are not caught at commit time, and the operator discovers
the violation at runtime (possibly months later, via a BETA-FINDING-K
type incident).

### Fix proposal

Fail-loud: if parse fails, exit 2 with a visible error. The cost is
one broken commit when a dependency is missing, which is the
correct outcome — the operator sees the error immediately and fixes
the dependency. Silent degradation is worse.

```bash
COMMAND="$(echo "$INPUT" | jq -r '.tool_input.command // empty' 2>/dev/null)"
JQ_STATUS=$?
if [ $JQ_STATUS -ne 0 ]; then
  echo "axiom-commit-scan: jq failed to parse hook input — cannot scan commit" >&2
  echo "Install jq and retry: paru -S jq" >&2
  exit 2
fi
if [ -z "$COMMAND" ]; then
  # Command field genuinely empty — not a hook parse failure
  exit 0
fi
```

## Top-5 ranked gaps for fix attention

| rank | finding | axiom weight | risk class | fix effort |
|---|---|---|---|---|
| 1 | #1 `_no_work_data` fail-open on missing metadata | 90 | HIGH (live risk) | ~10 lines |
| 2 | #2 obsidian-hapax `providers/` directory missing | 90 | HIGH (missing feature, not fail-open but defeats axiom on corporate devices) | multi-day implementation |
| 3 | #4 `check_full` precedent store silent catch | any (affects all) | MEDIUM | ~5 lines |
| 4 | #5 SDLC commit hook jq fail-open | any (affects T0 at commit) | MEDIUM | ~15 lines |
| 5 | #3 `management_governance` regex narrow coverage | 85 | MEDIUM (defense in depth) | spec + implementation work |

## Cross-reference with PR #761 (BETA-FINDING-K fix)

PR #761 (alpha, in flight) is the fix-closed init path for
`ConsentGatedReader`. Its pattern is:

1. Exception in `ConsentGatedReader.create()` → raise, not swallow
2. `conversation_pipeline.py:1281` — refuse to proceed if reader
   is None (fail-closed)

The fix pattern for **Finding 1** (`_no_work_data`) should be
identical: raise on missing metadata instead of returning True.

The fix pattern for **Finding 4** (`check_full`) is softer —
`log.warning` + counter instead of fail-closed, because the fast
rule path still provides basic coverage.

## Backlog additions (for retirement handoff)

89. **`fix(governance): _no_work_data fail-closed on missing metadata`** [Phase 1 Finding 1] — ~10 lines in `agents/_governance/agent_governor.py`. CRITICAL-adjacent (HIGH+active axiom weight). Same fix pattern as PR #761 (BETA-FINDING-K).
90. **`feat(obsidian-hapax): direct API provider path (anthropic.ts + openai-compatible.ts)`** [Phase 1 Finding 2] — multi-day scope. Implements the `cb-llm-001` implication that the sufficiency probe already tests for. Without this, the axiom is actively violated on employer-managed devices.
91. **`fix(governance): check_full precedent store error to WARNING + counter + partial flag`** [Phase 1 Finding 4] — ~10 lines in `shared/axiom_enforcement.py`.
92. **`fix(sdlc): axiom-commit-scan.sh jq fail-loud on parse failure`** [Phase 1 Finding 5] — ~15 lines in `hooks/scripts/axiom-commit-scan.sh`. Also audit other hooks for similar fail-open patterns.
93. **`feat(governor): broaden management_governance regex OR add LLM classifier`** [Phase 1 Finding 3] — either a list of additional synonyms (feedback → guidance, recommendations, talking points, outline, etc.) or a cheaper LLM call. Design decision required.
94. **`research(governance): audit every hook in hooks/scripts/ for fail-open patterns`** [Phase 1 Finding 5 extension] — Phase 1 looked at one hook; there are 20+. Each should be audited for silent degradation paths.
95. **`feat(governance): hapax_governance_partial_checks_total counter`** [Phase 1 Finding 4 followup] — tracks how often `check_full` runs without the precedent layer. Paired with a Grafana alert for rate > 0.
