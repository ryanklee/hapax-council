# IFC Enforcement Through Distributed Processing Pipelines

**Date**: 2026-03-31
**Type**: Deep research
**Status**: Complete
**Scope**: Information flow control label propagation, boundary checking vs. flow tracking, architectural options for the hapax-council consent system

---

## 1. IFC Implementation Patterns in Real Systems

### 1.1 LIO (Labeled IO, Haskell) — Dynamic Floating Labels

LIO (Stefan, Russo, et al., Haskell'11) is the system closest in design to the hapax consent algebra. Key mechanism:

- A **single mutable label** (the "current label") floats upward to reflect all data observed during a computation.
- The current label restricts what the computation can subsequently write to — it can only write to destinations whose label is at least as restrictive as the current label.
- A **clearance** bounds how far the label can float, preventing a computation from reading data so sensitive that it can no longer produce any useful output.
- The `LIO` monad wraps Haskell's `IO` monad, intercepting all I/O operations and checking label constraints.

**Hapax correspondence**: `Behavior[T].consent_label` already implements the floating label mechanism — labels join upward on `.update()`, never declassify. `FusedContext.consent_label` already implements the LIO equivalent of "current label after reading multiple sources." The gap is that the floating label lives in-memory but is stripped during JSON serialization.

**LIO's enforcement boundary**: LIO enforces at the monad level — every I/O operation is intercepted. This is equivalent to enforcing at every function call boundary, not just at persistence points. The runtime overhead is the cost of label comparison (set subset check) on every I/O operation. In LIO, this is negligible because Haskell labels are small algebraic values, and the checks are O(|policies|).

**Key insight from LIO**: The floating label mechanism is only useful if the label is checked at output points. In hapax, the label floats correctly through `Behavior.update()` and `FusedContext` joins, but `write_perception_state()` calls `json.dumps(state)` without consulting any label. The floating is implemented; the gate at the output is not connected to the floating label for most data paths.

### 1.2 Jif (Java Information Flow) — Static + Dynamic

Jif (Myers, Cornell) extends Java's type system with information flow labels checked at compile time. Key distinction:

- **Compile-time**: Most label checks happen during type checking. The compiler tracks a **program counter label** (pc) representing implicit flows through control structure.
- **Runtime**: Dynamic labels (labels determined at runtime) require programmer-inserted runtime checks. JRIF (Reactive Information Flow Control for Java) extends this to reactive systems.

**Hapax correspondence**: A static approach would mean encoding consent labels in Python's type system (via `Labeled[T]` generic) and checking at lint/typecheck time. This is partially achieved — `Labeled[T]` exists as a generic wrapper — but Python's type system cannot enforce that labeled data is never unwrapped without a gate check. Pyright cannot prove `unlabel()` is only called after `contract_check()`.

**Verdict for hapax**: Static enforcement is not viable in Python without a custom type checker plugin. Runtime enforcement (LIO-style) is the practical path.

### 1.3 FlowFox / JSFlow — Browser IFC

FlowFox uses **secure multi-execution**: the program runs multiple times (once per security level), with I/O operations filtered by level. JSFlow uses an instrumented JavaScript interpreter with per-value taint tags.

**Runtime overhead**:
- FlowFox: ~20% on macro benchmarks, ~200% on JavaScript execution benchmarks, ~88% memory overhead on top-500 websites.
- JSFlow: Similar overhead profile for a full interpreter rewrite.

**Hapax relevance**: These systems enforce IFC on untrusted third-party code (web scripts). Hapax has no untrusted code — all 45+ agents are first-party. The overhead of FlowFox/JSFlow is only justified when the threat model includes adversarial code execution, which does not apply here.

### 1.4 When Real Systems Choose Boundary Checking

Real systems overwhelmingly choose boundary checking when:
1. All code is trusted (no adversarial execution).
2. Data flows through well-defined channels (files, APIs, message queues).
3. The number of boundary points is small relative to internal operations.
4. The threat model is data misuse (accidental), not data exfiltration (adversarial).

Full flow tracking is chosen when:
1. Untrusted code executes within the system (browser extensions, plugins, applets).
2. Implicit flows through control structure could leak information.
3. Regulatory requirements demand provable non-interference.

---

## 2. IFC in Distributed Systems

### 2.1 DIFC Operating Systems: HiStar, Flume, Laminar

**HiStar** (Zeldovich et al., SOSP'06): Labels are attached to OS-level objects (threads, segments, containers). Every system call checks label constraints. Labels are sets of `(category, level)` pairs. The kernel is the only trusted component.

**Flume** (Krohn et al., SOSP'07): Labels attach to processes and IPC channels (pipes, file descriptors). A process can only send data to a destination whose label is at least as restrictive. Labels propagate through pipe reads/writes automatically.

**Laminar** (Roy et al., PLDI'09): Fine-grained DIFC within a JVM, using Java's type system and bytecode instrumentation. Labels attach to heap objects and propagate through method calls.

### 2.2 DStar — DIFC Across Network Boundaries

DStar (Zeldovich et al., NSDI'08) extends Flume/HiStar to distributed systems:

- Network messages carry labels as metadata.
- When process S sends message M to process R: the system enforces `L_S <= L_M <= L_R` (the message label must be between sender and receiver labels).
- Labels use **self-certifying names** (public key included in the label name) to prevent forgery across trust domains.
- DStar does not require any fully trusted processes or machines.

**Hapax correspondence**: The 14 processes coordinating through `/dev/shm` JSON files are analogous to Flume processes communicating through pipes. DStar shows that labels CAN propagate across process boundaries if the transport carries them. The JSON files currently carry no label metadata — this is the fundamental gap.

### 2.3 Labels on /dev/shm Files

**Can /dev/shm files carry labels?**

- **Extended attributes (xattr)**: tmpfs supports `security.*` and `trusted.*` namespaces, but **user.* extended attributes are not permitted on tmpfs** (kernel restriction). This means application-level xattr labeling on `/dev/shm` would require the `trusted.*` namespace (needs `CAP_SYS_ADMIN`) or the `security.*` namespace (normally reserved for SELinux/AppArmor). This is fragile and non-portable.
- **SELinux labels**: SELinux can label tmpfs files, but this requires system-wide SELinux policy (not appropriate for single-operator consent).
- **Embedded in payload**: The most practical approach. JSON payloads can include a `_consent` metadata field.
- **Sidecar files**: A `perception-state.consent.json` file alongside `perception-state.json`. Atomic consistency is hard to guarantee.
- **Registry**: A central label registry keyed by file path, consulted by readers. Adds a coordination point.

**Verdict**: Embedded in payload is the only practical approach for `/dev/shm` JSON files. xattr on tmpfs is a dead end for `user.*` namespace.

### 2.4 Heterogeneous Trust Levels

DStar's model handles processes with different trust levels by assigning each process a label reflecting its maximum sensitivity. In hapax, all processes run as the same user with the same trust level (single operator, no adversary). The trust distinction is about **data sensitivity**, not **process trust** — perception data containing guest biometrics carries a higher label than perception data with only operator-own signals.

---

## 3. Gradual/Hybrid Enforcement

### 3.1 The Expressiveness Result

Rajani, Bichhawat, Garg, Hammer (POPL'20, tutorial '22) proved a foundational result: **coarse-grained and fine-grained dynamic IFC are equally expressive**. There exist semantics-preserving translations in both directions. This means:

- A system that tracks labels at the process level (coarse-grained, like Flume) can enforce the same policies as one tracking labels per variable (fine-grained, like JSFlow).
- The difference is in annotation burden and false alarm rate, not in theoretical capability.

**Implication for hapax**: Tracking labels at the Behavior/file level (coarse-grained) is not theoretically less powerful than tracking labels on every intermediate variable. The current architecture's granularity (one label per Behavior, one joined label per FusedContext) is sufficient.

### 3.2 Co-Inflow: Practical Coarse-Grained IFC

Co-Inflow (Chong et al., IEEE S&P'21) applies coarse-grained IFC to Java with minimal annotation burden. Key findings:
- Programmers add very few annotations to convert a Java program to a Co-Inflow program.
- The coarse-grained label tracks the "taint" of the entire execution context (analogous to LIO's floating label).
- Performance overhead in the prototype is not optimized but "has great potential for improvement."

**Hapax correspondence**: The current system already has the equivalent of Co-Inflow's coarse-grained labels — `Behavior.consent_label` and `FusedContext.consent_label` track the label of the entire perception context, not of individual fields within it. This is the right granularity.

### 3.3 When Boundary Enforcement Leaks

Boundary enforcement (checking only at read/write points) can miss:

1. **Laundering through derived values**: Process A reads labeled data, computes a derivative (e.g., averages biometric data from multiple people), writes the result without labels. The derivative carries information about the original data but no consent obligation.
2. **Label stripping through serialization**: Process writes labeled data to JSON, strips the label; reader gets raw data with no label context. This is the current hapax gap.
3. **Implicit flows through control structure**: Process reads labeled data, takes a branch based on it, writes non-labeled data from that branch. The written data implicitly carries information from the labeled input.

Boundary enforcement catches (2) if labels are embedded in the serialization format. It does NOT catch (1) or (3). Full flow tracking catches (1) and (3) but at significant runtime cost.

### 3.4 The Gradual Typing Analogy

The consent system already uses a gradual approach (DD-16): `consent_label: ConsentLabel | None`, where `None` means "untracked." This is precisely the gradual IFC pattern — some values carry labels, some do not, and the system handles the boundary between tracked and untracked regions.

The key property of gradual IFC: as more behaviors gain labels, the enforcement surface grows without requiring a big-bang rewrite. This is already the design intent.

---

## 4. Label Propagation Through Data Transformations

### 4.1 Map/Filter/Reduce

`Labeled[T].map(f)` preserves the label — the output carries the input's label unchanged. This is correct for pure transformations where the output is a function of the input.

**Filter**: Filtering a collection of labeled values should produce a collection with the join of all input labels (because the filter criterion itself might leak information about which values were present).

**Reduce/Aggregate**: Aggregating labeled values (e.g., computing the mean of heart rate readings from multiple people) produces a value whose label is the join of all input labels. Even if the aggregate "anonymizes" individual values, the label must float upward because the aggregate was derived from the inputs. Declassification (downgrading the label) requires explicit action (DD-4).

### 4.2 LLM Processing

This is the most novel question. When labeled data enters an LLM prompt:

- The LLM output is derived from the input. Under taint tracking, the output carries the input's label.
- The LLM is a black box — it might memorize, regurgitate, or transform the input arbitrarily.
- **Conservative position**: All LLM output inherits the join of all input labels. This is what FIDES (Costa, Kopf et al., Microsoft Research, arXiv:2505.23643, May 2025) implements.

**FIDES** (Flow Integrity Deterministic Enforcement System) is directly relevant:
- It applies dynamic taint tracking to AI agent planners.
- LLM inputs are labeled with confidentiality and integrity tags.
- LLM outputs inherit the join of input labels.
- A "quarantine" mechanism allows constrained decoding that produces outputs fitting a schema, enabling the system to declassify specific fields of the output.
- Evaluation shows that with capable models (o1-class), FIDES achieves near-oracle utility while maintaining security guarantees.

**Hapax implication**: When the cognitive loop sends perception data to an LLM for classification (`llm_activity`, `llm_flow_hint`), the LLM output should carry the perception input's consent label. Currently, the LLM output is written as a raw string to a Behavior with no label. The fix is straightforward: the LLM classification backend should propagate the input FusedContext's consent label to the output Behavior.

### 4.3 Embedding/Vectorization

When labeled text is embedded into a vector space:
- The vector is a lossy transformation of the text. Individual words are not recoverable from the embedding, but semantic information is preserved.
- Under strict IFC: the embedding vector carries the text's label. The vector is derived from the text; information flows from text to vector.
- In Qdrant: vectors stored in collections that contain consent-governed text should carry labels. The `qdrant_gate.py` module already gates writes to Qdrant by consent — this is boundary enforcement at the persistence point.

**Practical note**: Embedding-level label tracking is only necessary if embeddings are shared across trust domains. In a single-operator system where all Qdrant queries are made by the same operator's agents, the embedding inherits the collection-level access policy rather than requiring per-vector labels.

### 4.4 Dynamic Taint Analysis as Precedent

Perl's taint mode and Ruby's `$SAFE` levels are production-grade examples of lightweight taint tracking:
- Perl marks all external input as "tainted." Tainted data cannot be used in security-sensitive operations (file open, exec, SQL) without explicit "laundering" through a regex match.
- Overhead: negligible (a single bit per scalar value).
- Limitation: no implicit flow tracking, no label joins — binary taint only.

Dynamic taint analysis research (Schwartz et al., Oakland'10; Kang et al., NDSS'11) classifies propagation into three operations:
1. **Tag allocation**: Marking a value as tainted at a source.
2. **Tag copy**: Transferring taint when data moves between variables.
3. **Tag combination**: Joining taints when values are combined.

The hapax consent system already implements all three: `ConsentLabel.from_contract()` (allocation), `Labeled[T].map()` (copy), `ConsentLabel.join()` (combination).

---

## 5. Consent-Specific IFC

### 5.1 GDPR Data Lineage Requirements

GDPR Article 30 requires "records of processing activities" including the purposes of processing and categories of data. Article 17 ("right to erasure") requires deletion of all personal data when consent is withdrawn. Article 20 ("data portability") requires the ability to export all data associated with a consent.

Real GDPR compliance systems implement:
- **Data registries**: Maps of (data item) → (storage locations, processing systems).
- **Workflow engines**: Orchestrate erasure requests across all systems.
- **Execution engines**: System-specific deletion plugins.

**Hapax correspondence**: The `RevocationPropagator` with pluggable `PurgeHandler`s is precisely this architecture. Subsystems register handlers; on revocation, the propagator cascades purge. The gap is that not all data-holding subsystems are registered. The `/dev/shm` perception state files, Qdrant collections, and Langfuse traces need purge handlers.

### 5.2 Consent Revocation Cascade

The Oxford Cybersecurity Journal (Politou et al., 2018) identifies key challenges:
- **Propagation latency**: How quickly must revocation propagate? Real-time? Eventually consistent?
- **Derived data**: Must derivatives of consented data also be deleted?
- **Third-party propagation**: If data was shared with external systems, can deletion be enforced?

**Hapax architecture**: All data is local (single operator, single machine). No third-party propagation needed. Derived data (LLM outputs, embeddings) should be purgeable by provenance. The `ProvenanceExpr` semiring already supports this — tensor (both required) means revoking either contract invalidates the derived datum.

### 5.3 The DLM as Consent Model

Myers and Liskov's Decentralized Label Model is exactly the formalism underlying the hapax consent algebra:
- Each label has **owners** who control the data.
- Each owner specifies **readers** who may access it.
- Declassification requires the owner's explicit action.
- Labels from multiple owners combine conjunctively (all owners' policies apply).

The hapax `ConsentLabel` with `policies: frozenset[tuple[str, frozenset[str]]]` is a direct implementation of DLM labels where each `(owner, readers)` tuple is a DLM principal-reader policy.

### 5.4 No Prior Work on Consent-as-IFC-Label

Extensive search found no academic work that explicitly models interpersonal consent as an IFC label in the DLM tradition. The closest is:
- **Consentio** (Kaaniche et al., arXiv:1910.07110): Blockchain-based consent management, but uses access control (binary allow/deny), not information flow.
- **FIDES** (Costa et al., 2025): Uses IFC for AI agent security, but models confidentiality/integrity, not interpersonal consent.
- The hapax approach of repurposing DLM for consent governance appears to be novel.

---

## 6. Architectural Options for Hapax

### 6.1 Option A: Embedded Labels in JSON Payloads

**Mechanism**: Every JSON file written by the system includes a `_consent` metadata field:

```json
{
  "_consent": {
    "label": [["guest-alice", ["operator", "guest-alice"]]],
    "provenance": ["contract-alice-2026-03-15"],
    "provenance_expr": "contract-alice-2026-03-15"
  },
  "operator_present": true,
  "person_count": 2,
  ...
}
```

Readers parse `_consent` before consuming the payload and either:
- Verify they have authority to read (check `can_flow_to`).
- Propagate the label to their own outputs.

**Engineering cost**: 3–5 days.
- Modify `write_perception_state()` to include `_consent` from the joined `FusedContext` label.
- Modify all readers (stimmung, fortress, VLA, reactive engine, API routes) to parse `_consent` and thread it through their outputs.
- Add a helper: `read_labeled_json(path) -> Labeled[dict]`.

**What it prevents**: Label stripping through serialization (gap 3.3.2 above). Every consumer of perception state knows the consent obligations.

**What it does not prevent**: A consumer that ignores the `_consent` field. This is the "honor system" limitation of any embedded metadata approach.

**Precedent**: DStar embeds labels in network messages. HDFS extended attributes (Hadoop) embed security labels in file metadata. Every modern web API embeds authorization context in request headers.

### 6.2 Option B: Filesystem Extended Attributes (xattr)

**Mechanism**: Use `trusted.hapax.consent` xattr on `/dev/shm` files.

**Engineering cost**: 2–3 days for the mechanism, plus ongoing fragility.

**Problems**:
- `user.*` xattr is not supported on tmpfs. Must use `trusted.*` namespace, requiring `CAP_SYS_ADMIN`.
- xattr is not preserved by atomic write-then-rename (the standard pattern used in `write_perception_state()`).
- xattr is filesystem-specific. Moving to a different IPC mechanism (Unix sockets, shared memory segments) would break the approach.
- No tooling support — `jq` cannot read xattr; debugging requires `getfattr`.

**Verdict**: Not recommended. The tmpfs limitation and fragility make this impractical.

### 6.3 Option C: Central Label Registry

**Mechanism**: A label registry (in-memory dict, Redis, or a JSON file) maps file paths to their consent labels. Writers register labels; readers query the registry.

**Engineering cost**: 2–3 days for the registry, plus coordination complexity.

**Problems**:
- Race condition between file write and registry update.
- Single point of failure.
- Added IPC overhead for every read.
- Overkill for the current architecture where files are the communication medium.

**Verdict**: Only useful if the system moves to a message-bus architecture. Not recommended for the current filesystem-as-bus design.

### 6.4 Option D: Source-Based Label Inference

**Mechanism**: Labels are inferred from the data source rather than carried with the data. If perception-state.json was written by the daimonion process during a guest-present state, it carries the guest's consent label. The reader knows this because it knows the source.

**Engineering cost**: 0–1 days (document the convention).

**Problems**:
- Breaks when data flows through intermediaries. If stimmung reads perception-state.json and writes stimmung.json, the stimmung consumer doesn't know whether the perception data was guest-labeled.
- Requires all consumers to have global knowledge of the system topology.
- Not compositional — adding a new data source requires updating all consumers.

**Verdict**: This is the implicit current approach (and why it's broken). The lack of explicit labels is exactly the gap this research addresses.

### 6.5 Option E: Hybrid — Embedded Labels + Boundary Gates

**Mechanism**: Combine Options A and D. Embed labels in JSON payloads (Option A), but enforce only at boundary points where data leaves the system (API responses, LLM tool results, Qdrant writes, notification text). Interior processes propagate labels through their outputs but are not gated.

**Engineering cost**: 4–6 days.
- Option A's embedded labels (3–5 days).
- Wire the existing `ConsentGatedWriter` to all persistence boundaries (1–2 days, partially done).

**What it achieves**: Labels propagate through the system (visible, auditable, testable), but enforcement happens at boundaries where data could actually leak. Interior processes are trusted (they're all first-party code running as the same user).

**This is the recommended approach.**

---

## 7. Cost-Benefit Analysis

### 7.1 Full IFC Enforcement (Flow Tracking)

**What it means**: Every function that transforms data propagates labels. Every intermediate value carries a consent label. Every I/O operation checks labels.

**Engineering cost**: 4–8 weeks. Every data-processing function in 45+ agents would need to accept and return `Labeled[T]` values. The entire perception pipeline, stimmung computation, reactive engine, and API layer would need to be rewritten to thread labels.

**Runtime overhead**: Negligible per-operation (label join is O(|policies|), currently ~5 policies). But pervasive — every function call pays the cost.

**What it prevents beyond boundary checking**:
- Implicit flows through control structure (if guest-present, take branch A; branch A writes different data).
- Label laundering through derived values (aggregate biometrics, then write without label).

**Honest assessment**: In a single-operator system with ~5 consent contracts and no adversarial code execution, implicit flow attacks are not a realistic threat. The operator is the only consumer of the data. Label laundering through derivation is a real concern (the aggregation case), but it can be addressed by labeling aggregation outputs without requiring full flow tracking.

### 7.2 Boundary Checking (Current + Embedded Labels)

**What it means**: Labels propagate through the system as metadata but are only enforced at persistence/output boundaries (file writes, API responses, LLM prompts, Qdrant upserts, notifications).

**Engineering cost**: 4–6 days (Option E above).

**Runtime overhead**: Near zero. Label joins only at boundary points (~10 boundaries in the current system).

**What it prevents**:
- Accidental persistence of guest data without consent (the primary threat).
- Unlabeled data flowing through the system without consent context (the current gap).
- Stale labels after revocation (provenance check at boundaries).

**What it does NOT prevent**:
- Implicit flows through control structure (theoretical, not a practical threat in a single-operator system).
- In-memory label stripping by buggy code (would require full flow tracking to catch).

**Honest assessment**: Sufficient for the current threat model. The system has a single operator, no adversarial code, and the consent obligation is about interpersonal transparency (not preventing data exfiltration). Boundary enforcement catches all realistic consent violations.

### 7.3 Decision Matrix

| Criterion | Full Flow Tracking | Boundary + Embedded Labels |
|---|---|---|
| Engineering cost | 4–8 weeks | 4–6 days |
| Runtime overhead | Pervasive, small per-op | Near zero |
| Prevents serialization stripping | Yes | Yes |
| Prevents implicit flows | Yes | No |
| Prevents label laundering | Yes | Partially (at boundaries) |
| Required for single-operator system | No | No (but improves governance posture) |
| Comparable systems exist | LIO, FIDES | DStar, GDPR compliance systems |
| Scales to future multi-user | Foundation for it | Would need upgrade |

### 7.4 The Governance Obligation Question

Is boundary checking a governance failure or engineering pragmatism?

**The case for pragmatism**: The interpersonal transparency axiom (it-consent-001) requires that no persistent state about non-operator persons exists without active consent. Boundary checking at persistence points is a complete enforcement of this property — it gates every path to persistence. Internal in-memory processing of guest data that never persists does not violate the axiom.

**The case for governance obligation**: The consent algebra was designed for flow tracking, not boundary checking. The algebraic properties (join-semilattice, functor law on `map`, provenance semiring) are wasted if labels only exist at boundaries. The algebra implies a design intent that the system should track consent through transformations, not just at gates. Shipping the algebra without using it for flow tracking is like having a type system that's never compiled — it documents intent but doesn't enforce it.

**Resolution**: The algebra is not wasted by boundary enforcement. The algebra provides:
1. Correct label computation at fusion points (FusedContext.join).
2. Correct label propagation through transformations (Labeled.map).
3. Correct revocation evaluation (ProvenanceExpr.evaluate).

These properties hold regardless of whether enforcement is at every step or only at boundaries. The algebra makes boundary enforcement correct; full flow tracking would make it complete. Correctness is sufficient for the current threat model; completeness is a future investment for multi-operator scenarios.

### 7.5 Recommendation

**Implement Option E (Hybrid: Embedded Labels + Boundary Gates)** in this order:

1. **Add `_consent` to perception-state.json** (1 day): Modify `write_perception_state()` to include the joined consent label from the perception engine's behaviors.

2. **Add `read_labeled_json()` utility** (0.5 day): A helper that parses `_consent` from JSON payloads and returns `Labeled[dict]`.

3. **Propagate labels through stimmung** (1 day): Stimmung reads perception-state.json, computes mood dimensions, writes stimmung.json. The stimmung output should carry the perception input's label (join of input labels).

4. **Wire `ConsentGatedWriter` to remaining boundaries** (1–2 days): API responses, LLM tool results, notification text, Qdrant writes.

5. **Add LLM output labeling** (0.5 day): When the cognitive loop or LLM classification backend sends perception data to an LLM, the output Behavior should carry the input's consent label.

6. **Property tests for label propagation** (1 day): Hypothesis tests verifying that labels are preserved through the full pipeline (perception → stimmung → API → LLM output).

Total: ~5 days of implementation. This closes the serialization gap, makes labels visible throughout the system, and enforces at all output boundaries. Full flow tracking remains available as a future upgrade if the system ever serves multiple operators.

---

## Sources

### IFC Foundations
- [LIO: Labeled IO Information Flow Control Library](https://hackage.haskell.org/package/lio)
- [Stefan et al., "Flexible Dynamic Information Flow Control in Haskell" (Haskell'11)](https://www.scs.stanford.edu/~dm/home/papers/stefan:lio.pdf)
- [Stefan et al., "Flexible Dynamic Information Flow Control in the Presence of Exceptions"](https://arxiv.org/abs/1207.1457)
- [Jif: Language-based Information-flow Security in Java](https://www.cs.cornell.edu/jif/)
- [Myers, "Jif: Java Information Flow" (arXiv:1412.8639)](https://arxiv.org/pdf/1412.8639)
- [JRIF: Reactive Information Flow Control for Java](https://www.cs.cornell.edu/fbs/publications/JRIF.POST.techRpt.pdf)

### DIFC / Distributed Systems
- [Zeldovich et al., "Making Information Flow Explicit in HiStar" (SOSP'06)](https://www.semanticscholar.org/paper/Making-information-flow-explicit-in-HiStar-Zeldovich-Boyd-Wickizer/f7ebf78763ba219807bd57f9e574cd15608540ac)
- [Krohn et al., "Information Flow Control for Standard OS Abstractions" (Flume)](https://read.seas.harvard.edu/~kohler/pubs/krohn07information.pdf)
- [Zeldovich et al., "Securing Distributed Systems with Information Flow Control" (DStar, NSDI'08)](https://people.csail.mit.edu/nickolai/papers/zeldovich-dstar.pdf)
- [Roy et al., "Laminar: Practical Fine-Grained DIFC" (PLDI'09)](https://www.cs.utexas.edu/~witchel/pubs/pldi09-roy.pdf)

### Coarse-Grained / Gradual IFC
- [Rajani et al., "From Fine- to Coarse-Grained Dynamic Information Flow Control and Back"](https://arxiv.org/abs/2208.13560)
- [Co-Inflow: Coarse-grained Information Flow Control for Java (IEEE S&P'21)](https://people.seas.harvard.edu/~chong/pubs/oakland21_coinflow.pdf)
- [Co-Inflow Prototype (GitHub)](https://github.com/HarvardPL/CIFC)

### Browser IFC
- [FlowFox: A Web Browser with Flexible and Precise IFC (CCS'12)](https://www.securitee.org/files/flowfox_ccs2012.pdf)
- [JSFlow: Tracking Information Flow in JavaScript and its APIs](https://www.cse.chalmers.se/~andrei/sac14.pdf)

### AI Agent IFC
- [Costa, Kopf et al., "Securing AI Agents with Information-Flow Control" (arXiv:2505.23643)](https://arxiv.org/abs/2505.23643)
- [Microsoft FIDES (GitHub)](https://github.com/microsoft/fides)

### Taint Analysis
- [Schwartz et al., "All You Ever Wanted to Know About Dynamic Taint Analysis" (Oakland'10)](https://users.ece.cmu.edu/~aavgerin/papers/Oakland10.pdf)
- [Kang et al., "DTA++: Dynamic Taint Analysis with Targeted Control-Flow Propagation" (NDSS'11)](http://bitblaze.cs.berkeley.edu/papers/dta++-ndss11.pdf)
- [Dynamic Taint Analysis with Label-Defined Semantics (ACM MPLR'22)](https://dl.acm.org/doi/10.1145/3546918.3546927)

### DLM / Consent
- [Myers, Liskov, "Protecting Privacy using the Decentralized Label Model"](https://www.cs.cornell.edu/andru/papers/iflow-tosem.pdf)
- [Myers, Liskov, "A Model for Decentralized Information Flow Control" (SOSP'97)](https://www.cs.cornell.edu/andru/papers/iflow-sosp97/paper.html)

### GDPR / Consent Revocation
- [Politou et al., "Forgetting Personal Data and Revoking Consent Under the GDPR" (J. Cybersecurity, 2018)](https://academic.oup.com/cybersecurity/article/4/1/tyy001/4954056)
- [Implementing GDPR Right to Be Forgotten in Delta Lake (Databricks)](https://www.databricks.com/blog/2022/03/23/implementing-the-gdpr-right-to-be-forgotten-in-delta-lake.html)
- [Twitter Engineering: Deleting Data Distributed Throughout Microservices](https://blog.twitter.com/engineering/en_us/topics/infrastructure/2020/deleting-data-distributed-throughout-your-microservices-architecture)

### Filesystem / xattr
- [tmpfs: implement generic xattr support (LWN)](https://lwn.net/Articles/439320/)
- [Extended File Attributes (Wikipedia)](https://en.wikipedia.org/wiki/Extended_file_attributes)
- [xattr(7) - Linux manual page](https://man7.org/linux/man-pages/man7/xattr.7.html)
