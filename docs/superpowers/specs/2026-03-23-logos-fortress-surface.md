# Logos Fortress Surface

**Status:** Design (UI surface specification)
**Date:** 2026-03-23
**Builds on:** Fortress State Schema, Fortress Governance Chains, Logos Design Language (`docs/logos-design-language.md`)

---

## 1. Embedding Strategy

The fortress surface is not a game renderer. It is a structured data visualization of fortress state, governance decisions, and narrative, implemented within the existing Logos design language, component patterns, and theme system.

Two embedding points are defined:

1. **Ground region variant.** When fortress mode is active, the Ground region displays a fortress dashboard in place of camera feeds. The same depth model (surface / stratum / core) applies.
2. **Dedicated page route.** `/fortress` is accessible via command palette or direct URL.

The choice between variants is driven by `working_mode`. DF mode may be introduced as a third working mode (alongside research and R&D) or as a feature toggle within R&D mode. This design decision is deferred to implementation.

## 2. Ground Region -- Surface Depth

Minimal ambient display, consistent with the existing ground surface pattern.

- **Fortress headline.** Top-left, replacing TimeDisplay. Format: `"Year 3, Late Autumn -- 47 dwarves -- Siege!"`.
- **Survival counter.** Top-right, prominent. Format: `"Day 1,247"`.
- **Ambient text cycling.** Fortress events narrated by the storyteller role. Events fade in sequence (e.g., `"A migrant wave of 12 has arrived."` followed by `"The mason has created a masterwork door."`).
- **Mood indicator.** Overall fortress mood expressed as a single color tint applied to the ambient shader. Mapping: green = content, yellow = stressed, orange = danger, red = tantrum spiral.
- **Era badge.** One of: `founding`, `growth`, `establishment`, `prosperity`, `legendary`. Derived from FortressPosition.

## 3. Ground Region -- Stratum Depth

Structured dashboard, consistent with the existing ground stratum camera grid pattern.

- **Population panel** (top-left). Citizen count, idle count, military count, mood histogram (five bars: ecstatic / happy / fine / unhappy / miserable).
- **Resources panel** (top-right). Food and drink bars (green-to-red gradient), key stockpile counts (wood, metal, cloth).
- **Military panel** (bottom-left). Squad count, equipment quality, active threats, alert status.
- **Activity panel** (bottom-right). Active goals from GoalPlanner, current season priorities, governance chain activity indicators (six dots; color encodes suppression level).

## 4. Ground Region -- Core Depth

Deep detail view.

- **Governance flow.** Six-node directed acyclic graph (one node per chain) with directed edges representing suppression fields. Edge thickness encodes suppression level. Node color encodes activity level. Edges animate when a chain produces a command.
- **Goal tree.** Active CompoundGoals rendered as an expandable tree. Each SubGoal displays its state (pending / active / completed / blocked). Selecting a node reveals the FortressState snapshot that drove the decision.
- **Event timeline.** Horizontal scrollable timeline of FortressEvents, color-coded by severity. Selecting an event displays the storyteller narrative for that episode.

## 5. Bedrock Integration

Fortress vitals appear in the bedrock surface alongside existing health, cost, and axiom indicators.

- **Fortress health dot.** Green (nominal), yellow (stressed), orange (crisis), red (dying).
- **Survival days counter.** Compact numeric display.
- **Active threats indicator.** Skull icon with count, visible when threat count exceeds zero.

## 6. Hapax-Bar Integration

The StimmungField reflects fortress context when DF mode is active.

- Stance maps from fortress health: nominal / cautious / degraded / critical, derived from fortress mood, threat level, and food supply.
- Agent count includes the six fortress governance chains as additional agents.

## 7. Investigation Overlay Integration

The fortress is queryable via the investigation overlay (`/` key). Example queries:

- `"What happened since the last siege?"` -- The storyteller retrieves relevant episodes and produces a narrative summary.
- `"Should I breach the third cavern?"` -- The advisor assesses military readiness, stockpile levels, and risk factors.
- `"Why did Urist die?"` -- The advisor queries death events and constructs a causal explanation.

These queries use the existing investigation API. Fortress-directed queries are routed to the advisor chain via the standard query dispatch mechanism.

## 8. Theme Compliance

All fortress UI components use CSS custom properties defined in the design language.

- Severity colors per section 3.7: `green-400`, `yellow-400`, `orange-400`, `red-400`.
- Signal pips per section 5.2: 6px, 8px, or 10px based on severity.
- Zone density per section 5.3: maximum three signals per zone at stratum depth.
- Typography per section 1.6: JetBrains Mono.
- No hardcoded hex values.

The R&D theme (Gruvbox Hard Dark) is the primary theme for fortress play. The Research theme (Solarized Dark) is applied if fortress mode is active during research mode. This case is unlikely but technically supported.

## 9. Data Sources

| Component | API Endpoint | Poll Cadence |
|---|---|---|
| Fortress headline | `/api/fortress/state` (new) | 5s |
| Population panel | `/api/fortress/state` | 5s |
| Resources panel | `/api/fortress/state` | 5s |
| Military panel | `/api/fortress/state` | 5s |
| Governance flow | `/api/fortress/governance` (new) | 2s |
| Goal tree | `/api/fortress/goals` (new) | 5s |
| Event timeline | `/api/fortress/events` (new) | 5s |
| Survival counter | `/api/fortress/state` | 5s |

All endpoints are served by logos-api, reading from `/dev/shm/hapax-df/` state files.
