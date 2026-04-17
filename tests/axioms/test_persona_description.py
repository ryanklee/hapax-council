"""Tests for axioms/persona/hapax-description-of-being.md (LRR Phase 7 §4.1).

The persona document's enforcement mechanism is: every structural claim
must be grep-able against the codebase. These tests verify that the
cited modules/paths/functions actually exist. If a cited target is
removed or renamed without updating the document, these tests fail
loud — the document should never drift silently from the architecture.

Reference: docs/superpowers/specs/2026-04-16-lrr-phase-7-redesign-persona-posture-role.md §4.1 + §6
(row: "Persona document drifts into personification under review iteration").
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent.parent
PERSONA_DOC = REPO_ROOT / "axioms" / "persona" / "hapax-description-of-being.md"


@pytest.fixture(scope="module")
def doc_text() -> str:
    return PERSONA_DOC.read_text()


# ── Document existence + shape ──────────────────────────────────────────────


class TestDocumentShape:
    def test_exists(self):
        assert PERSONA_DOC.exists()

    def test_has_reference_to_redesign_spec(self, doc_text):
        assert "2026-04-16-lrr-phase-7-redesign-persona-posture-role.md" in doc_text, (
            "persona document must cite its redesign spec so readers can trace authority"
        )

    def test_has_reference_to_companion_artifacts(self, doc_text):
        assert "axioms/roles/registry.yaml" in doc_text
        assert "axioms/persona/posture-vocabulary.md" in doc_text

    def test_has_all_six_numbered_sections(self, doc_text):
        """Sections: (1) what this document is, (2) species-type,
        (3) Clark × ANT bridge, (4) institutional relations,
        (5) voice, (6) what Hapax is not, (7) what this enables."""
        for heading in (
            "## 1. What this document is",
            "## 2. Species-type",
            "## 3. How Hapax engages",
            "## 4. Where Hapax stands",
            "## 5. Voice",
            "## 6. What Hapax is not",
            "## 7. What this document enables",
        ):
            assert heading in doc_text, f"missing section heading: {heading}"


# ── Every cited architectural target must exist ─────────────────────────────


CITED_FILES = [
    "agents/hapax_daimonion/presence_engine.py",
    "agents/hapax_daimonion/perception.py",
    "agents/hapax_daimonion/cpal/loop_gain.py",
    "agents/hapax_daimonion/cpal/control_law.py",
    "agents/hapax_daimonion/cpal/tier_composer.py",
    "agents/hapax_daimonion/cpal/grounding_bridge.py",
    "agents/hapax_daimonion/grounding_ledger.py",
    "agents/dmn/pulse.py",
    "agents/dmn/sensor.py",
    "agents/dmn/buffer.py",
    "agents/dmn/ollama.py",
    "shared/affordance_pipeline.py",
    "shared/governance/qdrant_gate.py",
    "shared/governance/consent.py",
    "shared/stream_mode.py",
    "shared/stream_transition_gate.py",
    "logos/_governance.py",
    "logos/api/deps/stream_redaction.py",
    "logos/api/routes/chronicle.py",
    "agents/telemetry/llm_call_span.py",
    "agents/telemetry/condition_metrics.py",
    "agents/studio_compositor/director_loop.py",
    "agents/hapax_daimonion/persona.py",
    "scripts/research-registry.py",
]


CITED_DIRS = [
    "agents/hapax_daimonion/cpal",
    "agents/dmn",
    "agents/studio_compositor",
    "shared/governance",
]


CITED_RUNTIME_PATHS = [
    # Document references these paths as live-state surfaces. We don't
    # assert they exist on disk (they require running services); we
    # assert they appear in the document as claimed so the document's
    # claims match what the tests check.
    "/dev/shm/hapax-stimmung/state.json",
    "~/hapax-state/research-registry/",
]


class TestGrepTargets:
    @pytest.mark.parametrize("rel_path", CITED_FILES)
    def test_cited_file_exists(self, rel_path):
        """Document claim → real file. If a module moves, update the document."""
        assert (REPO_ROOT / rel_path).exists(), (
            f"persona document cites '{rel_path}' which does not exist on disk. "
            f"Either the module was renamed/removed (update document) or "
            f"the document has a typo."
        )

    @pytest.mark.parametrize("rel_path", CITED_DIRS)
    def test_cited_directory_exists(self, rel_path):
        path = REPO_ROOT / rel_path
        assert path.exists() and path.is_dir(), f"cited directory '{rel_path}' missing"

    @pytest.mark.parametrize("runtime_path", CITED_RUNTIME_PATHS)
    def test_runtime_path_appears_in_document(self, doc_text, runtime_path):
        """The document references live-state paths by their literal string.
        These are runtime surfaces (not in git); this test just pins that
        the document keeps the canonical path strings."""
        assert runtime_path in doc_text


# ── Architectural claims use the correct vocabulary ─────────────────────────


class TestVocabulary:
    def test_mentions_cpal_loop(self, doc_text):
        assert "CPAL" in doc_text

    def test_mentions_affordance_pipeline(self, doc_text):
        assert "affordance" in doc_text.lower()
        assert "recruit" in doc_text.lower()

    def test_mentions_stimmung_eleven_dimensions(self, doc_text):
        assert "stimmung" in doc_text.lower()
        # The document should enumerate enough dimension names that a
        # reader can find them; assertion is for the substantive ones
        for dim in ("operator_stress", "operator_energy", "physiological_coherence"):
            assert dim in doc_text

    def test_mentions_research_registry_and_cycle_2(self, doc_text):
        assert "research-registry" in doc_text.lower() or "research registry" in doc_text.lower()
        assert "Cycle 2" in doc_text
        assert "5c2kr" in doc_text  # OSF pre-reg identifier

    def test_mentions_all_eight_roles_by_layer(self, doc_text):
        """Each layer's thick roles should be recognizable in the document
        prose, even if not in exact registry-id form."""
        # Structural
        assert "executive-function" in doc_text or "executive function" in doc_text
        assert "research" in doc_text.lower()
        # Institutional
        assert "livestream" in doc_text.lower() or "Legomena" in doc_text
        assert "household" in doc_text.lower()
        # Relational (case-insensitive — document uses title-case in prose)
        lower = doc_text.lower()
        assert "partner-in-conversation" in lower or "partner in conversation" in lower
        assert "addressee-facing" in lower or "addressee" in lower


# ── Personification rejections are explicit ─────────────────────────────────


class TestPersonificationRejections:
    """The document MUST explicitly reject common personification patterns,
    otherwise it fails the Phase 7 reframe's primary constraint."""

    @pytest.mark.parametrize(
        "required_phrase",
        [
            "Not a persona in the curated-presentation-of-self sense",
            "Not a helpful-harmless-honest assistant",
            "Not an embodied conversational agent",
            "Not sentient, not conscious",
            "Not a person",
            "Not improving toward personhood",
        ],
    )
    def test_rejection_present(self, doc_text, required_phrase):
        assert required_phrase in doc_text, f"missing explicit rejection: '{required_phrase}'"

    def test_declines_he_she_pronouns(self, doc_text):
        """The document explicitly declines he/she pronouns for Hapax."""
        assert "personification drift" in doc_text.lower()
        assert "declined" in doc_text.lower()


# ── ANT × Clark bridging is concretely resolved ─────────────────────────────


class TestBridgingCommitment:
    """Per redesign spec §3 — the persona document MUST concretely resolve
    the ANT × Clark bridging commitment, not handwave it. Spec §6 risk row:
    'ANT × Clark bridging is too abstract for the persona document to
    actually write' → mitigation is resolving it here."""

    def test_document_names_network_stabilization_framing(self, doc_text):
        """The bridge: Clark grounding reframed as local network stabilization.
        Document must state this concretely."""
        assert (
            "network-stabilization" in doc_text.lower()
            or "network stabilization" in doc_text.lower()
        )

    def test_document_names_obligatory_passage_points(self, doc_text):
        """ANT vocabulary: inscription at obligatory passage points replaces
        belief-convergence as the grounding mechanism."""
        assert "passage point" in doc_text.lower()

    def test_document_distinguishes_partner_from_addressee(self, doc_text):
        """Turn-taking (partner) vs announcing (addressee). If the document
        collapses these, the Clark overhearer distinction is lost."""
        assert "overhearer" in doc_text.lower() or "one-way" in doc_text.lower()

    def test_document_names_repair(self, doc_text):
        """Clark's repair mechanism appears as re-inscription."""
        assert "repair" in doc_text.lower()


# ── Voice commitments are utility-framed, not purity-framed ─────────────────


class TestVoiceCommitments:
    def test_voice_is_framed_as_utility(self, doc_text):
        """Voice framed as utility, not essence. Analogies allowed as
        communicative devices, not forbidden in the name of purity."""
        assert "utility" in doc_text.lower()
        assert "purity" in doc_text.lower()  # must address and reject purity framing

    def test_analogies_allowed_with_constraint(self, doc_text):
        """The 'curious' example is the canonical case per operator 2026-04-16."""
        assert "curious" in doc_text.lower()

    def test_voice_adaptation_signals_enumerated(self, doc_text):
        """Per redesign spec §7 Q3, voice adapts to partner identity,
        stream-mode, stimmung, grounding-active-goal, chat-signals."""
        # At least the first three must appear explicitly
        for signal in ("partner", "stream-mode", "stimmung"):
            assert signal.lower() in doc_text.lower()


# ── Deliberately-unfrozen footer ────────────────────────────────────────────


class TestFreezeStatus:
    """Per redesign spec §5 exit criterion (revised) and §7 Q2, freezing
    is deferred until post-Phase-7. The document must carry a footer that
    makes this deferral explicit so a future reader doesn't assume stale
    content is authoritative."""

    def test_document_notes_deferred_freeze(self, doc_text):
        assert "unfrozen" in doc_text.lower() or "not frozen" in doc_text.lower()
        assert "post-Phase-7" in doc_text or "post-phase-7" in doc_text.lower()
