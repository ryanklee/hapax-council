"""Tests for the imagination bus — data models, SHM publisher, and escalation."""

from __future__ import annotations

from agents.imagination import (
    ContentReference,
    ImaginationFragment,
)

# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


def _make_fragment(**overrides) -> ImaginationFragment:
    """Factory for test fragments with sensible defaults."""
    defaults = {
        "content_references": [
            ContentReference(kind="text", source="test", salience=0.5),
        ],
        "dimensions": {"intensity": 0.4, "tension": 0.2},
        "salience": 0.7,
        "continuation": False,
        "narrative": "test narrative",
    }
    defaults.update(overrides)
    return ImaginationFragment(**defaults)


# ---------------------------------------------------------------------------
# Task 1: Data model tests
# ---------------------------------------------------------------------------


class TestContentReference:
    def test_construction(self) -> None:
        ref = ContentReference(kind="qdrant_query", source="memory", salience=0.8)
        assert ref.kind == "qdrant_query"
        assert ref.source == "memory"
        assert ref.salience == 0.8
        assert ref.query is None

    def test_query_field(self) -> None:
        ref = ContentReference(
            kind="qdrant_query", source="memory", query="recent events", salience=0.6
        )
        assert ref.query == "recent events"


class TestImaginationFragment:
    def test_full_fragment(self) -> None:
        refs = [
            ContentReference(kind="text", source="input", salience=0.5),
            ContentReference(kind="qdrant_query", source="memory", query="mood", salience=0.9),
        ]
        frag = ImaginationFragment(
            content_references=refs,
            dimensions={"intensity": 0.7, "depth": 0.3},
            salience=0.8,
            continuation=True,
            narrative="a brooding passage",
            parent_id="abc123",
        )
        assert len(frag.content_references) == 2
        assert frag.continuation is True
        assert frag.parent_id == "abc123"
        assert len(frag.id) == 12
        assert frag.timestamp > 0

    def test_medium_agnostic_dimension_keys(self) -> None:
        """Dimensions are free-form strings — not tied to any specific medium."""
        dims = {
            "intensity": 0.5,
            "tension": 0.3,
            "diffusion": 0.1,
            "degradation": 0.0,
            "depth": 0.4,
            "pitch_displacement": 0.2,
            "temporal_distortion": 0.6,
            "spectral_color": 0.7,
            "coherence": 0.9,
        }
        frag = _make_fragment(dimensions=dims)
        assert len(frag.dimensions) == 9
        assert all(isinstance(k, str) for k in frag.dimensions)
        assert all(isinstance(v, float) for v in frag.dimensions.values())

    def test_serialization_roundtrip(self) -> None:
        frag = _make_fragment()
        data = frag.model_dump_json()
        restored = ImaginationFragment.model_validate_json(data)
        assert restored.id == frag.id
        assert restored.narrative == frag.narrative
        assert restored.content_references == frag.content_references
        assert restored.dimensions == frag.dimensions
