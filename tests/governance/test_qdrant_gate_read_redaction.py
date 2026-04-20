"""Read-side mental-state redaction on ConsentGatedQdrant.

Wires the #208 dead-bridge: ``shared.governance.mental_state_redaction``
had zero production callers. The gate's read methods now auto-apply it
for the five mental-state collections when the stream is publicly
visible.

Reference:
    - shared/governance/mental_state_redaction.py (the redactor)
    - agents/_governance/qdrant_gate.py (the wired proxy)
    - docs/research/2026-04-20-dead-bridge-modules-audit.md
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from agents._governance.qdrant_gate import ConsentGatedQdrant


class _ScoredPoint:
    """Shape-alike for qdrant_client.ScoredPoint — carries .payload attribute."""

    def __init__(self, payload: dict) -> None:
        self.payload = payload


def _gate(inner: MagicMock) -> ConsentGatedQdrant:
    return ConsentGatedQdrant(inner=inner)


class TestSearchRedaction:
    def test_mental_state_collection_redacted_on_public_stream(self) -> None:
        inner = MagicMock()
        inner.search.return_value = [
            _ScoredPoint(payload={"episode_text": "operator felt anxious"}),
        ]
        gate = _gate(inner)
        with patch(
            "shared.governance.mental_state_redaction.is_publicly_visible",
            return_value=True,
        ):
            result = gate.search("operator-episodes", query_vector=[0.1])
        assert result[0].payload["episode_text"].startswith("[redacted")

    def test_mental_state_collection_passthrough_on_private_stream(self) -> None:
        inner = MagicMock()
        inner.search.return_value = [
            _ScoredPoint(payload={"episode_text": "operator felt anxious"}),
        ]
        gate = _gate(inner)
        with patch(
            "shared.governance.mental_state_redaction.is_publicly_visible",
            return_value=False,
        ):
            result = gate.search("operator-episodes", query_vector=[0.1])
        assert result[0].payload["episode_text"] == "operator felt anxious"

    def test_non_mental_state_collection_untouched(self) -> None:
        """`affordances` is not a mental-state collection — no redaction."""
        inner = MagicMock()
        inner.search.return_value = [
            _ScoredPoint(payload={"description": "speech capability"}),
        ]
        gate = _gate(inner)
        with patch(
            "shared.governance.mental_state_redaction.is_publicly_visible",
            return_value=True,
        ):
            result = gate.search("affordances", query_vector=[0.1])
        assert result[0].payload["description"] == "speech capability"

    def test_safe_summary_substitutes_when_present(self) -> None:
        inner = MagicMock()
        inner.search.return_value = [
            _ScoredPoint(
                payload={
                    "episode_text": "operator felt anxious",
                    "mental_state_safe_summary": "operator had an uneasy moment",
                }
            ),
        ]
        gate = _gate(inner)
        with patch(
            "shared.governance.mental_state_redaction.is_publicly_visible",
            return_value=True,
        ):
            result = gate.search("operator-episodes", query_vector=[0.1])
        assert result[0].payload["episode_text"] == "operator had an uneasy moment"


class TestScrollRedaction:
    def test_tuple_result_first_element_redacted(self) -> None:
        inner = MagicMock()
        inner.scroll.return_value = (
            [_ScoredPoint(payload={"fact_text": "operator prefers mornings"})],
            "next_offset_token",
        )
        gate = _gate(inner)
        with patch(
            "shared.governance.mental_state_redaction.is_publicly_visible",
            return_value=True,
        ):
            points, offset = gate.scroll("profile-facts", limit=10)
        assert points[0].payload["fact_text"].startswith("[redacted")
        assert offset == "next_offset_token"

    def test_bare_list_result_redacted(self) -> None:
        """Some mock / client versions return a plain list — still redacted."""
        inner = MagicMock()
        inner.scroll.return_value = [
            _ScoredPoint(payload={"pattern_description": "operator works in bursts"}),
        ]
        gate = _gate(inner)
        with patch(
            "shared.governance.mental_state_redaction.is_publicly_visible",
            return_value=True,
        ):
            result = gate.scroll("operator-patterns")
        assert result[0].payload["pattern_description"].startswith("[redacted")


class TestRetrieveRedaction:
    def test_retrieve_applies_redaction(self) -> None:
        inner = MagicMock()
        inner.retrieve.return_value = [
            _ScoredPoint(payload={"apperception_narrative": "operator lit up when..."}),
        ]
        gate = _gate(inner)
        with patch(
            "shared.governance.mental_state_redaction.is_publicly_visible",
            return_value=True,
        ):
            result = gate.retrieve("hapax-apperceptions", ids=["x"])
        assert result[0].payload["apperception_narrative"].startswith("[redacted")


class TestQueryPointsRedaction:
    def test_response_points_attr_redacted(self) -> None:
        inner = MagicMock()
        response = SimpleNamespace(
            points=[_ScoredPoint(payload={"correction_text": "operator corrected..."})]
        )
        inner.query_points.return_value = response
        gate = _gate(inner)
        with patch(
            "shared.governance.mental_state_redaction.is_publicly_visible",
            return_value=True,
        ):
            result = gate.query_points("operator-corrections", query=[0.1])
        assert result.points[0].payload["correction_text"].startswith("[redacted")


class TestNonMentalStateCollectionsPassThroughGate:
    """Reads of non-mental-state collections still route through the gate without touching redaction."""

    def test_scroll_affordances_passes_through(self) -> None:
        inner = MagicMock()
        inner.scroll.return_value = (
            [_ScoredPoint(payload={"name": "speech.render"})],
            None,
        )
        gate = _gate(inner)
        # is_publicly_visible never even gets called because the collection
        # is not in MENTAL_STATE_COLLECTIONS — no patch needed.
        points, _ = gate.scroll("affordances", limit=5)
        assert points[0].payload["name"] == "speech.render"


class TestGetattrFallback:
    def test_other_methods_still_proxy(self) -> None:
        """Methods we don't wrap (get_collection, etc.) still route to inner."""
        inner = MagicMock()
        inner.get_collection.return_value = "the-collection-info"
        gate = _gate(inner)
        assert gate.get_collection("any") == "the-collection-info"
