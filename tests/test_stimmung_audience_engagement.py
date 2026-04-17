"""Tests for Continuous-Loop Research Cadence §3.1 — stimmung 12th dim.

Validates the ``audience_engagement`` dimension: field presence on
``SystemStimmung``, membership in ``_DIMENSION_NAMES`` + cognitive
weight class, update+snapshot round-trip, inversion semantics (high
engagement → low stimmung value), staleness behaviour.
"""

from __future__ import annotations


class TestSystemStimmungSchema:
    def test_audience_engagement_field_present(self):
        from shared.stimmung import DimensionReading, SystemStimmung

        stim = SystemStimmung()
        assert hasattr(stim, "audience_engagement")
        assert isinstance(stim.audience_engagement, DimensionReading)

    def test_audience_engagement_in_dimension_names(self):
        from shared.stimmung import _DIMENSION_NAMES

        assert "audience_engagement" in _DIMENSION_NAMES

    def test_audience_engagement_is_cognitive_weight(self):
        from shared.stimmung import _COGNITIVE_DIMENSION_NAMES

        assert "audience_engagement" in _COGNITIVE_DIMENSION_NAMES


class TestUpdateAudienceEngagement:
    def _collector(self):
        from shared.stimmung import StimmungCollector

        return StimmungCollector(enable_exploration=False)

    def test_high_engagement_yields_low_stimmung(self):
        c = self._collector()
        c.update_audience_engagement(engagement=0.9)
        snap = c.snapshot()
        # High audience engagement → stimmung value near 0 (good state)
        assert snap.audience_engagement.value < 0.2

    def test_low_engagement_yields_high_stimmung(self):
        c = self._collector()
        c.update_audience_engagement(engagement=0.1)
        snap = c.snapshot()
        assert snap.audience_engagement.value > 0.8

    def test_zero_engagement_is_clamped_to_one(self):
        c = self._collector()
        c.update_audience_engagement(engagement=0.0)
        snap = c.snapshot()
        assert snap.audience_engagement.value == 1.0

    def test_one_engagement_is_clamped_to_zero(self):
        c = self._collector()
        c.update_audience_engagement(engagement=1.0)
        snap = c.snapshot()
        assert snap.audience_engagement.value == 0.0

    def test_out_of_range_values_clamped(self):
        c = self._collector()
        c.update_audience_engagement(engagement=-5.0)
        assert c.snapshot().audience_engagement.value == 1.0
        c.update_audience_engagement(engagement=5.0)
        assert c.snapshot().audience_engagement.value == 0.0

    def test_no_update_yields_stale_reading(self):
        c = self._collector()
        snap = c.snapshot()
        # No update means the dimension defaults; with fresh collector it
        # appears stale (freshness > _STALE_THRESHOLD_S).
        from shared.stimmung import _STALE_THRESHOLD_S

        assert snap.audience_engagement.freshness_s > _STALE_THRESHOLD_S


class TestStanceInteraction:
    def _collector(self):
        from shared.stimmung import StimmungCollector

        return StimmungCollector(enable_exploration=False)

    def test_low_engagement_alone_cannot_reach_degraded(self):
        """Cognitive weight 0.3× → even raw=1.0 gives effective 0.3 → CAUTIOUS max."""
        c = self._collector()
        c.update_audience_engagement(engagement=0.0)  # worst case
        snap = c.snapshot()
        from shared.stimmung import Stance

        # Cognitive cap: CAUTIOUS reachable, DEGRADED/CRITICAL must not be.
        assert snap.overall_stance in (Stance.NOMINAL, Stance.SEEKING, Stance.CAUTIOUS)


class TestFormatForPrompt:
    def test_audience_engagement_included_in_prompt_text(self):
        from shared.stimmung import StimmungCollector

        c = StimmungCollector(enable_exploration=False)
        c.update_audience_engagement(engagement=0.7)
        text = c.snapshot().format_for_prompt()
        assert "audience_engagement" in text
