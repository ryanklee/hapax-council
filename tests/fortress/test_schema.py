"""Tests for fortress state schema models."""

from __future__ import annotations

import pytest

from agents.fortress.schema import (
    CaravanEvent,
    CaveInEvent,
    DeathEvent,
    DwarfSkill,
    DwarfUnit,
    FastFortressState,
    FortressPosition,
    FullFortressState,
    MandateEvent,
    MegabeastEvent,
    MigrantEvent,
    MoodEvent,
    SeasonChangeEvent,
    SiegeEvent,
    StockpileSummary,
)


class TestDwarfUnit:
    def test_construction(self):
        unit = DwarfUnit(
            id=1,
            name="Urist McTest",
            profession="Miner",
            skills=(DwarfSkill(name="MINING", level=5),),
            stress=0,
            mood="normal",
            current_job="Mining",
        )
        assert unit.id == 1
        assert unit.skills[0].level == 5

    def test_frozen(self):
        unit = DwarfUnit(
            id=1,
            name="Urist",
            profession="Miner",
            skills=(),
            stress=0,
            mood="normal",
            current_job="idle",
        )
        with pytest.raises(Exception):  # ValidationError for frozen model
            unit.name = "Changed"  # type: ignore[misc]

    def test_optional_squad(self):
        unit = DwarfUnit(
            id=1,
            name="Urist",
            profession="Miner",
            skills=(),
            stress=0,
            mood="normal",
            current_job="idle",
        )
        assert unit.military_squad_id is None

        unit_with_squad = DwarfUnit(
            id=2,
            name="Urist",
            profession="Axedwarf",
            skills=(),
            stress=0,
            mood="normal",
            current_job="idle",
            military_squad_id=3,
        )
        assert unit_with_squad.military_squad_id == 3


class TestStockpileSummary:
    def test_defaults_zero(self):
        s = StockpileSummary()
        assert s.food == 0
        assert s.drink == 0
        assert s.weapons == 0

    def test_custom_values(self):
        s = StockpileSummary(food=100, drink=50, metal_bars=20)
        assert s.food == 100


class TestFortressEvents:
    def test_siege_event(self):
        e = SiegeEvent(attacker_civ="Goblin Dark", force_size=40)
        assert e.type == "siege"
        assert e.force_size == 40

    def test_migrant_event(self):
        e = MigrantEvent(count=12)
        assert e.type == "migrant"

    def test_death_event(self):
        e = DeathEvent(unit_id=5, unit_name="Urist McFarmer", cause="goblin pikeman")
        assert e.type == "death"

    def test_mood_event(self):
        e = MoodEvent(unit_id=7, mood_type="fey")
        assert e.type == "mood"

    def test_caravan_event(self):
        e = CaravanEvent(civ="Mountainhomes", goods_value=14000)
        assert e.type == "caravan"

    def test_season_change_event(self):
        e = SeasonChangeEvent(new_season=2, new_year=3)
        assert e.type == "season_change"
        assert e.new_season == 2

    def test_cave_in_event(self):
        e = CaveInEvent(z_level=-5)
        assert e.type == "cave_in"

    def test_mandate_event(self):
        e = MandateEvent(noble="Baron", item_type="silver goods", quantity=3)
        assert e.type == "mandate"

    def test_megabeast_event(self):
        e = MegabeastEvent(creature_type="Bronze Colossus")
        assert e.type == "megabeast"


class TestFastFortressState:
    def test_construction(self):
        state = FastFortressState(
            timestamp=1711234567.0,
            game_tick=120000,
            year=3,
            season=2,
            month=8,
            day=15,
            fortress_name="Boatmurdered",
            paused=False,
            population=47,
            food_count=234,
            drink_count=100,
            active_threats=0,
            job_queue_length=15,
            idle_dwarf_count=3,
            most_stressed_value=5000,
        )
        assert state.fortress_name == "Boatmurdered"
        assert state.population == 47

    def test_with_events(self):
        siege = SiegeEvent(attacker_civ="Goblins", force_size=30)
        state = FastFortressState(
            timestamp=0.0,
            game_tick=0,
            year=0,
            season=0,
            month=0,
            day=0,
            fortress_name="Test",
            paused=False,
            population=10,
            food_count=50,
            drink_count=50,
            active_threats=30,
            job_queue_length=0,
            idle_dwarf_count=0,
            most_stressed_value=0,
            pending_events=(siege,),
        )
        assert len(state.pending_events) == 1
        assert state.pending_events[0].type == "siege"

    def test_frozen(self):
        state = FastFortressState(
            timestamp=0.0,
            game_tick=0,
            year=0,
            season=0,
            month=0,
            day=0,
            fortress_name="Test",
            paused=False,
            population=0,
            food_count=0,
            drink_count=0,
            active_threats=0,
            job_queue_length=0,
            idle_dwarf_count=0,
            most_stressed_value=0,
        )
        with pytest.raises(Exception):
            state.population = 99  # type: ignore[misc]


class TestFullFortressState:
    def test_extends_fast(self):
        """FullFortressState is a valid FastFortressState (Liskov)."""
        full = FullFortressState(
            timestamp=0.0,
            game_tick=0,
            year=1,
            season=0,
            month=0,
            day=0,
            fortress_name="Test",
            paused=False,
            population=20,
            food_count=100,
            drink_count=80,
            active_threats=0,
            job_queue_length=5,
            idle_dwarf_count=2,
            most_stressed_value=1000,
            units=(
                DwarfUnit(
                    id=1,
                    name="Urist",
                    profession="Miner",
                    skills=(DwarfSkill(name="MINING", level=3),),
                    stress=1000,
                    mood="normal",
                    current_job="Mining",
                ),
            ),
            stockpiles=StockpileSummary(food=100, drink=80),
        )
        assert full.population == 20
        assert len(full.units) == 1
        assert full.stockpiles.food == 100

    def test_defaults_empty(self):
        full = FullFortressState(
            timestamp=0.0,
            game_tick=0,
            year=0,
            season=0,
            month=0,
            day=0,
            fortress_name="Test",
            paused=False,
            population=0,
            food_count=0,
            drink_count=0,
            active_threats=0,
            job_queue_length=0,
            idle_dwarf_count=0,
            most_stressed_value=0,
        )
        assert full.units == ()
        assert full.squads == ()
        assert full.stockpiles.food == 0


class TestFortressPosition:
    def test_from_tick_year_zero(self):
        pos = FortressPosition.from_tick(0, population=5)
        assert pos.tick == 0
        assert pos.day == 0
        assert pos.month == 0
        assert pos.season == 0
        assert pos.year == 0
        assert pos.era == "founding"

    def test_from_tick_mid_year(self):
        # Month 6 (7th month) = season 2 (autumn)
        ticks_per_month = 1200 * 28  # 33600
        tick = 6 * ticks_per_month + 10 * 1200  # month 6, day 10
        pos = FortressPosition.from_tick(tick, population=30)
        assert pos.month == 6
        assert pos.day == 10
        assert pos.season == 2
        assert pos.year == 0
        assert pos.era == "growth"

    def test_era_thresholds(self):
        tick = 100000
        assert FortressPosition.from_tick(tick, population=0).era == "founding"
        assert FortressPosition.from_tick(tick, population=19).era == "founding"
        assert FortressPosition.from_tick(tick, population=20).era == "growth"
        assert FortressPosition.from_tick(tick, population=50).era == "establishment"
        assert FortressPosition.from_tick(tick, population=100).era == "prosperity"
        assert FortressPosition.from_tick(tick, population=150).era == "legendary"
        assert FortressPosition.from_tick(tick, population=200).era == "legendary"

    def test_season_range(self):
        """Season is always 0-3."""
        for month in range(12):
            ticks_per_month = 1200 * 28
            pos = FortressPosition.from_tick(month * ticks_per_month)
            assert 0 <= pos.season <= 3

    def test_year_rollover(self):
        ticks_per_year = 1200 * 28 * 12  # 403200
        pos = FortressPosition.from_tick(ticks_per_year * 3 + 1000, population=0)
        assert pos.year == 3


class TestEventDiscriminatedUnion:
    def test_json_roundtrip(self):
        """Events can be serialized and deserialized via discriminated union."""
        state = FastFortressState(
            timestamp=0.0,
            game_tick=0,
            year=0,
            season=0,
            month=0,
            day=0,
            fortress_name="Test",
            paused=False,
            population=0,
            food_count=0,
            drink_count=0,
            active_threats=0,
            job_queue_length=0,
            idle_dwarf_count=0,
            most_stressed_value=0,
            pending_events=(
                SiegeEvent(attacker_civ="Goblins", force_size=20),
                MigrantEvent(count=5),
                DeathEvent(unit_id=1, unit_name="Urist", cause="drowned"),
            ),
        )
        # Round-trip through JSON
        data = state.model_dump()
        restored = FastFortressState.model_validate(data)
        assert len(restored.pending_events) == 3
        assert restored.pending_events[0].type == "siege"
        assert restored.pending_events[1].type == "migrant"
        assert restored.pending_events[2].type == "death"
