# Dwarf Fortress AI: Game State Fields for Strategic Decision-Making

Research into what game state a strategic DF AI needs, organized by access frequency,
with DFHack access methods and role assignments.

## Access Methods Overview

Two primary interfaces exist for accessing DF game state:

1. **DFHack Lua API** -- Direct memory access via `df.global.*` paths and helper modules
   (`dfhack.units`, `dfhack.items`, `dfhack.maps`, `dfhack.buildings`, `dfhack.military`).
   Runs in-process. Full read/write.

2. **RemoteFortressReader (RFR)** -- Protobuf RPC over TCP (default `127.0.0.1:5000`).
   39 methods. Read-heavy with some command methods. Out-of-process safe.

3. **Eventful plugin** -- Lua callback hooks for 16 event types (TICK, UNIT_DEATH,
   INVASION, JOB_COMPLETED, ITEM_CREATED, BUILDING, SYNDROME, REPORT, etc.).

Roles referenced below:
- **P** = Planner (construction, room layout, long-term fortress design)
- **M** = Military (squads, threats, defense)
- **R** = Resource (stocks, food, drink, materials, labor)
- **C** = Crisis (immediate threats to fortress survival)

---

## 1. Critical (Every Tick / Every Game Day)

Fields that must be polled constantly or hooked via eventful to prevent cascade failures.

| Field | DFHack Access | Type | Range / Notes | Roles |
|-------|--------------|------|---------------|-------|
| Active unit list | `df.global.world.units.active` | vector<unit> | All non-dead on-map units | C, M |
| Unit alive/dead status | `dfhack.units.isAlive(unit)`, `isDead()`, `isKilled()` | bool | Per unit | C |
| Unit stress level | `dfhack.units.getStressCategory(unit)` | int | 0 (ecstatic) to 6 (completely broken). Thresholds via `getStressCutoffs()`. Raw stress at `unit.status.current_soul.personality.stress` (normal 0-500k, negative=very stable, >500k=danger) | C, R |
| Unit sanity | `dfhack.units.isSane(unit)`, `isCrazed(unit)` | bool | Crazed = berserk, about to kill | C |
| Hostile units on map | `dfhack.units.isDanger(unit)`, `isGreatDanger(unit)`, `isInvader(unit)` | bool | Per unit. `isGreatDanger` = megabeast/titan | C, M |
| Food count | `df.global.world.items.all` filtered by food types | int | Minimum ~50 meals per 7 dwarves. df-ai targets 100/dwarf | R, C |
| Drink count | `df.global.world.items.all` filtered by drink types | int | Minimum ~30 drinks per 7 dwarves. df-ai targets 200/dwarf. No booze = tantrum spiral trigger | R, C |
| Current jobs | `df.global.job_list` | linked list | Suspended jobs need clearing. `dfhack.job.getWorker(job)` for assignment | R |
| Game tick | `df.global.world.frame_counter` | int | Monotonic. 1200 ticks/day, 403200 ticks/year | all |
| Current year/tick | `df.global.cur_year`, `df.global.cur_year_tick` | int | Calendar position | all |
| Water/magma levels | `Maps::getTileBlock(pos).designation[x][y].flow_size` | int | 0-7 per tile. >0 = flooding risk | C, P |
| Pause state | RFR: `get_pause_state()` / `set_pause_state()` | bool | AI needs to manage pause for events | all |

### Eventful hooks for critical events (zero-latency):

| Event | Hook | Callback Data | Roles |
|-------|------|---------------|-------|
| Unit death | `UNIT_DEATH` | unit_id | C, M |
| Invasion begins | `INVASION` | (none -- poll units for invaders) | C, M |
| Report/announcement | `REPORT` | report_id (siege, caravan, mood, etc.) | C |
| Syndrome applied | `SYNDROME` | unit_id, syndrome_id | C |
| Unit attack | `UNIT_ATTACK` | attacker_id, defender_id | M |

---

## 2. Important (Every Season -- ~100,800 ticks)

Checked quarterly. Drives medium-term resource and workforce planning.

| Field | DFHack Access | Type | Range / Notes | Roles |
|-------|--------------|------|---------------|-------|
| Citizen list | `dfhack.units.getCitizens()` | vector<unit> | Living, sane citizens only | R, P |
| Population count | `#dfhack.units.getCitizens()` | int | Triggers nobles at thresholds, sieges at 80+ | R, P |
| Skill levels per dwarf | `dfhack.units.getEffectiveSkill(unit, skill)` | int | 0-20+. Accounts for rust. Critical for labor assignment | R |
| Noble positions | `dfhack.units.getNoblePositions(unit)` | table | Mayor, baron, etc. Mandates come from nobles | R, C |
| Squad composition | `dfhack.military.getSquadName(id)` | string | df-ai: 25-75% of population in military | M |
| Squad membership | `dfhack.military.addToSquad/removeFromSquad` | -- | Rebalance per population changes | M |
| Stockpile item counts | Iterate `df.global.world.items.all`, classify by type | int per category | df-ai tracks 80+ categories: ammo, armor, clothing, furniture, tools, blocks, mechanisms, etc. | R |
| Workshop status | `dfhack.buildings.findAtTile(pos)` or iterate buildings | building obj | Idle workshops = wasted labor | R, P |
| Happiness distribution | `dfhack.units.getStressCategory(unit)` over all citizens | histogram | If median > 3, approaching tantrum spiral | C, R |
| Unit health/wounds | `unit.body.wounds` | vector | Count wounded, track recovery. `unit.health` for medical needs | C, R |
| Medical operations needed | `unit.health.op_history` | vector | Surgery, sutures, casts, diagnosis queued | R |
| Strange mood status | `unit.mood` field | enum | Mood types: fey, secretive, possessed, macabre, fell. Need materials or dwarf goes insane | C, R |
| Mandate tracking | Noble mandates via `df.global.plotinfo` | struct | ~6 months to fulfill. Failure = punishment + unhappy thoughts | R, C |
| Babies/children count | `dfhack.units.isBaby(unit)`, `isChild(unit)` | bool | Future labor force. Children can't work | R |
| Animal populations | `dfhack.units.isAnimal(unit)`, `isTame(unit)` | bool | Livestock for food, war animals for defense | R, M |
| Trade depot status | Buildings of type trade depot | building obj | Required for caravan interaction | R |

---

## 3. Strategic (Every Year -- ~403,200 ticks)

Long-term fortress trajectory. Influences macro decisions about expansion, defense investment,
and resource extraction priorities.

| Field | DFHack Access | Type | Range / Notes | Roles |
|-------|--------------|------|---------------|-------|
| Created wealth | `df.global.plotinfo.tasks.wealth.total` (approximate path) | int | Triggers: forgotten beast at 50k, megabeast at 100k, baron/count/duke at wealth thresholds | P, M |
| Exported wealth | `df.global.plotinfo.tasks.wealth.exported` (approximate path) | int | Megabeast trigger at 10k exported | M, R |
| Cavern discovery status | `df.global.world.features.map_features[n].flags.Discovered` | bool | Per cavern layer (typically 3). Discovery triggers forgotten beasts and unlocks underground resources | P, M |
| Magma access | Map scan for magma tiles or magma sea z-level | bool + z-level | Magma sea typically around z=-120. Magma forges = free fuel | P |
| Ore deposit map | Block events of type `block_square_event_mineralst` | material per vein | Iron, copper, tin, gold, adamantine locations. `locate-ore` script pattern | P, R |
| Military equipment quality | Item quality flags on weapons/armor | enum | 0-5 (ordinary to masterwork). Steel > iron > copper | M |
| Room satisfaction | Noble room requirements vs current assignments | comparison | Nobles demand quality rooms. Unmet = unhappy thoughts | P, R |
| Technology progression | Available reactions/workshops | set | Smelting, steel-making, glass, pottery unlocked by materials | P, R |
| Adamantine discovery | Specific ore vein detection | bool | Endgame material. Breaching too deep = hidden fun stuff (demons) | P, M, C |
| Trade balance | Caravan interaction history | ledger | What you can get vs what you can export | R |
| Population capacity | Bedroom count, food production rate | int | Can the fortress sustain more migrants? | P, R |

---

## 4. Event-Driven (Immediate Response Required)

Game events that demand dropping everything and responding. Detected via eventful hooks
or report scanning.

| Event | Detection Method | Required Response | State Needed | Roles |
|-------|-----------------|-------------------|-------------|-------|
| **Siege** | `INVASION` event + scan for `isInvader(unit)` | Raise drawbridge, activate military, recall civilians | Invader count, type, position. Military readiness. Bridge/trap status | C, M |
| **Caravan arrival** | `REPORT` announcement scan | Prepare trade goods, haul to depot | Depot exists, goods marked for trade, broker skill | R |
| **Migrant wave** | New citizens appearing (poll `getCitizens()` delta) | Assign bedrooms, labors, equipment | Available rooms, skill gaps, clothing/equipment stock | R, P |
| **Strange mood** | `unit.mood` changes from -1 | Ensure workshop available, materials accessible | Mooded dwarf's highest skill (determines workshop), material preferences (shells, cloth, bones, gems, metal, wood, stone) | R, C |
| **Cave-in** | `REPORT` announcement | Assess damage, rescue wounded, rebuild | Structural integrity, wounded list, blocked paths | C, P |
| **Forgotten beast** | `REPORT` + `isForgottenBeast(unit)` | Seal cavern, deploy military or trap | Beast position, abilities (fire, web, syndrome), cavern access points | C, M |
| **Megabeast/Titan** | `isGreatDanger(unit)`, `isMegabeast()`, `isTitan()` | Full military mobilization | Beast combat stats, military strength, trap inventory | C, M |
| **Noble mandate** | Mandate data in plotinfo | Queue production orders | What item is demanded, current stock, production capability | R |
| **Dwarf goes insane** | `dfhack.units.isCrazed(unit)` | Isolate berserk dwarf, contain damage | Berserk dwarf position, nearby civilians, available cage traps | C |
| **Flooding** | Tile flow_size increasing in fortress area | Seal breaches, evacuate levels | Water source, flow direction, available floodgates/doors | C, P |
| **Mood failure** | Dwarf goes insane after failed mood | Contain, prevent spiral | Insane dwarf type (berserk vs melancholy vs catatonic) | C |

---

## 5. Spatial (Map-Level Information)

Static or slowly-changing map data. Queried at embark and when new areas are revealed.

| Field | DFHack Access | Type | Notes | Roles |
|-------|--------------|------|-------|-------|
| Map dimensions | `dfhack.maps.getSize()` (blocks), `getTileSize()` (tiles) | int x3 | Typically 4x4 embark = 192x192 tiles, 200+ z-levels | P |
| Tile types | `Maps::getTileType(pos)` + `ENUM_ATTR(tiletype, ...)` | enum | Wall, floor, ramp, stair, etc. Shape + material | P |
| Tile walkability | `Maps::getTileWalkable(pos)` | bool | Pathfinding validation | P, M |
| Hidden/revealed tiles | `Maps::isTileVisible(pos)` or block designation hidden flag | bool | Unrevealed = unexplored territory | P |
| Water sources | Scan for river tiles, murky pools, aquifer layers | tile positions | River = infinite water. Aquifer = nuisance or resource. Light aquifer (19/20) vs heavy (1/20) | P |
| Aquifer presence | Block designation `aquifer_light` / `aquifer_heavy` | bool | Heavy aquifer blocks digging without engineering. Light = manageable | P |
| Cavern layers | `df.global.world.features.map_features` | feature list | Typically 3 layers. Each has underground trees, creatures, water. Discovery = forgotten beast risk | P, M |
| Magma sea z-level | Scan for magma tiles at deep z-levels | z-coordinate | Typically z ~ -120. Magma tubes may extend higher | P |
| Surface features | River, brook, pool, ocean biome at surface z-levels | tile classification | Fresh water critical. Ocean = salt water aquifer | P |
| Ore vein locations | `map_block.block_events` of type `block_square_event_mineralst` | material + position | Iron ore, flux stone, fuel (coal/lignite) locations. Only discovered veins by default | P, R |
| Soil vs stone boundary | Tile material type transition | z-level | Soil = easy digging, farms. Stone = mining, industry | P |
| Constructed buildings | `df.global.world.buildings.all` | vector<building> | Workshops, walls, bridges, traps, stockpiles | P |
| Traffic designations | Tile designation flags | enum | High/normal/low/restricted traffic for pathfinding optimization | P |
| Burrow definitions | `df.global.plotinfo.burrows` | burrow list | Civilian alert zones, restricted areas | M, C |

---

## Top 5 Causes of Fortress Death and Monitoring State

### 1. Tantrum Spiral (cascading mental breakdowns)

The single most common fortress killer. One unhappy dwarf snaps, injures or kills another,
their family and friends become unhappy, more snap, positive feedback loop destroys the fortress.

**Monitoring state:**
- `dfhack.units.getStressCategory(unit)` for ALL citizens every season
- Track stress distribution: if >25% of citizens at category 4+ or any at 6, emergency
- `unit.status.current_soul.personality.stress` raw value (>250,000 = warning, >500,000 = critical)
- Needs satisfaction: alcohol availability, dining room quality, bedroom assignments, social activities
- Death count (each death cascades unhappiness to friends/family)
- `dfhack.units.isCrazed(unit)` -- berserk dwarves must be isolated immediately

**Prevention state:** Drink count > 200/dwarf, all citizens have bedrooms, dining room exists with quality furniture, temple and tavern operational, low corpse exposure.

### 2. Starvation / Dehydration

No food or (critically) no alcohol. Dwarves can drink water but it makes them miserable,
accelerating tantrum spiral.

**Monitoring state:**
- Food item count (meals + raw edible items)
- Drink item count (booze specifically)
- Farm plot status: are farms planted? Growing season active?
- Still/kitchen workshop: are they operational? Are brewing jobs queued?
- Seed stock: can you plant next season?
- Barrel/pot availability (brewing requires empty containers)

**Prevention state:** Food > 100/dwarf, drinks > 200/dwarf, multiple crop types planted across seasons, still always has pending brew jobs, seed stock > 20 per plantable species.

### 3. Military Defeat (siege, megabeast, forgotten beast)

Fortress overrun by enemies. Either no military, or military too weak, or defenses breached.

**Monitoring state:**
- `dfhack.units.isInvader(unit)` count and positions
- `dfhack.units.isGreatDanger(unit)` -- megabeast/titan presence
- Military squad size vs threat (df-ai: 25-75% of population)
- Weapon and armor quality/material (steel >> iron >> copper >> wood)
- Trap count and placement at choke points
- Bridge/drawbridge operational status (can you seal the entrance?)
- Created wealth (triggers: 50k=forgotten beast, 100k=megabeast)
- Population (trigger: 80+ = goblin sieges)

**Prevention state:** At least one trained squad, entrance bottleneck with traps, functional drawbridge, created wealth awareness for threat anticipation.

### 4. Flooding (water or magma)

Breaching an aquifer, river, or cavern lake without preparation. Magma flooding from
careless mining near magma sea. Sourced water floods are nearly irrecoverable.

**Monitoring state:**
- `flow_size` on tiles near active digging operations
- Aquifer layer positions (mapped at embark)
- Proximity of digging designations to known water/magma sources
- Floodgate and drain availability
- Pump stack operational status

**Prevention state:** Never channel/mine adjacent to unknown tiles without checking. Map aquifer boundaries. Have floodgates on every water-adjacent passage. Magma operations only with tested containment.

### 5. Strange Mood Failure / Insanity Chain

Dwarf claims workshop, can't find materials, goes insane. Berserk insanity = killing spree.
Dead dwarves trigger unhappiness cascade (see #1).

**Monitoring state:**
- `unit.mood` field for all citizens (changes from -1 when mood strikes)
- Mooded dwarf's highest moodable skill (determines which workshop needed)
- Available materials: bones, shells, cloth, gems, metal bars, wood, stone
- Workshop availability (mooded dwarf needs to claim one)
- Current artifact count (more artifacts = more material demands per mood)

**Prevention state:** Keep diverse material stocks (bones from butchery, gems from mining, cloth from weaving, metal bars from smelting). Never have zero of any material category. Ensure at least one of each workshop type exists.

---

## Minimal Viable State (Fortress That Doesn't Die Immediately)

The absolute minimum state an AI must track from tick one:

```
minimal_state = {
    # Population
    citizen_count: int,          # dfhack.units.getCitizens()
    max_stress: int,             # max(getStressCategory(u) for u in citizens)

    # Subsistence
    food_count: int,             # items of type FOOD
    drink_count: int,            # items of type DRINK
    has_farm: bool,              # at least one farm plot exists and is planted
    has_still: bool,             # at least one still exists

    # Security
    hostile_count: int,          # count of isDanger(unit) on map
    has_entrance_seal: bool,     # drawbridge or lockable door at entrance
    military_count: int,         # citizens assigned to squads

    # Infrastructure
    bedroom_count: int,          # assigned bedrooms vs citizen count
    picks_available: int,        # can't mine without picks
    axes_available: int,         # can't chop wood without axes

    # Spatial
    water_source_known: bool,    # river, pool, or well accessible
    cavern_breached: bool,       # underground threat vector open
}
```

This set of ~15 fields, polled every game day (~1200 ticks), would prevent the most common
fortress deaths. Everything else is optimization.

---

## DFHack Module Summary for AI Integration

| Module | Key Functions | Primary Use |
|--------|-------------|-------------|
| `dfhack.units` | `getCitizens()`, `getStressCategory()`, `isCrazed()`, `isDanger()`, `isGreatDanger()`, `isMegabeast()`, `isForgottenBeast()`, `isInvader()`, `getEffectiveSkill()`, `getNoblePositions()`, `isSane()`, `isAlive()` | Unit assessment |
| `dfhack.items` | `getValue()`, `getDescription()`, `canTrade()`, `canMelt()`, `getPosition()` | Resource valuation |
| `dfhack.maps` | `getSize()`, `getTileBlock()`, `isTileVisible()`, `getTileType()` | Spatial awareness |
| `dfhack.buildings` | `findAtTile()` | Infrastructure tracking |
| `dfhack.military` | `makeSquad()`, `addToSquad()`, `removeFromSquad()` | Defense management |
| `dfhack.job` | `listNewlyCreated()`, `getWorker()`, `removeJob()`, `checkBuildingsNow()` | Labor management |
| `eventful` | TICK, UNIT_DEATH, INVASION, REPORT, SYNDROME, JOB_COMPLETED, ITEM_CREATED | Reactive triggers |
| RFR (protobuf) | `get_unit_list()`, `get_block_list()`, `get_map_info()`, `get_building_def_list()`, `send_dig_command()` | Out-of-process access |

---

## df-ai Reference Architecture

BenLubar's df-ai (the most complete DF AI to date) splits into these modules:

| Module | Responsibility | Key State Accessed |
|--------|---------------|-------------------|
| `stocks.cpp` | Track 80+ item categories, order production when below thresholds | Item counts (free/total), per-dwarf scaling (ammo 250/dwarf, drinks 200/dwarf, meals 100/dwarf) |
| `population.cpp` | Citizen management, military drafting, bedroom assignment, medical tracking, labor assignment | Unit list, skills, wounds, syndromes, squad composition, noble positions, job queue |
| `plan.cpp` | Room layout, building placement, mining designations, vertical fortress design | Tile types, walkability, vein locations, z-level organization, building positions |
| `plan_priorities.cpp` | Priority queue for what to build next | Room status, stockpile levels, workshop availability |
| `stocks_forge.cpp` | Metal industry management | Ore counts, bar counts, fuel availability, forge status |
| `stocks_detect.cpp` | Item classification and counting | Item type/subtype/material enumeration |
| `population_justice.cpp` | Crime and punishment handling | Justice system state, noble demands |
| `population_occupations.cpp` | Tavern/temple/library worker assignment | Occupation slots, visitor/resident management |

---

## Sources

- [BenLubar/df-ai (GitHub)](https://github.com/BenLubar/df-ai)
- [jjyg/df-ai (original Ruby version)](https://github.com/jjyg/df-ai)
- [DFHack Lua API Reference](https://docs.dfhack.org/en/latest/docs/dev/Lua%20API.html)
- [DFHack df-structures](https://github.com/DFHack/df-structures)
- [DFHack eventful plugin](https://docs.dfhack.org/en/latest/docs/tools/eventful.html)
- [DFHack RemoteFortressReader](https://github.com/DFHack/dfhack/tree/master/plugins/remotefortressreader)
- [dfhack-remote (Rust client, full RFR method list)](https://docs.rs/dfhack-remote/latest/dfhack_remote/struct.RemoteFortressReader.html)
- [Dwarf Fortress Wiki: Losing](https://dwarffortresswiki.org/index.php/Losing)
- [Dwarf Fortress Wiki: Strange mood](https://dwarffortresswiki.org/index.php/Strange_mood)
- [Dwarf Fortress Wiki: Noble](https://dwarffortresswiki.org/index.php/Noble)
- [Dwarf Fortress Wiki: Forgotten beast](https://dwarffortresswiki.org/index.php/Forgotten_beast)
- [Dwarf Fortress Wiki: Megabeast](https://dwarffortresswiki.org/index.php/Megabeast)
- [Dwarf Fortress Wiki: Aquifer](https://dwarffortresswiki.org/index.php/Aquifer)
- [Dwarf Fortress Wiki: Cavern](https://dwarffortresswiki.org/index.php/Cavern)
- [Dwarf Fortress Wiki: Magma sea](https://dwarffortresswiki.org/index.php/Magma_sea)
- [Dwarf Fortress Wiki: Quickstart guide](https://dwarffortresswiki.org/Quickstart_guide)
- [Dwarf Fortress Wiki: Food guide](https://dwarffortresswiki.org/index.php/Food_guide)
- [Dwarf Fortress Wiki: Mental breakdown](https://dwarffortresswiki.org/index.php/Mental_breakdown)
- [Dwarf Fortress Wiki: Announcement](https://dwarffortresswiki.org/index.php/Announcement)
- [Dwarf Fortress Wiki: Mandate](https://dwarffortresswiki.org/index.php/Mandate)
- [Teaching an AI to Play Dwarf Fortress (DEV Community)](https://dev.to/rpmiller/teaching-an-ai-to-play-dwarf-fortress-the-idea-2o6i)
