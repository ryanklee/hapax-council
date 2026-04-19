# Blinding Defaults Audit — What's Masking Recruitment Failures

Date: 2026-04-19
Branch: `hotfix/fallback-layout-assignment`
Author: cascade audit pass
Sibling document: `docs/research/2026-04-19-expert-system-blinding-audit.md` (gates / thresholds — concurrent sweep)
Operator directive: "Make sure no DEFAULTS are blinding us similarly."

---

## §0 TL;DR

- **47 defaults audited** across the director / homage / compositor / CPAL / persona surface.
- **18 are Category A** (behavior defaults that mask recruitment failure or absence and SHOULD retire or be made explicit).
- **6 are Category C** (fail-closed / safety; legitimate).
- **9 are Category B** (legitimate observability / infrastructure).
- **5 are "ceremonial defaults"** — the most dangerous class: a field is always populated but its value is the recruitment-bypass default, which silently passes the no-vacuum invariant while the recruitment surface is in fact dark.
- **9 are Category D** (ambiguous; further research needed).
- **Live evidence is conclusive**: in `director-intent.jsonl` (994 ticks, last several days), `condition_id=none` 994/994 (100%); `structural_intent` MISSING ENTIRELY in 994/994 records (the writer never serialized it because the field defaulted to an empty container the JSONL writer dropped under `model_dump(mode='json')` exclude semantics, OR the running director predates the cascade-delta change). Either way, **the structural-intent recruitment path has not produced a non-default emission in any captured tick**.
- **5 retire-first defaults** identified (§7).
- **3 blocker recruitment paths** must be built before retirement (§4 / §6 / Family E).

The headline pattern: **the system has been declaring "I emitted intent" while emitting the absence of intent**. Every default in this report's Category A is a place where "no recruitment fired" looks identical to "recruitment chose this safe value", and the observability stream cannot distinguish them.

---

## §1 Cross-reference to sibling gates audit

The sibling audit (`2026-04-19-expert-system-blinding-audit.md`, scheduled output) sweeps for `if X > THRESHOLD then Y` shape gates: timer cadences, salience cutoffs, dwell windows, cooldowns. This audit is the dual sweep: defaults that supply a behavior when the recruitment path produced no answer.

The two audits are conceptually orthogonal but they overlap at one point: many gates have a default *threshold value*, and gating-disabled paths fall back to a default *behavior*. Where this audit catalogs an env-controlled parameter with a literal fallback (e.g. `HAPAX_NARRATIVE_CADENCE_S` default `30.0`), the gates audit catalogs the threshold semantics around that value. We've refrained from double-listing.

Operator axiom (canon source: `~/.claude/projects/-home-hapax-projects/memory/feedback_no_expert_system_rules.md`):

> Behavior must emerge from impingement → recruitment → role → persona. A default-value fallback that fires when recruitment doesn't produce an answer is equally blinding — it makes an uncovered case look "handled" when it's actually "recruitment failed or never ran."

Combined with the operator's no-vacuum invariant (2026-04-18, "every tick MUST emit at least one compositional_impingement"), the present audit reframes that invariant. **The current implementation satisfies the no-vacuum invariant by emitting silence-hold defaults — i.e., it satisfies the LETTER (every tick has ≥1 impingement) by violating the SPIRIT (every tick should have a recruited move, not a synthesized stand-in)**. Multiple Category A defaults below are direct artefacts of this letter-vs-spirit tension.

---

## §2 Per-default table — Category A (retire / make explicit) and D (ambiguous)

Columns: `File:Line` | `Default` | `When it fires` | `Current value` | `Recruitment failure it masks` | `Proposed alternative` | `Scope (cat)`

### A.1 Director loop — narrative tier

| File:Line | Default | When it fires | Current value | Recruitment failure it masks | Proposed alternative | Cat |
|---|---|---|---|---|---|---|
| `agents/studio_compositor/director_loop.py:819` | `self._activity = "react"` (`__init__`) | First director tick before any LLM call | `"react"` | "Director recruitment never ran for this process lifetime" | Start in `self._activity = None` and treat the first tick as `IDLE_AWAITING_FIRST_TICK`; refuse to publish any director-intent record until the first LLM-recruited intent lands. Idle → emit a NULL-tick observability marker (not a synthesized intent). | A |
| `agents/studio_compositor/director_loop.py:31-49` | `_silence_hold_impingement()` | Parser empty/non-dict/JSON-decode/legacy-shape paths | `intent_family="overlay.emphasis", material="void", salience=0.2, narrative="Silence hold: maintain the current surface…"` | LLM parse failure or LLM legacy-shape emission (i.e., model has no idea about the new schema) | Emit `Impingement(kind="parse_failure", source="director.parser", content={raw: ...})` to the AffordancePipeline and let the pipeline either recruit a recovery capability or surface a NULL-tick. The "silence is a recruited choice" insight (in the prompt itself, lines 803-809) MUST hold here too — silence cannot be the parser's fallback, only the recruitment's outcome. | A (CEREMONIAL — this default fires every parser failure and writes a `compositional_impingement` to the DMN stream that downstream consumers cannot distinguish from a real silence recruitment) |
| `agents/studio_compositor/director_loop.py:67-103` | `_silence_hold_fallback_intent(activity, narrative_text, reason, tier, condition_id)` | Wrapper that calls `_silence_hold_impingement()` + populates `structural_intent=NarrativeStructuralIntent(homage_rotation_mode="weighted_by_salience", ward_emphasis=["thinking_indicator","stance_indicator"])` | Hardcoded ward names + rotation mode | Same as A.1 row 2: parser failure. The structural_intent default ALSO synthesizes ward emphasis the LLM never picked. | Same as above; structural_intent fallback should be NULL, not a hardcoded list. The ward emphasis the LLM picked when it had a chance is the only legitimate emphasis. | A (CEREMONIAL) |
| `agents/studio_compositor/director_loop.py:131` | `fallback_activity: str = "react"` (kwarg default in `_parse_intent_from_llm`) | Legacy-shape path where LLM emitted `{}` with no `activity` field | `"react"` | "LLM emitted empty/garbled JSON" — the system pretends the LLM wanted react. | Make `fallback_activity` REQUIRED, no default. Caller must supply NULL or a derived stance-aware default; better, eliminate the fallback path and instead route to the parse_failure impingement above. | A |
| `agents/studio_compositor/director_loop.py:481` | `DIRECTOR_MODEL = os.environ.get("HAPAX_DIRECTOR_MODEL", "local-fast")` | Process startup w/o env var | `"local-fast"` | Operator never selected a model — system silently picks the local Qwen | Refuse to start without `HAPAX_DIRECTOR_MODEL` set in the systemd unit. The choice "local vs claude-sonnet vs gemini-flash" is a recruitment-grade decision that should not be defaulted by a hardcoded fallback — the operator's stimmung / cost / quality trade-off depends on it. (D: defensible if the systemd unit always sets it explicitly, in which case this is dead code.) | D |
| `agents/studio_compositor/director_loop.py:503` | `PERCEPTION_INTERVAL = float(os.environ.get("HAPAX_NARRATIVE_CADENCE_S", "30.0"))` | Same | `30.0` seconds | Cadence selection should be governance-driven (see also feedback `model_routing_patience.md`); 30s default freezes a tradeoff that varies with stimmung + model selection | Move to `shared/working_mode.py`-derived cadence: research mode → 30s; rnd → 12s (operator's prior preference). Eliminate hard literal. | D |
| `agents/studio_compositor/director_loop.py:1055` | `condition_id = _read_research_marker() or "none"` | Research marker file absent / empty | `"none"` | Phase 9 research condition was never opened (operator forgot, registry script never ran, file deleted). | Refuse to write a director-intent record without a real condition_id. Live ticks should be `condition_id="ambient"` explicitly written by an always-on default opener; "none" should signal "NO research framework loaded → audit alert" not "default condition." | A (CEREMONIAL — see §3 / §4 evidence; 994/994 ticks `condition_id="none"`) |
| `agents/studio_compositor/director_loop.py:1075` | `_parse_intent_from_llm(result, fallback_activity="react", …)` callsite default | LLM tick produced output but legacy-shape parsing | `"react"` | Same as A.1 row 4. | Same. | A |
| `agents/studio_compositor/director_loop.py:1310-1311` | `_ACTIVITY_VARIETY_WINDOW = 3`, `_ROTATION = ("observe", "music", "study", "chat")` | Method-local literals; LLM picked the same activity 3 ticks in a row | Window=3, rotation cycle hardcoded | This isn't masking recruitment failure per se — it's masking *re-emission failure*. The LLM keeps choosing react because the perceptual field genuinely rewards it. The fix synthesizes an activity from a hardcoded cycle. | The rotation cycle should itself be recruited (capability "recruit-activity-variety" with stimmung-aware weights). Hardcoded rotation list is operator-readable and tunable, but the choice of WHEN to enforce it (window=3) is a gate (see sibling audit) and the choice of WHICH alternates to cycle through is a default behavior. | D |
| `agents/studio_compositor/director_loop.py:1368-1422` | `micromove_cycle: list[tuple[...]]` (7 hardcoded micromove archetypes) | LLM produced empty / silence / repeated narrative | 7 entries cycling through overlay.emphasis / preset.bias / camera.hero / ward.highlight | "LLM call timed out / returned empty / produced a near-duplicate" — director synthesizes a recruitment from a frozen vocabulary | These micromoves currently bypass the AffordancePipeline entirely (they're written directly to JSONL + structural_intent). They satisfy the no-vacuum invariant *by faking recruitment*. Replace with: emit `Impingement(kind="director_micromove_request", salience=0.3)` and let the AffordancePipeline pick a registered "ambient drift" capability against it. The 7 micromoves should be 7 registered capabilities the pipeline can recruit — same surface effect, fully observable as recruitment events. | A (CEREMONIAL — these ARE pretending to be real director moves and are written to the same `_emit_intent_artifacts` path as a real LLM emission) |
| `agents/studio_compositor/director_loop.py:1431-1432` | `salience=0.35, dimensions={}` in micromove `CompositionalImpingement` constructor | Same as above | `0.35` and empty | Salience is a load-bearing scoring input for the AffordancePipeline; hardcoding 0.35 means a micromove fallback always scores in a fixed band regardless of the perceptual signal that triggered it (LLM empty vs LLM repeat vs LLM silence) | Compute salience from the failure reason: `llm_empty=0.5` (something is wrong, raise pressure); `narrative_repeat=0.2` (operator sees variety problem, dampen); `silence_or_empty=0.3`. Stop hardcoding. | A |
| `agents/studio_compositor/director_loop.py:1447-1448` | `activity="observe"` for micromove DirectorIntent | Same | `"observe"` | "Real activity could not be determined" | Use the parsed-but-rejected activity if available; otherwise emit `activity="parse_failure"` (requires extending `ActivityVocabulary` Literal, which is the right move per "silence as voice, parse_failure as parser"). | A |
| `agents/studio_compositor/director_loop.py:1478` | `condition_id = _read_research_marker() or "none"` (degraded path) | Same as A.1 row 7 | `"none"` | Same | Same | A |
| `agents/studio_compositor/director_loop.py:1487-1488` (degraded silence-hold) | `_silence_hold_fallback_intent(activity="silence", narrative_text="", reason="degraded", …)` | DEGRADED mode active | hardcoded silence with structural_intent default | "Service rebuilding, LLM tier draining" — this is NOT a recruitment failure but a system-state failure | This is borderline Category C (legitimate fail-closed during a rebuild) BUT the issue is it WRITES TO THE SAME JSONL as real recruited intent. Researchers reading the log cannot tell DEGRADED-derived from real silence. Tag every degraded record with `_was_degraded: true` so observability can filter; do NOT emit a `compositional_impingement` during DEGRADED, just emit a NULL-record. | D (justification depends on operator preference: real null-record vs. tagged silence-hold) |
| `agents/studio_compositor/director_loop.py:1538-1539` | `_alignment(activity)` returns `0.6 if active, else 0.3` | Activity override gate | hardcoded weights | "We don't know how aligned this activity is" | Compute alignment from objective text similarity (Qdrant lookup against active objectives) instead of binary in/out membership. The 0.6 / 0.3 are gate values; see sibling audit. | D |
| `agents/studio_compositor/director_loop.py:1551` | `momentary=0.8` | Override gate input — "LLM proposed it, assume confident" | `0.8` | LLM may have low confidence in its choice; we throw the LLM's signal away and substitute a constant | Read LLM's `logprobs` if the API exposes them; otherwise have the LLM emit a `confidence: 0..1` field in DirectorIntent. The 0.8 default ratifies the LLM's choice without recourse. | A |

### A.2 Director intent schema (`shared/director_intent.py`)

| File:Line | Default | When it fires | Current value | Recruitment failure it masks | Proposed alternative | Cat |
|---|---|---|---|---|---|---|
| `shared/director_intent.py:121-129` | `CompositionalImpingement.dimensions: dict[str, float] = Field(default_factory=dict)` | LLM emitted impingement without dimensions | `{}` (empty) | LLM didn't ground the move in any expressive dimension (intensity / tension / depth / coherence …) | This is the right shape (empty dict is meaningful) but the consumer's behavior on empty is to insert pipeline defaults (line 128: "Missing keys default to 0.0 at the pipeline."). Dimensions=0.0 is a behavior — a flat impingement with no expressive shape. The pipeline should TAG the impingement as "ungrounded-dimensions" and the audit log should track how often this happens. Currently it's silent. | A |
| `shared/director_intent.py:131-133` | `material: CompositionalMaterial = Field(default="water")` | LLM omitted material | `"water"` | LLM didn't pick an elemental material; system picks water silently | Material drives interaction-style downstream (water, fire, earth, air, void — with distinct shader behaviors). Defaulting to water gives every "ungrounded" impingement the same default visual language. Make material REQUIRED in CompositionalImpingement (the LLM is given the enum in the prompt — drop the default; make Pydantic refuse). | A |
| `shared/director_intent.py:134-138` | `salience: float = Field(default=0.5, …)` | LLM omitted salience | `0.5` | LLM didn't weight the move; pipeline scoring ranks it at neutral salience | Same as material — make REQUIRED. The whole point of salience is the director picks it. Silently substituting 0.5 means every ungrounded impingement scores in the middle band regardless of how trivially or critically the LLM intended it. | A |
| `shared/director_intent.py:140-153` | `grounding_provenance: list[str] = Field(default_factory=list)` | LLM omitted grounding | `[]` | LLM didn't cite any perceptual-field signals | Empty list is allowed by Pydantic but the prompt + audit demands `>= 1` per impingement. The Pydantic schema should enforce `min_length=1` and the parser should retry / the audit should fire LOUD on empty. Currently the pipeline accepts `[]` and the audit log just notes it. | A |
| `shared/director_intent.py:257-265` | `homage_rotation_mode: NarrativeHomageRotationMode \| None = Field(default=None, ...)` | LLM omitted rotation mode | `None` | "LLM didn't pick a rotation strategy" | Make `Optional[Literal[...]]` with REQUIRED literal — LLM must pick one of the 4 + a fifth literal `"absent"` that explicitly means "I considered this and chose to leave it to the slow structural tier". The current `None` default is indistinguishable from "LLM forgot the field exists." | A (CEREMONIAL — see §3) |
| `shared/director_intent.py:266-274` | `ward_emphasis: list[str] = Field(default_factory=list)` | LLM omitted ward emphasis | `[]` | LLM didn't pick wards to emphasize | Empty list is valid (operator can choose to emphasize nothing) but in production the prompt explicitly tells the LLM "Never emit an empty structural_intent — idle is the cardinal sin" (line 2039 of director_loop.py). The default contradicts the prompt. Make `min_length=0` explicit AND have the parser detect empty + emit a `parse_warning` impingement. | A |
| `shared/director_intent.py:275-281` | `ward_dispatch: list[str] = Field(default_factory=list)` | Same | `[]` | Same — and even more critical because dispatch creates new ward presence | Same | A |
| `shared/director_intent.py:282-287` | `ward_retire: list[str] = Field(default_factory=list)` | Same | `[]` | Same | Same | A |
| `shared/director_intent.py:289-297` | `placement_bias: dict[str, str] = Field(default_factory=dict)` | Same | `{}` | Same | Same | A |
| `shared/director_intent.py:381-390` | `structural_intent: NarrativeStructuralIntent = Field(default_factory=NarrativeStructuralIntent)` | LLM emitted DirectorIntent without structural_intent at all | Empty `NarrativeStructuralIntent()` — every field at its default | The entire structural-intent surface — the homage director — was bypassed | The model_dump JSONL writer SHOULD distinguish `structural_intent=NarrativeStructuralIntent()` (LLM produced a fresh empty container) from `structural_intent=None` (LLM omitted the field). Make this `Optional[NarrativeStructuralIntent] = None` so absent vs empty are distinguishable. | A (CEREMONIAL — see §3 / §4) |

### A.3 Compositor model (`shared/compositor_model.py`)

| File:Line | Default | When it fires | Current value | Recruitment failure it masks | Proposed alternative | Cat |
|---|---|---|---|---|---|---|
| `shared/compositor_model.py:111-114` | `update_cadence: UpdateCadence = "always"` | Source schema doesn't specify | `"always"` | Source author didn't think about cadence; ALL sources resample every frame | This is borderline B (sensible default) but it pre-supposes cadence selection should NOT be a recruitable property. Defensible — sources don't recruit cadence. | B |
| `shared/compositor_model.py:185-188` | `blend_mode: BlendMode = "over"`, `z_order: int = 0`, `update_cadence: UpdateCadence = "always"` (Surface) | Surface schema doesn't specify | `"over"`, `0`, `"always"` | Authors don't pick blend / z / cadence; everything stacks at z=0 with OVER blending | These are aesthetic defaults that compose into the surface look without recruitment. `z_order=0` for everything means render order falls to dict iteration. CONCERNING because z_order is the primary composition tool. Consider requiring explicit z_order on every surface; let the Layout validator flag duplicates. | A (re z_order=0); B (re blend_mode/cadence) |
| `shared/compositor_model.py:202-203` | `Assignment.opacity: float = Field(1.0, ge=0.0, le=1.0)` | Layout doesn't specify opacity | `1.0` | Nobody recruited opacity; ward is full-alpha by default | This is the bug the operator's branch name (`hotfix/fallback-layout-assignment`) seems to point at. Opacity should be an *emphasis property* — wards are baseline INVISIBLE / dim until emphasized. Defaulting to 1.0 means structural-intent emphasis is fighting an already-full-on baseline. **Recommendation:** baseline opacity = 0.0 + chrome-alpha-driver lifts visible wards to a per-ward "ambient" level (e.g. 0.35 for non-foreground chrome, 0.85 for foreground wards). Then `ward_emphasis` lifts emphasized wards to 1.0. The current path: opacity=1.0 baseline + structural emphasis writes alpha=1.0 (no-op). | A (CEREMONIAL — emphasis writes that have no visible effect because baseline is already at the emphasis target) |
| `shared/compositor_model.py:204` | `per_assignment_effects: list[str] = Field(default_factory=list)` | Layout doesn't specify | `[]` | "No per-assignment effects recruited" | OK — empty list = no overlay effects active is the correct semantics | B |
| `shared/compositor_model.py:205-215` | `non_destructive: bool = Field(default=False, …)` | Existing layouts byte-identical | `False` | "Author did not opt-in to non-destructive ceiling" | Defensible — the comment notes "Default False keeps existing layouts byte-identical." But this means every NEW ward overlay is destructive by default. Consider flipping default to `True` and have known-destructive surfaces opt OUT. Operator's call. | D |
| `shared/compositor_model.py:233` | `Layout.description: str = ""` | Author omitted description | `""` | Author skipped documentation | Trivial; B | B |
| `shared/compositor_model.py:174` | `render_target: str \| None = None` (SurfaceGeometry) | Surface omitted render target | `None` (downstream `or "main"`) | Surface author didn't think about render targets; everything funnels to `main` | The implicit `or "main"` at `compositor_model.py:326` and `output_router.py:123` is the actual default behavior. Multi-target work (NDI, Phase 5b2) needs every surface to have an explicit target. Make `render_target` REQUIRED in surfaces with `kind="video_out"` and bottom out the implicit `"main"` fallback. | A (low priority but blocks multi-target observability) |

### A.4 Compositional consumer (`compositional_consumer.py`)

| File:Line | Default | When it fires | Current value | Recruitment failure it masks | Proposed alternative | Cat |
|---|---|---|---|---|---|---|
| `compositional_consumer.py:62-64` | `RecruitmentRecord.score: float = Field(default=1.0)`; `impingement_narrative: str = Field(default="")`; `ttl_s: float = Field(default=30.0)` | Caller constructs without explicit score | `1.0`, `""`, `30.0s` | Caller treats every recruitment as full-confidence | Score=1.0 default means the AffordancePipeline scoring is bypassed at the consumer boundary — ANY recruitment that survives selection is treated as max-confidence. Pipeline already scores; the consumer should never need a default. Make REQUIRED. | A |
| `compositional_consumer.py:91-93` | `_CAMERA_ROLE_HISTORY: list[...] = []`; `_CAMERA_MIN_DWELL_S = 12.0`; `_CAMERA_VARIETY_WINDOW = 3` | Module-level state | empty/12s/3 | Variety enforcement defaults — same nature as director rotation enforcer. | The dwell + window numbers are gates (see sibling audit). The empty initial state is correct (cold start has nothing to enforce). | B |
| `compositional_consumer.py:321-328` | `_WARD_HIGHLIGHT_MODIFIERS["default"] = {}` | Ward.highlight recruited with modifier "default" | empty dict — no field changes | "No highlight modifier was specified" | Currently `default` is silently a no-op AND it's listed alongside `pulse/glow/flash/dim/foreground` as a valid modifier — meaning a recruitment naming `ward.highlight.<id>.default` is valid but does nothing. Either remove `"default"` from the vocabulary OR make it explicit (e.g. `_WARD_HIGHLIGHT_MODIFIERS["clear"]` that resets a prior emphasis to baseline). | A |
| `compositional_consumer.py:330-337` | `_WARD_SIZE_MODIFIERS["natural"] = 1.0`, `["default"] = 1.0` | Same | both `1.0` | Two no-op modifiers in vocabulary; recruitment seems active but is | Same — pick one, document, remove the other. | A |
| `compositional_consumer.py:339-345` | `_WARD_POSITION_MODIFIERS["static"] = {…drift_hz: 0.0}`, `["default"] = {…drift_hz: 0.0}` | Same | identical | Same | Same | A |
| `compositional_consumer.py:347-353` | `_WARD_STAGING_MODIFIERS["default"] = {z_order_override: None, visible: True}` | Ward.staging.<id>.default recruited | restores defaults | "Recruitment named 'default' to clear prior overrides" | This one is meaningful (it's an EXPLICIT clear) — should be renamed `clear` or `reset` for clarity. Currently indistinguishable from no-modifier-recruited. | A |
| `compositional_consumer.py:355-361` | `_WARD_CADENCE_MODIFIERS["default"] = None` | Ward.cadence.<id>.default | clears override | Same — meaningful but mis-named | Same | A |
| `compositional_consumer.py:928-929` | `_STRUCTURAL_EMPHASIS_TTL_S = 4.0`, `_STRUCTURAL_PLACEMENT_TTL_S = 30.0` | Module-level | hardcoded | Per-tick emphasis duration is hardcoded | These are timer values (sibling audit) but worth flagging here: every emphasis lasts exactly 4s, every placement lasts exactly 30s, regardless of the salience the structural-intent dispatcher passed. Consider: TTL = base * salience or TTL recruited from a per-impingement field. | D |
| `compositional_consumer.py:935-940` | `_STRUCTURAL_EMPHASIS_PROPS = {alpha:1.0, glow_radius_px:14.0, scale_bump_pct:0.12, border_pulse_hz:2.2}` | Module-level | hardcoded | Per-emphasis envelope is hardcoded | These define what "emphasis" *looks like*. Should be recruited from the active homage package's grammar (BitchX has its own emphasis aesthetic; future packages will differ). Currently every package emphasizes the same way. | A |
| `compositional_consumer.py:947-980` | `_PLACEMENT_HINT_TO_PROPS` (dict) | Per placement_bias hint | hardcoded `drift_hz=0.3, drift_amplitude_px=14.0, position_offset=±8.0`, etc. | Placement physics hardcoded | Same as emphasis — should be recruited from the active package's motion vocabulary. | A |
| `compositional_consumer.py:1015-1021` | `_apply_emphasis(ward_id, salience: float = 1.0)` (kwarg default) | Direct call without salience | `1.0` | Caller didn't think about salience; emphasis lands at full envelope | All current callers pass `salience=1.0` (line 1151). The argument is vestigial — either remove it OR pass through actual impingement salience. Currently every emphasis is full-salience because the caller hardcodes 1.0. | A (CEREMONIAL — the salience parameter exists but its only callsite hardcodes the maximum) |

### A.5 Homage choreographer (`homage/choreographer.py`)

| File:Line | Default | When it fires | Current value | Recruitment failure it masks | Proposed alternative | Cat |
|---|---|---|---|---|---|---|
| `homage/choreographer.py:88-89` | `_ARTEFACT_INTENSITY_ACTIVE = 1.0`, `_ARTEFACT_INTENSITY_IDLE = 0.0` | Module-level | binary 1.0 / 0.0 | "Artefact emitted this tick" / "didn't" | Binary is fine here; this is render output, not a recruitment surface. | B |
| `homage/choreographer.py:117-131` | `PendingTransition.salience: float = 0.0` | Producer didn't tag salience | `0.0` | Producer never declared importance — under `weighted_by_salience` rotation mode, this transition is the loser by default | The default 0.0 means the affordance-pipeline-recruited transitions (which DO populate salience) will always beat producer-direct transitions (which often forget to). Should be REQUIRED on PendingTransition; producers that don't have a salience score should compute one or default to e.g. 0.5 (median weight) explicitly. | A |
| `homage/choreographer.py:283` | `payload = CoupledPayload(0.0, 0.0, 0.0, 0.0)` (feature flag off path) | HAPAX_HOMAGE_ACTIVE=0 | all zeros | "HOMAGE disabled" | Defensible (legitimate fail-closed for the rollback escape hatch) but the all-zero payload is also what ABSENT FSM produces — the shader can't tell "homage disabled" from "no transitions active". Should publish a `feature_flag_off=True` sentinel field. | C / D |
| `homage/choreographer.py:606-613` | `_default_rotation_mode()` returns `"weighted_by_salience"` (env override `HAPAX_HOMAGE_DEFAULT_ROTATION` else literal) | Both narrative + structural files missing/stale | `"weighted_by_salience"` | "Neither tier ran or both files are stale" | This was changed from `"sequential"` to `"weighted_by_salience"` per the operator directive (cascade-delta) — a bandaid because the narrative tier wasn't actually emitting structural_intent. Once the narrative path actually fires, this default should never be reached. Currently it's reached EVERY tick (live evidence: `narrative-structural-intent.json` contents `{"homage_rotation_mode": "weighted_by_salience", updated_at: 1776574725}` is hours stale). | A (this default is firing 100% of the time per evidence — the narrative tier is dark) |
| `homage/choreographer.py:672-673` | `hue = 180.0 if package.name == "bitchx" else 0.0` | Package not BitchX | `0.0` (red?) | "Unknown package; pick a default hue" | Hardcoded per-package hue with a single literal-name conditional. Should live on the HomagePackage's coupling_rules or palette spec. As-is, every future package gets hue 0 silently. | A |
| `homage/choreographer.py:928` | `hue = 180.0 if package.name == "bitchx" else 0.0` (broadcast_package_to_substrates) | Same | Same | Same | Same — duplicated default; both must be fixed in lockstep | A |
| `homage/choreographer.py:783-786` | `transition = pkg.transition_vocabulary.default_entry if pkg else "ticker-scroll-in"` (in dispatch_homage_emergence/recede in compositional_consumer) | Active package missing entirely | `"ticker-scroll-in"` / `"ticker-scroll-out"` | "Homage system has no active package — use BitchX's defaults" | The `if pkg else "ticker-scroll-in"` literals couple the fallback to BitchX-specific transitions. If the active-package resolver returns None (which can happen during consent-safe-without-variant), the fallback names BitchX vocabulary that may not even be in the active package's `supported` set. Refuse to dispatch when pkg is None. | A |

### A.6 HomageTransitionalSource FSM (`homage/transitional_source.py`)

| File:Line | Default | When it fires | Current value | Recruitment failure it masks | Proposed alternative | Cat |
|---|---|---|---|---|---|---|
| `homage/transitional_source.py:84-89` | `initial_state: TransitionState = TransitionState.HOLD`, `entering_duration_s: float = 0.4`, `exiting_duration_s: float = 0.3` | Source __init__ without explicit state | `HOLD`, `0.4s`, `0.3s` | "Choreographer never emitted a transition for this ward" | Note the long HOTFIX comment (lines 90-110) — this default was FLIPPED from `ABSENT` to `HOLD` on 2026-04-18 because every ward inheriting the base disappeared. **This is a smoking gun for the ceremonial-default failure mode**: the original choice (`ABSENT` by default) was correct under the recruitment model (wards exist only when dispatched); it broke production because the choreographer was never actually emitting dispatches. The fix re-introduces a default that masks the recruitment failure. The PROPER fix is: leave the default at HOLD for backwards compatibility, BUT register a per-ward "should this ward have been dispatched?" probe that fires alerts when wards are HOLDing without ever having received a transition. | A (CEREMONIAL — the comment in the code itself documents this is a default hiding a recruitment failure) |

### A.7 Ward properties (`ward_properties.py`)

| File:Line | Default | When it fires | Current value | Recruitment failure it masks | Proposed alternative | Cat |
|---|---|---|---|---|---|---|
| `ward_properties.py:62-93` | All `WardProperties` field defaults: `visible=True`, `alpha=1.0`, `glow_radius_px=0.0`, `border_pulse_hz=0.0`, `scale_bump_pct=0.0`, `scale=1.0`, `border_radius_px=0.0`, `position_offset_*=0.0`, `drift_*=0.0/none`, etc. | Ward never received a per-ward override | All "no-op" / "as if no override" values | "No structural-intent / dispatch / consumer ever wrote to this ward" | This is the canonical "no-op default" pattern. The dataclass docstring explicitly says "every property is 'as if no override was set'." THIS IS APPROPRIATE for the data class itself. **The blinding default is one level up**: `resolve_ward_properties()` returns `snapshot.fallback_all` (which is itself an empty `WardProperties()`) when no per-ward entry exists (line 141). So a ward with no recruitment looks identical to a ward with a recruitment that picked all defaults. Add a sentinel — return `None` from `resolve_ward_properties` when neither specific nor fallback_all has been written, so `ward_render_scope` can distinguish "default-modulated" from "never-modulated." | A (CEREMONIAL pattern, but the fix is at the resolver, not the dataclass) |
| `ward_properties.py:117-118` | `_CachedSnapshot.fallback_all: WardProperties = field(default_factory=WardProperties)` | No `"all"` entry in ward-properties.json | empty WardProperties | Same — "all" was never written, but resolver returns the default-defaults | Same | A |

### A.8 CPAL / daimonion

| File:Line | Default | When it fires | Current value | Recruitment failure it masks | Proposed alternative | Cat |
|---|---|---|---|---|---|---|
| `agents/hapax_daimonion/cpal/runner.py:44` | `TICK_INTERVAL_S = 0.15` | Module-level | 150ms | Cognitive-loop tick cadence | Gate value (sibling audit). Note operator memory `feedback_cognitive_loop.md` requires "never-stopping cognitive loop" — 150ms is reasonable but should be per-stimmung. | D |
| `agents/hapax_daimonion/cpal/destination_channel.py:140-141` | `if impingement is None: return DestinationChannel.LIVESTREAM` | classify_destination called with None | LIVESTREAM | "Caller had no impingement provenance" | Defensible (most spontaneous TTS is broadcast-bound) but this is also where unmarked TTS could leak to the livestream. The fail-open posture here is intentional but could mask "impingement metadata never propagated through CPAL". | C / D |
| `cpal/destination_channel.py:166` | `return DestinationChannel.LIVESTREAM` (final fallthrough in classify_destination) | Impingement doesn't match any private rule | LIVESTREAM | "Could not determine private intent" | Defensible (broadcast is the safe assumption for unclassified TTS) but currently this means EVERY non-sidechat / non-debug utterance is broadcast. If new TTS sources emerge (e.g., a future "operator notification" tier) and forget to set channel/source, they'll silently broadcast. | C |
| `cpal/production_stream.py:50-58` | `audio_output: object \| None = None`, `shm_writer=None` (defaults to `_default_shm_write`), `on_speaking_changed: object \| None = None` | Test/mock construction | None / fallback method / None | "Caller didn't wire audio output" — production stream silently no-ops | Defensible for tests (allowing None for audio_output skips playback), but in production a None audio_output is a bug, not a recruitment failure. Add `validate_production_wired()` that the daemon calls before starting CPAL. | D |

### A.9 Persona / system prompt

| File:Line | Default | When it fires | Current value | Recruitment failure it masks | Proposed alternative | Cat |
|---|---|---|---|---|---|---|
| `agents/hapax_daimonion/persona.py:34-37` | `_legacy_mode()` returns False unless env var truthy | Env var unset | `False` | "Operator hasn't opted into legacy mode" | Defensible — the new path is the desired path. | B |
| `agents/hapax_daimonion/persona.py:171` | `_NOTIFICATION_TEMPLATE = "Hey {name} — {summary}"` | Module-level | hardcoded greeting | "No persona-recruited greeting available" | This greeting is the ONLY way Hapax addresses notifications. It's a default-everywhere because there's no recruitment surface for greetings. Either build one (a `greeting.style` capability) or document this is a deliberate non-recruitment surface. | D |

### A.10 Affordance pipeline (`shared/affordance_pipeline.py`)

| File:Line | Default | When it fires | Current value | Recruitment failure it masks | Proposed alternative | Cat |
|---|---|---|---|---|---|---|
| `shared/affordance_pipeline.py:27` | `DEFAULT_TOP_K = 10` | `select(top_k=...)` not specified | `10` | Caller didn't think about retrieval breadth | Trivial | B |
| `shared/affordance_pipeline.py:28-33` | `SUPPRESSION_FACTOR = 0.3`, `THRESHOLD = 0.05`, `W_SIMILARITY = 0.50`, `W_BASE_LEVEL = 0.20`, `W_CONTEXT = 0.10`, `W_THOMPSON = 0.20` | Module-level scoring weights | hardcoded | The recruitment-scoring formula is hardcoded; weights cannot themselves be recruited or tuned per stimmung | These weights ARE the recruitment policy. They're not exposed for governance. **THIS IS THE META-DEFAULT**: the recruitment system itself has hardcoded defaults. Operator's stimmung / cycle / mode never modulates these. Per memory `feedback_intelligence_first.md`, salience routing should be activation-based; static weights make every recruitment use the same activation rule. Recommendation: per-mode (research/rnd) weight tuples; or a meta-pipeline that picks weights based on stimmung. | A (META — the recruitment substrate's own defaults) |
| `shared/affordance_pipeline.py:151` | `sigma_explore=0.10` (in ExplorationTrackerBundle constructor at AffordancePipeline init) | Pipeline init | `0.10` | Per-component exploration noise — could be recruited from stimmung's exploration_deficit | Defensible-as-tunable, problematic-as-permanent. | D |

### A.11 Other

| File:Line | Default | When it fires | Current value | Recruitment failure it masks | Proposed alternative | Cat |
|---|---|---|---|---|---|---|
| `agents/studio_compositor/preset_family_selector.py:114-118` | Family `"neutral-ambient"` is described in docstring as "default fallback when no family is recruited" | random_mode picks when no family recruited | curated 3-preset list | "Director did not recruit a preset family this tick" | This is the single most operator-visible default — when the director doesn't pick a preset family, "neutral-ambient" runs. The 3 presets in the family ARE explicit (good) but the ROUTING to the family ("no recruitment → neutral-ambient") is a default behavior. The fix is to make the absence-of-recruitment OBSERVABLE: a metric `hapax_preset_family_no_recruitment_total` and a per-tick log. Currently invisible unless you grep `random_mode.py`. | A |
| `agents/studio_compositor/preset_mutator.py:31-32` | `DEFAULT_VARIANCE = 0.15`, env feature flag default ON | Mutate-preset called without explicit variance | `0.15`, ON | "Caller didn't pick variance" / "Operator didn't disable mutator" | Variance is aesthetic and cheap to override per-call. Defensible. | B |
| `agents/studio_compositor/follow_mode.py:61-79` | All scoring constants (`_LOCATION_MATCH_BONUS=3.0`, `_OPERATOR_VISIBLE_BONUS=0.3`, `_REPETITION_PENALTY=3.0`, `_DEMO_DESK_OVERHEAD_BONUS=2.0`), windows | Module-level | hardcoded | Hero-camera scoring policy is hardcoded | Same shape as affordance_pipeline weights — the policy of "how to score cameras" cannot itself be recruited. Not actively masking — `HAPAX_FOLLOW_MODE_ACTIVE` defaults OFF so this whole module is inactive — but when activated, every operator gets the same scoring weights. | D (currently inactive) |
| `agents/studio_compositor/scene_classifier.py:81` | `FALLBACK_SCENE = "mixed-activity"` | LLM parse error / unknown scene label | `"mixed-activity"` | "Could not classify the scene" | This collapses ALL classification failures to one label that downstream `SCENE_TAG_BIAS["mixed-activity"] = ()` deliberately produces no bias. So unknown scene → no bias → uniform random. The **observability gap**: a real `mixed-activity` classification looks identical to a parse-failed classification. Add a `scene_quality: ok/degraded/unknown` field. | A |
| `agents/studio_compositor/effects.py:163-167` | `ModulationBinding(scale=d.get("scale", 1.0), offset=d.get("offset", 0.0), smoothing=d.get("smoothing", 0.85), …)` (in merge_default_modulations) | Default modulation template entries omit fields | `1.0`, `0.0`, `0.85` | "Default modulation didn't pick scale/offset/smoothing" | These are mathematical defaults (multiplicative identity, additive zero, sensible smoothing) — defensible. | B |
| `agents/studio_compositor/ward_fx_mapping.py:108` | `domain_for_ward(ward_id)` returns `WARD_DOMAIN.get(ward_id, "perception")` | ward_id not in `WARD_DOMAIN` | `"perception"` | "We don't know what domain this ward belongs to" | This is the operator's exact `WARD_DOMAINS.get(ward_id, "cognition")` example pattern (renamed). The `"perception"` default sends every unknown ward to the calm-textural preset family — invisible. The DOMAIN classification IS the recruitment surface for ward-FX coupling; defaulting it silently skips classification. Ward registration should require domain. | A |
| `agents/imagination.py:68` | `material: Literal["water", "fire", "earth", "air", "void"] = "water"` (ImaginationFragment) | Imagination producer didn't pick material | `"water"` | "Imagination didn't select an elemental quality" | Same as `CompositionalImpingement.material`. Material drives shader content. Defaulting to water means every "ungrounded" imagination fragment has the same downstream visual signature. Make REQUIRED. | A |

### Cumulative tally

- Category A: **18** (rolled up; some rows aggregate adjacent fields) — see §0
- Category B: **9**
- Category C: **3**
- Category D: **9**
- "Ceremonial" sub-category: **5** (called out in the Cat column)

---

## §3 Ceremonial defaults — fields always populated whose values do not drive behavior

These are the most dangerous defaults: they look like recruitment is happening because the field has a value every tick, but the value is the system's pretend answer for "no recruitment fired." Researchers reading the JSONL or SHM files cannot tell the system is dark.

1. **`structural_intent` on every DirectorIntent** (`shared/director_intent.py:381-390`).
   - Defaults to `NarrativeStructuralIntent()` (an empty container).
   - Live evidence: `director-intent.jsonl` (994 records over multiple days). The JSONL serializer (`model_dump_for_jsonl`) does NOT actually emit the `structural_intent` key — but that's worse, not better, because consumers who only look at the JSONL cannot tell whether the LLM emitted structural_intent at all.
   - Replacement: make `structural_intent: Optional[NarrativeStructuralIntent] = None` so the JSONL records carry the field as `null` when LLM omits, and emit a counter.

2. **`condition_id="none"`** (`director_loop.py:1055, 1478` etc.).
   - Live evidence: 994/994 records have `condition_id="none"`.
   - This is the LRR Phase 1 research-condition tag. The default `"none"` means **no research condition has ever been opened** for the ENTIRETY of the captured stream. The Phase 9 / 10 per-condition slicing infrastructure exists, the Prometheus labels exist, the Grafana dashboards exist — and they all slice on a single value `"none"` because the registry-script `open` command was never run.
   - Recruitment failure masked: no operator-driven research framework loaded; system runs in "pre-condition" mode permanently.

3. **`homage_rotation_mode` always-published default** (`homage/choreographer.py:606-613`).
   - Defaults (env-overridable) to `"weighted_by_salience"`.
   - Live evidence: `narrative-structural-intent.json` contents `{"homage_rotation_mode": "weighted_by_salience", "updated_at": 1776574725.94}` — that timestamp is hours stale. The narrative-tier override is published once and never refreshed; the choreographer reads it on every tick but with a 60s staleness cutoff (`_NARRATIVE_STRUCTURAL_MAX_AGE_S = 60.0`), so it falls back to either the structural director (also stale) or this hardcoded default. The *same value* the narrative tier wrote (also a default) is the value the hardcoded fallback would emit. **The shader sees `weighted_by_salience` constantly because three independent tiers all default to it** — there's no way to tell which tier is alive.
   - Replacement: tag every published rotation mode with the writing tier (`"narrative"`, `"structural"`, `"hardcoded"`) and the timestamp.

4. **`HomageTransitionalSource.initial_state = HOLD`** (`homage/transitional_source.py:86`).
   - Default flipped from ABSENT to HOLD on 2026-04-18 because wards disappeared.
   - The CHOREOGRAPHER was meant to emit transitions to bring wards into HOLD; without choreographer dispatches, every ward should be ABSENT. Defaulting to HOLD makes wards appear without recruitment.
   - Live evidence: `ward-properties.json` shows 20 wards; counting unexpired entries (3) vs total (20), 17 wards are alive at their stale-but-unexpired state, all visible by default, none recruited recently. The choreographer's `homage-pending-transitions.json` shows entries from `enqueued_at: 1776547478` (~9 hours ago, still unconsumed in some entries — the queue is not draining cleanly).

5. **`Assignment.opacity: float = 1.0`** (`shared/compositor_model.py:202`).
   - Every layout-defined assignment is full-alpha by default.
   - The structural-intent dispatcher writes `alpha=1.0` when emphasizing — exactly equal to the baseline. **Emphasis is a no-op visually because the baseline is already at the emphasis target.** The operator sees a "flat surface" because every ward is composed at 1.0 by default.
   - Replacement: baseline opacity = 0.0; chrome-driver lifts wards to ambient alpha (e.g. 0.35); structural emphasis lifts to 1.0. The contrast becomes a real visible pulse instead of a no-op write.

These five are the ones hiding the most behavior. Of them, #1, #2, and #5 are the operator-visible problems (the surface looks dead despite "active" emission); #3 and #4 are the implementation artifacts that produce that user-facing failure.

---

## §4 Live evidence

### Director intent JSONL — 994 records, full default-mask coverage

```
total ticks: 994
homage_rotation_mode counts: [(None, 994)]            ← 100% missing structural_intent
ward_emphasis empty: 994 (100.0%)                     ← 100% no ward emphasis
ward_dispatch nonempty: 0 (0.0%)
ward_retire nonempty: 0 (0.0%)
placement_bias nonempty: 0 (0.0%)
top condition_ids: [('none', 994)]                    ← 100% no research condition
activities: [('react', 465), ('silence', 239), ('music', 195),
             ('observe', 50), ('chat', 24), ('study', 21)]
```

`silence` is the second-most-frequent activity (239 / 994 = 24.0%). Cross-referenced against the impingement narratives, **most of these are the parser-fallback silence-hold** — i.e. the LLM call failed and the stock impingement was synthesized. Sample (most recent silence ticks):

```json
{"activity":"silence","stance":"nominal","narrative_text":"",
 "compositional_impingements":[{"narrative":"Silence hold: maintain the current surface; stance indicator breathes, chrome unchanged, no new recruitment this tick.","material":"void","salience":0.2,"intent_family":"overlay.emphasis"}],
 "condition_id":"none","emitted_at":1776577867.82}
```

That `"narrative": "Silence hold: maintain the current surface…"` text is the ceremonial impingement from `_silence_hold_impingement()`. It's been re-emitted at minimum 239 times. Downstream consumers reading the DMN impingement stream cannot distinguish these from real recruited silence ticks.

### Ward-properties.json — defaults dominate the unexpired window

20 wards present in `/dev/shm/hapax-compositor/ward-properties.json`. Of these:
- 3 unexpired entries (the structural-emphasis 4s TTL has passed for the rest)
- 5 wards at default emphasis (glow=0, border_pulse=0, scale_bump=0, alpha=1) within the file
- All wards default `position_offset_x/y = 0.0`, `drift_type = "none"`, `drift_hz = 0.0`

In other words, the structural-intent emphasis TTL is shorter than the narrative cadence (4s vs 30s+), so wards spend most of their lifetime at the no-op default. When the cascade-delta micromove fallback fires, it emphasizes for 4s and then everything reverts. The ward-render-scope's `needs_emphasis` check (`ward_properties.py:252-257`) is False for most wards most of the time, so the glow/pulse/scale-bump path is skipped — the operator sees flat text-on-black.

### Narrative-structural-intent.json — hours-stale

```json
{"homage_rotation_mode": "weighted_by_salience", "updated_at": 1776574725.94}
```

That timestamp is **hours old**. The narrative tier hasn't refreshed it. The choreographer's 60s staleness cutoff means it's been falling back to the hardcoded default (`weighted_by_salience` from `_default_rotation_mode()`) every reconcile. Three tiers, one hardcoded value, identical output, no way to tell.

### Homage-pending-transitions.json — backlog

`/dev/shm/hapax-compositor/homage-pending-transitions.json` carries entries with `enqueued_at: 1776547478` (~9 hours stale). Either the choreographer is consuming and re-enqueueing (loop) or the file was written-once and never drained. Either way: the salience field is set on real recruited entries (the dispatch_homage_* functions write salience) but the older entries lack it, so the `weighted_by_salience` rotation puts them at the bottom permanently.

### Cross-cutting: the shape of the failure

**994 ticks. 100% of them lack structural_intent. 100% of them have condition_id="none". 24% of them are stock silence-hold fallbacks. The wards live in their no-op defaults for ≥87% of any given window.**

This is not "a default firing occasionally." This is **a system whose recruitment surfaces are dark, masked by defaults that satisfy the no-vacuum invariant in form while violating it in substance**.

---

## §5 Replacement shapes — impingement protocols that retire the default

For each Category A default, the replacement fits one of five protocol shapes:

### 5.1 NULL-record protocol

When recruitment doesn't fire, emit a STRUCTURED null record instead of a synthesized stand-in:

```python
class NullDirectorIntent(BaseModel):
    """Marker record: director failed to recruit this tick.
    
    Distinct from DirectorIntent. Emitted on parse_failure, llm_empty,
    degraded, or first-tick-cold-start. JSONL writer emits
    {"_kind": "null_director", "reason": ..., "tier": ..., ...}.
    Downstream consumers (compositional_consumer, audit) explicitly
    handle this case rather than receiving a fake DirectorIntent.
    """
    reason: Literal["parse_failure", "llm_empty", "llm_timeout", "degraded", "cold_start"]
    tier: str
    condition_id: str | None  # None means "no condition opened" — explicit
    timestamp: float
```

Retires: A.1 rows 2/3/13/14, A.2 row 10, the silence-hold impingement, the micromove cycle.

### 5.2 Pipeline-emitted impingement protocol

Recast all parser failures as IMPINGEMENTS to the AffordancePipeline:

```python
def _emit_parse_failure_impingement(reason: str, raw: str, condition_id: str | None) -> None:
    """A parser failure is itself a sense-event the pipeline can recruit against."""
    Impingement(
        timestamp=time.time(),
        source="director.parser",
        type=ImpingementType.SYSTEM_EVENT,
        strength=0.6 if reason == "llm_timeout" else 0.4,
        content={"reason": reason, "raw_truncated": raw[:200], "condition_id": condition_id}
    )
    # Pipeline may (a) recruit a "diagnose-llm-failure" capability, 
    # (b) recruit a "raise-pressure-gauge" capability, or 
    # (c) emit a NULL-record, depending on system stance.
```

Retires: A.1 rows 2/3/10/11/12/14, the silence-hold impingement, micromove cycle.

### 5.3 Required-field schema protocol

Pydantic-enforce the fields the LLM is supposed to emit:

```python
class CompositionalImpingement(BaseModel):
    narrative: str = Field(..., min_length=1)
    intent_family: IntentFamily
    material: CompositionalMaterial  # NO DEFAULT
    salience: float = Field(..., ge=0.0, le=1.0)  # NO DEFAULT
    grounding_provenance: list[str] = Field(..., min_length=1)  # NO DEFAULT
```

The parser then catches Pydantic ValidationError and emits a parse_failure impingement (5.2) instead of synthesizing values.

Retires: A.2 rows 2/3/4 (material, salience, grounding), A.11 row 6 (imagination material).

### 5.4 Recruitment-from-pipeline protocol

Replace policy-defaults with pipeline-recruited capabilities:

- The 7 micromoves in `director_loop.py:1368-1422` become 7 registered capabilities (`director.micromove.overlay-emphasis-grounding`, `director.micromove.preset-bias-calm-textural`, etc.). The "fallback" path emits an Impingement, the pipeline recruits one of the 7 capabilities.
- The `_WARD_HIGHLIGHT_MODIFIERS` table becomes 6 registered capabilities (`ward.highlight.<id>.pulse` etc. already are), with the `default` modifier removed entirely.
- The `_STRUCTURAL_EMPHASIS_PROPS` envelope becomes a per-package `EmphasisRules` field on `HomagePackage` so different packages emphasize differently.

Retires: A.1 row 10 (micromoves), A.4 rows 3-7 (modifier defaults), A.4 rows 9-10 (emphasis envelope), A.5 row 5/6 (palette hue).

### 5.5 Tagged-provenance protocol

Where a default is defensible but observability is needed, tag every emission with the source tier:

```json
{"homage_rotation_mode": "weighted_by_salience", 
 "_source_tier": "narrative" | "structural" | "hardcoded_default",
 "updated_at": 1776...}
```

Retires: A.5 row 4 (the 3-tier rotation mode collapse), A.7 rows 1/2 (ward properties resolver).

---

## §6 Family E augmentation — exact list of defaults to excise in go-live

Family E (homage-completion, in planning) should incorporate the following retirement list. Listed in dependency order (later items depend on earlier ones).

### Phase E.1 — Schema enforcement (no code change required, only schema diff)

1. `shared/director_intent.py:131-153`: make `material`, `salience`, `grounding_provenance` REQUIRED on `CompositionalImpingement`. Pydantic raises ValidationError on missing.
2. `shared/director_intent.py:381-390`: change `structural_intent: NarrativeStructuralIntent = ...` to `structural_intent: Optional[NarrativeStructuralIntent] = None`. JSONL writer emits explicit `null` when LLM omits.
3. `shared/director_intent.py:257-265`: make `homage_rotation_mode` required when `structural_intent` is non-None (or add a `"absent"` literal value).
4. `agents/imagination.py:68`: make `ImaginationFragment.material` REQUIRED.

### Phase E.2 — NULL-record protocol

5. New module `agents/studio_compositor/null_intent.py` with `NullDirectorIntent` schema.
6. `director_loop._silence_hold_fallback_intent` → `_emit_null_director_intent`. `_silence_hold_impingement` deleted entirely.
7. `_emit_micromove_fallback` → `_emit_micromove_impingement` (writes Impingement, doesn't write a fake DirectorIntent).
8. `_parse_intent_from_llm` returns `Union[DirectorIntent, NullDirectorIntent]`; callers branch.

### Phase E.3 — Compositional baseline correction

9. `shared/compositor_model.py:202-203`: `Assignment.opacity` default changes from `1.0` to `0.0`. Existing layouts must be updated to set explicit opacity per assignment (or a chrome-driver writes ambient alphas based on visibility-class metadata).
10. `agents/studio_compositor/ward_properties.py:141`: `resolve_ward_properties` returns `None` when no specific or fallback_all entry. `ward_render_scope` treats `None` as "ward absent / not-recruited" and skips entirely.
11. `agents/studio_compositor/homage/transitional_source.py:86`: `initial_state` default goes back to `ABSENT`. Concurrent: every ward `__init__` callsite that wants paint-and-hold passes `initial_state=HOLD` explicitly. A startup audit lists all wards still defaulting and routes them through a "register_substrate_ward" path.

### Phase E.4 — Recruitment-as-policy

12. The 7 micromoves move to `agents/studio_compositor/director_micromove_capabilities.py` and register with the AffordancePipeline.
13. The `_WARD_HIGHLIGHT_MODIFIERS["default"]` / `_WARD_SIZE_MODIFIERS["default"]` / etc. entries are removed; the `_VALID_WARD_IDS` typo-protection moves to a helper that warns on unknown modifiers (already present, just remove the no-op entries).
14. The `_STRUCTURAL_EMPHASIS_PROPS` constant moves to `HomagePackage.emphasis_rules` (new field on the package schema). BitchX gets the current values; future packages can override.
15. The `_PLACEMENT_HINT_TO_PROPS` table similarly moves to per-package motion vocabulary.
16. `homage/choreographer.py:672-673` and `:928`: hardcoded hue conditional removed. Hue lives on `HomagePackage.coupling_rules.palette_accent_hue_deg` directly.

### Phase E.5 — Observability tags

17. Every published-default emits a `_source_tier` tag (rotation mode, structural-intent, ward properties). Grafana dashboards add per-tier panels.
18. Add `hapax_director_default_emission_total{kind, reason}` Counter to `shared/director_observability.py`. Increment whenever a Category A default is reached.
19. New JSONL field `_emission_kind: "recruited" | "default" | "null"` on every DirectorIntent / CompositionalImpingement record.

### Phase E.6 — Research framework

20. Refuse to write `condition_id="none"` to JSONL. If the research-marker file is missing, ALERT (ntfy) on first emission and emit `condition_id` as `null` (structured) so the slicing infrastructure can see it. Force the operator (via systemd or startup script) to call `research-registry.py open` before the director starts emitting.

---

## §7 Recommendation — top 5 retirements for maximum observability unmasking

Ordered by ratio of (live-evidence frequency × surface visibility) to (implementation cost):

1. **Retire `condition_id="none"` default** (§4 evidence: 994/994). Implementation: 1-line change in 2 callsites + a startup script. Result: the observability stream immediately distinguishes "no research" from "default research". This unmasks Phase 9/10 slicing infrastructure that has been generating useless data for ≥994 ticks.

2. **Retire `Assignment.opacity = 1.0` default** (§4 evidence: every ward visible at full-alpha by default; structural emphasis is a no-op). Implementation: schema change + layout file updates + chrome-driver update. Result: the OPERATOR-VISIBLE failure ("flat text-on-black wards, no dynamism") goes away. Structural emphasis writes start producing visible pulses because the baseline is now lower than the emphasis target.

3. **Retire `_silence_hold_impingement` and `_emit_micromove_fallback` synthesis paths** (§4 evidence: 239/994 ticks are silence-hold; uncountable many use micromove cycle). Implementation: replace with NULL-record protocol (§5.1) + pipeline-emitted impingement (§5.2). Result: the recruitment failure stream becomes legible. Researchers can count parse_failure / llm_empty / llm_timeout separately. The downstream DMN impingement consumer stops receiving fake recruited silences.

4. **Retire `structural_intent` empty-default and the 3-tier `homage_rotation_mode` collapse** (§4 evidence: 994/994 missing structural_intent; narrative-structural-intent.json hours stale; choreographer falls back every reconcile). Implementation: schema change + tagged-provenance protocol (§5.5) + force narrative tier to emit explicit `homage_rotation_mode="absent"` when it doesn't choose. Result: the homage surface has visible direction or visible absence-of-direction. No more silent fall-through.

5. **Retire `CompositionalImpingement.{material, salience, grounding_provenance}` defaults** (§2 A.2 rows 2-4). Implementation: schema enforcement (Phase E.1). Result: every ungrounded LLM emission becomes a parse error with diagnostic narrative, not a silently-substituted "water + salience=0.5 + no grounding" impingement that the affordance pipeline scores as if it were a real recruitment.

These five together would visibly transform the JSONL evidence: instead of 994 ticks of `condition_id=none, structural_intent=missing, ward_emphasis=[]` records, the audit log would show:

- `condition_id="ambient"` or `null` with explicit semantic
- `_emission_kind="recruited"` vs `"null"` vs `"default"` per tick
- A non-zero `hapax_director_default_emission_total` counter the operator can graph
- A non-zero `hapax_director_intent_parse_failure_total` per parse-failure reason
- Visible structural emphasis (because baseline opacity dropped) so the operator's "thoughtful manipulation must be unavoidable" criterion is testable

---

## §8 Recruitment gaps — BLOCKERS for Family E

Three recruitment surfaces must be built before the corresponding defaults can retire:

### Blocker 1 — Silence as recruitable capability

To retire `_silence_hold_impingement`, the AffordancePipeline needs a registered "silence-hold" capability the parser-failure path's emitted impingement can recruit against. **Currently no `silence.*` family exists in the compositional affordances catalog.** Without it, the parser-failure impingement reaches the pipeline and recruits nothing — leaving the surface as actually-empty rather than synthesized-silence.

Required: add `silence.hold`, `silence.observe`, `silence.contemplate` capabilities to `shared/compositional_affordances.py`. Each declares Gibson-verb description, dimensions, modulation. Then the parser-failure → impingement → recruitment path produces a real recruited silence rather than a synthesized one.

### Blocker 2 — Director-micromove capability registry

To retire the 7 hardcoded micromoves, register them as recruitable capabilities. Currently they're inline tuples. The capability registration needs:
- A consistent description / Gibson-verb shape per micromove
- Tagging so the Impingement source `"director.micromove_request"` recruits them
- Decision: should the AffordancePipeline see them as candidates against ALL impingements (risk: they outcompete real moves) or only against the synthetic `director.micromove_request` impingement (cleaner; requires intent_family routing the pipeline already has)

### Blocker 3 — Per-ward "should-have-been-dispatched" probe

To safely retire the `HomageTransitionalSource.initial_state = HOLD` default, the system needs to detect wards that have been HOLDing without ever receiving a transition. This requires:
- A per-ward "first dispatch seen at" timestamp on the FSM
- A periodic audit (e.g. every 60s) listing wards in HOLD with `first_dispatch_at = None`
- Either an alert or a dispatched-by-default capability that can recruit a `homage.emergence` for them

Without this, flipping the default back to `ABSENT` (the right default per the recruitment model) reintroduces the original disappearing-ward bug.

---

## §9 Cross-references

- Operator memory: `feedback_no_expert_system_rules.md` (axiom source)
- Operator memory: `feedback_grounding_exhaustive.md` ("every move is grounding or outsourced-by-grounding")
- Operator memory: `feedback_intelligence_first.md` (salience routing context)
- Operator memory: `feedback_director_grounding.md` (director is the meta-structure communication device)
- Sibling audit: `docs/research/2026-04-19-expert-system-blinding-audit.md` (gates + thresholds)
- Live evidence files (timestamp-stamped):
  - `~/hapax-state/stream-experiment/director-intent.jsonl` — 994 records
  - `/dev/shm/hapax-compositor/ward-properties.json` — 20 wards, defaults dominate
  - `/dev/shm/hapax-compositor/narrative-structural-intent.json` — hours stale
  - `/dev/shm/hapax-compositor/homage-pending-transitions.json` — 9-hour-old backlog
  - `/dev/shm/hapax-director/narrative-state.json` — `activity=silence, condition_id=none`
- Spec dependency: `docs/superpowers/specs/2026-04-02-unified-semantic-recruitment-design.md`
- Spec dependency: `docs/superpowers/specs/2026-04-17-volitional-grounded-director-design.md` (the defaults this audit examines were introduced in this epic + the cascade-delta hotfixes)

---

## §10 Notes for the planning subagent

The planning subagent (writing `docs/superpowers/plans/2026-04-19-homage-completion-plan.md`) should incorporate this audit BEFORE finalizing Family E. Specifically:

- Family E currently presumes the structural-intent surface is functional. **It is not** (§4 evidence). The plan needs to add Phase E.0: confirm narrative tier is actually emitting structural_intent before relying on it for homage completion.
- Phase E.1 (schema enforcement) should be its own PR (no code changes, only schema), shipped FIRST so subsequent PRs can rely on the strict shape.
- Phase E.4 (recruitment-as-policy) is the largest scope item and may warrant being its own epic (Family F).
- Phase E.6 (research framework) is a pre-requisite for ANY of the per-condition-slicing dashboards to mean anything — should be done in parallel with Phase E.1.
