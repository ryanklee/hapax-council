# Fortress State Schema — Design Spec

> **Status:** Design (data model specification)
> **Date:** 2026-03-23
> **Scope:** `shared/`, `agents/superpowers/` — structured game state representation for governance chains
> **Builds on:** [DFHack Bridge Protocol](2026-03-13-domain-schema-north-star.md), [Perception Primitives Design](2026-03-11-perception-primitives-design.md)

## Problem

Governance chains require a well-typed, versioned representation of Dwarf Fortress game state. The DFHack bridge protocol exports raw data at two cadences (fast: 120 ticks, full: 1200 ticks). Without a formal schema layer, downstream consumers must parse ad hoc structures, field availability varies silently between cadences, and governance decisions operate on unvalidated input.

## Goal

Define Pydantic models that:

1. Map every field to a documented DFHack Lua API path
2. Enforce strict typing with no `Any` fields
3. Preserve immutability via frozen model configuration (consistent with `Stamped[T]` semantics)
4. Partition fields by governance consumer so each role can declare its minimum required subset

---

## Section 1: Design Principles

### 1.1 Two-Tier State Model

The bridge protocol emits state at two cadences:

| Tier | Cadence | Contents | Use |
|------|---------|----------|-----|
| Fast | Every 120 ticks (~3.4 real seconds at 35 FPS) | Scalar summaries, event buffer | Real-time monitoring, crisis detection |
| Full | Every 1200 ticks (~34 real seconds at 35 FPS) | Complete entity enumerations | Strategic planning, narrative generation |

`FullFortressState` extends `FastFortressState`. Any consumer that accepts `FastFortressState` automatically accepts `FullFortressState` by Liskov substitution.

### 1.2 Strict Typing

All models use `model_config = ConfigDict(frozen=True, strict=True)`. No field may be typed as `Any`, `dict`, or unparameterized `list`. Every collection field carries its element type. Optional fields use explicit `None` unions where absence is semantically meaningful.

### 1.3 Immutability

Frozen models ensure that a state snapshot, once constructed, cannot be mutated by any consumer. This matches the `Stamped[T]` pattern from the perception primitives type system: a stamped value is a fact about a moment in time, and facts do not change.

### 1.4 Source Traceability

Every field documents the DFHack Lua expression from which it is derived (Section 7). This serves two purposes: implementation guidance for the bridge exporter, and auditability for governance decisions that depend on specific field values.

### 1.5 Consumer-Oriented Grouping

Fields are grouped not only by data domain but by governance consumer. Section 5 provides a mapping from each governance role to its required field set.

---

## Section 2: FastFortressState (every 120 ticks)

The fast-cadence model provides scalar summaries sufficient for real-time monitoring and crisis detection. All fields are derivable from O(1) or O(n) scans of DFHack global state.

```python
class FastFortressState(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True)

    # Temporal
    timestamp: float          # Wall-clock time of export (Unix epoch seconds)
    game_tick: int             # Current world tick (df.global.cur_year_tick)
    year: int                  # Fortress year (df.global.cur_year)
    season: int                # Season within year, 0-3 (spring/summer/autumn/winter)
    month: int                 # Month within year, 0-11
    day: int                   # Day within month, 0-27

    # Identity
    fortress_name: str         # Current fortress name

    # Simulation
    paused: bool               # Whether the game is currently paused

    # Population
    population: int            # Count of alive citizens
    idle_dwarf_count: int      # Citizens with no active job assignment
    most_stressed_value: int   # Highest stress score among citizens (higher = worse)

    # Resources
    food_count: int            # Total edible item count across all stockpiles
    drink_count: int           # Total drinkable item count across all stockpiles

    # Labor
    job_queue_length: int      # Total jobs in the fortress job queue

    # Threats
    active_threats: int        # Count of hostile units on the map

    # Events
    pending_events: list[FortressEvent]  # Events accumulated since last export
```

Field semantics:

- `season`: Derived from `game_tick`. Each season spans 100800 ticks. Values: 0 = spring, 1 = summer, 2 = autumn, 3 = winter.
- `month`: Each month spans 33600 ticks. Twelve months per year.
- `day`: Each day spans 1200 ticks. Twenty-eight days per month.
- `most_stressed_value`: The maximum `stress_level` across all citizens. A value above 100000 indicates a dwarf at risk of tantrum. This is a scalar proxy; the full per-unit breakdown is available in `FullFortressState.units`.
- `pending_events`: Accumulated since the previous export. The bridge clears the buffer after each emission. Event ordering reflects game-tick ordering.

---

## Section 3: FullFortressState (every 1200 ticks)

The full-cadence model extends `FastFortressState` with complete entity enumerations. These fields require iteration over entity lists and are therefore more expensive to compute.

```python
class FullFortressState(FastFortressState):
    # Citizens
    units: list[DwarfUnit]

    # Military
    squads: list[MilitarySquad]

    # Resources (detailed)
    stockpiles: StockpileSummary

    # Infrastructure
    workshops: list[Workshop]
    buildings: BuildingSummary

    # Economy
    wealth: WealthSummary

    # Geography
    map_summary: MapSummary

    # Governance (in-game)
    nobles: list[NoblePosition]

    # Anomalies
    strange_moods: list[StrangeMood]
```

### 3.1 DwarfUnit

```python
class DwarfSkill(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True)

    skill: str       # Skill name (e.g., "MINING", "MASONRY")
    level: int       # Skill level (0-20, where 15+ is legendary)

class DwarfUnit(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True)

    id: int
    name: str                        # Full name (first + last)
    profession: str                  # Current displayed profession
    skills: list[DwarfSkill]         # All nonzero skills
    stress: int                      # Stress level (lower is better, negative = happy)
    mood: Literal[
        "normal", "fey", "secretive",
        "possessed", "berserk", "insane",
        "melancholy"
    ]
    current_job: str | None          # Current job description, None if idle
    military_squad_id: int | None    # Squad ID if assigned, None if civilian
```

### 3.2 MilitarySquad

```python
class MilitarySquad(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True)

    id: int
    name: str
    member_ids: list[int]             # Unit IDs of squad members
    equipment_quality: float          # Normalized 0.0-1.0 (average item quality)
    training_level: float             # Normalized 0.0-1.0 (average combat skill)
```

### 3.3 StockpileSummary

```python
class StockpileSummary(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True)

    food: int
    drink: int
    wood: int
    stone: int
    metal_bars: int
    cloth: int
    thread: int
    weapons: int
    armor: int
    ammo: int
    mechanisms: int
    seeds: int
    gems: int
    leather: int
    bones: int
    shells: int
    crafts: int
    furniture: int
```

### 3.4 Workshop

```python
class Workshop(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True)

    type: str                  # Workshop type (e.g., "Craftsdwarf's Workshop")
    position: tuple[int, int, int]  # (x, y, z) map coordinates
    is_active: bool            # Whether the workshop is currently in use
    current_job: str | None    # Job description if active, None otherwise
```

### 3.5 BuildingSummary

```python
class BuildingSummary(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True)

    doors: int
    beds: int
    tables: int
    chairs: int
    statues: int
    armor_stands: int
    weapon_racks: int
    coffins: int
    trade_depot: int           # 0 or 1 (at most one trade depot)
```

### 3.6 WealthSummary

```python
class WealthSummary(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True)

    created: int       # Total value of goods created
    exported: int      # Total value of goods exported via trade
    imported: int      # Total value of goods imported via trade
```

### 3.7 MapSummary

```python
class MapSummary(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True)

    z_levels_explored: int          # Number of z-levels with revealed tiles
    cavern_layers_breached: int     # 0-3, number of cavern layers opened
    has_magma_access: bool          # Whether magma is reachable
    has_water_source: bool          # Whether a water source exists (river/brook/aquifer)
    aquifer_present: bool           # Whether the embark has aquifer layers
```

### 3.8 NoblePosition

```python
class NoblePosition(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True)

    position: str              # Title (e.g., "Mayor", "Baron", "Duke")
    holder_id: int | None      # Unit ID of holder, None if vacant
    demands: list[str]         # Active mandates/demands (human-readable descriptions)
```

### 3.9 StrangeMood

```python
class StrangeMood(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True)

    unit_id: int
    mood_type: Literal["fey", "secretive", "possessed"]
    claimed_workshop: str | None        # Workshop type claimed, None if seeking
    materials_needed: list[str]         # Required material types (e.g., "metal bars", "gems")
```

---

## Section 4: FortressEvent (event buffer)

Events are modeled as a discriminated union using a `type` field. Each event records an occurrence between successive state exports. The bridge accumulates events into the `pending_events` buffer and clears the buffer after each emission.

```python
class FortressEventBase(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True)
    game_tick: int    # Tick at which the event occurred

class SiegeEvent(FortressEventBase):
    type: Literal["siege"] = "siege"
    attacker_civ: str          # Civilization name of the attacking force
    force_size: int            # Estimated number of hostile units

class MigrantEvent(FortressEventBase):
    type: Literal["migrant"] = "migrant"
    count: int                 # Number of migrants arriving

class DeathEvent(FortressEventBase):
    type: Literal["death"] = "death"
    unit_id: int               # ID of the deceased unit
    unit_name: str             # Name of the deceased
    cause: str                 # Cause of death (e.g., "combat", "starvation", "cave-in")

class MoodEvent(FortressEventBase):
    type: Literal["mood"] = "mood"
    unit_id: int
    mood_type: Literal["fey", "secretive", "possessed", "berserk", "insane", "melancholy"]

class CaravanEvent(FortressEventBase):
    type: Literal["caravan"] = "caravan"
    civ: str                   # Civilization name of the trading caravan
    goods_value: int           # Estimated total value of goods brought

class SeasonChangeEvent(FortressEventBase):
    type: Literal["season_change"] = "season_change"
    new_season: int            # 0-3
    new_year: int              # Year after the change

class CaveInEvent(FortressEventBase):
    type: Literal["cave_in"] = "cave_in"
    z_level: int               # Z-level where the collapse occurred

class MandateEvent(FortressEventBase):
    type: Literal["mandate"] = "mandate"
    noble: str                 # Title of the noble issuing the mandate
    item_type: str             # Item type demanded (e.g., "scepters", "crowns")
    quantity: int              # Quantity demanded

class MegabeastEvent(FortressEventBase):
    type: Literal["megabeast"] = "megabeast"
    creature_type: str         # Creature type (e.g., "bronze colossus", "dragon")

FortressEvent = Annotated[
    SiegeEvent | MigrantEvent | DeathEvent | MoodEvent |
    CaravanEvent | SeasonChangeEvent | CaveInEvent |
    MandateEvent | MegabeastEvent,
    Field(discriminator="type"),
]
```

---

## Section 5: Governance Consumer Mapping

Each governance role consumes a defined subset of the fortress state. This mapping serves two purposes: it documents the minimum data contract each role requires, and it guides selective field export when bandwidth or computation is constrained.

| Role | Fast-Tier Fields | Full-Tier Fields |
|------|-----------------|------------------|
| **Fortress Planner** | population, paused | map_summary, buildings, workshops |
| **Military Commander** | active_threats, population | squads, wealth |
| **Resource Manager** | food_count, drink_count, idle_dwarf_count, job_queue_length | stockpiles, workshops |
| **Storyteller** | ALL | ALL |
| **Advisor** | ALL | ALL |
| **Crisis Responder** | most_stressed_value, active_threats, food_count, drink_count, pending_events | strange_moods, units (stress subset) |

Notes:

- The Storyteller and Advisor roles require full context by design. Narrative coherence and strategic reasoning both degrade under partial state.
- The Crisis Responder's full-tier access is limited to anomaly-relevant entities (`strange_moods`, stress-filtered `units`). It does not require `workshops`, `buildings`, or `wealth` under normal conditions.
- The Military Commander requires `wealth` because fortress wealth is the primary trigger for siege frequency and force size in the Dwarf Fortress threat model.

---

## Section 6: FortressPosition (temporal hierarchy)

`FortressPosition` replaces `MusicalPosition` for the Dwarf Fortress domain. It provides the same structural role — a hierarchical temporal coordinate system that maps between domain-specific time units and wall-clock time — but its hierarchy reflects fortress time rather than musical time.

```python
class FortressPosition(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True)

    tick: int        # Current game tick (atomic unit)
    day: int         # Day within month, 0-27
    month: int       # Month within year, 0-11
    season: int      # Season within year, 0-3
    year: int        # Fortress age in years
    era: Literal[
        "founding",       # Population < 20
        "growth",         # Population 20-49
        "establishment",  # Population 50-99
        "prosperity",     # Population 100-149
        "legendary",      # Population 150+
    ]
```

### 6.1 Derivation Rules

All temporal fields except `era` are derivable from `tick` by pure arithmetic:

| Field | Derivation |
|-------|-----------|
| `day` | `(tick % 33600) // 1200` |
| `month` | `(tick % 403200) // 33600` |
| `season` | `(tick % 403200) // 100800` |
| `year` | `tick // 403200` |

These derivations mirror the `MusicalPosition` pattern: the position is a view over a single monotonic counter. Redundant fields exist for consumer convenience, not as independent state.

### 6.2 Era Derivation

`era` breaks the pure-arithmetic pattern. It depends on `population`, which is external to the tick counter. The thresholds are:

| Era | Population Range |
|-----|-----------------|
| `founding` | 0-19 |
| `growth` | 20-49 |
| `establishment` | 50-99 |
| `prosperity` | 100-149 |
| `legendary` | 150+ |

These thresholds are based on standard Dwarf Fortress population milestones (migrant wave triggers, noble arrival thresholds, and economy activation points).

---

## Section 7: DFHack Lua API Mapping

Each field below documents the DFHack Lua expression used by the bridge exporter to populate it. All expressions assume the DFHack Lua scripting environment with `df` and `dfhack` globals available.

### 7.1 Temporal Fields

| Field | Lua Expression |
|-------|---------------|
| `game_tick` | `df.global.cur_year_tick` |
| `year` | `df.global.cur_year` |
| `season` | `df.global.cur_year_tick // 100800` |
| `month` | `df.global.cur_year_tick // 33600` |
| `day` | `(df.global.cur_year_tick % 33600) // 1200` |
| `paused` | `df.global.pause_state` |

### 7.2 Identity

| Field | Lua Expression |
|-------|---------------|
| `fortress_name` | `dfhack.TranslateName(df.global.world.world_data.active_site[0].name)` |

### 7.3 Population and Labor

| Field | Lua Expression |
|-------|---------------|
| `population` | `#dfhack.units.getCitizens()` |
| `idle_dwarf_count` | Iterate `dfhack.units.getCitizens()`, count where `dfhack.units.getNoblePositions(u)` is nil and `u.job.current_job` is nil |
| `most_stressed_value` | `math.max` over `dfhack.units.getCitizens()` mapping `u.status.current_soul.personality.stress_level` |
| `job_queue_length` | `#df.global.world.jobs.list` (traverse linked list) |

### 7.4 Resources

| Field | Lua Expression |
|-------|---------------|
| `food_count` | Iterate `df.global.world.items.other.ANY_COOKABLE`, count where `dfhack.items.getGeneralRef(item, df.general_ref_type.CONTAINED_IN_ITEM)` resolves to a food stockpile or is loose |
| `drink_count` | Iterate `df.global.world.items.other.DRINK`, count non-forbidden |

### 7.5 Threats

| Field | Lua Expression |
|-------|---------------|
| `active_threats` | Iterate `df.global.world.units.active`, filter where `dfhack.units.isActive(u)` and `dfhack.units.isDanger(u)` |

### 7.6 Units (Full State)

| Field | Lua Expression |
|-------|---------------|
| `units[].id` | `u.id` |
| `units[].name` | `dfhack.TranslateName(dfhack.units.getVisibleName(u))` |
| `units[].profession` | `dfhack.units.getProfessionName(u)` |
| `units[].skills` | Iterate `u.status.current_soul.skills`, map `{skill=df.job_skill[s.id], level=s.rating}` |
| `units[].stress` | `u.status.current_soul.personality.stress_level` |
| `units[].mood` | Map `u.mood` enum to string literal |
| `units[].current_job` | `dfhack.job.getName(u.job.current_job)` if non-nil |
| `units[].military_squad_id` | `u.military.squad_id` if not -1 |

### 7.7 Military

| Field | Lua Expression |
|-------|---------------|
| `squads[].id` | `squad.id` from `df.global.world.squads.all` |
| `squads[].name` | `dfhack.TranslateName(squad.name)` |
| `squads[].member_ids` | `squad.positions[*].occupant` where non -1 |

### 7.8 Stockpiles

Stockpile counts are derived by iterating item vectors under `df.global.world.items.other` with the corresponding item type enums. Each category maps to one or more `df.item_type` values.

### 7.9 Map and Buildings

| Field | Lua Expression |
|-------|---------------|
| `map_summary.has_magma_access` | Scan `df.global.world.map.map_blocks` for tiles with `magma_level > 0` within fortress bounds |
| `map_summary.cavern_layers_breached` | Count unique `cavern_layer` values among revealed underground regions |
| `wealth.created` | `df.global.world.status.wealth_created` (or fortress entity wealth fields) |
| `buildings` | Iterate `df.global.world.buildings.all`, group by `getType()`, count |

---

## Open Questions

1. **Event deduplication.** If the bridge emits at both cadences and an event falls within a fast-cadence window that is also captured by a full-cadence export, should the event appear in both? Current design: events appear only in the first export after they occur, regardless of cadence.

2. **Stockpile granularity.** The current `StockpileSummary` uses flat integer counts. Some governance decisions (e.g., "do we have enough steel for a full squad refit?") require material-specific breakdowns. A future revision may introduce nested material maps.

3. **Era hysteresis.** Population can oscillate around thresholds (e.g., deaths dropping from 20 to 19 and back). The current design does not apply hysteresis. If era flickering causes downstream instability, a dead-band or minimum-duration constraint should be added.
