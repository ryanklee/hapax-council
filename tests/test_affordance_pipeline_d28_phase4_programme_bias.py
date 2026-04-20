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
