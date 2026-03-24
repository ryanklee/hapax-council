"""Tests for blueprint library — parameterized quickfort CSV generation."""

from __future__ import annotations

import pytest

from agents.fortress.blueprints import (
    BlueprintRegistry,
    bedroom_block,
    central_stairwell,
    dining_hall,
    entrance_defense,
    farm_block,
    generate_blueprint,
    generate_fortress_plan,
    phases_to_csv,
    starter_fortress,
    stockpile_hub,
    workshop_pocket,
)


class TestCentralStairwell:
    def test_generates_phases(self) -> None:
        phases = central_stairwell(depth=3, width=3)
        assert len(phases) >= 1
        assert phases[0].mode == "#dig"

    def test_depth_scaling(self) -> None:
        csv3 = phases_to_csv(central_stairwell(depth=3))
        csv5 = phases_to_csv(central_stairwell(depth=5))
        # More depth = more content
        assert len(csv5) > len(csv3)

    def test_invalid_width(self) -> None:
        with pytest.raises(ValueError):
            central_stairwell(width=4)  # only 3 or 5


class TestBedroomBlock:
    def test_basic_quality(self) -> None:
        phases = bedroom_block(n_rooms=4, quality="basic")
        csv = phases_to_csv(phases)
        assert "#dig" in csv
        assert "#build" in csv

    def test_quality_scaling(self) -> None:
        basic = phases_to_csv(bedroom_block(n_rooms=4, quality="basic"))
        noble = phases_to_csv(bedroom_block(n_rooms=4, quality="noble"))
        assert len(noble) > len(basic)  # noble rooms have more furniture

    def test_invalid_quality(self) -> None:
        with pytest.raises(ValueError):
            bedroom_block(quality="legendary")


class TestDiningHall:
    def test_generates(self) -> None:
        phases = dining_hall(capacity=20)
        assert len(phases) >= 1

    def test_size_scales_with_capacity(self) -> None:
        small = phases_to_csv(dining_hall(capacity=10))
        large = phases_to_csv(dining_hall(capacity=100))
        assert len(large) > len(small)


class TestWorkshopPocket:
    def test_generates(self) -> None:
        phases = workshop_pocket("Craftsdwarfs")
        assert len(phases) >= 1
        csv = phases_to_csv(phases)
        assert "#dig" in csv


class TestFarmBlock:
    def test_generates(self) -> None:
        phases = farm_block(n_plots=4, size=3)
        assert len(phases) >= 1

    def test_plot_scaling(self) -> None:
        small = phases_to_csv(farm_block(n_plots=2))
        large = phases_to_csv(farm_block(n_plots=6))
        assert len(large) > len(small)


class TestEntranceDefense:
    def test_generates(self) -> None:
        phases = entrance_defense()
        csv = phases_to_csv(phases)
        assert "#dig" in csv
        assert "#build" in csv


class TestStockpileHub:
    def test_generates(self) -> None:
        phases = stockpile_hub(categories=("food", "drink", "wood"))
        csv = phases_to_csv(phases)
        assert "#place" in csv

    def test_category_count(self) -> None:
        two = phases_to_csv(stockpile_hub(categories=("food", "drink")))
        four = phases_to_csv(stockpile_hub(categories=("food", "drink", "wood", "stone")))
        assert len(four) > len(two)


class TestStarterFortress:
    def test_generates(self) -> None:
        phases = starter_fortress(target_population=50)
        assert len(phases) > 0

    def test_population_scaling(self) -> None:
        small = starter_fortress(target_population=20)
        large = starter_fortress(target_population=100)
        assert len(large) >= len(small)


class TestRegistry:
    def test_list_templates(self) -> None:
        templates = BlueprintRegistry()
        templates.register("test", "infra", lambda: [])
        assert "test" in templates.list_templates()

    def test_unknown_template(self) -> None:
        reg = BlueprintRegistry()
        with pytest.raises(ValueError):
            reg.generate("nonexistent")


class TestPublicAPI:
    def test_generate_blueprint(self) -> None:
        csv = generate_blueprint("central_stairwell", depth=2, width=3)
        assert isinstance(csv, str)
        assert "#dig" in csv

    def test_generate_fortress_plan(self) -> None:
        plan = generate_fortress_plan(target_population=30)
        assert isinstance(plan, list)
        assert len(plan) > 0
        for label, csv in plan:
            assert isinstance(label, str)
            assert isinstance(csv, str)


class TestCSVValidity:
    """Structural CSV validity checks."""

    def test_no_empty_lines_within_phase(self) -> None:
        """Each phase's rows should not contain empty lines."""
        phases = central_stairwell(depth=3)
        for phase in phases:
            for row in phase.rows:
                # No row should be all empty
                assert any(cell != "" and cell != "`" for cell in row)
