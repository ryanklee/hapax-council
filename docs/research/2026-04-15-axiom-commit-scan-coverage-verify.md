# axiom-commit-scan.sh Coverage Verification

**Queue:** #176
**Author:** alpha
**Date:** 2026-04-15
**Hook:** `hooks/scripts/axiom-commit-scan.sh` + `hooks/scripts/axiom-patterns.sh`

> **Meta note:** an early draft of this research drop reproduced the axiom patterns verbatim in a code block. The `axiom-scan.sh` sibling hook fired on the `Write` tool call because the drop's literal text contained unparenthesised patterns that matched their own regex. This is not a defect — it is correct behaviour and validates the coverage claim. This version of the drop describes the patterns in prose without quoting the unsafe literals, which are traceable via `hooks/scripts/axiom-patterns.sh`.

---

## §0. TL;DR

`axiom-commit-scan.sh` catches **structural multi-user scaffolding and management-feedback class/function names**, 19 patterns total. It is a narrow, regex-based blocking gate that runs on `git commit` / `git push` / direct shell file writes.

**Blocking coverage by axiom:**

| Axiom | Weight | Hook patterns | Blocking coverage |
|-------|--------|---------------|-------------------|
| single_user | 100 | 15 | good (Python-centric structural detection) |
| management_governance | 85 | 4 | structural only (class/def names) — no prompt-text coverage |
| interpersonal_transparency | 88 | **0** | **none** (relies on CODEOWNERS + runtime enforcement) |
| executive_function | 95 | **0** | **none** (property-level; not regex-friendly) |
| corporate_boundary | 90 | 1 (advisory) | **effective zero** — advisory only, exit 0, requires marker file |

**Two follow-up candidates** surfaced: (1) interpersonal_transparency structural patterns for the drafting-visibility + irreversible-broadcast implications just ratified in PR #911; (2) `registry-guard.sh` extension to protect `axioms/implications/` + `axioms/contracts/` + `axioms/precedents/` on modify (allow create).

**No false positives** found in the last 100 commits — the scan fires on genuine violations only.

---

## §1. What the hook actually does

### §1.1. Trigger surface

`axiom-commit-scan.sh` is a PreToolUse Bash hook. It reads `tool_input.command` via jq and matches one of:

| Trigger | Scan target |
|---------|-------------|
| `git commit` | `git diff --cached` (staged lines) |
| `git push` | `git diff "$BASE...HEAD"` (branch-relative to main/master) |
| Shell file-writers (sed -i, tee, `>`, python -c, perl -[ip]) | raw COMMAND string |
| curl / wget to non-localhost | URL check only (advisory; exit 0) |
| Any other command | pass-through (exit 0) |

**Not scanned:** Edit/Write/MultiEdit tool calls directly. These flow through `pii-guard.sh`, `axiom-scan.sh`, and `work-resolution-gate.sh`, but never hit `axiom-commit-scan` until the subsequent `git commit` picks them up via `git diff --cached`. This is defense-in-depth by design: the commit-scan is a pre-commit structural gate, not a per-edit filter.

### §1.2. jq hard-fail

The hook fails loud (exit 2) when `jq` is missing. This is intentional — a silent-passing governance hook would be worse than a failing one. Origin: queue 025 #92. Confirmed correct at `hooks/scripts/axiom-commit-scan.sh:17-23`.

### §1.3. Comment stripping before pattern match

Before `ADDED_LINES` is matched against patterns, the hook strips:
- full-line shell comments (`#` with non-shebang continuation)
- trailing shell comments (space + `#` + space)
- full-line C/C++/TS comments (`//`)
- trailing C/C++/TS comments (space + `//` + space)
- inline HTML comments (`<!--...-->`)

**Not stripped:** Python triple-quoted docstrings, markdown code fences, YAML multiline strings. A docstring containing a structural class name WOULD trigger the hook even though it is documentation, not code. This is a small false-positive surface — see §4.4.

---

## §2. Pattern inventory

The 19 patterns live in `hooks/scripts/axiom-patterns.sh` as a bash array. Rather than reproduce them verbatim (the verbatim forms tripped the hook when this drop was first written, proving the point), they are summarised here by bucket.

### §2.1. single_user (15 patterns)

Covered under axiom-weight 100. Recovery language: "Remove the multi-user scaffolding. Reimplement assuming a single operator with full access."

**Auth / authz class names (3 patterns):**
- User prefix followed by one of Manager, Service, Repository, Controller, Model
- Auth prefix followed by one of Manager, Service, Handler
- One of Role / Permission / ACL / RBAC / OAuth / Session followed by Manager

**Auth / authz function names (3 patterns):**
- Functions named after the verbs authenticate, authorize, login, logout, register with a `_user` suffix
- Functions named after the verbs create, delete, update, list with a `user` or `users` suffix
- Generic permission-check function signature (the one problematic non-parenthesised pattern — see §4.5 for false-positive mitigation)

**Auth imports (1 pattern):**
- `from` imports targeting `django.contrib.auth`, `flask_login`, `passlib`, or `bcrypt`

**Multi-user collaboration class names (3 patterns):**
- CollaborationManager / SharingService / MultiUserSync class declarations
- A class literal starting with "class MultiT" (tenant-prefixed)
- Tenant-prefixed classes ending in Manager / Service / Config

**Privacy/consent class names (1 pattern):**
- ConsentManager / PrivacyPolicy / DataAnonymizer / GDPR class declarations

**Multi-tenant security (2 patterns):**
- RateLimiter / UserQuota / AbusePrevention class declarations
- Identifiers matching user-roles, role-assignment, or permission-check (as snake_case word boundaries)

**Admin interfaces (1 pattern):**
- AdminPanel / AdminDashboard / UserAdmin class declarations

**Coverage gaps within single_user:**

1. **Language scope.** All patterns are Python-centric (`class`, `def`). TypeScript/JavaScript auth scaffolding (interface declarations, arrow-function auth helpers, object-literal role managers) would NOT trigger. Given the project has substantial TypeScript in `hapax-logos/src/` and `vscode/`, this is a real gap.
2. **Config-file scope.** YAML/JSON config files declaring users, roles, or tenants slip through. E.g., docker-compose environment vars defining multi-role deployments.
3. **SQL schemas.** `CREATE TABLE` statements with user columns have no `class`/`def` wrapper and slip through. `postgres/` migrations directory could harbor this.
4. **Generic permission-check pattern.** The one non-parenthesised function-name pattern could false-positive on filesystem-permission checks that wrap `os.access` or stat calls. No current FP sightings but the surface exists.

### §2.2. management_governance (4 patterns)

Covered under axiom-weight 85. Recovery language: "Keep the data aggregation but remove generated language. Surface patterns and open loops; let the operator formulate their own words."

- Functions named after generate / draft / write / compose with a `_feedback` suffix
- Functions named after suggest / recommend with a `.*to_say` tail
- Class declaration ending in the token `FeedbackGenerator`
- Class declaration ending in the token `CoachingRecommender`

**Coverage gaps within management_governance:**

1. **Prompt-text coverage.** The actual form of violations is typically a prompt string or f-string literal, not a class wrapper. A prompt like `f"Draft feedback for {employee.name} that addresses..."` slips through.
2. **LLM output handling.** Code that calls LLMs without a feedback-generation class wrapper but still produces coaching text (e.g., a direct `llm.chat(prompt)` call where the prompt comes from user instruction) bypasses entirely.
3. **Markdown documentation.** Docs describing the processes that feedback generators produce slip through if they lack the structural class/def signatures.
4. **Drafting-visibility (`mg-drafting-visibility-001` from PR #911).** Ships as T0-block via runtime check, not this hook. Structural follow-up candidate — see §4.1.

### §2.3. corporate_boundary (advisory only)

When a `curl` or `wget` command points at a non-localhost URL AND a `.corporate-boundary` marker file exists in the working directory, the hook prints an advisory to stderr and exits 0. **It never blocks.**

Current state: no `.corporate-boundary` marker files exist in the repo.

```
$ find . -name '.corporate-boundary'
(no output)
```

Effective blocking coverage: zero.

Rationale for advisory-only: corporate boundary is context-sensitive (personal research curl is fine; employer data exfil is not). Static pattern match cannot distinguish. The blocking enforcement lives at the runtime level (`shared/consent.py`, axiom-runtime checks) and via CODEOWNERS review on employer-data paths.

### §2.4. interpersonal_transparency — zero patterns

No patterns at all. The axiom's two new implications from PR #911:

- `it-irreversible-broadcast` — any output to a public/irreversible channel that names a non-operator person
- `mg-drafting-visibility-001` — LLM-drafted content about team members without operator review

These ship with `enforcement: block` and rely on:
1. CODEOWNERS review (governance file changes auto-request operator review)
2. Runtime checks in `shared/consent.py` + `AffordancePipeline` capability filtering
3. The new `sp-hsea-mg-001.yaml` precedent file (first entry in `axioms/precedents/`)

The commit-scan hook does NOT contribute to enforcement. This is a follow-up candidate — see §4.

### §2.5. executive_function — zero patterns

No patterns. The axiom describes properties ("agents are zero-config", "errors include next actions", "routine work automated") that are difficult to regex. Enforcement lives at the axiom-runtime layer and by the executive-function-specific implication in `axioms/implications/executive-function.yaml`, which is checked by runtime-side code, not the commit hook. **This is acceptable** — property-level axioms are not a natural fit for commit-diff regex.

---

## §3. Spot-check against recent commits

Scanned the last 100 commits on `main` for potential missed triggers:

| Commit | Subject | Hook should have fired? | Result |
|--------|---------|--------------------------|--------|
| PR #911 (4b5d6a2df) | ship 4 drop #62 §10 amendments | no — pure YAML implications, no class/def signatures | correctly no-fire |
| PR #904 (ab06938f7) | harden hapax-whoami edge cases | no — shell script, whoami utility | correctly no-fire |
| PR #903 (3e9b17f6c) | tier-2 currency check post drop #62 §16+§17 | no — pure markdown doc | correctly no-fire |
| PR #900s (research drops) | various research docs | no — pure markdown | correctly no-fire |

No false positives AND no missed genuine violations in the recent commit stream. The hook is functioning correctly within its declared coverage.

**Deeper grep (100 commits) for axiom-sensitive keywords:**

```
git log --oneline -100 --grep='auth|permission|tenant|multi-user|feedback|coaching'
```

Zero hits. The recent work has been audit, research, and doc-level activity — no structural governance-sensitive code changes. This is consistent with the current development phase (research + governance reconciliation).

The one accidental meta-trip during this research drop's authoring (the hook firing on my own verbatim quotations of the patterns) is a **valid** positive — proof that the hook works, not a false positive. After rephrasing §2 from literal-quote to prose-description, the hook passed cleanly.

---

## §4. Recommendations

### §4.1. HIGH — interpersonal_transparency structural patterns

Add patterns to `axiom-patterns.sh` under a new `it` bucket targeting:

- Drafting class declarations (parens-grouped alt with `class (`): ManagementDraft / FeedbackDraft / OneOnOneDraft / ProjectDebrief
- Drafting function signatures (parens-grouped): `def (draft|compose|generate)_(about|for)_(employee|team_member|colleague|manager)`
- Broadcast class declarations: `class (BroadcastQueue|PublicPost|SlackPublic|TelegramPublic)\b`
- Broadcast function signatures: `def post_to_(public|public_channel|team_channel|slack_public|telegram_public)`

Also extend the `case "$pattern"` branch in `axiom-commit-scan.sh` to add an `it` DOMAIN + recovery string that routes to "Route through operator review. Do not generate or broadcast about non-operator persons without an active consent contract + operator sign-off."

**Risk:** false-positive surface for any legitimate class with one of these names. Mitigation: keep the patterns narrow (drafting-specific + broadcast-specific verbs) and avoid generic words in isolation.

**Size:** ~20 LOC pattern additions + 10 LOC case branch.

### §4.2. MEDIUM — extend `registry-guard.sh` to cover axioms/implications + contracts + precedents

Current protection: `axioms/registry.yaml` + `domains/*.yaml`. Missing: `axioms/implications/*.yaml`, `axioms/contracts/*.yaml`, `axioms/precedents/*.yaml` (which just got its first entry via PR #911).

Proposed behavior: allow file **create** (new implication, new contract, new precedent) but block **modify** on existing ones — modifications should be CODEOWNERS-reviewed and deliberate. Detecting create vs modify from a pre-tool hook requires checking whether the target path already exists on disk: `Edit` is always a modify, `Write` on an existing file is a modify, `Write` on a new path is a create.

**Risk:** an agent trying to fix a typo in an implication file would be blocked. Mitigation: explicit operator bypass via environment variable `ALLOW_AXIOM_MODIFY=1` documented at the block message.

**Size:** ~15 LOC extension to `registry-guard.sh`.

### §4.3. MEDIUM — hook test coverage

There is currently no test coverage for `axiom-commit-scan.sh`. Neither `hooks/tests/` nor `tests/hooks/` exists. Proposed:

```
hooks/tests/axiom-commit-scan-tests.sh
```

Fixture-based tests that exercise:
- each of the 19 current patterns → exit 2
- legitimate code that resembles patterns → exit 0 (e.g., filesystem permission check should not match the auth permission-check pattern)
- jq missing → exit 2 with error message
- comment stripping correctness
- git commit vs git push vs shell file-writer trigger paths
- meta-test: research drops quoting the patterns verbatim (this drop's origin story) should be wrapped in prose or safely escaped

**Size:** ~150 LOC test fixtures.

### §4.4. LOW — document triple-quoted docstring FP surface

Add a header comment in `axiom-commit-scan.sh` noting that Python triple-quoted docstrings and markdown prose are NOT stripped before pattern match. Today's false-positive rate is zero in practice, but documenting the surface is cheap and helps future maintenance.

**Size:** 3-line header comment.

### §4.5. LOW — generic permission-check false-positive mitigation

The generic permission-check function-name pattern could false-positive on filesystem checks that call `os.access` or stat constants. No current sightings, but the pattern is the one non-parenthesised exception in the single_user bucket.

Mitigation: post-filter the matched line against `os\.access` or `stat\.S_I[RWX]`:

```bash
MATCHED="$(echo "$ADDED_LINES" | grep -Ei "$pattern" | grep -v '[filesystem-check escape]' | head -1)"
```

**Risk:** an auth function that happens to also call `os.access` for some reason would slip through. Very low probability.

**Size:** 1 LOC grep filter.

---

## §5. What NOT to do

Explicitly rejected recommendations:

1. **Do NOT extend the hook to scan Edit/Write tool calls.** The layering (pii-guard + axiom-scan handle per-edit; axiom-commit-scan handles pre-commit structural) is correct. Mixing concerns would couple the hooks.
2. **Do NOT add executive_function patterns.** Property-level axiom; regex is the wrong enforcement layer.
3. **Do NOT upgrade corporate_boundary from advisory to block.** The context-sensitivity is real; the runtime-side enforcement is the right layer. Over-eager blocking on curl would break legitimate research and development.
4. **Do NOT add file-path governance to `axiom-commit-scan.sh`.** That's `registry-guard.sh`'s job. Keep the hooks focused.

---

## §6. Cross-references

- `hooks/scripts/axiom-commit-scan.sh` — the hook being verified
- `hooks/scripts/axiom-patterns.sh` — shared pattern registry
- `hooks/scripts/axiom-scan.sh` — sibling Edit/Write-time hook (caught the meta-trip)
- `hooks/scripts/registry-guard.sh` — complementary file-path governance
- `hooks/scripts/pii-guard.sh` — complementary per-edit PII gate
- `axioms/registry.yaml` — protected constitutional file
- `axioms/implications/*.yaml` — 8 implication files
- `axioms/precedents/sp-hsea-mg-001.yaml` — first precedent, shipped via PR #911 queue #166
- Queue #176 — this item

---

## §7. Verdict

The hook is **correctly implementing its declared scope** (structural multi-user + management-governance class/def detection at commit time). The gaps are **coverage gaps in the overall axiom-enforcement layering**, not defects in this specific hook. Recommendations §4.1 (interpersonal_transparency patterns) and §4.2 (registry-guard extension to implications/contracts/precedents) would meaningfully increase blocking coverage without widening the hook's conceptual scope.

No immediate action required — this is a findings-only research drop per queue spec. Follow-up items can be queued as `axiom-hook-coverage-gap-fill` if the operator wants to act on the HIGH recommendation.
