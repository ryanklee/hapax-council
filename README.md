# hapax-council

Externalized executive function infrastructure governed by constitutional axioms. LLM agents handle the cognitive work that produces no deliverables — tracking open loops, maintaining context across conversations, noticing when things go stale — for a single operator on a single workstation.

## The Problem This Solves

Knowledge workers perform substantial executive function labor that compounds when neglected. Remembering which direct report mentioned a blocker three meetings ago. Noticing that a service has been degraded for three days and nobody brought it up. Keeping documentation in sync with a codebase that moves faster than anyone's attention. Recognizing that a calendar invite for a 1:1 was cancelled and the underlying issue was never resolved.

For an operator with ADHD and autism, this labor isn't merely inconvenient. Task initiation, sustained attention, and routine maintenance are genuine cognitive constraints — not character flaws to overcome, but structural bottlenecks that conventional productivity tools do not address because they assume the executive function they are meant to support. A todo list does not help if the executive function required to maintain the todo list is the same executive function that's constrained.

hapax-council encodes these constraints as architecture. The system doesn't remind the operator to check a dashboard; it processes the data, evaluates what matters, and pushes a notification with a concrete next action. A meeting transcript placed in the right directory is ingested, the relevant person's context is updated, nudges are recalculated, and a notification is queued — without operator involvement. The operator's cognitive budget is spent on judgment, not bookkeeping.

## Constitutional Governance

The system is governed by five axioms defined in [hapax-constitution](https://github.com/ryanklee/hapax-constitution). These are not configuration options or feature flags. They are structural constraints — things the system cannot do regardless of how useful they might seem — with formal enforcement at commit time, at runtime, and in a growing body of precedent decisions.

| Axiom | Weight | Constraint |
|-------|--------|------------|
| `single_user` | 100 | One operator. No authentication, no roles, no multi-user abstractions. This is absolute. |
| `executive_function` | 95 | Zero-config agents. Errors include next actions. Routine work automated. State visible without investigation. |
| `corporate_boundary` | 90 | Work data stays in employer systems. Home infrastructure is personal + management-practice only. |
| `interpersonal_transparency` | 88 | No persistent state about non-operator persons without an active, revocable consent contract. |
| `management_governance` | 85 | LLMs prepare context; humans deliver feedback. No generated coaching language about individuals. |

### How Governance Works

Axioms are short principles. To enforce them, the system derives concrete implications — ~81 currently — using four interpretive canons borrowed from statutory and constitutional interpretation in law. This is not a metaphorical borrowing. These are the reasoning techniques that courts use to derive specific obligations from general texts.

**Textualist reading**: what does the axiom literally say? `single_user` says "one operator" — the codebase cannot contain structures that model distinct identities. **Purposivist reading**: what goal does the axiom serve? `executive_function` accommodates specific cognitive constraints — an error that says "check the logs" violates the purpose. **Absurdity doctrine**: reject interpretations that produce nonsensical results — `single_user` doesn't prohibit password-protecting a local interface. **Omitted-case canon**: what does the axiom's silence mean? `management_governance` doesn't say "LLMs may draft suggested feedback language" — the silence is a prohibition.

Implications are enforced at graduated tiers. **T0** implications are structurally blocked — Claude Code hooks scan every file edit, every commit, and every push against 20 regex patterns. A T0 violation never reaches review. **T1** implications require human sign-off before merging. **T2** produce warnings. **T3** are advisory. The governance system also includes sufficiency probes that verify positive requirements: not just "the system doesn't do X" but "the system actively provides Y" — error messages actually contain next actions, recurring agents actually have systemd timers.

### Precedent

Eighty-one implications cannot anticipate every situation. When an implication encounters a novel case, the system records a precedent: the situation, the decision, the reasoning, and the distinguishing facts. Future encounters consult these precedents via semantic search in Qdrant. This is the common law mechanism — consistency over time without exhaustive specification.

Precedents carry authority weights: operator decisions (1.0) bind over agent decisions (0.7), which bind over derived decisions (0.5). An agent's governance call stands until the operator reviews it, but can be overridden. Over time, the precedent store accumulates a body of case law that handles the edge cases the axioms couldn't anticipate.

See [axioms/README.md](axioms/README.md) for the full governance architecture.

### The Consent Framework

The `interpersonal_transparency` axiom creates a hard boundary around data about non-operator persons. The system operates in a household with other people. Cameras detect faces, microphones pick up voices, arrival patterns are observable. Without explicit governance, this data accumulates into persistent models of other people's behavior.

The enforcement mechanism is a consent contract: a bilateral agreement between operator and subject that enumerates permitted data categories, grants the subject inspection access to all data the system holds about them, and is revocable by either party at any time with full data purge on revocation. The `ConsentRegistry` gates data flows at the ingestion boundary — before embeddings are extracted, before state is persisted, before any downstream processing.

Transient perception is permitted (VAD detects a voice but doesn't persist identity), but any derived or persistent state about a specific person requires a contract. The system doesn't default to "it's just environmental sensing."

## Architecture

```
Coordination:  Markdown files with YAML frontmatter on disk (filesystem-as-bus)
Agents:        Pydantic AI, invoked by CLI/API/timer (stateless per-invocation)
Scheduling:    systemd timers (autonomous) + CLI (on-demand) + Claude Code (interactive)
API:           FastAPI cockpit (30+ endpoints, SSE for live updates)
Dashboard:     React SPA (council-web/)
Knowledge:     Qdrant (768d nomic-embed-text-v2-moe, 4 collections)
Inference:     LiteLLM proxy → Anthropic Claude / Google Gemini / Ollama (local RTX 3090)
Voice:         Always-on daemon (wake word, speaker ID, ambient perception, Gemini Live)
IDE:           VS Code extension + Claude Code skills and hooks
```

### Filesystem-as-Bus

Agents coordinate by reading and writing markdown files with YAML frontmatter, not by calling each other through APIs or message queues. All state is human-readable, git-versioned, and debuggable with `cat` and `grep`. There is no broker, no schema migration, no service to monitor. If the reactive engine goes down, the data is still there. This trades transactional consistency for debuggability and operational simplicity — a deliberate choice for a single-operator system where the operator is also the maintainer.

### The Reactive Engine

When a file changes in the data directory, inotify fires. The change event is enriched with metadata (document type from YAML frontmatter, file category from path). Rules — pure functions mapping events to actions — evaluate against each event. Multiple rules can fire; duplicate actions collapse. Actions execute in phases: deterministic work first (cache refreshes, metric recalculation — unlimited concurrency, zero cost), then LLM work (synthesis, evaluation — semaphore-bounded at 2 concurrent to prevent GPU saturation or API cost runaway). Self-trigger prevention tracks the engine's own writes and skips events from them.

### The Voice Daemon and Perception Type System

The voice daemon (`agents/hapax_voice/`) is an always-on multimodal interaction system built on a perception type system that addresses a specific hard problem: fusing signals that arrive at vastly different rates — MIDI clock at <1ms, audio energy at 50ms, emotion at 1–2s, workspace analysis at 10–15s — into governance decisions without losing data, temporal precision, or correctness.

The type system has three layers, each with algebraic properties that make composition safe:

**Perceptives** — continuous and discrete signal abstractions. `Behavior[T]` represents a continuously-available value with a monotonic watermark (always has a current reading; time never goes backward). `Event[T]` represents a discrete occurrence (happens at a specific instant; no "current value"). `Stamped[T]` is their common currency: an immutable snapshot frozen at a moment in time. These map to the Behavior/Event duality from functional reactive programming (Elliott 2009, Yampa, Reflex), adapted with watermarks from stream processing (Flink) for staleness reasoning.

**Detectives** — governance composition primitives. `VetoChain[C]` composes constraints where any link can deny, evaluated exhaustively for audit. Adding a veto can only make the system more restrictive, never less — a monotonicity property borrowed from Cedar's authorization semantics that makes governance changes safe by construction. `FallbackChain[C, T]` selects the highest-priority eligible action with guaranteed graceful degradation. `FreshnessGuard` rejects decisions made on stale perception data. These compose into a pipeline: trigger → fuse → freshness check → veto → fallback → command.

**Directives** — action descriptions that carry full provenance. A `Command` is an immutable data object recording what action was selected, what governance evaluation produced it, which veto chain allowed it, and the minimum watermark of the perception data that informed it. Commands do nothing until an `Executor` acts on them. The gap between description and execution is where governance lives.

The key combinator is `with_latest_from(trigger, behaviors)`, borrowed from Rx: when a fast event fires, sample all slow behaviors at their current values and emit a `FusedContext` with watermarks. This is how MIDI-rate decisions incorporate second-scale perception without blocking or polling. See [agents/hapax_voice/README.md](agents/hapax_voice/README.md) for the full architecture.

### Agent Manifest System

Every agent has a four-layer YAML manifest (`agents/manifests/`) that serves as its formalized personnel file:

- **Structural** — identity, organizational position, dependencies, peer relationships
- **Functional** — purpose, inputs/outputs, capabilities, schedule, model requirements
- **Normative** — autonomy tier (full/supervised/advisory), decision scope, axiom bindings with roles (subject/enforcer/evaluator), RACI matrix
- **Operational** — health monitoring group, service tier, metrics source

The `AgentRegistry` loads and validates these manifests, providing query methods by category, capability, autonomy tier, axiom binding, and RACI task. This is the single source of truth for what agents exist, what they're allowed to do, and who is responsible for what.

### Agents

| Category | Agents | LLM | Purpose |
|----------|--------|-----|---------|
| Management | `management_prep`, `briefing`, `profiler`, `meeting_lifecycle` | Yes | 1:1 context, morning briefings, operator modeling, meeting prep |
| Sync/RAG | `gdrive_sync`, `gcalendar_sync`, `gmail_sync`, `youtube_sync`, `chrome_sync`, `claude_code_sync`, `obsidian_sync` | No | Seven cron agents keep the knowledge base current |
| Analysis | `digest`, `scout`, `drift_detector`, `research`, `code_review`, `deliberation_eval` | Yes | Content digestion, component fitness scanning, documentation drift, research |
| System | `health_monitor`, `introspect`, `knowledge_maint` | No | Health monitoring (deterministic, 15min cadence), knowledge pruning |
| Knowledge | `ingest`, `query` | Mixed | RAG ingestion pipeline, semantic search |
| Voice | `hapax_voice`, `audio_processor` | Mixed | Always-on daemon, audio processing |
| Demo | `demo`, `demo_eval` + `demo_pipeline/` | Yes | Self-demonstrating capability |
| Dev narrative | `dev_story/` | Yes | Correlates commits with conversation transcripts |

### Profile System

The operator profiler maintains a structured model across 11 dimensions, split between **trait dimensions** (stable, interview-sourced: identity, neurocognitive, values, communication style, relationships) and **behavioral dimensions** (dynamic, observation-sourced: work patterns, energy and attention, information seeking, creative process, tool usage, communication patterns). The split is enforced at write time — sync agents can only update behavioral dimensions. Traits are sealed once established through interview.

This profile is injected into every agent's system prompt, so agent outputs are contextualized to this specific operator's priorities, knowledge, and cognitive patterns. The profile updates continuously from source data; the operator does not configure it.

### SDLC Pipeline

The system includes an LLM-driven software development lifecycle where issues flow through automated stages. The pipeline is designed around a specific concern: velocity gains from LLM-authored code are transient, but technical debt increases are persistent. Every stage includes a defense mechanism.

1. **Triage** (Sonnet) — classify type/complexity, check axiom relevance, find similar closed issues
2. **Plan** (Sonnet) — identify files, acceptance criteria, diff estimate
3. **Implement** (Opus via Claude Code) — sandboxed `agent/*` branch, run tests, open PR
4. **Adversarial Review** (Sonnet, independent context) — up to 3 rounds, then human escalation
5. **Axiom Gate** (Haiku) — structural checks + semantic LLM judge against constitutional axioms
6. **Auto-merge** (squash) on pass, block on T0 violation, advisory label on T1+

Different models are used for author and reviewer to prevent the self-recognition bias that makes homogeneous multi-agent review ineffective. Agent PRs are restricted to `agent/*` branches with `agent-authored` labels. CODEOWNERS protects governance files. Every stage logs to a JSONL event stream with correlated trace IDs.

### Model Routing

All agents reference logical model aliases, not provider model IDs:

| Alias | Current route | Use |
|-------|---------------|-----|
| `fast` | Gemini 2.5 Flash | Scheduled agents (briefing, digest, drift detection) |
| `balanced` | Claude Sonnet 4 | On-demand agents (research, profiler, code review) |
| `reasoning` | Qwen 3.5 27B (local) | Complex local reasoning |
| `local-fast` | Qwen 3 8B (local) | Lightweight local tasks |

LiteLLM provides routing with bidirectional fallback chains. When a better model ships, update the alias map — agents never change. All inference is traced in Langfuse.

## Domain Specifications

The voice perception domain maintains two complementary formal specifications:

**North Star** (`docs/superpowers/specs/2026-03-13-domain-schema-north-star.md`) — a domain schema where every prose sentence decomposes into a valid type sequence from the implemented type system. This constrains the specification to statements that project onto real types — no aspirational prose without type backing. Contains behavior/event/executor registries, governance chain compositions, validation traces, and a coverage matrix showing which behaviors are sourced, governed, and tested.

**Dog Star** (`docs/superpowers/specs/2026-03-13-dog-star-spec.md`) — the negative complement. Forbidden type sequences derived from axioms: compositions that are syntactically constructible but semantically prohibited. Each entry identifies the axiom it violates and the current enforcement level (Type/Runtime/Convention/None). Entries marked `[gap]` indicate places where forbidden sequences execute successfully — the system is honest about where it trusts social conventions over runtime checks.

## Quick Start

```bash
git clone git@github.com:ryanklee/hapax-council.git
cd hapax-council
uv sync

# Run tests (all mocked, no infrastructure needed)
uv run pytest tests/ -q

# Run an agent
uv run python -m agents.health_monitor --history
uv run python -m agents.briefing --hours 24 --save
uv run python -m agents.research --interactive

# Start the cockpit API
uv run python -m cockpit.api --host 127.0.0.1 --port 8051
```

Agents require LiteLLM (localhost:4000), Qdrant (localhost:6333), and Ollama (localhost:11434) for production use. Tests are fully mocked.

## Project Structure

```
hapax-council/
├── agents/           26+ agents + 4 agent packages (hapax_voice, demo_pipeline, dev_story, system_ops)
│   └── manifests/    YAML agent manifests (4-layer schema, RACI, axiom bindings)
├── shared/           41+ shared modules (config, axioms, profile, consent, agent_registry, deliberation_metrics)
├── cockpit/          FastAPI API + 11 data collectors + reactive engine (watcher, rules, executor)
├── council-web/      React SPA dashboard (health, agents, nudges, chat, demos)
├── vscode/           VS Code extension (chat, RAG, management commands)
├── skills/           15 Claude Code skills (slash commands)
├── hooks/            Claude Code hooks (axiom scanning, session context)
├── axioms/           Governance axioms (registry + implications + precedents + consent contracts)
├── systemd/          Timer and service unit files + watchdog scripts
├── docker/           Dockerfiles + docker-compose (cockpit-api, sync-pipeline)
├── tests/            2700+ tests (all mocked, no infrastructure needed)
├── docs/             Design documents, domain specs, research, plans
│   └── superpowers/  North Star spec, Dog Star spec, enforcement gaps audit, prior art survey
└── scripts/          SDLC pipeline scripts (triage, plan, review, axiom gate)
```

## Ecosystem

Three repositories compose the hapax system:

- **[hapax-constitution](https://github.com/ryanklee/hapax-constitution)** — The pattern specification. Defines the governance architecture: axioms, implications, interpretive canon, sufficiency probes, precedent store, filesystem-as-bus, reactive engine, three-tier agent model.
- **hapax-council** (this repo) — Personal operating environment. Reference implementation of the constitution. 26+ agents, voice daemon, RAG pipeline, reactive cockpit.
- **[hapax-officium](https://github.com/ryanklee/hapax-officium)** — Management-domain extraction. Originally part of council, extracted when the management agents proved usable independently. Designed to be forked. Includes a self-demonstrating capability and a synthetic seed corpus.

The three repos share infrastructure (Qdrant, LiteLLM, Ollama, PostgreSQL) but not code. Each implementation owns its full stack. The constitution constrains both; the implementations evolve independently.

## License

Apache 2.0 — see [LICENSE](LICENSE).
