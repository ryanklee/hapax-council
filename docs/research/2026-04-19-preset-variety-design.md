# Preset + Chain Variety — Scoring + Programme Design

Research + design write-up. Tracked as task #166. Operator directive 2026-04-19:
> "preset variety and preset chain variety still very repetitive and samey"

This document argues that variety is not a rotation problem and not solvable by
re-introducing the anti-repeat gates retired in tonight's F1/F2 work. Variety is
a **scoring problem** (the affordance pipeline does not currently price-in
recency or perceptual distance) and a **programme problem** (the recruitable
surface is narrower than the preset corpus and dominated by a single family).
The proposed moves are additive: a recency-distance scoring input, a
non-recruitment Thompson decay term, an affordance-catalog audit, perceptual
distance as an impingement, explicit transition affordances, and per-programme
palette ranges.

Scope: post-HOMAGE completion, post-F1/F2 retirements, pre-content-programming
shipment. Cross-references the parallel research docs
`2026-04-19-content-programming-layer-design.md` (programme layer §5.6 depends
on) and `2026-04-19-expert-system-blinding-audit.md` (gate-retirement evidence
§6).

## §1. Telemetry-First Audit — What Is Actually Happening

### Preset corpus

`presets/` contains 30 files: `ambient`, `ascii_preset`, `clean`, `datamosh`,
`datamosh_heavy`, `diff_preset`, `dither_retro`, `feedback_preset`,
`fisheye_pulse`, `ghost`, `glitch_blocks_preset`, `halftone_preset`,
`heartbeat`, `kaleidodream`, `mirror_rorschach`, `neon`, `nightvision`,
`pixsort_preset`, `reverie_vocabulary`, `screwed`, `sculpture`, `silhouette`,
`slitscan_preset`, `thermal_preset`, `trails`, `trap`, `tunnelvision`,
`vhs_preset`, `voronoi_crystal` (plus one default-modulations file). The
runtime catalog excludes `clean`, `echo`, `reverie_vocabulary`, leaving **27
loadable named presets**.

### Family map (`FAMILY_PRESETS` in `agents/studio_compositor/preset_family_selector.py`)

5 families, 24 unique preset memberships:

| Family | Presets |
|---|---|
| `audio-reactive` | feedback_preset, heartbeat, fisheye_pulse, neon, mirror_rorschach, tunnelvision |
| `calm-textural` | ambient, kaleidodream, voronoi_crystal, sculpture, silhouette, ghost |
| `glitch-dense` | datamosh, datamosh_heavy, glitch_blocks_preset, pixsort_preset, slitscan_preset, trap |
| `warm-minimal` | dither_retro, vhs_preset, thermal_preset, halftone_preset, trails, ascii_preset |
| `neutral-ambient` | nightvision, screwed, diff_preset |

Three loadable presets are **not in any family**: none of the affordance-only
"reverie_vocabulary" or compositor-test files appear in `FAMILY_PRESETS`, but
of the 27 named presets I find no orphans — coverage looks complete on paper.
Actual selection telemetry (below) tells a much darker story.

### Live recruitment + narrative state

`recent-recruitment.json` (snapshot 2026-04-19 02:43Z) records `preset.bias` as
`{family: "calm-textural", ttl_s: 30.0}`. Sampling `_call_activity_llm` log
lines across the last >4h: every narrative refers to the **`'calm-textural'`
preset family** (16:13Z, 16:14Z, 16:17Z, 16:32Z, 16:33Z, 16:34Z, 16:35Z, 16:37Z,
16:38Z, 16:39Z, 16:40Z, 16:42Z — 12+ samples, all the same family token). Zero
narratives invoke `audio-reactive`, `glitch-dense`, `warm-minimal`, or
`neutral-ambient`. The director loop's narrative is itself **stuck** on
`calm-textural`.

### Slot-level activation (12h `activate_plan` count)

20,510 `activate_plan` calls across 12h, **27 unique node types**.
Heavily front-loaded: `colorgrade` (2,321), `bloom` (2,170), `vignette`
(1,670), `noise_overlay` (1,518), `content_layer` (1,274),
`chromatic_aberration` (1,214), `scanlines` (1,055), `postprocess` (969),
`passthrough` (934). Top 9 are universal post-process nodes plus
`vhs`/`kaleidoscope`/`tunnel` (the high-frequency "signature look").

The bottom of the distribution is the personality nodes operator reads as
"same-y" by their absence: `slitscan` (155), `threshold` (153), `invert`
(153), `posterize` (152), `dither` (152), `rutt_etra` (151), `pixsort` (151),
`stutter` (149), `glitch_block` (149), `ascii` (149), **`halftone` (49)**.
A 47:1 ratio between `colorgrade` and `halftone`. The personality slots fire
1–4% of the post-process slots' rate.

### Adjacent state signals

`fx-current.txt` reads `chain` — no single preset is "current"; the FX state
is a slot-pipeline composition. `ward-fx-events.jsonl` shows `hardm_dot_matrix`
ward enters from the `music` domain at intensity 0.75 — HARDM is firing as a
ward-level emphasis but is not yet wired to bias the FX-chain preset family
(that is B6 from tonight's plan, **un-shipped**). The `glfeedback` plugin
shows shader-compile errors 30+ times in 12h — the `thermal` shader is failing
to recompile and dropping to passthrough, silently shrinking the `warm-minimal`
family by one (separate fix).

### What §1 tells us

1. The director's narrative is locked on a single preset family
   (`calm-textural`), and `recent-recruitment.json` confirms this is the only
   preset.bias family being recruited.
2. The slot-level activation distribution is heavily front-loaded on
   common-denominator post-process nodes; the personality nodes
   (`pixsort`, `halftone`, `ascii`, `glitch_block`) are 1–4 % of the top-node
   activations.
3. The narrative is producing an LLM-level loop — same wording, same family,
   tick after tick — which means the director cannot break out of `calm-textural`
   even when the wider system has wards firing in the `music` domain
   (HARDM emissive).

The dominant failure is **family monotony at the recruitment layer**. This is
not a "rotation rule missing" problem; it's a "the recruitment surface only ever
selects one option" problem.

## §2. Diagnose — Which Failure Mode Dominates

Of the 8 hypothesized causes:

1. **Recruitment score monotony — DOMINANT.** The director's narrative is
   stuck on the same family token, so the cosine query against the preset
   capability descriptions returns the same top-1 every tick. Evidence: §1
   narrative samples, recent-recruitment record. The narrative being itself
   stuck is **upstream** of the affordance pipeline — but the pipeline cannot
   correct for it because it has no signal about what "we have been on this
   family for too long" looks like.

2. **Base-level saturation — CONTRIBUTING.** `ActivationState.base_level()`
   uses ACT-R style decay (recent + old approximation, decay=0.5). After 4h
   of `calm-textural` recruitments, that family's base-level component
   dominates — `0.20 × base_level` is enough to keep `calm-textural` ahead of
   competitors when the cosine similarity tie-breaker is roughly equal.

3. **Context-boost non-variation — CONTRIBUTING.** No diversity signal flows
   into `_compute_context_boost`. The context dict carries operational state
   but no "we have been on this preset / family for N seconds" entry.

4. **Sparse affordance catalog — NOT THE BOTTLENECK HERE.** `_PRESET_FAMILY`
   declares all 5 families. The catalog is closed. The bottleneck is upstream
   (narrative monotony) rather than catalog breadth. (However, the
   parallel-investigated `ward.highlight` family in the gate-audit IS sparse
   — that is a separate issue, see §3 cross-refs.)

5. **PresetReactor cooldown dominance — NOT DOMINANT.** Chat reactor is
   30 s default; this only matters when chat is actively naming presets,
   which §1 telemetry does not show as a major signal.

6. **Chain-level transition sameness — CONTRIBUTING.** The `transition_out`
   / `transition_in` fade cycle is fixed (12 steps × 100 ms = 1.2 s). Every
   preset change uses the same fade-to-black transition. Even if the preset
   variety problem were solved, every transition would still feel identical.

7. **Palette collapse — POSSIBLE BUT UNVERIFIED.** Without per-preset palette
   metadata, this cannot be diagnosed from §1. Worth instrumenting (Phase 1
   below).

8. **No recency-aware scoring — DOMINANT (architectural).** Nothing in the
   pipeline de-weights recently-applied capabilities. Combined with #2,
   recently-recruited capabilities monotonically gain advantage rather than
   ceding territory.

The combination of #1 + #2 + #8 forms a self-reinforcing loop: the director's
narrative drifts toward whatever family was last applied, the base-level boost
locks that family in, and no decay clears the pull. The retirement of the F1
camera-hero variety-gate (which suppressed 14 % of camera dispatches) **does
not address this** — the affordance pipeline never had a variety mechanism for
preset.bias the way the camera-hero path had a hardcoded one.

## §3. Prior Art + Adjacent Systems In-Repo

- **`shared/affordance_pipeline.py:367-470`** — `select()` formula:
  `combined = (W_SIMILARITY × similarity + W_BASE_LEVEL × base_level +
  W_CONTEXT × context_boost + W_THOMPSON × thompson) × cost_weight`. Weights
  in `shared/affordance_pipeline.py:30-33`: `0.50 / 0.20 / 0.10 / 0.20`.
  No recency-distance term.
- **`shared/affordance.py:30-88`** — `ActivationState`. `record_success` and
  `record_failure` apply geometric decay `gamma=0.99` — **only when the
  capability is recruited**. There is no time-based decay path for
  non-recruited capabilities. `_TS_CAP=10.0` and `_TS_FLOOR=1.0` cap the
  dynamic range to prevent saturation but do not introduce drift toward
  exploration.
- **`agents/studio_compositor/preset_family_selector.py`** — `FAMILY_PRESETS`
  static map; `pick_from_family` does within-family non-repeat (avoids
  back-to-back of the same preset, but does not avoid back-to-back of the
  same family).
- **`agents/studio_compositor/random_mode.py`** — reads
  `recent-recruitment.json::preset.bias.family`; if recruited within 20 s,
  picks from that family; otherwise falls back to `neutral-ambient`. The
  fallback is **hardcoded** (gate-audit A6, line 242–244 of
  `2026-04-19-expert-system-blinding-audit.md`). This is its own
  expert-system rule that should also retire under the
  `feedback_no_expert_system_rules` axiom.
- **`agents/studio_compositor/chat_reactor.py`** — chat keyword → preset
  graph mutation. Cooldown 30 s default, 90 s in research mode. Bypasses the
  affordance pipeline entirely (chat input goes straight to the mutation
  bus). Out of scope for variety scoring but worth noting as a **third bias
  channel** (director, family-selector, chat reactor) that could amplify or
  dampen variety depending on usage.
- **`agents/studio_compositor/fx_tick.py:74-130`** — `tick_governance`. Calls
  `_atmospheric_selector.evaluate(stance, energy_level, available_presets,
  genre)`. This is the second selector path (independent of director
  recruitment). When live, it can override the recruitment-driven family.
  Its inputs are `gov_data.desk_activity` and `gov_data.music_genre`, both
  of which can be flat for hours.
- **`docs/superpowers/plans/2026-04-19-homage-completion-plan.md` §B6** —
  HARDM emphasis → FX-chain neon bias. Un-shipped at time of writing. This
  introduces ward → FX-bias coupling for one ward class. The proposed
  extension (§5 below) is to generalise this so multiple ward classes bias
  multiple families.
- **`docs/research/2026-04-19-expert-system-blinding-audit.md` A6, A7, A11**
  — F1, F2, A6, A7 retirements. F1 (camera variety-gate) did not affect
  preset variety. F2 (deterministic micromove) did not affect preset
  variety. The relevant gate from the audit is A6 (`random_mode` neutral-
  ambient fallback) and A7 (twitch director's hardcoded "if active_signals
  >= 6: emit `preset.bias.pressure-discharge`" rule). A6 + A7 retirement is
  **complementary** to this work — without §4 / §5 below, retiring A6 will
  produce *less* variety, not more.

## §4. Hypothesis — Where Variety Actually Lives

**Variety is not a rotation problem. Variety is a scoring problem and a
programme problem.**

The `AffordancePipeline.select()` scoring formula
(`0.50×similarity + 0.20×base + 0.10×context + 0.20×thompson`) makes no
contact with the question "is this candidate perceptually similar to
recently-applied candidates?" When the director narrative is monotonous —
which §1 demonstrates — the cosine ranking is monotonous, base-level
saturation reinforces the leader, Thompson sampling has nothing to widen
because rewards are monotonic, and the system stays put.

The fix is not a hardcoded de-weight. The fix is to make recency a **scoring
input** the pipeline weighs alongside everything else, and to make perceptual
similarity to recent history an **impingement** the pipeline can recruit away
from. Both moves preserve the no-expert-system axiom (`feedback_no_expert_system_rules`):
no rule, just a richer signal landscape.

The programme layer (cross-ref `2026-04-19-content-programming-layer-design.md`)
provides the second leg. A programme is an **affordance-expander, not an
affordance-replacer** (`project_programmes_enable_grounding`). Each programme
opens a different palette / motion-family / feedback-intensity range — between
programmes the variety surface widens by 5–10×. A "vinyl-listening" programme
biases toward `calm-textural` and `warm-minimal`; a "beat-making" programme
biases toward `audio-reactive` and `glitch-dense`. Cross-programme rotation
gives more variety than within-programme could.

Combined: scoring + programme = variety emerges from the same mechanism as
everything else (impingement → recruitment → role → persona), no rules.

## §5. Architectural Moves (Shape, Not Code)

### 5.1 `recency_distance` as scoring input

Add a new term to `SelectionCandidate`:

```python
class SelectionCandidate(BaseModel):
    # ... existing fields ...
    recency_distance: float = 0.0  # min cosine distance to last-N applied capabilities
```

Maintain a rolling window in `AffordancePipeline`:

```python
class _RecencyTracker(BaseModel):
    window_size: int = 10
    recent_embeddings: list[list[float]] = Field(default_factory=list)
    recent_capability_names: list[str] = Field(default_factory=list)

    def record_apply(self, capability_name: str, embedding: list[float]) -> None: ...
    def distance(self, candidate_embedding: list[float]) -> float:
        # Returns 1 - max(cosine_sim) over the window. Higher = more novel.
```

When `select()` scores a candidate, fold in `recency_distance`:

```
final = (W_SIMILARITY × similarity
       + W_BASE_LEVEL × base_level
       + W_CONTEXT × context_boost
       + W_THOMPSON × thompson_score
       + W_RECENCY × recency_distance) × cost_weight
```

Proposed weights (renormalized): `0.45 / 0.18 / 0.09 / 0.18 / 0.10`. The
recency weight (0.10) is small enough that strong narrative signal still
wins, but it is enough to break ties between similarly-scored candidates in
favor of perceptually-distant options.

This is a **scoring input**, not a filter. Highly-grounded recruitment can
still apply the same family twice in a row — but only when the signal
strongly justifies it.

Prior art: novelty-bonus terms in contextual bandits and intrinsic-motivation
RL (Pathak et al. 2017, "curiosity-driven exploration"; Burda et al. 2018,
RND). Latent-space recency penalties are also standard in recommendation
systems (Spotify Discover, Netflix's diversity reranker).

### 5.2 Thompson posterior decay (non-recruitment branch)

`ActivationState` currently decays `ts_alpha` and `ts_beta` only on
`record_success` / `record_failure`. Add a third path:

```python
def decay_unused(self, gamma_unused: float = 0.995) -> None:
    """Pull alpha/beta toward Beta(2, 1) prior when capability not recruited."""
    target_alpha, target_beta = 2.0, 1.0
    self.ts_alpha = self.ts_alpha * gamma_unused + target_alpha * (1 - gamma_unused)
    self.ts_beta = self.ts_beta * gamma_unused + target_beta * (1 - gamma_unused)
```

Called once per tick (or per minute) on every capability NOT recruited this
period. After a long monopoly by capability A, capability B's
`thompson_sample()` slowly recovers toward 0.67 (Beta(2,1) mean), giving B a
chance to win on Thompson variance even when its base-level is depressed.

Decay-rate tradeoff: `0.999` → ~700-tick half-life (gentle, recovers over
hours); `0.99` → ~70-tick (recovers in ~1 min @ 1 Hz); `0.95` → ~14-tick
(restless). Recommended start: `0.999` at 1 Hz, tune down if monopoly
persists.

### 5.3 Affordance-catalog audit + closure

§1 shows the preset family map is closed (5 families, 24 presets); but the
gate-audit identifies a parallel `ward.highlight` issue (returns 0 candidates
10× per 12h — same architectural shape, narrow per-family catalogs cause
empty retrievals). Before any scoring change, run a comprehensive audit:
enumerate every `preset.bias.<family>` capability in Qdrant; cross-check
against `FAMILY_PRESETS` and `presets/*.json`; flag families <3 members
(`neutral-ambient` is at the floor with 3); flag presets registered but
failing to load (e.g., `thermal` fragment-compile failure noted above).
Without this audit, scoring changes price in recency over a possibly-narrow
pool.

### 5.4 Perceptual distance as impingement

When the recency tracker observes that the last-N preset embeddings have
clustered (e.g., mean pairwise cosine similarity > 0.85), emit an
impingement:

```python
Impingement(
    source="affordance_pipeline.recency",
    intent_family="content.too-similar-recently",
    content={"metric": "preset_recency_cluster",
             "cluster_similarity": float,
             "cluster_size": int},
    narrative=(
        "The visual chain has stayed in a similar register for the last "
        f"{cluster_size} applies (cluster similarity {cluster_similarity:.2f}). "
        "Reach for something perceptually distant if the moment allows."
    ),
)
```

The pipeline can then recruit a `novelty.shift` capability (if registered)
that biases toward a distant preset family. Critically, the impingement
**does not force a shift** — it is one signal among many. If the operator is
mid-narration and the moment demands continuity, the director's narrative
similarity will still outweigh the novelty impingement.

This is the anti-repetition signal **as an impingement**, not as a gate. The
pipeline decides whether to act on it. It satisfies
`feedback_no_expert_system_rules` because the impingement is a fact about the
perceptual surface, not a hardcoded rule about what to do next.

### 5.5 Chain-level: explicit transition affordances

Currently `random_mode.transition_out` / `transition_in` apply a fixed
brightness fade (12 steps × 100 ms) — every preset change uses the same
transition. Register the transition family as an affordance domain (5
records: `transition.fade.smooth`, `transition.cut.hard`,
`transition.netsplit.burst`, `transition.ticker.scroll`,
`transition.dither.noise`), each with its own Gibson-verb description. Per
chain change, the pipeline recruits **both a preset (or family) AND a
transition** — roughly doubling the chain-level vocabulary at no cost to
within-preset variety. Transitions can be programme-biased (§5.6); the
existing brightness-fade primitive becomes the implementation behind
`transition.fade.smooth`. The other 4 each need a small new primitive
function.

### 5.6 Programme-owned palette ranges (depends on content-programming layer)

Cross-reference: `docs/research/2026-04-19-content-programming-layer-design.md`.

Each programme declares a **palette-family range** — a soft prior over which
preset families fit the programme's aesthetic register. Schema sketch:

```python
class ProgrammeAesthetics(BaseModel):
    palette_bias: dict[str, float]    # family_name -> weight 0..1
    transition_bias: dict[str, float] # transition_name -> weight 0..1
    feedback_intensity_range: tuple[float, float]
    motion_register: Literal["still", "drift", "pulse", "burst"]
```

Example: a `vinyl-listening` programme leans `calm-textural` 0.4 / `warm-minimal`
0.4 / `audio-reactive` 0.2 / `glitch-dense` 0.0 with smooth transitions and
low feedback intensity. A `beat-making` programme inverts to `audio-reactive`
0.5 / `glitch-dense` 0.4 with burst transitions and high feedback. The
`palette_bias` is folded into `_compute_context_boost` so programme-aligned
families get a context-boost when active. Between programmes, the active
palette flips — cross-programme rotation yields the dramatic step
within-programme rotation cannot.

Per `project_programmes_enable_grounding`, palette_bias is a **soft prior**,
not a hard gate. If impingement strongly demands a glitch-dense move during
a vinyl-listening programme, the recruitment can still win — the bias just
tilts the field.

## §6. Integration With Tonight's Retirements + Un-Shipped Work

**F1 (camera-hero variety-gate retirement)** — operated on `cam.hero.*`, not
`fx.family.*`. Does not affect preset variety directly. However: F1's gate
was hiding camera-hero recruitment producing same winners 14% of the time —
identical failure-mode shape to §1's preset.bias monoculture. Pre-F1
operator perception of camera variety may have been artificially inflated;
post-F1, raw recruitment quality is visible, and §4 / §5 moves are needed
on the preset side as well.

**F2 (deterministic micromove retirement)** — exposes raw recruitment
surface; same caveat as F1.

**A6 (`random_mode` neutral-ambient fallback) — un-retired** — sibling
expert-system rule per §3 reference. **Sequence: ship §5.1–§5.4 first, then
retire A6.** Without recency scoring + Thompson decay first, retiring A6
will make variety *worse* in the interim. Ship architectural fix, validate
on telemetry, then remove gate.

**A7 (twitch director `pressure-discharge` rule) — un-retired** — emits a
hardcoded `preset.bias.pressure-discharge` when `active_signals >= 6`. Replace
with a real perceptual signal.

**B6 (HARDM emphasis → FX-chain neon bias) — un-shipped** — first wired ward
→ FX-bias coupling. **Generalise the pattern:** every prominent ward should
bias a *different* preset family.

| Ward class | Family bias | Programme hint |
|---|---|---|
| HARDM dot-matrix (music kicks) | `audio-reactive` (or `glitch-dense` on burst) | beat-making |
| Vinyl platter rotating | `calm-textural` | vinyl-listening |
| Album overlay foregrounded | `warm-minimal` | reflection |
| Token pole high | `neutral-ambient` | working |
| Sierpinski active | `glitch-dense` | exploration |
| Activity header (research) | `warm-minimal` | research |

Each coupling is an impingement-emit, not a hardcoded gate — the ward
emphasis emits an impingement carrying `intent_family=preset.bias`, the
pipeline scores it, and the recruitment may or may not act. Diversity comes
from wider coupling: more wards driving more families.

### B4 (rotation modes: steady / deliberate / rapid / burst)
Rotation mode should correlate with the §5.1 recency weight:

| Rotation mode | `W_RECENCY` value |
|---|---:|
| steady | 0.04 |
| deliberate | 0.08 |
| rapid | 0.12 |
| burst | 0.18 |

In `burst` mode, novelty matters more — recency penalty is heavier. In
`steady` mode, continuity matters more — recency penalty is lighter. The
mode itself is recruited (per the homage-completion design), so this is a
context-boost-driven adjustment to the scoring formula at runtime. This is
*not* a rule — it is a parameterisation of an existing scoring input.

## §7. Post-Live Integration Sequencing

Eight phases. Phase 1 is telemetry-first (per `feedback_exhaust_research_before_solutioning`)
to pin a before/after.

| Phase | Scope | Files | Deps | LOC | Success criteria |
|---|---|---|---|---:|---|
| 1 — Variety telemetry baseline | Family-distribution + per-preset apply-count Prometheus metrics, Grafana panel "preset.bias family distribution (rolling 1h)" | `shared/affordance_metrics.py`, `agents/studio_compositor/director_observability.py` | None | ~150 | 2h baseline captured before any scoring change; family entropy time-series visible |
| 2 — Affordance-catalog audit | §5.3 script enumerating Qdrant ↔ FAMILY_PRESETS ↔ disk discrepancies | `scripts/audit-preset-affordances.py` + audit report | Phase 1 | ~100 | Audit run <30s; flags Qdrant/disk mismatches; flags load-failures |
| 3 — Thompson posterior decay | §5.2 `decay_unused` on `ActivationState` + tick-loop hook | `shared/affordance.py`, `shared/affordance_pipeline.py` | None | ~60 | Idle posterior drifts to Beta(2,1) in 24h; unit tests verify drift |
| 4 — `recency_distance` scoring input | §5.1 recency tracker + new scoring term, feature-flagged via `HAPAX_AFFORDANCE_RECENCY_WEIGHT` | `shared/affordance_pipeline.py`, `shared/affordance.py`, `tests/shared/test_affordance_recency.py` | Phases 1, 2 | ~250 | Family entropy ≥30% higher than Phase 1 baseline after 2h |
| 5 — Perceptual-distance impingement | §5.4 emit `content.too-similar-recently` + register `novelty.shift` capability | `shared/affordance_pipeline.py`, `shared/compositional_affordances.py`, `agents/studio_compositor/compositional_consumer.py` | Phase 4 | ~150 | Impingement fires within 1 tick when last-10 cluster ≥0.85; novelty.shift recruitment visible in metrics |
| 6 — Transition affordances | §5.5 register 5 transition affordances + primitives + chain-change recruitment | `shared/compositional_affordances.py`, `agents/studio_compositor/random_mode.py`, `agents/studio_compositor/transition_primitives.py` (new) | Phases 4, 5 | ~400 | 5 transitions visually verifiable on `/dev/video42`; transition entropy ≥0.6 over 1h |
| 7 — Generalised ward → FX bias | §6 pattern: each prominent ward emits `preset.bias` impingement | `agents/studio_compositor/hothouse_sources.py`, `shared/director_intent.py` | Phases 4–6 | ~200 | Family entropy ≥30% higher than Phase 5 baseline |
| 8 — Programme-owned palette ranges | §5.6 `ProgrammeAesthetics` schema; programme-aware context-boost | `shared/programmes/`, `shared/affordance_pipeline.py::_compute_context_boost` | Content-programming layer + Phase 7 | ~300 | ≥2 programmes declare palette_bias; cross-programme palette flips visible; multi-programme 4h entropy ≥0.8 |

Phases 3 and 5 are parallel-safe siblings of Phase 1. Phases 6 and 7 are
parallel-safe with each other. Phase 8 is terminal (depends on the
content-programming layer landing first).

## §8. Open Questions for the Operator

1. **What does "same-y" mean specifically?** Same palette, same motion
   register, same density, same node composition? §5.1's recency-distance
   is a generic embedding-distance term; if the operator is responding to
   a specific axis (e.g., low-saturation), a palette-distance term may be
   needed in addition.

2. **Chain-level vs within-preset:** is the chain transition (§5.5) the
   loudest miss, or within-preset visual variety? Phase 6 vs Phase 4
   sequencing depends on this.

3. **Per-programme palette characterizations:** the §5.6 sketches
   (vinyl-listening = calm/warm; beat-making = audio-reactive/glitch-dense)
   are first guesses. Need a brief pairing session once the programme layer
   ships.

4. **Thompson decay aggressiveness:** is exploration recovery over hours
   (`gamma_unused=0.999`) acceptable, or should it be minutes (`0.99`)?
   Aggressive decay makes the system feel "restless"; gentle keeps
   continuity but risks long-form monocultures.

5. **Novelty-impingement veto:** when `content.too-similar-recently` fires,
   should the operator be able to suppress it for a deliberate-listening
   register (would need an operator-controlled `affordance_inhibition`)?

6. **F1/F2 retirement perceptual baseline:** did the "same-y" complaint
   appear before or after F1/F2 went live? If post-F1/F2, some perceived
   variety may have been camera/micromove rotation masking preset
   monoculture.

7. **HARDM B6 unshipped expectation:** is B6 alone enough, or is the wider
   §6 pattern required?

8. **Director narrative monotony — separate fix?** The §1 finding that the
   director's narrative is itself locked on `'calm-textural'` for hours
   suggests a director-loop bug independent of the affordance pipeline.
   Worth a separate research thread — possibly the director's prompt is
   templating in the recently-recruited family name and creating a
   self-reinforcing loop.

---

**Cross-references:**
- `docs/research/2026-04-19-content-programming-layer-design.md` (§5.6
  programme-palette ranges depend on)
- `docs/research/2026-04-19-expert-system-blinding-audit.md` (§3 + §6 gate
  retirements)
- `docs/research/2026-04-19-blinding-defaults-audit.md` (related defaults
  cleanup)
- `docs/superpowers/plans/2026-04-19-homage-completion-plan.md` §B6 (un-shipped
  HARDM → FX-chain coupling)
- Memory: `feedback_no_expert_system_rules`, `project_programmes_enable_grounding`,
  `project_effect_graph`, `feedback_grounding_exhaustive`
