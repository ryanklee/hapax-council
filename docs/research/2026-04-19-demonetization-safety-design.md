# De-monetization Safety Gate — Design

**Date:** 2026-04-19
**Status:** Research + design (pre-implementation)
**Session:** cascade-2026-04-18 (delta)
**Scope:** Architectural design for a fail-closed safety gate that prevents
the livestream surface from emitting content that could trigger YouTube
demonetization, Content ID strikes, advertiser yellow-icon flags, or
adjacent platform-level revenue suspensions.
**Operator directive (verbatim, 2026-04-19):**
> "at no point should any content ever be a red-flag for de-monetization"
**Tracked as task #165.**
**Register:** scientific, neutral.
**Cross-refs:**
- `docs/governance/consent-safe-gate-retirement.md` — sibling fail-closed
  gate precedent (consent at ingestion, face-obscure at egress)
- `shared/governance/consent.py` + `shared/governance/consent_gate.py` —
  capability-level fail-closed gate pattern
- `agents/studio_compositor/face_obscure_integration.py` — egress-level
  fail-closed pattern (FAIL-CLOSED to full-frame mask on detector failure)
- `scripts/lint_personification.py` — build-time governance gate (task #155)
- `shared/compositional_affordances.py` — capability declaration site
- `agents/studio_compositor/youtube_turn_taking.py` — D2 single-slot gate
- `scripts/youtube-player.py` — current YouTube path with the half-speed
  DMCA-evasion hack (task #66)
- `docs/research/2026-04-19-youtube-content-visibility-design.md` — adjacent
  YouTube surface design
- `docs/research/2026-04-19-content-programming-layer-design.md` — sibling
  research (programmes-as-soft-priors)
- Memory: `feedback_no_expert_system_rules.md`, `project_programmes_enable_grounding.md`,
  `feedback_grounding_exhaustive.md`, `project_livestream_is_research.md`

---

## 1. Threat model — what platforms flag and demonetize

The livestream simulcasts to YouTube as the primary monetized surface; a
secondary Twitch simulcast is on the roadmap. The risk surface differs by
platform but is dominated by YouTube because that is where revenue lives.

### 1.1 YouTube — advertiser-friendly content guidelines

Per `support.google.com/youtube/answer/6162278` (2026 state), demonetizing
categories: **inappropriate language** (strong profanity permitted only in
first 7s and occasionally throughout; sustained or title/thumbnail use
yellow-icons; slurs against protected groups categorically demonetized),
**sexual content** (graphic depiction, not topic mention), **violence /
harmful acts** (graphic only), **hateful content** (categorical),
**recreational drugs / firearms** (promotion / modifications / sales),
**shocking content** (gore, distressed subjects — categorical),
**controversial issues** (graphic detail only; discussion permitted as of
the 2025 update), and **demonetized-by-reference** (gambling promotion,
recent-tragedy framing).

### 1.2 YouTube — Content ID / DMCA

Audio-fingerprint matching is robust to pitch / tempo / crop / noise
perturbations. Public reverse-engineering (Smitelli 2020) suggests deltas
must exceed ~5% to defeat the fingerprinter; the 2026 enforcement state
explicitly enumerates altered-content evasion (slow, pitch-shift, reverse)
as both detected and a Terms-of-Service violation. The current
`scripts/youtube-player.py:_playback_rate` 0.5x default is well outside the
~5% tolerance window and is therefore both ineffective AND a ToS
violation. Livestream Content ID matches mute audio in-stream + claim on
the VOD. Three live strikes terminate the channel.

### 1.3 YouTube — AI-generated / synthetic content

The 2025-2026 enforcement wave targets "AI slop"; January 2026 wave
terminated 16 channels (4.7B lifetime views). Two separate policy tracks:
**disclosure** (the `Modified or Synthetic` label is required for realistic
altered/synthetic content — deepfakes, synthetic voices of real people),
and **inauthentic content** (mass-produced low-effort AI content,
disclosure-independent). Hapax avoids the disclosure axis (no synthetic
real-people content). The inauthentic axis is the residual risk: an
advertiser or reviewer's read of "AI-driven channel" can produce
revenue-affecting decisions absent any policy violation. Mitigations:
operator's physical presence on cameras, operator's music production work,
explicit research-instrument framing.

### 1.4 Twitch — community guidelines + DMCA

Secondary surface (simulcast on roadmap). Material differences from
YouTube: DMCA strikes are permanent (no probation), three strikes
terminate. Music enforcement is more aggressive than YouTube's; mitigations
include separate audio buses per platform (mute on Twitch, play on
YouTube). Simulcast is permitted as of October 2023; combined-chat
penalty removed March 2026.

### 1.5 Platform-ambiguous / adjacent risk

Visible hardware logos (low risk unless critical), on-screen personal data
(governance + platform risk), chat text rendered on canvas (becomes
Hapax-emitted content for monetization purposes if rendered), and
third-party YouTube reaction content (inherits source risk; transformation
defense weakens with longer unaltered playback).

---

## 2. The content surfaces Hapax controls (blast-radius map)

| Surface | Path | Current safeguards | Risk |
|---|---|---|---|
| TTS narrative (`cpal/production_stream.py`) | LLM → Kokoro → audio mix | Anti-personification linter (build-time, task #155); persona pinning. **No runtime classifier.** | **High** |
| Captions overlay (`captions_source.py`) | Mirrors TTS → Pango → cairooverlay | Inherits TTS safeguards only | **High** |
| Activity header / chronicle / chat-legend / grounding ticker / stream overlay | LLM (chronicle) + template (activity, labels) | Build-time linter on some prompts; templates ungated | Medium |
| Ward labels / impingement cascade / recruitment candidates | Hand-authored capability descriptions in `compositional_affordances.py` | Code review | Low |
| Album / vinyl splattribution text | Discogs / operator playlist metadata | None | Low (text); HIGH on accompanying audio |
| YouTube reaction content (Sierpinski + D2 gate + dedicated ward) | Third-party video via `youtube-player.py` ffmpeg | Half-speed (#66) — **deprecated as defense per §7**. D2 single-slot gate. | **High** |
| Music on stream (vinyl / SoundCloud / future Hapax pool) | Operator-controlled into audio mix | No provenance tagging | **High** (DMCA) |
| Camera feeds | USB → `face_obscure_integration.py` → compositor | Faces fail-closed pixelated (#129). On-screen content / whiteboard / scrollback ungated | Medium |
| Chat rendering (chat-ambient ward) | Per task #123, aggregate counters only — confirm invariant | Design-level invariant only | Low (if invariant holds) |
| Research condition IDs / labels | Bounded internal taxonomy | — | Low |
| Ward choreography signature artefacts (BitchX MOTD, quit-quips, kick-reasons) | Hand-authored catalog | Code review; `refuses_anti_patterns` package set | Low-Medium |

High-tier surfaces — TTS + captions, YouTube reaction content, on-stream
music — drive the classifier and provenance design in §4-§7.

---

## 3. Resolving the expert-system-rules tension

This is the design crux. The operator's directive — "at no point should any
content ever be a red-flag for de-monetization" — reads like a deny-list:
"never emit a red-flag word." But the architecture has explicitly retired
deny-list-style rules (per `feedback_no_expert_system_rules.md` and the
F1/F2 retirements in PR #1107: variety-gate, narrative-too-similar,
activity-rotation). The tension is real, and the resolution is structural,
not stylistic.

### 3.1 The thesis

Demonetization-safety is not a tactical rule like "narrative-too-similar"
(which the pipeline should decide via recruitment scores). It is a
**governance axiom** — the same tier as `interpersonal_transparency`
(consent) and the face-obscure invariant. The stack already has precedent
for governance-axiom-level fail-closed gates that coexist with the
no-expert-system-rules architecture:

- `ConsentRegistry.contract_check` removes non-consented capabilities from
  the candidate set BEFORE the pipeline scores anything (CLAUDE.md
  §Unified Semantic Recruitment).
- `face_obscure_integration.py` returns a full-frame Gruvbox-dark mask on
  detector failure — fail-closed at egress.
- `lint_personification.py` is a CI-blocking build-time gate.

These coexist with rules-are-bugs because they operate at the
**axiom-enforcement layer**, not the **decision-making layer**. The
axiom-enforcement layer removes entire capability/pixel/token classes from
the operating set, fail-closed under uncertainty; the decision-making
layer scores remaining options via cosine + base-level + context +
Thompson. A rule like "if narrative contains 'fuck' >3x, withhold" sits at
the decision layer and is a violation. A capability-class declaration "this
capability emits high-risk content, exclude from candidacy unless the
active programme opts in" sits at the axiom layer, alongside consent.

### 3.2 The proposal

Demonetization-safety is implemented as a sibling governance-axiom-level
gate. Concretely:

- Extend capability declarations
  (`shared/affordance.py::OperationalProperties`) with a
  `monetization_risk: Literal["none", "low", "medium", "high"]` field plus
  a `risk_reason: str` for documentation.
- Fail-closed candidate filter:
  `monetization_risk in {"medium", "high"}` capabilities are NOT in the
  pipeline's candidate set unless the active programme has explicitly
  flagged them as opt-in (programme-level, operator-curated; see §6).
  `monetization_risk == "high"` is permanently excluded — programmes
  cannot opt in.
- Post-generation content classifier on LLM-generated text (the high-tier
  surfaces from §2) — a lightweight classifier pass, surfaced as a signal
  for next-tick recruitment rather than silently dropped (see §4-§5).
- Egress audit log (sample-rate JSONL of what landed on the livestream)
  for human-reviewable post-hoc audit and classifier improvement.

The decision-making layer sees only safe candidates. The pipeline scores
the safe candidates against the live moment. Speech, ward choreography,
preset family selection — all the dynamic recruitment behavior — happens
exactly as before, but on a candidate set that has had the high-risk
content classes pre-filtered out. This is the same shape as consent: the
operator can interact with non-operator persons whose contracts are
active, and the pipeline picks the right capability for the moment among
the consented options.

This resolves the tension. There is no "if rendered_text contains X then
withhold" rule sitting between recruitment and emission. There is a
candidate-set filter at the axiom-enforcement layer (§4 Ring 1) plus a
classifier-as-signal at the post-generation boundary (§4 Ring 2) that
emits an impingement, letting the pipeline make a grounded recovery
decision on the next tick.

---

## 4. The Content Safety Layer — architecture

Three concentric rings. Each ring is independently testable, independently
deployable, and has its own failure mode + recovery path (§9). The rings
are listed inside-out (closest to the LLM call first).

### 4.1 Ring 1 — capability-level axiom gate (fail-closed removal)

Runs at `AffordancePipeline.select()` time, before any scoring. Removes
capabilities from the candidate set when:

- `monetization_risk == "high"`: always excluded.
- `monetization_risk == "medium"`: excluded unless the active programme's
  `monetization_opt_ins` set contains the capability name.
- `monetization_risk == "low"`: included; logged in egress audit (§4.3).
- `monetization_risk == "none"`: included; not separately logged.

This is structurally the same as the existing consent gate filter. The
filter runs on the result of the Qdrant cosine retrieval, before
base-level + Thompson scoring. Capabilities never enter the score
competition.

### 4.2 Ring 2 — pre-render content classifier (signal-emitting)

Runs on every LLM-generated text emission destined for an externally
visible surface (TTS, captions, chronicle, activity header narration,
director commentary on the YouTube embed ward). Does NOT run on
hand-authored template content (ward labels, signature artefacts,
capability names) — those are handled by code review + the build-time
linter (§4 Ring 0, below).

Process:

1. LLM emits `rendered_text` for surface `S`.
2. Classifier produces `RiskAssessment` (§5).
3. If `assessment.score >= 2`: withhold render, emit a `content.flagged`
   impingement carrying `{surface_kind, score, guideline, original_capability}`.
   The pipeline's next tick receives this impingement as perceptual ground
   and recruits an alternative capability (a different narrative, a quieter
   ward emphasis, a recede-to-vinyl move). No expert-system retry logic;
   the recovery is grounded in the same recruitment loop.
4. If `assessment.score < 2`: render proceeds, egress-audit logs the
   payload + score (§4.3).

The classifier emits a signal; it does NOT make the next decision. The
pipeline does. This is the architectural distinction from a deny-list.

### 4.3 Ring 3 — egress audit (sample-rate JSONL)

Append-only JSONL at `~/hapax-state/monetization-audit/egress-{date}.jsonl`,
one entry per render at low-tier surfaces and 100% per render at high-tier
surfaces. Schema:

```
{
  "timestamp": "2026-04-19T14:32:01Z",
  "surface_kind": "tts" | "captions" | "chronicle" | "activity_header" | ...,
  "capability": "say.spontaneous-narration" | ...,
  "rendered_text": "...",         // truncated to 512 chars
  "classifier_score": 0..3,
  "guideline": "inappropriate_language" | null,
  "music_provenance": "operator-vinyl" | "soundcloud" | "hapax-pool" | null,
  "youtube_source": {url, title, channel, runtime_s} | null,
  "decision": "rendered" | "withheld",
  "decision_reason": "..."
}
```

For human-reviewable post-hoc audit and classifier improvement. The audit
log is the corpus for tuning the classifier prompt and identifying
false-positive / false-negative patterns. Daily rotation; 90-day retention.

### 4.4 Ring 0 — build-time linter (existing pattern, extend)

Already implemented for the personification axiom
(`scripts/lint_personification.py`). Extend the same shape to scan the
hand-authored content surfaces — capability descriptions, ward labels,
signature artefact catalog entries, MOTD/quit-quip blocks — for terms
matching the deny-list categories from §1.1. Failures block merge.
Catalog edits are rare; this is the cheap layer.

### 4.5 Architectural sketch (Pydantic-shape, not real code)

```
class RiskAssessment(BaseModel, frozen=True):
    score: int  # 0..3 (0=none, 1=low, 2=medium, 3=high)
    guideline: str | None  # which YouTube guideline triggers, if any
    redaction_suggestion: str | None  # for human audit / classifier improvement

class MonetizationRiskGate:
    def candidate_filter(
        self,
        capabilities: list[Capability],
        programme: Programme | None,
    ) -> list[Capability]:
        """Ring 1. Filter by capability.monetization_risk + programme opt-ins."""

    def content_classify(
        self,
        rendered_text: str,
        surface_kind: str,
    ) -> RiskAssessment:
        """Ring 2. Synchronous local-LLM classifier call. <10ms expected."""

    def egress_log(
        self,
        payload: RenderedContent,
        decision: Literal["rendered", "withheld"],
        reason: str,
    ) -> None:
        """Ring 3. Append to per-day JSONL."""
```

The gate is owned by a single module
(`shared/governance/monetization_safety.py` is the natural location,
sitting next to `consent.py` and `consent_gate.py`).

---

## 5. The classifier (Ring 2 detail)

Per `feedback_director_grounding.md` and `feedback_grounding_exhaustive.md`,
all LLM moves are grounded. The classifier is itself a grounding move:
it perceives rendered text against guidelines. It is therefore not a
separate tier — it is a structured sub-prompt to the grounded model that
runs director generation (`local-fast` LiteLLM → TabbyAPI Qwen3.5-9B
EXL3). No additional VRAM; same model already loaded.

**Prompt shape.** Structured JSON-only output. Inputs: cached YouTube
guidelines (24h refresh via `WebFetch`, fallback to last-known on fetch
failure with stale alert at >7d); the rendered text; the surface kind
(TTS spoken weighs more than a chronicle log entry). Output schema:

```
You are evaluating one piece of rendered content for advertiser-friendly-content
risk on YouTube. Apply the guidelines below; return JSON only.

Guidelines (cached 2026-04-19):
- Inappropriate language: occasional strong profanity is permitted; sustained
  use, title/thumbnail use, or slurs targeting protected groups are not.
- ... [remaining categories from §1.1] ...

Surface: {surface_kind}
Rendered text: """
{rendered_text}
"""

Return JSON: { "score": 0|1|2|3, "guideline": "<category>|null",
"redaction_suggestion": "<one-line suggestion or null>" }
```

**Score semantics.** 0 = none; 1 = low (render, audit-only); 2 = medium
(withhold + `content.flagged` impingement); 3 = high (withhold +
`content.incident` impingement + suppress same-capability for 5 ticks via
affordance `suppression_until`).

**Recall over precision.** False positive = one withheld utterance + one
recovery impingement. False negative = yellow icon / Content ID strike.
Tune for higher scores under uncertainty.

**Operating envelope.** Synchronous, blocking. p50 ≤ 10ms, p99 ≤ 50ms;
>100ms triggers classifier-degradation control law (§9). LRU cache
`(rendered_text → RiskAssessment, maxsize=1024)` for repeated utterances
(chronicle headers, attribution lines).

---

## 6. Programme-layer interaction

Per the sibling content-programming-layer research doc (parallel work
2026-04-19) and `project_programmes_enable_grounding.md`, programmes are
affordance-EXPANDERS with soft priors, never affordance-replacers. The
demonetization gate interacts at Ring 1 only.

**Programme `monetization_opt_ins`.** A `frozenset[str]` field naming
capabilities whose `monetization_risk == "medium"` the programme accepts.
Example: a "loose-rap-session" programme opts into `say.profanity-eligible`
(register-heavier capability) while Ring 2 classifier still filters
rendered text. Default ("calm-listening-session") opts into nothing —
only `none`/`low` capabilities candidate.

**Authorship constraint.** Operator-authored programmes only. Hapax-authored
programmes with non-empty `monetization_opt_ins` fail validation. This
preserves the human-in-the-loop property the consent system depends on
— a Programme cannot grant a capability the operator did not explicitly
sanction.

**Hard limits.** `monetization_risk == "high"` is permanently in the
deny-set; no programme can opt in. Ring 2 classifier ALWAYS runs
regardless of programme — opt-in expands candidacy, does not bypass
classification.

**Symmetry with consent.** A capability declares `consent_required=True`;
the gate filters unless an active bilateral contract exists. A capability
declares its risk; the programme can opt into medium-risk capabilities,
but the operator-authorship requirement on programmes mirrors the
bilateral-contract requirement on consent.

---

## 7. Music + vinyl — the DMCA corner

The vinyl-on-stream path and the YouTube half-speed playback hack
(`scripts/youtube-player.py:_playback_rate` defaulting to 0.5x) are the
current state. The half-speed hack is not a defense per the §1.2 research
findings: Content ID's tolerance for pitch/tempo deltas is roughly ±5%,
not ±50%, and the 2026 enforcement state explicitly enumerates pitch-shift
and speed-change as evasion attempts that constitute a Terms of Service
violation. The current behavior carries both DMCA-strike risk and a
ToS-violation overlay.

### 7.1 Music provenance tagging

Add a `music_provenance` tag at the splattribution layer (`scripts/youtube-player.py`
already writes attribution files; extend the schema). Values:

- `operator-vinyl` — operator owns the physical record. Fair-use-adjacent
  for playback in the studio; DMCA risk on broadcast is HIGH but the
  operator's ownership is the policy claim.
- `soundcloud-licensed` — operator's SoundCloud account; per-track license
  read from SoundCloud metadata. Some are CC-BY, some are all-rights-
  reserved. The provenance tag carries the per-track license string.
- `hapax-pool` — Hapax-curated license-cleared pool (future, task #130).
  License statuses pre-cleared at pool ingestion; only `cc-by`, `cc-by-sa`,
  `public-domain`, and `licensed-for-broadcast` tracks are eligible.
- `youtube-react` — third-party YouTube content, see §7.3.
- `unknown` — fail-closed: if provenance cannot be determined at playback
  time, the audio path is muted (silent video) and a
  `music.provenance.unknown` impingement fires for operator review.

Egress audit (Ring 3) records the provenance tag for every track that
plays. This is the audit trail.

### 7.2 YouTube reaction content — recommend mute + transcript overlay

The half-speed hack should be retired. Three alternatives, in order of
preference:

1. **Mute YouTube audio entirely; render transcript overlay.** Use yt-dlp
   to fetch caption tracks (when available); render captions in the
   dedicated YouTube embed ward (per the 2026-04-19 visibility design). The
   operator's voice carries the audio of the moment; the visual + caption
   carries the source content. This is the cleanest defense — Content ID is
   audio-fingerprint-driven; muted audio cannot match.
2. **Short-clip framing.** Limit each YouTube source's playback to ≤ 30s
   contiguous and require ≥ 60s of operator-narrated transformation between
   replays of the same source. Fair-use adjacent; not a guaranteed defense.
   Defer until alternative 1 is shipped.
3. **Source-swap to Creative Commons / licensed equivalents.** Long-term
   path for the Hapax-curated pool (task #130). Not applicable to the
   reaction-mode use case where the source IS the subject.

**Recommendation:** ship alternative 1 as the default. Make
`HAPAX_YOUTUBE_PLAYBACK_RATE` removable (no rate manipulation; play at
1.0x). Mute the audio output of the youtube-player ffmpeg pipeline; route
the YouTube audio nowhere. Render transcript overlay in the dedicated
YouTube embed ward when captions are available.

### 7.3 SoundCloud — per-track license enumeration

Operator's linked SoundCloud account contains tracks under varying
licenses. The integration (task #131) must enumerate licenses at
ingestion time and tag accordingly. Tracks without a clear license tag
default to `unknown` and are excluded from the play queue. This is a
data-quality requirement on the SoundCloud integration; the monetization
gate consumes the tag, it does not derive it.

---

## 8. Personified-AI + advertiser perception

The 2025-2026 YouTube enforcement wave on AI-generated content is the
adjacent risk. Hapax avoids the disclosure requirement (no synthetic voices
of real people, no deepfake content of real events) and avoids the
inauthentic-content axis (the operator is physically present; the canvas
shows real cameras, real music production). But advertiser perception is
its own axis — an advertiser scanning the channel may make a
decisional call about "AI-driven channel" that does not require a policy
violation to manifest.

### 8.1 Egress-level "research instrument" footer

Proposal: add a non-removable footer to the chronicle and captions wards:

> Council research instrument — experimental cognitive architecture
> (operator: <name>, research home: <url>)

Renders in BitchX-grammar muted-grey, low-prominence, persistent across
all stream modes. Frames the channel for advertiser review without
claiming AI sentience (which would tangle with the anti-personification
axiom). The operator's name + research URL contextualizes the channel as
operator-driven research, not autonomous AI content.

### 8.2 Limits

- Will not address the underlying inauthenticity-policy enforcement. If
  Hapax content reads to a reviewer as "channel of an AI making decisions
  by itself", the footer is a small mitigation. The structural mitigations
  are the operator's physical presence + the operator's curated music +
  the explicit research framing throughout the stream copy (channel
  description, video titles, thumbnails).
- The footer text itself must pass Ring 0 lint + Ring 2 classifier as an
  invariant. Rendered every frame, so the cost is dominated by once-per-
  startup classification + cache hit thereafter.

---

## 9. Failure modes + recovery

| Mode | Detection | Recovery |
|---|---|---|
| **Classifier false negative** (risky content leaks) | Ring 3 audit + operator review + `monetization_safety.estimated_fnr` metric | Emit `content.incident` impingement → pipeline switches to `quiet-frame` programme (vinyl-only, no TTS) for ~20 ticks; classifier prompt updated with the missed example |
| **Classifier false positive** (safe content blocked) | Ring 3 log records `decision: "withheld"` | `content.flagged` impingement fires; pipeline recruits alternative on next tick. Operator can whitelist a per-pattern (regex) entry via `hapax-monetization-whitelist add <pattern>` (Phase 7). Flagged content time-windowed at 7 days in `~/hapax-state/monetization-flagged/` |
| **Classifier unavailable** (TabbyAPI down) | `content_classify` raises / 200ms timeout | **FAIL-CLOSED**: withhold ALL LLM-generated text for external surfaces; templates-only emission for surfaces that have them; TTS goes silent. Same control-law shape as consent gate (3 consecutive failures → degraded + ntfy `priority=high`; 5 successes → nominal) |
| **Programme opt-in abuse** (overly-broad opt-ins) | Programme-switch emits `programme.entered` carrying opt-in set; operator audit | Hapax-authored programmes with `monetization_opt_ins` fail validation; hard-cap `MAX_OPT_INS = 3`. Ring 2 classifier still runs regardless of opt-in |
| **Egress audit log fills disk** | `du` exceeds 1 GiB | 90-day retention + daily gzip rotation; rotation failure ntfys but gate continues to log (protection > disk hygiene) |
| **Half-speed hack reintroduction** | CI test asserts `_playback_rate()` returns 1.0 (or function is removed) | Phase 5 ships the audio-mute migration as a single commit that removes the rate-manipulation path |

---

## 10. Integration sequencing (post-live)

Phase breakdown follows the same shape as the homage-completion plan
(scope, dependencies, parallel-safe siblings, success criteria, LOC
estimate). Each phase ships independently and is testable in isolation.

| # | Phase | Depends | LOC | Success criterion |
|---|---|---|---|---|
| **1** | `MonetizationRiskGate` primitive + `OperationalProperties.monetization_risk` field + capability annotations + Ring 1 filter wired into `AffordancePipeline.select()` next to the consent filter | — | ~250 | All capabilities annotated; high-risk filter test passes |
| **2** | Pre-render classifier + `content.flagged` impingement emission. Wire into `cpal/production_stream.py` (TTS) + `captions_source.py` | 1 | ~400 | p50 ≤ 10ms; impingement present in `impingements.jsonl`; integration test confirms next-tick recovery |
| **3** | Programme `monetization_opt_ins` field + Ring 1 plumbing; Hapax-authored programmes with opt-ins fail validation; hard-cap `MAX_OPT_INS = 3` | 1 + parallel content-programming epic | ~150 | Validation tests pass |
| **4** | Egress audit JSONL + daily gzip rotation + sample-rate config | 2 | ~200 | Audit log present; 90-day cleanup runs |
| **5** | Music provenance tagging (`music_provenance` on splattribution); SoundCloud license enumeration; **mute YouTube audio**; remove `_playback_rate`; transcript overlay where captions exist | 4 | ~350 | YouTube audio muted by default; provenance written for every track; unknown → muted + impingement |
| **6** | Anti-personification "research instrument" footer on chronicle + captions wards | 4 | ~80 | Footer present in layout snapshot |
| **7** | Operator review + whitelist CLI (`hapax-monetization-flagged`, `hapax-monetization-whitelist`) | 2 + 4 | ~250 | Whitelist reduces FP rate without weakening high-risk filter |
| **8** | Incident-recovery `quiet-frame` programme triggered by `content.incident` for 20 ticks | 3 + parallel epic | ~180 | Programme switch + auto-exit verified |

Total: 8 phases, approximately 1860 LOC. Phases 1 + 2 are the
minimum-viable safety surface; Phases 3-8 deepen the recovery + audit
capabilities. Phase 5 (music provenance + YouTube audio mute) is the
highest-impact DMCA-risk reduction and should be prioritized after
Phase 2.

---

## 11. Open questions (for operator)

The two highest-leverage decisions are bolded.

1. **MUSIC POLICY** — Confirm §7 recommendations: vinyl stays (HIGH DMCA
   risk, accepted), SoundCloud enumerates licenses + `unknown` mutes,
   future Hapax-pool license-cleared only, **YouTube reaction audio
   muted by default with transcript overlay**. Loosening any of these
   re-opens the most likely demonetization vector.

2. **REACTION-CONTENT VIABILITY UNDER MUTE** — The 2026-04-19 visibility
   design's intent ("YouTube content needs to be more visible") was
   audio-inclusive. Muting reduces the use case to silent video +
   transcript + operator-narrated reaction. Acceptable, or does the
   operator prefer the §7.2 alternative 2 (≤30s contiguous clips +
   operator-transformative narration as fair-use defense) at higher
   strike risk?

3. False-negative tolerance — target <0.1% miss rate (≤1.4 missed
   utterances per 24h at 1 emission/min)? Tighter is safer at the cost
   of expressive register.

4. Operator face — should any content class trigger face-obscure on the
   operator (sensitive screen-share, on-screen personal data)? Trigger
   mechanism — hotkey, content classifier on screen surface, both?

5. Chat content rendering — confirm the task #123 invariant holds
   (aggregate counters only, no message text). Roadmap to render chat
   messages on canvas?

6. Whitelist pattern grain — regex (powerful, broaden-prone) vs exact
   string (safe, tedious)?

7. `MAX_OPT_INS = 3` adequate, or is an "improvisation session"
   programme planned that needs more?

8. Egress audit retention — 90 days enough to back-trace a Content ID
   strike or yellow-icon notification?

9. "Research instrument" footer wording — accept §8.1 draft or
   alternative framing?

10. Twitch simulcast scope — gate enforces full posture across both
    platforms, or per-platform audio bus with gate only on the
    YouTube-bound bus?

---

## Sources

- [Advertiser-friendly content guidelines — YouTube Help](https://support.google.com/youtube/answer/6162278?hl=en)
- [Upcoming and recent ad guideline updates — YouTube Help](https://support.google.com/youtube/answer/9725604?hl=en)
- [How Content ID works — YouTube Help](https://support.google.com/youtube/answer/2797370?hl=en)
- [Fun with YouTube's Audio Content ID System — Smitelli](https://www.scottsmitelli.com/articles/youtube-audio-content-id/)
- [DMCA on YouTube in 2026: Takedowns & Copyright Strikes — DMCAdesk](https://dmcadesk.com/blogs/dmca-on-youtube-copyright-strikes-and-takedowns/)
- [YouTube AI Content Policy 2026 — Upgrowth](https://upgrowth.in/youtubes-new-policy-a-step-towards-transparency-in-ai-generated-content/)
- [YouTube AI Monetisation Policy 2026 — Boss Wallah](https://bosswallah.com/blog/creator-hub/youtube-ai-monetisation-policy-2026-what-changes-whats-allowed-and-whats-banned/)
- [YouTube Inauthentic Content Policy: AI Enforcement Wave 2026 — Flocker](https://flocker.tv/posts/youtube-inauthentic-content-ai-enforcement/)
- [Twitch DMCA & Copyright FAQs](https://help.twitch.tv/s/article/dmca-and-copyright-faqs?language=en_US)
- [Twitch Simulcasting Guidelines FAQ](https://help.twitch.tv/s/article/simulcasting-guidelines?language=en_US)
- [The Era of Simulcasting 2026 — StreamMetrix](https://streammetrix.com/blog/ultimate-simulcasting-guide-2026)
