"""Tests for agents.environmental_perception.aggregator (Phase 8 item 9)."""

from __future__ import annotations

from datetime import datetime

import pytest


class TestBandTimeOfDay:
    @pytest.mark.parametrize(
        "hour,expected",
        [
            (0, "late-night"),
            (4, "late-night"),
            (5, "morning"),
            (8, "morning"),
            (9, "midday"),
            (11, "midday"),
            (12, "afternoon"),
            (16, "afternoon"),
            (17, "evening"),
            (20, "evening"),
            (21, "night"),
            (23, "night"),
        ],
    )
    def test_bands(self, hour, expected):
        from agents.environmental_perception.aggregator import band_time_of_day

        assert band_time_of_day(hour) == expected


class TestWeatherSummary:
    def test_temp_f_plus_condition(self):
        from agents.environmental_perception.aggregator import _weather_summary

        assert (
            _weather_summary({"temp_f": 47, "condition": "partly cloudy"}) == "47°F, partly cloudy"
        )

    def test_temperature_plus_description(self):
        from agents.environmental_perception.aggregator import _weather_summary

        assert _weather_summary({"temperature": 71.5, "description": "clear"}) == "72°F, clear"

    def test_empty_state(self):
        from agents.environmental_perception.aggregator import _weather_summary

        assert _weather_summary({}) is None

    def test_only_temp(self):
        from agents.environmental_perception.aggregator import _weather_summary

        assert _weather_summary({"temp_f": 30}) == "30°F"


class TestAmbientEnergyBand:
    def test_low(self):
        from agents.environmental_perception.aggregator import _ambient_energy_band

        assert _ambient_energy_band({"operator_energy": {"value": 0.1}}) == "low"

    def test_medium(self):
        from agents.environmental_perception.aggregator import _ambient_energy_band

        assert _ambient_energy_band({"operator_energy": {"value": 0.5}}) == "medium"

    def test_high(self):
        from agents.environmental_perception.aggregator import _ambient_energy_band

        assert _ambient_energy_band({"operator_energy": {"value": 0.8}}) == "high"

    def test_missing_returns_none(self):
        from agents.environmental_perception.aggregator import _ambient_energy_band

        assert _ambient_energy_band({}) is None

    def test_non_dict_value_returns_none(self):
        from agents.environmental_perception.aggregator import _ambient_energy_band

        assert _ambient_energy_band({"operator_energy": "not a dict"}) is None


class TestReadEnvironmentalSnapshot:
    def test_all_sources_missing_returns_partial(self):
        from agents.environmental_perception.aggregator import read_environmental_snapshot

        snap = read_environmental_snapshot(
            now=datetime(2026, 4, 17, 14, 30),
            weather_reader=lambda: None,
            stimmung_reader=lambda: None,
        )
        assert snap.local_hour_24 == 14
        assert snap.time_of_day == "afternoon"
        assert snap.weather_summary is None
        assert snap.weather_fresh is False
        assert snap.ambient_energy_band is None

    def test_with_weather_state(self):
        from agents.environmental_perception.aggregator import read_environmental_snapshot

        snap = read_environmental_snapshot(
            now=datetime(2026, 4, 17, 10, 0),
            weather_reader=lambda: {"temp_f": 58, "condition": "sunny"},
            stimmung_reader=lambda: None,
        )
        assert snap.weather_summary == "58°F, sunny"

    def test_with_stimmung_state(self):
        from agents.environmental_perception.aggregator import read_environmental_snapshot

        snap = read_environmental_snapshot(
            now=datetime(2026, 4, 17, 10, 0),
            weather_reader=lambda: None,
            stimmung_reader=lambda: {"operator_energy": {"value": 0.75}},
        )
        assert snap.ambient_energy_band == "high"

    def test_full_snapshot(self):
        from agents.environmental_perception.aggregator import read_environmental_snapshot

        snap = read_environmental_snapshot(
            now=datetime(2026, 4, 17, 21, 0),
            weather_reader=lambda: {"temp_f": 45, "condition": "drizzle"},
            stimmung_reader=lambda: {"operator_energy": {"value": 0.35}},
        )
        assert snap.time_of_day == "night"
        assert snap.weather_summary == "45°F, drizzle"
        assert snap.ambient_energy_band == "medium"
        assert snap.captured_at.startswith("2026-04-17T21:")
