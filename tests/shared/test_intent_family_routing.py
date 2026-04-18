"""Tests for intent_family-restricted recruitment in AffordancePipeline.

Stage 1 routing fix (2026-04-18): the director's compositional impingements
carry an ``intent_family`` tag (camera.hero, ward.size, preset.bias, etc.)
that should restrict recruitment to capabilities of that family. Without
this, a Reverie satellite shader could win a recruitment intended for the
livestream surface.

These tests exercise:
- Impingement carries the field
- Family-name → capability-prefix canonicalization
- Family-restricted retrieval filters wider candidate window correctly
- None / unset intent_family falls through to global retrieval
"""

from __future__ import annotations

from unittest.mock import MagicMock

from shared.affordance_pipeline import AffordancePipeline, SelectionCandidate
from shared.impingement import Impingement, ImpingementType


class TestImpingementHasIntentFamilyField:
    def test_default_is_none(self):
        imp = Impingement(
            timestamp=0.0,
            source="test",
            type=ImpingementType.SALIENCE_INTEGRATION,
            strength=0.5,
        )
        assert imp.intent_family is None

    def test_can_be_set(self):
        imp = Impingement(
            timestamp=0.0,
            source="test",
            type=ImpingementType.SALIENCE_INTEGRATION,
            strength=0.5,
            intent_family="camera.hero",
        )
        assert imp.intent_family == "camera.hero"

    def test_serializes_to_json(self):
        imp = Impingement(
            timestamp=0.0,
            source="test",
            type=ImpingementType.SALIENCE_INTEGRATION,
            strength=0.5,
            intent_family="ward.staging",
        )
        payload = imp.model_dump_json()
        assert '"intent_family":"ward.staging"' in payload

    def test_deserializes_from_json(self):
        raw = (
            '{"timestamp": 0.0, "source": "x", "type": "salience_integration", '
            '"strength": 0.5, "intent_family": "preset.bias"}'
        )
        imp = Impingement.model_validate_json(raw)
        assert imp.intent_family == "preset.bias"


class TestCanonicalFamilyPrefix:
    def test_camera_hero_maps_to_cam_hero(self):
        assert AffordancePipeline._canonical_family_prefix("camera.hero") == "cam.hero."

    def test_preset_bias_maps_to_fx_family(self):
        assert AffordancePipeline._canonical_family_prefix("preset.bias") == "fx.family."

    def test_overlay_emphasis_maps_to_overlay(self):
        assert AffordancePipeline._canonical_family_prefix("overlay.emphasis") == "overlay."

    def test_ward_families_use_self_prefix(self):
        assert AffordancePipeline._canonical_family_prefix("ward.size") == "ward.size."
        assert AffordancePipeline._canonical_family_prefix("ward.staging") == "ward.staging."
        assert (
            AffordancePipeline._canonical_family_prefix("ward.choreography") == "ward.choreography."
        )

    def test_unknown_family_falls_through_as_prefix(self):
        # Unknown families don't crash — best-effort.
        assert AffordancePipeline._canonical_family_prefix("future.thing") == "future.thing."


class TestRetrieveFamily:
    def _candidates(self, *names_with_scores):
        return [
            SelectionCandidate(
                capability_name=name,
                similarity=score,
                payload={},
            )
            for name, score in names_with_scores
        ]

    def test_filters_to_family_prefix(self):
        pipeline = AffordancePipeline.__new__(AffordancePipeline)
        # Wider window contains both camera and reverie satellite candidates;
        # the family filter must keep only the camera ones.
        wider = self._candidates(
            ("cam.hero.overhead.vinyl-spinning", 0.72),
            ("node.sat_zoom_content", 0.71),
            ("cam.hero.desk-c920.coding", 0.65),
            ("node.sat_emphasis_glow", 0.60),
            ("space.ir_hand_zone", 0.55),
        )
        pipeline._retrieve = MagicMock(return_value=wider)
        out = pipeline._retrieve_family([0.0] * 768, "camera.hero", top_k=10)
        names = {c.capability_name for c in out}
        assert names == {
            "cam.hero.overhead.vinyl-spinning",
            "cam.hero.desk-c920.coding",
        }
        assert "node.sat_zoom_content" not in names

    def test_returns_empty_when_no_family_match(self):
        pipeline = AffordancePipeline.__new__(AffordancePipeline)
        pipeline._retrieve = MagicMock(
            return_value=self._candidates(
                ("node.sat_zoom_content", 0.71),
                ("space.ir_hand_zone", 0.55),
            )
        )
        out = pipeline._retrieve_family([0.0] * 768, "camera.hero", top_k=10)
        assert out == []

    def test_sorted_by_similarity_descending(self):
        pipeline = AffordancePipeline.__new__(AffordancePipeline)
        pipeline._retrieve = MagicMock(
            return_value=self._candidates(
                ("ward.size.album.shrink-20pct", 0.40),
                ("ward.size.token_pole.grow-110pct", 0.80),
                ("ward.size.captions.natural", 0.60),
            )
        )
        out = pipeline._retrieve_family([0.0] * 768, "ward.size", top_k=10)
        assert [c.capability_name for c in out] == [
            "ward.size.token_pole.grow-110pct",
            "ward.size.captions.natural",
            "ward.size.album.shrink-20pct",
        ]

    def test_top_k_caps_returned_count(self):
        pipeline = AffordancePipeline.__new__(AffordancePipeline)
        pipeline._retrieve = MagicMock(
            return_value=self._candidates(
                *[(f"cam.hero.role-{i}.ctx", 1.0 - i * 0.01) for i in range(20)]
            )
        )
        out = pipeline._retrieve_family([0.0] * 768, "camera.hero", top_k=5)
        assert len(out) == 5

    def test_widens_retrieval_window(self):
        # _retrieve_family should request a wider candidate window than top_k
        # so the post-filter has material to keep.
        pipeline = AffordancePipeline.__new__(AffordancePipeline)
        pipeline._retrieve = MagicMock(return_value=[])
        pipeline._retrieve_family([0.0] * 768, "camera.hero", top_k=10)
        called_with_top_k = (
            pipeline._retrieve.call_args[1].get("top_k") or pipeline._retrieve.call_args[0][1]
        )
        assert called_with_top_k >= 50, f"expected wider window (>=50), got {called_with_top_k}"
