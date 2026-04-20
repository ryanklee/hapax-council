"""D-28 Phase 4 — programme-as-soft-prior bias on the affordance pipeline.

Tests the `_apply_programme_bias` helper + its integration in
`AffordancePipeline.select`. The hard invariant: bias is a multiplier;
the candidate set length is preserved exactly. Per
`project_programmes_enable_grounding` memory + plan §5.1.
"""

from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import MagicMock

import pytest  # noqa: TC002

from shared.affordance import SelectionCandidate
from shared.affordance_pipeline import AffordancePipeline


@dataclass
class _FakeProgramme:
    """Minimal stub matching the Programme structural type used by the
    bias path (only `bias_multiplier` + `programme_id` needed)."""

    programme_id: str = "test-001"
    biases: dict[str, float] | None = None

    def bias_multiplier(self, capability_name: str) -> float:
        if self.biases is None:
            return 1.0
        return self.biases.get(capability_name, 1.0)


def _candidate(name: str, combined: float = 0.5) -> SelectionCandidate:
    return SelectionCandidate(
        capability_name=name,
        similarity=0.5,
        combined=combined,
        payload={},
    )


@pytest.fixture
def pipeline() -> AffordancePipeline:
    return AffordancePipeline()


class TestApplyProgrammeBiasIdentity:
    def test_no_programme_returns_input_unchanged(self, pipeline) -> None:
        cands = [_candidate("a", 0.3), _candidate("b", 0.6)]
        result = pipeline._apply_programme_bias(cands, None)
        assert result is cands  # exact reference, no copy
        assert [c.combined for c in result] == [0.3, 0.6]

    def test_programme_with_no_biases_no_op(self, pipeline) -> None:
        cands = [_candidate("a", 0.3), _candidate("b", 0.6)]
        prog = _FakeProgramme()
        result = pipeline._apply_programme_bias(cands, prog)
        assert [c.combined for c in result] == [0.3, 0.6]


class TestApplyProgrammeBiasMultipliers:
    def test_positive_bias_amplifies(self, pipeline) -> None:
        cands = [_candidate("knowledge.web_search", 0.5)]
        prog = _FakeProgramme(biases={"knowledge.web_search": 2.0})
        result = pipeline._apply_programme_bias(cands, prog)
        assert result[0].combined == 1.0  # 0.5 * 2.0

    def test_negative_bias_attenuates(self, pipeline) -> None:
        cands = [_candidate("camera.hero", 0.8)]
        prog = _FakeProgramme(biases={"camera.hero": 0.25})
        result = pipeline._apply_programme_bias(cands, prog)
        assert result[0].combined == pytest.approx(0.2)

    def test_unbiased_capabilities_unchanged(self, pipeline) -> None:
        cands = [
            _candidate("biased", 0.5),
            _candidate("not_biased", 0.5),
        ]
        prog = _FakeProgramme(biases={"biased": 0.5})
        result = pipeline._apply_programme_bias(cands, prog)
        # First halved, second unchanged.
        assert result[0].combined == 0.25
        assert result[1].combined == 0.5


class TestSetSizeInvariant:
    """The hard architectural invariant: bias is a soft prior, never a
    candidate-set reduction. Per project_programmes_enable_grounding."""

    def test_strong_negative_bias_does_not_drop_candidates(self, pipeline) -> None:
        """Even with the strongest legal negative bias (smallest non-zero
        per the Programme validator), candidate count is preserved."""
        cands = [
            _candidate("a", 0.5),
            _candidate("b", 0.5),
            _candidate("c", 0.5),
        ]
        prog = _FakeProgramme(biases={"a": 0.01, "b": 0.01, "c": 0.01})
        result = pipeline._apply_programme_bias(cands, prog)
        assert len(result) == 3, "set size MUST be preserved"
        for c in result:
            assert c.combined > 0.0  # zero would be a validator bug

    def test_pathological_all_zero_input_still_preserves_set(self, pipeline) -> None:
        """Input candidates with combined=0 stay in the set."""
        cands = [_candidate("a", 0.0), _candidate("b", 0.0)]
        prog = _FakeProgramme(biases={"a": 5.0, "b": 5.0})
        result = pipeline._apply_programme_bias(cands, prog)
        assert len(result) == 2  # set preserved despite zero scores

    def test_combined_clamped_at_zero(self, pipeline) -> None:
        """Negative input combined would multiply weirdly; clamp to >= 0."""
        cand = _candidate("a", -0.5)  # synthetic negative input
        cands = [cand]
        prog = _FakeProgramme(biases={"a": 2.0})
        result = pipeline._apply_programme_bias(cands, prog)
        assert result[0].combined >= 0.0


class TestProgrammeMethodFailures:
    def test_bias_multiplier_raises_treated_as_neutral(self, pipeline) -> None:
        """A programme stub without bias_multiplier (or one that raises)
        must NOT break recruitment — fall back to multiplier=1.0."""
        cands = [_candidate("a", 0.5)]
        broken = MagicMock()
        broken.bias_multiplier.side_effect = RuntimeError("borked")
        broken.programme_id = "broken-001"
        result = pipeline._apply_programme_bias(cands, broken)
        # Score unchanged because helper falls back to 1.0
        assert result[0].combined == 0.5
        assert len(result) == 1

    def test_bias_multiplier_returns_non_float(self, pipeline) -> None:
        cands = [_candidate("a", 0.5)]
        broken = MagicMock()
        broken.bias_multiplier.return_value = "not a number"
        broken.programme_id = "broken-002"
        result = pipeline._apply_programme_bias(cands, broken)
        assert result[0].combined == 0.5  # fallback to 1.0


class TestImpingementPressureOverridesBias:
    """Per spec §5.1 line 530-535: a strongly-biased-negative capability
    can still recruit if its base similarity is high enough.

    Concrete numbers from the spec example:
      - 0.9 cosine × 0.25 bias = 0.225 → below threshold 0.30 → no recruit
      - 0.95 cosine × 0.5 bias = 0.475 → above threshold → recruit
    """

    def test_low_pressure_loses_against_negative_bias(self, pipeline) -> None:
        cand = _candidate("biased_cap", 0.9)
        prog = _FakeProgramme(biases={"biased_cap": 0.25})
        result = pipeline._apply_programme_bias([cand], prog)
        assert result[0].combined == pytest.approx(0.225)
        # Note: the threshold filter (separate stage) would drop this; our
        # helper just produces the score. Set size invariant holds.
        assert len(result) == 1

    def test_high_pressure_wins_through_negative_bias(self, pipeline) -> None:
        cand = _candidate("biased_cap", 0.95)
        prog = _FakeProgramme(biases={"biased_cap": 0.5})
        result = pipeline._apply_programme_bias([cand], prog)
        assert result[0].combined == pytest.approx(0.475)


class TestInvariantCounter:
    """``hapax_programme_candidate_set_reduction_total`` must stay at zero
    under healthy operation. Increments only on implementation bug —
    the validator on ``capability_bias_negative`` rejects 0.0, so the
    helper *cannot* legitimately drop a candidate. These tests pin the
    counter wiring without triggering the bug path.
    """

    def test_no_increment_on_healthy_path(self, pipeline, monkeypatch) -> None:
        """Across the realistic scoring shape, counter stays untouched."""
        from shared.governance import demonet_metrics

        increments: list[str] = []
        monkeypatch.setattr(
            demonet_metrics.METRICS,
            "inc_programme_candidate_set_reduction",
            lambda pid: increments.append(pid),
        )
        cands = [_candidate("a", 0.4), _candidate("b", 0.7), _candidate("c", 0.2)]
        prog = _FakeProgramme(biases={"a": 0.5, "b": 1.5, "c": 0.25})
        pipeline._apply_programme_bias(cands, prog)
        assert increments == [], "counter must not increment on healthy bias path"

    def test_no_increment_on_pathological_all_negative(self, pipeline, monkeypatch) -> None:
        from shared.governance import demonet_metrics

        increments: list[str] = []
        monkeypatch.setattr(
            demonet_metrics.METRICS,
            "inc_programme_candidate_set_reduction",
            lambda pid: increments.append(pid),
        )
        cands = [_candidate("a", 0.5), _candidate("b", 0.5), _candidate("c", 0.5)]
        prog = _FakeProgramme(biases={"a": 0.01, "b": 0.01, "c": 0.01})
        pipeline._apply_programme_bias(cands, prog)
        # Helper preserved set, so counter MUST stay quiet.
        assert increments == []


class TestRealProgrammeIntegration:
    """The helper is documented against the structural type but real
    deployment uses ``shared.programme.Programme``. These pin the
    integration with the actual pydantic model so a future refactor
    of ``bias_multiplier`` semantics is caught immediately.
    """

    def test_real_programme_negative_bias_attenuates(self, pipeline) -> None:
        from shared.programme import (
            Programme,
            ProgrammeConstraintEnvelope,
            ProgrammeRole,
        )

        prog = Programme(
            programme_id="prog-listening-001",
            role=ProgrammeRole.LISTENING,
            planned_duration_s=300.0,
            constraints=ProgrammeConstraintEnvelope(
                capability_bias_negative={"speech_production": 0.2},
            ),
            parent_show_id="show-test",
        )
        cands = [_candidate("speech_production", 0.5), _candidate("camera.hero", 0.5)]
        result = pipeline._apply_programme_bias(cands, prog)
        assert result[0].combined == pytest.approx(0.1)  # 0.5 * 0.2
        assert result[1].combined == pytest.approx(0.5)  # untouched
        assert len(result) == 2

    def test_real_programme_positive_bias_amplifies(self, pipeline) -> None:
        from shared.programme import (
            Programme,
            ProgrammeConstraintEnvelope,
            ProgrammeRole,
        )

        prog = Programme(
            programme_id="prog-tutorial-001",
            role=ProgrammeRole.TUTORIAL,
            planned_duration_s=300.0,
            constraints=ProgrammeConstraintEnvelope(
                capability_bias_positive={"speech_production": 1.5},
            ),
            parent_show_id="show-test",
        )
        cands = [_candidate("speech_production", 0.4)]
        result = pipeline._apply_programme_bias(cands, prog)
        assert result[0].combined == pytest.approx(0.6)  # 0.4 * 1.5

    def test_negative_bias_overcome_fires_soft_prior_counter(self, pipeline, monkeypatch) -> None:
        """Phase 9 invariant: soft-prior-overridden counter must fire when
        a candidate received negative bias yet still survives the
        recruitment threshold. Validates the soft-prior-not-hardening
        detector wires through `_apply_programme_bias`.
        """
        from shared import programme_observability as obs

        captured: list[tuple[str, str]] = []

        def fake_emit(pid: str, reason: str = "high_pressure") -> None:
            captured.append((pid, reason))

        monkeypatch.setattr(obs, "emit_soft_prior_override", fake_emit)
        # 0.95 * 0.5 = 0.475 — well above THRESHOLD (0.05) so override fires
        cands = [_candidate("biased_cap", 0.95)]
        prog = _FakeProgramme(programme_id="prog-test", biases={"biased_cap": 0.5})
        pipeline._apply_programme_bias(cands, prog)
        assert ("prog-test", "negative_bias_overcome") in captured

    def test_positive_bias_does_not_fire_override_counter(self, pipeline, monkeypatch) -> None:
        """Positive bias is not an override event — counter must stay quiet."""
        from shared import programme_observability as obs

        captured: list[tuple[str, str]] = []
        monkeypatch.setattr(
            obs, "emit_soft_prior_override", lambda pid, reason="x": captured.append((pid, reason))
        )
        cands = [_candidate("amplified", 0.5)]
        prog = _FakeProgramme(biases={"amplified": 1.5})
        pipeline._apply_programme_bias(cands, prog)
        assert captured == []

    def test_real_programme_set_size_invariant_under_bias(self, pipeline) -> None:
        """Pin the architectural axiom against the real Programme model."""
        from shared.programme import (
            Programme,
            ProgrammeConstraintEnvelope,
            ProgrammeRole,
        )

        prog = Programme(
            programme_id="prog-pathological-001",
            role=ProgrammeRole.LISTENING,
            planned_duration_s=300.0,
            constraints=ProgrammeConstraintEnvelope(
                capability_bias_negative={
                    "a": 0.01,
                    "b": 0.01,
                    "c": 0.01,
                    "d": 0.01,
                },
            ),
            parent_show_id="show-test",
        )
        cands = [_candidate(name, 0.5) for name in ("a", "b", "c", "d")]
        result = pipeline._apply_programme_bias(cands, prog)
        assert len(result) == 4  # invariant: set size preserved
        # And every score remains > 0 (validator forbade 0 multipliers)
        for c in result:
            assert c.combined > 0.0
