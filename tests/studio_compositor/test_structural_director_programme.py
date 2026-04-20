"""Phase 5 — programme-aware StructuralDirector emission.

Plan §lines 564-643 of
``docs/superpowers/plans/2026-04-20-programme-layer-plan.md``. Verifies:

  - Programme role + narrative_beat + soft priors render into the prompt
  - Emitted ``StructuralIntent`` carries ``programme_id`` when programme active
  - Programme absent → ``programme_id`` is None and prompt has no programme block
  - ``structural_cadence_prior_s`` overrides default cadence between ticks
  - Programme provider failure does NOT break the tick (defensive)
  - SOFT-PRIOR REGRESSION PIN: prompt programme block frames priors as
    "soft" / "prefers" / "bias toward" and never as "must" / "required" /
    "only" / "never" / "forbidden" — guards against hard-gate drift
  - Grounding-expansion: even with a `paused` rotation prior, the LLM
    can pick `random` / `weighted_by_salience` / `sequential` and the
    director publishes the LLM's choice (not the prior).
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from pathlib import Path

import pytest

from agents.studio_compositor import structural_director as sd
from shared.programme import (
    Programme,
    ProgrammeConstraintEnvelope,
    ProgrammeContent,
    ProgrammeRole,
)

# ── Fixtures ────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _redirect_paths(monkeypatch, tmp_path):
    monkeypatch.setattr(sd, "_STRUCTURAL_INTENT_PATH", tmp_path / "intent.json")
    monkeypatch.setattr(sd, "_STRUCTURAL_INTENT_JSONL", tmp_path / "structural-intent.jsonl")
    monkeypatch.setattr(sd, "_RESEARCH_MARKER_PATH", tmp_path / "no-research-marker.json")
    return tmp_path


def _programme(
    *,
    programme_id: str = "prog-listening-001",
    role: ProgrammeRole = ProgrammeRole.LISTENING,
    narrative_beat: str | None = "Sit with this groove for a while; let it breathe.",
    preset_family_priors: list[str] | None = None,
    homage_rotation_modes: list[str] | None = None,
    structural_cadence_prior_s: float | None = None,
) -> Programme:
    return Programme(
        programme_id=programme_id,
        role=role,
        planned_duration_s=600.0,
        constraints=ProgrammeConstraintEnvelope(
            preset_family_priors=preset_family_priors or [],
            homage_rotation_modes=homage_rotation_modes or [],
            structural_cadence_prior_s=structural_cadence_prior_s,
        ),
        content=ProgrammeContent(narrative_beat=narrative_beat),
        parent_show_id="show-test-001",
    )


def _stub_llm(payload: dict) -> Callable[[str], str]:
    """Return an LLM stub that always returns the given payload as JSON."""

    def fn(prompt: str) -> str:  # noqa: ARG001 — prompt unused in stub
        return json.dumps(payload)

    return fn


_DEFAULT_PAYLOAD: dict = {
    "scene_mode": "hardware-play",
    "preset_family_hint": "audio-reactive",
    "long_horizon_direction": "vinyl session, sit with it",
    "homage_rotation_mode": "sequential",
}


# ── Prompt rendering ────────────────────────────────────────────────────


class TestPromptRendering:
    def test_programme_section_present_when_programme_active(self) -> None:
        prog = _programme(role=ProgrammeRole.LISTENING)
        director = sd.StructuralDirector(
            llm_fn=_stub_llm(_DEFAULT_PAYLOAD), programme_provider=lambda: prog
        )
        prompt = director._build_prompt(programme=prog)
        assert "## Programme context" in prompt
        assert "listening" in prompt.lower()

    def test_programme_section_absent_when_no_programme(self) -> None:
        director = sd.StructuralDirector(llm_fn=_stub_llm(_DEFAULT_PAYLOAD))
        prompt = director._build_prompt(programme=None)
        assert "## Programme context" not in prompt

    def test_narrative_beat_renders_into_prompt(self) -> None:
        prog = _programme(narrative_beat="Wind down — quiet textures, slow camera moves.")
        director = sd.StructuralDirector(llm_fn=_stub_llm(_DEFAULT_PAYLOAD))
        prompt = director._build_prompt(programme=prog)
        assert "wind down" in prompt.lower()
        assert "quiet textures" in prompt.lower()

    def test_preset_family_priors_render(self) -> None:
        prog = _programme(preset_family_priors=["calm-textural", "warm-minimal"])
        director = sd.StructuralDirector(llm_fn=_stub_llm(_DEFAULT_PAYLOAD))
        prompt = director._build_prompt(programme=prog)
        assert "calm-textural" in prompt
        assert "warm-minimal" in prompt

    def test_homage_rotation_modes_render(self) -> None:
        prog = _programme(homage_rotation_modes=["paused", "weighted_by_salience"])
        director = sd.StructuralDirector(llm_fn=_stub_llm(_DEFAULT_PAYLOAD))
        prompt = director._build_prompt(programme=prog)
        assert "paused" in prompt
        assert "weighted_by_salience" in prompt

    def test_empty_priors_lists_omitted(self) -> None:
        """With empty prior lists the bullet doesn't render — keeps prompt tight."""
        prog = _programme(preset_family_priors=[], homage_rotation_modes=[])
        director = sd.StructuralDirector(llm_fn=_stub_llm(_DEFAULT_PAYLOAD))
        prompt = director._build_prompt(programme=prog)
        assert "prefers preset families" not in prompt
        assert "bias toward homage rotation modes" not in prompt

    def test_missing_narrative_beat_omits_direction_bullet(self) -> None:
        prog = _programme(narrative_beat=None)
        director = sd.StructuralDirector(llm_fn=_stub_llm(_DEFAULT_PAYLOAD))
        prompt = director._build_prompt(programme=prog)
        assert "programme direction:" not in prompt


# ── programme_id stamping ───────────────────────────────────────────────


class TestProgrammeIdStamping:
    def test_intent_carries_programme_id_when_active(self) -> None:
        prog = _programme(programme_id="prog-vinyl-2026-04-20-A")
        director = sd.StructuralDirector(
            llm_fn=_stub_llm(_DEFAULT_PAYLOAD), programme_provider=lambda: prog
        )
        intent = director.tick_once()
        assert intent is not None
        assert intent.programme_id == "prog-vinyl-2026-04-20-A"

    def test_intent_programme_id_none_when_no_programme(self) -> None:
        director = sd.StructuralDirector(llm_fn=_stub_llm(_DEFAULT_PAYLOAD))
        intent = director.tick_once()
        assert intent is not None
        assert intent.programme_id is None

    def test_persisted_intent_includes_programme_id(self, tmp_path: Path) -> None:
        prog = _programme(programme_id="prog-show-001")
        director = sd.StructuralDirector(
            llm_fn=_stub_llm(_DEFAULT_PAYLOAD), programme_provider=lambda: prog
        )
        director.tick_once()
        persisted = json.loads((tmp_path / "intent.json").read_text())
        assert persisted["programme_id"] == "prog-show-001"

    def test_provider_returning_none_yields_null_programme_id(self) -> None:
        director = sd.StructuralDirector(
            llm_fn=_stub_llm(_DEFAULT_PAYLOAD), programme_provider=lambda: None
        )
        intent = director.tick_once()
        assert intent is not None
        assert intent.programme_id is None


# ── Cadence override ────────────────────────────────────────────────────


class TestCadenceOverride:
    def test_default_cadence_when_no_programme(self) -> None:
        director = sd.StructuralDirector(cadence_s=90.0, llm_fn=_stub_llm(_DEFAULT_PAYLOAD))
        assert director._next_cadence_s() == pytest.approx(90.0)

    def test_programme_overrides_cadence(self) -> None:
        prog = _programme(structural_cadence_prior_s=45.0)
        director = sd.StructuralDirector(
            cadence_s=90.0,
            llm_fn=_stub_llm(_DEFAULT_PAYLOAD),
            programme_provider=lambda: prog,
        )
        assert director._next_cadence_s() == pytest.approx(45.0)

    def test_programme_without_cadence_prior_keeps_default(self) -> None:
        prog = _programme(structural_cadence_prior_s=None)
        director = sd.StructuralDirector(
            cadence_s=90.0,
            llm_fn=_stub_llm(_DEFAULT_PAYLOAD),
            programme_provider=lambda: prog,
        )
        assert director._next_cadence_s() == pytest.approx(90.0)


# ── Soft-prior framing regression pin (the keystone) ────────────────────


class TestSoftPriorFraming:
    """Pin the wording of the programme context block.

    A future drift-toward-hard-gate refactor would substitute "must" /
    "required" / "only" for "prefers" / "soft prior" / "bias toward".
    These tests catch that drift at the prompt-string level, before any
    LLM behaviour change can be observed in production.

    project_programmes_enable_grounding architectural axiom.
    """

    def test_programme_block_uses_soft_framing_words(self) -> None:
        prog = _programme(
            preset_family_priors=["calm-textural"],
            homage_rotation_modes=["paused"],
        )
        director = sd.StructuralDirector(llm_fn=_stub_llm(_DEFAULT_PAYLOAD))
        prompt = director._build_prompt(programme=prog)
        block = _extract_programme_block(prompt)
        # At least one soft-prior framing phrase MUST appear.
        soft_words = ["soft prior", "prefers", "bias toward", "preferences"]
        assert any(w in block.lower() for w in soft_words), (
            f"programme block missing soft-prior framing; block was:\n{block}"
        )

    def test_programme_block_avoids_hard_gate_words(self) -> None:
        prog = _programme(
            preset_family_priors=["calm-textural"],
            homage_rotation_modes=["paused"],
        )
        director = sd.StructuralDirector(llm_fn=_stub_llm(_DEFAULT_PAYLOAD))
        prompt = director._build_prompt(programme=prog)
        block = _extract_programme_block(prompt).lower()
        # Whole-word matches so we don't false-positive on substrings.
        forbidden = ["must", "required", "only", "never", "forbidden", "mandatory"]
        for word in forbidden:
            assert not re.search(rf"\b{word}\b", block), (
                f"programme block contains hard-gate word {word!r}; block:\n{block}"
            )

    def test_programme_block_explicitly_authorises_override(self) -> None:
        """The block must tell the LLM it CAN deviate from the priors."""
        prog = _programme()
        director = sd.StructuralDirector(llm_fn=_stub_llm(_DEFAULT_PAYLOAD))
        prompt = director._build_prompt(programme=prog)
        block = _extract_programme_block(prompt).lower()
        # One of these phrases makes "you may override" explicit
        slack = ["emit it", "different move", "expand grounding"]
        assert any(s in block for s in slack), (
            "programme block does not explicitly authorise the LLM to override priors"
        )


def _extract_programme_block(prompt: str) -> str:
    """Slice the '## Programme context' block out of the rendered prompt."""
    marker = "## Programme context"
    if marker not in prompt:
        return ""
    after = prompt.split(marker, 1)[1]
    next_section = after.find("\n## ")
    return after if next_section == -1 else after[:next_section]


# ── Provider robustness ─────────────────────────────────────────────────


class TestProviderRobustness:
    def test_provider_raising_does_not_break_tick(self) -> None:
        def boom() -> Programme | None:
            raise RuntimeError("provider broken")

        director = sd.StructuralDirector(
            llm_fn=_stub_llm(_DEFAULT_PAYLOAD), programme_provider=boom
        )
        intent = director.tick_once()
        assert intent is not None
        assert intent.programme_id is None  # Falls through to None

    def test_provider_raising_keeps_default_cadence(self) -> None:
        def boom() -> Programme | None:
            raise RuntimeError("provider broken")

        director = sd.StructuralDirector(
            cadence_s=90.0, llm_fn=_stub_llm(_DEFAULT_PAYLOAD), programme_provider=boom
        )
        assert director._next_cadence_s() == pytest.approx(90.0)


# ── Grounding-expansion: priors don't gate the LLM ──────────────────────


class TestGroundingExpansion:
    """A programme that prefers `paused` does not prevent the director
    from publishing `random` / `weighted_by_salience` / `sequential`
    when the LLM (responding to perceptual pressure in the real prompt
    + a stubbed pressure here) decides to move out of the prior.

    Mirrors the plan §line 599-602 burst-replay assertion at the
    wiring level: with a stub LLM that returns `burst`-equivalent
    out-of-prior responses, we assert the director PUBLISHES those
    responses unmodified — no silent rewrite-to-prior.
    """

    def test_director_publishes_out_of_prior_choice(self, tmp_path: Path) -> None:
        prog = _programme(homage_rotation_modes=["paused"])
        # LLM picks "weighted_by_salience" despite the "paused" prior
        out_of_prior_payload = {
            **_DEFAULT_PAYLOAD,
            "homage_rotation_mode": "weighted_by_salience",
        }
        director = sd.StructuralDirector(
            llm_fn=_stub_llm(out_of_prior_payload), programme_provider=lambda: prog
        )
        intent = director.tick_once()
        assert intent is not None
        # Director did NOT silently rewrite to the prior
        assert intent.homage_rotation_mode == "weighted_by_salience"

    def test_replay_distribution_passes_through_unmodified(self) -> None:
        """100-call replay: LLM returns 30% out-of-prior responses; the
        director publishes ALL 30 unmodified. This validates that the
        soft-prior framing in the prompt doesn't translate to any
        hard-gate filtering on the response side.
        """
        prog = _programme(homage_rotation_modes=["paused"])

        # Deterministic 30/70 split — first 30 calls return out-of-prior.
        responses = [
            json.dumps({**_DEFAULT_PAYLOAD, "homage_rotation_mode": "weighted_by_salience"})
        ] * 30 + [json.dumps({**_DEFAULT_PAYLOAD, "homage_rotation_mode": "paused"})] * 70
        idx = [0]

        def replay_llm(prompt: str) -> str:  # noqa: ARG001
            out = responses[idx[0] % len(responses)]
            idx[0] += 1
            return out

        director = sd.StructuralDirector(llm_fn=replay_llm, programme_provider=lambda: prog)

        out_of_prior = 0
        in_prior = 0
        for _ in range(100):
            intent = director.tick_once()
            assert intent is not None
            if intent.homage_rotation_mode == "weighted_by_salience":
                out_of_prior += 1
            elif intent.homage_rotation_mode == "paused":
                in_prior += 1

        # All 30 out-of-prior responses make it through unmodified.
        assert out_of_prior == 30
        assert in_prior == 70
