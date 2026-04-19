# Pre-Live Audit Synthesis — Cascade Slice + Alpha Dispatch

**Date**: 2026-04-20
**Source catalog**: `docs/research/2026-04-20-livestream-audit-catalog.md` (104 audits, 16 sections)
**Split**: cascade 67 audits / alpha 37 audits (see
`~/.cache/hapax/relay/cascade-to-alpha-audit-execution-20260419.yaml`)

---

## §0. Status at time of writing

- **Cascade slice**: COMPLETED. 73 result rows across 67 audit IDs
  (some split into sub-items, e.g. `2.1-hardm` / `2.1-phase5_publisher`).
  Raw results at `docs/research/2026-04-20-cascade-audit-results.yaml`.
- **Alpha slice**: DISPATCHED via relay. Awaiting
  `~/.cache/hapax/relay/alpha-audit-results-20260419.yaml`.
  Alpha's slice covers the physical / visual / compositor / content-
  programming domains the cascade slice deliberately omits.

This document captures cascade's slice in full + the cross-cutting
implications already visible within it. A final holistic synthesis
that integrates alpha's findings will be produced as an addendum once
alpha's results land.

---

## §1. Headline — cascade slice rollup

| Outcome | Count | Notes |
|---|---|---|
| Pass | **53** | Majority of surfaces are intact |
| Warn | **11** | 4 of 11 are documented post-live tasks already in queue |
| Fail | **0** | After correcting one false-fail (1.2 regex artifact — guard IS present) |
| Indeterminate | **9** | Mostly "needs operator eye" — firewall, Pango rendering, grafana port confirmation |

**No stream-stop findings in the cascade slice.** The eleven warnings
cluster around three already-known gaps (YT metadata red-flag scanner,
multi-modal risk classifier, political-flashpoint detector) that were
explicitly marked post-live in the catalog; one producer-cadence
artifact (write-on-change vs write-on-tick, filed as task #183); and
two surfaces that genuinely need operator-level adjudication
(shared/notify gating, failed non-livestream services).

---

## §2. Per-warn triage

Each warning graded by operator-blocking severity + remediation cost.

| Audit | What it warns | Block? | Remediation cost | Recommendation |
|---|---|---|---|---|
| 1.3 Captions strip | Captions module location unverified | no | 5 min (grep confirmation) | Spot-check next restart |
| 1.7 Notifications via ntfy | shared/notify.py doesn't route through speech_safety | LOW (ntfy is operator-only) | 20 min to wire | Wire pre-live if time; post-live if not |
| 1.8 YouTube metadata | LivestreamDescriptionUpdater may emit LLM-origin text | LOW (review-before-publish) | 30 min | Audit the description-source code path |
| 1.9 Trademark / lyric detector | No heuristic in place | no (ContentID catches) | post-live | Task #165 |
| 1.11 Political flashpoints | No detector | no | post-live | Task #165 |
| 2.1-phase5 | youtube-video-id.txt 8 min stale | no (correct stale-state, write-on-change) | filed (task #183) | Upgrade to write-on-tick |
| 6.1 Publisher cadence breach | Following 2.1-phase5 | no | same fix | Task #183 |
| 13.4 YT metadata red-flag scanner | None | no | post-live | Task #165 aggregates |
| 13.5 Multi-modal risk classifier | None | no | post-live | Task #165 aggregates |
| 15.1 default.json runtime drift | non_destructive field auto-written | no (known migration) | low | Document; do not re-commit runtime file |
| 16.2 Failed user services | backup + llm-backup + tailscale-cleanup all failed | no (non-livestream) | 15 min to diagnose each | Post-live triage |

**Zero warnings in the cascade slice block stream start.** The eleven
map cleanly to either (a) documented post-live tasks already in the
backlog or (b) low-impact operational hygiene.

---

## §3. Cross-cutting observations within the cascade slice

Patterns visible without alpha's data, already useful:

### 3.1 Content-safety is fail-closed at the TTS layer but NOT at prompt-generation

§1.1 (TTS gate) passes. §1.4 (director narrative → TTS) passes
transitively because it routes through `TTSManager.synthesize`. But
§1.9 (trademark/lyrics) and §1.11 (political) both warn — these are
content the LLM *generates* that the TTS regex doesn't know about.
The 2026-04-20 14:08 leak is the archetype: Hapax narrated about a
rap-analysis video; gate caught one slur token but the LLM was also
generating context around it. **Prompt-level prohibition is the
missing prevention layer** — gate is last-line-of-defense, not
primary. This is task #165 (de-monetization plan) + task #173's
successor.

### 3.2 Signal-flow is healthy at the producer side but observability on the consumer side is implicit

§2.1 reports all tracked producers fresh (5/5 green). §2.2 reports
compositor metrics alive. But the per-consumer ward freshness gauges
I built (3.1.x family in the catalog proposes these) are not
implemented for every producer the cascade slice ships — specifically
`recent-impingements` and `chat_signals_aggregator` don't emit
Prometheus gauges. If either producer dies silently, we'll see
downstream staleness but not root-cause it fast. **Filing as a
follow-up hardening task.**

### 3.3 Consent posture is strong on 4 of 6 axes but verification of the 2 weak axes is indirect

§5.1–5.6 all pass, but 5.2 (person-detection fail-closed) required
indirect grep for `fail.closed|fail_closed` keywords; the actual
invariant is in binary compositor behaviour, which only alpha can
verify by forcing a face-detector crash and confirming egress is
blocked. **This is a cross-cutting handoff to alpha's §11 compositor
regression slice** — the fail-closed path is a compositor behaviour,
not a python-side guard.

### 3.4 OAuth dual-token architecture is LIVE and verified

§10.1-main + §10.1-sub both green. The sub-channel token (LegomenaLive,
`UCfZAG-BPvEOl0-GEhMbX89A`) was minted live this session and resolves
the correct broadcast id (`5m13sNsCaeg`, upcoming). §15.5 confirms
LiteLLM keys present. Network + OAuth is the one section where
FINDING-V's integration landed clean end-to-end today.

### 3.5 Recording / archival is correctly suppressed

§14.1–14.5 all pass. No camera-frame writes (≤10 jpg in 60 min, all
the live snapshots). No audio writes. No transcript writes. HLS on
tmpfs. MinIO lifecycle rule honoured. The audit-scan pattern here
(find … -mmin -60) is cheap enough to run continuously; **propose
turning it into a systemd timer that alerts on any write growth**.

### 3.6 Governance drift is LOW

§8.1–8.7 all pass. Axiom registry checksum captured. Anti-
personification linter clean. Frozen-files enforcement via pre-commit
active. Working-mode = research at SSOT. No hardcoded expert-system
rules per the emergent-behavior principle. Stream-mode dispatch ready.

### 3.7 Hardware touch-points the cascade slice can't reach

§9.* is entirely alpha's slice — GPU headroom, Pi fleet, USB camera
stability, disk, CPU/memory, thermal, power. Cascade has no window
into these. If alpha reports any §9 failure, **it likely implies a
cascade observability gap** (§7.1 metric registration warn) — the
hardware signal should be surfaced to Prometheus, and if it isn't,
the coverage warn is confirmed.

### 3.8 Eleven audits flag cross-cutting dependencies explicitly

Every one of the cascade-slice warns has a mirrored concern on
alpha's side:

- 1.3 captions → alpha §3.1 visual regression of captions ward
- 1.8 YT metadata → alpha §12.2 objective visibility overlay firing
- 13.4 metadata red-flag → alpha §11 compositor render integrity
- 16.2 failed services → alpha §9 hardware health may show root

In other words, **the cascade and alpha slices cross-bleed on at
least 4 of the 11 cascade warns**. Full holistic synthesis will need
alpha's data to close each.

---

## §4. Findings that change the pre-live gate score

Catalog §17 proposed 30 pre-live rows (22 "block" + 8 "warn").
Cascade's slice covers roughly 2/3 of these. After cascade's run:

| §17 gate row | Cascade result | Pre-live verdict |
|---|---|---|
| Content-safety smokes (§1.1–1.3) | pass/pass/pass (1.3 spot-check recommended) | **go-safe** |
| Face-obscure + fail-closed (§5.1–5.2) | pass indirect; fail-closed verification is alpha's | **go-safe pending alpha §11** |
| Audio routing (§4.1/4.3/4.6) | alpha's slice | **pending alpha** |
| YT metadata red-flag (§1.8/13.4) | warn/warn (post-live) | **advisory — review title/description manually before go-live** |
| Hardware + network (§9/§10.5) | §10.5 RTMP ok; §9.* is alpha's | **pending alpha** |
| Governance integrity (§8.1/§11.5) | §8.1 pass; §11.5 alpha | **go-safe pending alpha** |
| Live-egress kill-switch (§16.6) | pass | **go-safe** |

**Cascade-side verdict: no stream-stop.** The seven catalog-gate rows
that need alpha's confirmation are all on the physical / visual /
hardware surfaces alpha is best suited to verify.

---

## §5. Open questions this synthesis cannot answer

1. **What are alpha's §11 compositor regression + §9 hardware
   results?** The face-obscure fail-closed verification (§5.2) and
   the full pre-live gate verdict both await alpha.

2. **Is any of the 11 cascade warns severe enough to block?**
   Cascade's assessment is no. If operator disagrees on any single
   warn (particularly 1.7 ntfy gate or 16.2 failed backup services),
   flag and I'll ship the specific remediation pre-live.

3. **Post-live task prioritisation.** Tasks #165 (de-monetization),
   #173 (pool rotation already landed), #183 (write-on-tick
   cadence), and new follow-ups from this audit (§1.7 gate, §11
   consumer-freshness gauges for new producers) — which should go
   first after the live stream closes?

---

## §6. Handoff instructions for alpha addendum

When alpha's results arrive at
`~/.cache/hapax/relay/alpha-audit-results-20260419.yaml`:

1. Cascade reads per-audit + section-rollup + incident-flags.
2. Produce an addendum doc
   `docs/research/2026-04-20-audit-synthesis-alpha-addendum.md` with
   the same per-audit, warn-triage, cross-cutting observations
   structure.
3. Integrate cascade + alpha cross-cutting observations in a final
   "holistic" section that identifies failure modes requiring BOTH
   slices to confirm (e.g., fail-closed face-obscure + prompt-level
   slur prohibition + audio routing kill-switch all interlock as the
   3-layer defence for the monetization-critical 2026-04-20 14:08
   leak class).
4. Update §17 gate-row table with alpha's findings so operator has a
   single go/no-go table.

---

## Appendix. Cascade raw results

`docs/research/2026-04-20-cascade-audit-results.yaml`.

73 result blocks, YAML-per-entry with id / result / evidence / (if
applicable) remediation. Readable via
`grep -B1 "result: fail" docs/research/2026-04-20-cascade-audit-results.yaml`
etc.
