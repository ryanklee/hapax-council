# Blueprint Library Specification

**Status:** Design (spatial planning specification)
**Date:** 2026-03-23
**Builds on:** DFHack Bridge Protocol, Fortress State Schema

---

## 1. Design Principles

Large language models cannot reason reliably about 2D tile grids (Miller 2026, Long 2026). Spatial planning for fortress construction must therefore be deterministic: precomputed templates with validated geometry, parameterized only along dimensions that do not affect structural correctness.

The following constraints govern the blueprint system:

- Blueprints use quickfort CSV format, which is trivially generated from Python string operations.
- Templates are parameterized by population, industry focus, and terrain constraints.
- Each structure requires four phases: dig, build, place, query (per quickfort convention).
- Templates compose into full fortress layouts via `#meta` orchestration blueprints.
- The LLM's role is restricted to three decisions: SELECT which template, WHERE to place it, WHEN to build it. The LLM does not determine HOW to lay out tiles within a template.

## 2. Template Registry

A Python module at `agents/fortress/blueprints.py` implements the registry.

### 2.1 `BlueprintTemplate` Dataclass

| Field | Type | Description |
|---|---|---|
| `name` | `str` | Unique template identifier |
| `category` | `str` | Grouping key (e.g., `housing`, `industry`, `defense`) |
| `parameters` | `dict[str, Any]` | Parameter names with default values |
| `phases` | `dict[str, Callable[..., str]]` | Phase name to CSV generator function |
| `z_levels` | `int` | Number of z-levels the template spans |
| `footprint` | `tuple[int, int]` | Width and height in tiles |

### 2.2 `BlueprintRegistry` Class

- `register(template: BlueprintTemplate) -> None` -- Add a template to the registry.
- `query(category: str) -> list[BlueprintTemplate]` -- Retrieve all templates in a category.
- `generate(name: str, **params) -> dict[str, str]` -- Produce phase-keyed CSV strings for a template with the given parameters.

Templates return quickfort CSV strings, not files. The CSV payload is passed to DFHack via the command protocol defined in the bridge specification.

## 3. Core Templates

The following templates constitute the minimum viable fortress.

### 3.1 `central_stairwell(depth, width=3)`

Vertical spine of the fortress connecting all z-levels.

- `width=3`: 9 up/down stairs per level in a 3x3 grid.
- `width=5`: spiral staircase with center void for line-of-sight.
- Generates `#dig` phase with `#>` separators between z-levels.
- `depth` specifies the number of z-levels to excavate.

### 3.2 `bedroom_block(n_rooms, quality="comfortable")`

Residential block with central corridor and rooms on both sides.

Quality tiers determine inner room dimensions:

| Quality | Inner Dimensions | Furnishing |
|---|---|---|
| `basic` | 2x2 | Bed, cabinet |
| `comfortable` | 3x3 | Bed, cabinet, chest, table, chair |
| `noble` | 5x5 | Full noble suite with smoothed walls |

Each room receives a door in the build phase. The template occupies a single z-level; vertical stacking is achieved via `#meta repeat()` directives.

### 3.3 `dining_hall(capacity)`

Common eating and meeting area.

- Width/height: `max(5, ceil(sqrt(capacity)) * 2 + 1)` -- always odd to permit centering.
- Interior filled with table+chair pairs in a regular grid.
- Meeting zone designated in the query phase.

### 3.4 `workshop_pocket(workshop_type)`

Self-contained workshop with integrated stockpile.

- Footprint: 7x7. The 3x3 workshop is centered; the surrounding ring is allocated to stockpiles.
- Stockpile category is auto-selected per workshop type:

| Workshop | Stockpile Categories |
|---|---|
| `forge` | bars, weapons, armor |
| `still` | food |
| `mason` | stone, furniture |
| `craftsdwarf` | finished goods, stone |
| `loom` | cloth, thread |
| `clothier` | cloth |
| `butcher` | food (refuse) |
| `kitchen` | food |
| `farmer` | seeds, plants |
| `smelter` | ore, bars |
| `furnace` | fuel, bars |
| `mechanic` | mechanisms, stone |

### 3.5 `workshop_cluster(industry)`

Grouped arrangement of `workshop_pocket` instances organized by production chain.

| Industry | Constituent Workshops |
|---|---|
| `military` | smelter, forge, furnace, craftsdwarf |
| `food` | still, kitchen, butcher, farmer |
| `textile` | farmer, loom, clothier |
| `stone` | mason, mechanic, craftsdwarf |

Workshops are arranged in a 2x2 grid with shared corridors. The cluster generates a single `#meta` blueprint that invokes each pocket at the correct offset.

### 3.6 `farm_block(n_plots=4, size=3)`

Underground farm plots for year-round food production.

- Default crop plan: plump helmets in all seasons (approximately 2700 units of brewable material per year per 3x3 plot).
- Irrigation channels included if the terrain requires muddy ground for underground farming.
- Plots are arranged in a row with 1-tile gaps for designation boundaries.

### 3.7 `entrance_defense(style="killbox")`

Surface-level fortification controlling ingress.

- Retractable drawbridge spanning a channel.
- 1-wide trap corridor behind the bridge, lined with cage traps.
- Lever linkage for the bridge is documented in the query phase notes.
- The `style` parameter is reserved for future defense variants (e.g., `"archer_tower"`, `"airlock"`).

### 3.8 `stockpile_hub(categories)`

Grid of named, categorized stockpiles.

- `categories` is a list of stockpile category strings corresponding to fields in the `StockpileSummary` schema.
- Each stockpile is 5x5 with 1-tile corridors between them.
- Designation names are assigned in the query phase for fortress-state tracking.

### 3.9 `cistern_well(source="aquifer")`

Sealed water supply with controlled flow.

- Sealed room with a channel from the specified water source.
- Floodgate and lever for fill/drain control.
- Well constructed above the cistern for dwarf access.
- The `source` parameter selects the water acquisition method: `"aquifer"` (tap directly), `"river"` (channel from surface), `"cavern"` (channel from cavern water).

## 4. Fortress Plan Templates

### 4.1 `starter_fortress()`

Complete fortress layout following the Dreamfort z-level allocation pattern.

| Z-Level | Function |
|---|---|
| Surface | Trade depot, pasture, entrance |
| -1 | Entrance defense |
| -2 | Workshops |
| -3 | Stockpiles |
| -4 | Dining hall, kitchen, brewery |
| -5 to -7 | Bedrooms (3 floors) |
| -8 | Hospital, jail, noble quarters |
| -9 | Temple, library, tavern |
| -10+ | Cistern, deep mining access |

The template generates a complete `#meta` blueprint that orchestrates all sub-templates at their designated z-offsets. Parameters:

- `target_population` (default: 50) -- scales bedroom floor count, farm plot count, and stockpile dimensions.

Population scaling rules:

| Population Range | Bedroom Floors | Farm Plots | Stockpile Scale |
|---|---|---|---|
| 1-30 | 2 | 4 | 1x |
| 31-80 | 3 | 8 | 2x |
| 81-150 | 5 | 12 | 3x |
| 151+ | 7 | 16 | 4x |

## 5. CSV Generation API

```python
def generate_blueprint(template_name: str, **params) -> str:
    """Return a quickfort CSV string for the given template and parameters.

    Args:
        template_name: Registered template identifier.
        **params: Template-specific parameters. Missing parameters
                  use the template's declared defaults.

    Returns:
        Quickfort-compatible CSV string covering all phases,
        separated by phase headers.

    Raises:
        KeyError: If template_name is not registered.
        ValueError: If parameters are out of valid range.
    """

def generate_fortress_plan(target_population: int = 50) -> list[tuple[str, str]]:
    """Return an ordered list of (phase_name, csv_string) pairs
    for a complete fortress.

    Phases are ordered for sequential execution: all dig phases first,
    then build, then place, then query. Within each phase type,
    ordering follows z-level (surface first, deepest last).

    Args:
        target_population: Target number of dwarves. Scales
                           bedroom floors, farm plots, and stockpile sizes.

    Returns:
        List of (phase_name, csv_string) tuples in execution order.
    """
```

## 6. Governance Integration

The blueprint library integrates with the council governance system as follows:

- The Fortress Planner role selects templates based on the current `FortressState` (population, industry needs, threat level).
- The Planner produces `dig`, `build`, `place`, and `query` Commands with the blueprint CSV as the command payload.
- Commands are transmitted to DFHack via the bridge protocol.
- VetoChain predicates enforce safety constraints:
  - Reject dig commands that would breach an aquifer (validated against `map_summary.aquifer_layers`).
  - Reject build commands when required materials are not available (validated against `stockpiles`).
- FallbackChain provides degraded alternatives: if the primary template does not fit the available terrain, the system selects a smaller variant of the same template category.

## 7. Extensibility

- New templates are registered via `BlueprintRegistry.register()` at module load time.
- Templates may compose other templates. For example, `workshop_cluster` invokes `workshop_pocket` for each constituent workshop.
- Existing community blueprints in quickfort CSV format can be imported and wrapped as `BlueprintTemplate` instances with fixed parameters.
- The LLM may propose new template designs by describing room layout in natural language. Such proposals require human review before addition to the registry. Automated template generation from LLM output is explicitly excluded from this specification.
