"""Tests for agents.programme_manager.transition.

Phase 7 of the programme-layer plan. Verifies:
  - the four ritual-scope intent_family prefixes are emitted in order
  - one-sided transitions (start-of-stream, end-of-stream) work
  - boundary_freeze always fires
  - ritual narratives reference role names
  - hint payloads (artefact, ward choreography) flow into content
  - ritual strength is the configured high-salience value
  - impingements are appended to the JSONL transport (not overwriting)
  - emit_fn embedding is wired and exception-safe
  - no transition step uses a hardcoded capability invocation
    (architectural assertion: every step is an Impingement)
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agents.programme_manager.transition import (
    DEFAULT_RITUAL_STRENGTH,
    RITUAL_INTENT_FAMILIES,
    TransitionChoreographer,
)
from shared.impingement import Impingement
from shared.programme import (
    Programme,
    ProgrammeConstraintEnvelope,
    ProgrammeRitual,
    ProgrammeRole,
)


def _programme(
    pid: str,
    role: ProgrammeRole,
    *,
    duration: float = 300.0,
    boundary_freeze: float = 6.0,
    exit_artefact: str | None = "vinyl-fade",
    entry_artefact: str | None = "kalimba-bell",
    saturation: float | None = 0.55,
) -> Programme:
    return Programme(
        programme_id=pid,
        role=role,
        planned_duration_s=duration,
        ritual=ProgrammeRitual(
            entry_signature_artefact=entry_artefact,
            entry_ward_choreography=["intro_pulse"],
            exit_signature_artefact=exit_artefact,
            exit_ward_choreography=["fade_pulse"],
            boundary_freeze_s=boundary_freeze,
        ),
        constraints=ProgrammeConstraintEnvelope(reverie_saturation_target=saturation),
        parent_show_id="test-show",
    )


@pytest.fixture
def imp_file(tmp_path: Path) -> Path:
    return tmp_path / "impingements.jsonl"


@pytest.fixture
def chor(imp_file: Path) -> TransitionChoreographer:
    fixed_now = 100_000.0
    return TransitionChoreographer(
        impingements_file=imp_file,
        now_fn=lambda: fixed_now,
    )


def _read_emitted(path: Path) -> list[Impingement]:
    if not path.exists():
        return []
    return [Impingement.model_validate_json(line) for line in path.read_text().splitlines() if line]


class TestEmissionOrder:
    def test_full_transition_emits_four_in_canonical_order(
        self, chor: TransitionChoreographer, imp_file: Path
    ) -> None:
        a = _programme("a", ProgrammeRole.LISTENING)
        b = _programme("b", ProgrammeRole.SHOWCASE)
        result = chor.transition(from_programme=a, to_programme=b)
        emitted = _read_emitted(imp_file)
        assert len(emitted) == 4
        # Canonical order: exit, freeze, palette_shift, entry.
        assert emitted[0].intent_family == f"{RITUAL_INTENT_FAMILIES[0]}.listening"
        assert emitted[1].intent_family == RITUAL_INTENT_FAMILIES[1]
        assert emitted[2].intent_family == f"{RITUAL_INTENT_FAMILIES[2]}.showcase"
        assert emitted[3].intent_family == f"{RITUAL_INTENT_FAMILIES[3]}.showcase"
        # And the returned struct matches.
        assert result.exit_ritual is not None
        assert result.boundary_freeze is not None
        assert result.palette_shift is not None
        assert result.entry_ritual is not None

    def test_start_of_stream_omits_exit_and_palette_carries_target(
        self, chor: TransitionChoreographer, imp_file: Path
    ) -> None:
        b = _programme("b", ProgrammeRole.AMBIENT)
        result = chor.transition(from_programme=None, to_programme=b)
        emitted = _read_emitted(imp_file)
        # Three only: freeze, palette, entry.
        assert len(emitted) == 3
        assert result.exit_ritual is None
        assert result.boundary_freeze is not None
        assert result.palette_shift is not None
        assert result.entry_ritual is not None
        assert all(imp.intent_family != "programme.exit_ritual.ambient" for imp in emitted)

    def test_end_of_stream_omits_palette_and_entry(
        self, chor: TransitionChoreographer, imp_file: Path
    ) -> None:
        a = _programme("a", ProgrammeRole.SHOWCASE)
        result = chor.transition(from_programme=a, to_programme=None)
        emitted = _read_emitted(imp_file)
        assert len(emitted) == 2  # exit + freeze only
        assert result.exit_ritual is not None
        assert result.boundary_freeze is not None
        assert result.palette_shift is None
        assert result.entry_ritual is None

    def test_boundary_freeze_always_fires(
        self, chor: TransitionChoreographer, imp_file: Path
    ) -> None:
        # Even a "void → void" transition fires boundary_freeze.
        result = chor.transition(from_programme=None, to_programme=None)
        assert result.boundary_freeze is not None
        assert result.boundary_freeze.intent_family == RITUAL_INTENT_FAMILIES[1]


class TestRitualPayload:
    def test_exit_ritual_carries_artefact_hints(self, chor: TransitionChoreographer) -> None:
        a = _programme(
            "a",
            ProgrammeRole.LISTENING,
            exit_artefact="vinyl-fade",
        )
        b = _programme("b", ProgrammeRole.SHOWCASE)
        result = chor.transition(from_programme=a, to_programme=b)
        assert result.exit_ritual is not None
        assert result.exit_ritual.content["ritual_artefact_hint"] == "vinyl-fade"
        assert result.exit_ritual.content["ward_choreography_hint"] == ["fade_pulse"]
        assert result.exit_ritual.content["from_role"] == "listening"

    def test_entry_ritual_carries_artefact_hints(self, chor: TransitionChoreographer) -> None:
        a = _programme("a", ProgrammeRole.LISTENING)
        b = _programme("b", ProgrammeRole.SHOWCASE, entry_artefact="kalimba-bell")
        result = chor.transition(from_programme=a, to_programme=b)
        assert result.entry_ritual is not None
        assert result.entry_ritual.content["ritual_artefact_hint"] == "kalimba-bell"
        assert result.entry_ritual.content["to_role"] == "showcase"
        assert result.entry_ritual.content["from_role"] == "listening"

    def test_palette_shift_carries_saturation_target(self, chor: TransitionChoreographer) -> None:
        b = _programme("b", ProgrammeRole.AMBIENT, saturation=0.42)
        result = chor.transition(from_programme=None, to_programme=b)
        assert result.palette_shift is not None
        assert result.palette_shift.content["saturation_target"] == pytest.approx(0.42)

    def test_boundary_freeze_uses_from_side_duration_when_present(
        self, chor: TransitionChoreographer
    ) -> None:
        a = _programme("a", ProgrammeRole.LISTENING, boundary_freeze=12.0)
        b = _programme("b", ProgrammeRole.SHOWCASE, boundary_freeze=2.0)
        result = chor.transition(from_programme=a, to_programme=b)
        assert result.boundary_freeze.content["freeze_s"] == pytest.approx(12.0)

    def test_boundary_freeze_falls_through_to_to_side(self, chor: TransitionChoreographer) -> None:
        b = _programme("b", ProgrammeRole.SHOWCASE, boundary_freeze=2.0)
        result = chor.transition(from_programme=None, to_programme=b)
        assert result.boundary_freeze.content["freeze_s"] == pytest.approx(2.0)


class TestStrengthAndTime:
    def test_ritual_strength_is_high_salience_default(self, chor: TransitionChoreographer) -> None:
        a = _programme("a", ProgrammeRole.LISTENING)
        b = _programme("b", ProgrammeRole.SHOWCASE)
        result = chor.transition(from_programme=a, to_programme=b)
        for imp in result.as_list():
            assert imp.strength == pytest.approx(DEFAULT_RITUAL_STRENGTH)
            assert imp.strength >= 0.8

    def test_now_fn_drives_timestamps(self, chor: TransitionChoreographer, imp_file: Path) -> None:
        a = _programme("a", ProgrammeRole.LISTENING)
        b = _programme("b", ProgrammeRole.SHOWCASE)
        result = chor.transition(from_programme=a, to_programme=b)
        for imp in result.as_list():
            assert imp.timestamp == pytest.approx(100_000.0)


class TestPersistence:
    def test_emissions_append_not_overwrite(
        self, imp_file: Path, chor: TransitionChoreographer
    ) -> None:
        a = _programme("a", ProgrammeRole.LISTENING)
        b = _programme("b", ProgrammeRole.SHOWCASE)
        chor.transition(from_programme=a, to_programme=b)
        chor.transition(from_programme=b, to_programme=a)
        emitted = _read_emitted(imp_file)
        # 4 + 4 = 8.
        assert len(emitted) == 8

    def test_lines_are_valid_json(self, imp_file: Path, chor: TransitionChoreographer) -> None:
        a = _programme("a", ProgrammeRole.LISTENING)
        b = _programme("b", ProgrammeRole.SHOWCASE)
        chor.transition(from_programme=a, to_programme=b)
        for line in imp_file.read_text().splitlines():
            json.loads(line)  # would raise on malformed JSON


class TestEmbedFn:
    def test_embed_fn_is_called_per_impingement(self) -> None:
        embed_calls: list[str] = []

        def fake_embed(text: str) -> list[float] | None:
            embed_calls.append(text)
            return [0.1, 0.2, 0.3]

        chor = TransitionChoreographer(
            impingements_file=Path("/dev/null"),
            embed_fn=fake_embed,
        )
        a = _programme("a", ProgrammeRole.LISTENING)
        b = _programme("b", ProgrammeRole.SHOWCASE)
        # Suppress write attempt by using /dev/null parent that exists.
        try:
            result = chor.transition(from_programme=a, to_programme=b)
        except OSError:
            # /dev/null parent works on linux, but if write fails the
            # builders still ran — the embed assertion still holds.
            result = None
        # 4 narratives → 4 embed calls.
        assert len(embed_calls) == 4
        if result is not None:
            for imp in result.as_list():
                assert imp.embedding == [0.1, 0.2, 0.3]

    def test_embed_fn_exception_does_not_break_emission(self, imp_file: Path) -> None:
        def boom(text: str) -> list[float] | None:
            raise RuntimeError("embed kaboom")

        chor = TransitionChoreographer(
            impingements_file=imp_file,
            embed_fn=boom,
        )
        a = _programme("a", ProgrammeRole.LISTENING)
        b = _programme("b", ProgrammeRole.SHOWCASE)
        # Must not raise.
        result = chor.transition(from_programme=a, to_programme=b)
        for imp in result.as_list():
            assert imp.embedding is None


class TestArchitecturalInvariants:
    def test_every_emission_is_an_impingement_not_a_capability_call(
        self, chor: TransitionChoreographer
    ) -> None:
        """Architectural assertion: rituals are recruited, not scripted.

        The choreographer must NEVER emit anything that looks like a
        direct dispatch_capability(...) call. Every step must be a
        normal Impingement going through the affordance pipeline.
        Matches plan §Phase 7 success criterion line 794-795.
        """
        a = _programme("a", ProgrammeRole.LISTENING)
        b = _programme("b", ProgrammeRole.SHOWCASE)
        result = chor.transition(from_programme=a, to_programme=b)
        for imp in result.as_list():
            assert isinstance(imp, Impingement)
            # Capabilities are recruited via intent_family + narrative.
            # No "dispatch_target" / "capability_id" fields ever appear.
            assert "dispatch_target" not in imp.content
            assert "capability_id" not in imp.content
            # Narrative is the only retrieval query.
            assert imp.content.get("narrative")
