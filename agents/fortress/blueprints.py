"""Blueprint library — parameterized quickfort CSV generation.

LLMs cannot reason about 2D tile grids (Miller 2026, Long 2026).
Spatial planning is deterministic via templates. The LLM selects
WHICH template, WHERE to place it, WHEN to build it — not HOW.

See docs/superpowers/specs/2026-03-23-blueprint-library-spec.md.
"""

from __future__ import annotations

import csv
import io
import math
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class BlueprintPhase:
    """A single phase of a blueprint (dig, build, place, or query)."""

    mode: str  # "#dig", "#build", "#place", "#query"
    label: str
    rows: tuple[tuple[str, ...], ...]  # 2D grid of designation codes


@dataclass(frozen=True)
class BlueprintTemplate:
    """A parameterized blueprint template."""

    name: str
    category: str  # "residential", "industrial", "defense", "infrastructure", "agriculture"
    description: str
    parameters: dict[str, Any] = field(default_factory=dict)

    def generate(self, **params: Any) -> list[BlueprintPhase]:
        """Override in subclasses or use registry functions."""
        raise NotImplementedError


class BlueprintRegistry:
    """Registry of blueprint templates."""

    def __init__(self) -> None:
        self._templates: dict[str, tuple[str, Callable[..., list[BlueprintPhase]]]] = {}

    def register(self, name: str, category: str, fn: Callable[..., list[BlueprintPhase]]) -> None:
        self._templates[name] = (category, fn)

    def generate(self, name: str, **params: Any) -> list[BlueprintPhase]:
        if name not in self._templates:
            raise ValueError(f"Unknown template: {name}")
        _, fn = self._templates[name]
        return fn(**params)

    def list_templates(self) -> list[str]:
        return sorted(self._templates.keys())

    def by_category(self, category: str) -> list[str]:
        return sorted(name for name, (cat, _) in self._templates.items() if cat == category)


def phases_to_csv(phases: list[BlueprintPhase]) -> str:
    """Convert blueprint phases to a single quickfort CSV string."""
    buf = io.StringIO()
    writer = csv.writer(buf)
    for phase in phases:
        writer.writerow([phase.mode, phase.label])
        for row in phase.rows:
            writer.writerow(row)
        writer.writerow([])  # blank line between phases
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------


def _grid(width: int, height: int, fill: str = "d") -> list[list[str]]:
    """Create a width x height grid filled with a designation code."""
    return [[fill] * width for _ in range(height)]


def _grid_to_rows(grid: list[list[str]]) -> tuple[tuple[str, ...], ...]:
    """Convert a mutable grid to an immutable tuple-of-tuples."""
    return tuple(tuple(row) for row in grid)


# ---------------------------------------------------------------------------
# Template: central_stairwell
# ---------------------------------------------------------------------------


def central_stairwell(depth: int = 10, width: int = 3) -> list[BlueprintPhase]:
    """Central stairwell — vertical spine of the fortress.

    Args:
        depth: Number of z-levels to carve. Must be >= 1.
        width: Stairwell width (and height). Must be 3 or 5.
    """
    if depth < 1:
        raise ValueError(f"depth must be >= 1, got {depth}")
    if width not in (3, 5):
        raise ValueError(f"width must be 3 or 5, got {width}")

    rows: list[list[str]] = []
    for z in range(depth):
        # Each z-level is a width x width grid of up/down stairs
        for _ in range(width):
            rows.append(["i"] * width)
        # Add z-level separator except after the last level
        if z < depth - 1:
            rows.append(["#>"])

    return [
        BlueprintPhase(
            mode="#dig",
            label=f"stairwell_{width}x{width}_z{depth}",
            rows=_grid_to_rows(rows),
        )
    ]


# ---------------------------------------------------------------------------
# Template: bedroom_block
# ---------------------------------------------------------------------------

_QUALITY_INNER: dict[str, int] = {"basic": 2, "comfortable": 3, "noble": 5}


def bedroom_block(n_rooms: int = 10, quality: str = "comfortable") -> list[BlueprintPhase]:
    """Bedroom block — corridor with rooms on both sides.

    Args:
        n_rooms: Number of bedrooms. Must be >= 1.
        quality: "basic", "comfortable", or "noble".
    """
    if n_rooms < 1:
        raise ValueError(f"n_rooms must be >= 1, got {n_rooms}")
    if quality not in _QUALITY_INNER:
        raise ValueError(f"quality must be one of {list(_QUALITY_INNER)}, got {quality!r}")

    inner = _QUALITY_INNER[quality]
    rooms_per_side = math.ceil(n_rooms / 2)
    # Total width: room_left + door + corridor + door + room_right
    total_width = inner + 1 + 1 + 1 + inner
    total_height = rooms_per_side * (inner + 1) - 1  # rooms + walls between

    # --- Dig phase ---
    dig = _grid(total_width, total_height, "`")  # ` = no-op in quickfort

    corridor_col = inner + 1  # 0-indexed column for the corridor
    for y in range(total_height):
        # Always dig the corridor
        dig[y][corridor_col] = "d"

        row_in_room = y % (inner + 1)

        if row_in_room < inner:
            # Left room
            for x in range(inner):
                dig[y][x] = "d"
            # Left door column
            if row_in_room == 0:
                dig[y][inner] = "d"

            # Right room
            for x in range(corridor_col + 2, total_width):
                dig[y][x] = "d"
            # Right door column
            if row_in_room == 0:
                dig[y][corridor_col + 1] = "d"

    # --- Build phase ---
    build = _grid(total_width, total_height, "`")

    for side in range(2):
        for r in range(rooms_per_side):
            actual_room = side * rooms_per_side + r
            if actual_room >= n_rooms:
                break

            base_y = r * (inner + 1)

            if side == 0:  # left
                door_x = inner
                room_x_start = 0
            else:  # right
                door_x = corridor_col + 1
                room_x_start = corridor_col + 2

            # Door
            build[base_y][door_x] = "d"

            # Bed (always)
            if base_y < total_height and room_x_start < total_width:
                build[base_y][room_x_start] = "b"

            # Comfortable: + cabinet + chest
            if quality in ("comfortable", "noble") and inner >= 3:
                if base_y + 1 < total_height:
                    build[base_y + 1][room_x_start] = "C"  # cabinet
                if base_y + 2 < total_height:
                    build[base_y + 2][room_x_start] = "h"  # chest

            # Noble: + armor stand + weapon rack + statue
            if quality == "noble" and inner >= 5:
                if base_y < total_height and room_x_start + 1 < total_width:
                    build[base_y][room_x_start + 1] = "A"  # armor stand
                if base_y + 1 < total_height and room_x_start + 1 < total_width:
                    build[base_y + 1][room_x_start + 1] = "r"  # weapon rack
                if base_y + 2 < total_height and room_x_start + 1 < total_width:
                    build[base_y + 2][room_x_start + 1] = "s"  # statue

    return [
        BlueprintPhase(
            mode="#dig",
            label=f"bedrooms_{n_rooms}_{quality}_dig",
            rows=_grid_to_rows(dig),
        ),
        BlueprintPhase(
            mode="#build",
            label=f"bedrooms_{n_rooms}_{quality}_build",
            rows=_grid_to_rows(build),
        ),
    ]


# ---------------------------------------------------------------------------
# Template: dining_hall
# ---------------------------------------------------------------------------


def dining_hall(capacity: int = 50) -> list[BlueprintPhase]:
    """Dining hall — square room with checkerboard table/chair layout.

    Args:
        capacity: Number of dwarves to seat.
    """
    size = max(5, math.ceil(math.sqrt(capacity)) * 2 + 1)
    if size % 2 == 0:
        size += 1  # force odd

    # --- Dig phase ---
    dig = _grid(size, size, "d")

    # --- Build phase: checkerboard of tables (t) and chairs (c) ---
    build = _grid(size, size, "`")
    for y in range(1, size - 1):
        for x in range(1, size - 1):
            if (x + y) % 2 == 0:
                build[y][x] = "t"  # table
            else:
                build[y][x] = "c"  # chair

    return [
        BlueprintPhase(
            mode="#dig",
            label=f"dining_hall_{size}x{size}_dig",
            rows=_grid_to_rows(dig),
        ),
        BlueprintPhase(
            mode="#build",
            label=f"dining_hall_{size}x{size}_build",
            rows=_grid_to_rows(build),
        ),
    ]


# ---------------------------------------------------------------------------
# Template: workshop_pocket
# ---------------------------------------------------------------------------

_WORKSHOP_CODES: dict[str, str] = {
    "Craftsdwarfs": "wc",
    "Carpenters": "wC",
    "Masons": "wm",
    "Forge": "wf",
    "Smelter": "ws",
    "Jewelers": "wj",
    "Clothiers": "wk",
    "Tanners": "wt",
    "Leatherworks": "we",
    "Butchers": "wb",
    "Kitchen": "wz",
    "Brewery": "wl",
    "Fishery": "wF",
    "Still": "wl",
    "Loom": "wo",
    "Mechanics": "wM",
    "Siege": "ws",
    "Bowyers": "wB",
    "Farmers": "ww",
}


def workshop_pocket(workshop_type: str = "Craftsdwarfs") -> list[BlueprintPhase]:
    """Workshop pocket — 7x7 room with centered workshop and surrounding stockpile.

    Args:
        workshop_type: Type of workshop (e.g. "Craftsdwarfs", "Forge").
    """
    code = _WORKSHOP_CODES.get(workshop_type, "wc")

    # --- Dig phase: 7x7 room ---
    dig = _grid(7, 7, "d")
    # Door at top-center
    dig[0][3] = "d"

    # --- Build phase: 3x3 workshop centered ---
    build = _grid(7, 7, "`")
    build[0][3] = "d"  # door
    for y in range(2, 5):
        for x in range(2, 5):
            build[y][x] = code

    # --- Place phase: stockpile ring ---
    place = _grid(7, 7, "`")
    for y in range(7):
        for x in range(7):
            if 2 <= y <= 4 and 2 <= x <= 4:
                continue  # workshop area
            if y == 0 and x == 3:
                continue  # door
            place[y][x] = "s"  # generic stockpile

    return [
        BlueprintPhase(
            mode="#dig",
            label=f"workshop_{workshop_type}_dig",
            rows=_grid_to_rows(dig),
        ),
        BlueprintPhase(
            mode="#build",
            label=f"workshop_{workshop_type}_build",
            rows=_grid_to_rows(build),
        ),
        BlueprintPhase(
            mode="#place",
            label=f"workshop_{workshop_type}_stockpile",
            rows=_grid_to_rows(place),
        ),
    ]


# ---------------------------------------------------------------------------
# Template: farm_block
# ---------------------------------------------------------------------------


def farm_block(n_plots: int = 4, size: int = 3) -> list[BlueprintPhase]:
    """Farm block — grid of farm plots with corridors.

    Args:
        n_plots: Number of farm plots. Must be >= 1.
        size: Size of each square plot.
    """
    if n_plots < 1:
        raise ValueError(f"n_plots must be >= 1, got {n_plots}")

    cols = 2
    plot_rows = math.ceil(n_plots / cols)

    # Total dimensions including 1-tile corridors between plots
    total_width = cols * size + (cols - 1)  # plots + corridor between
    total_height = plot_rows * size + (plot_rows - 1)

    # --- Dig phase ---
    dig = _grid(total_width, total_height, "d")

    # --- Build phase: farm plot designations ---
    build = _grid(total_width, total_height, "`")
    plots_placed = 0
    for pr in range(plot_rows):
        for pc in range(cols):
            if plots_placed >= n_plots:
                break
            x_off = pc * (size + 1)
            y_off = pr * (size + 1)
            for y in range(size):
                for x in range(size):
                    if y_off + y < total_height and x_off + x < total_width:
                        build[y_off + y][x_off + x] = "p"  # farm plot
            plots_placed += 1

    return [
        BlueprintPhase(
            mode="#dig",
            label=f"farm_{n_plots}x{size}_dig",
            rows=_grid_to_rows(dig),
        ),
        BlueprintPhase(
            mode="#build",
            label=f"farm_{n_plots}x{size}_build",
            rows=_grid_to_rows(build),
        ),
    ]


# ---------------------------------------------------------------------------
# Template: entrance_defense
# ---------------------------------------------------------------------------


def entrance_defense(style: str = "killbox") -> list[BlueprintPhase]:
    """Entrance defense — corridor with traps and a killbox room.

    Args:
        style: Defense style. Currently only "killbox" is supported.
    """
    corridor_len = 10
    room_size = 3
    total_height = corridor_len + room_size
    total_width = room_size  # corridor is 1-wide centered, room is 3-wide

    # --- Dig phase ---
    dig = _grid(total_width, total_height, "`")
    center = total_width // 2

    # 1-wide corridor
    for y in range(corridor_len):
        dig[y][center] = "d"

    # 3x3 room at end
    for y in range(corridor_len, total_height):
        for x in range(total_width):
            dig[y][x] = "d"

    # --- Build phase ---
    build = _grid(total_width, total_height, "`")

    # Drawbridge at entrance (row 0)
    build[0][center] = "gw"  # raising bridge

    # Cage traps along corridor (rows 1-9)
    for y in range(1, corridor_len):
        build[y][center] = "Tc"  # cage trap

    return [
        BlueprintPhase(
            mode="#dig",
            label=f"entrance_{style}_dig",
            rows=_grid_to_rows(dig),
        ),
        BlueprintPhase(
            mode="#build",
            label=f"entrance_{style}_build",
            rows=_grid_to_rows(build),
        ),
    ]


# ---------------------------------------------------------------------------
# Template: stockpile_hub
# ---------------------------------------------------------------------------

_STOCKPILE_CODES: dict[str, str] = {
    "food": "f",
    "drink": "f",  # food/drink share in quickfort
    "wood": "w",
    "stone": "s",
    "metal": "b",  # bars
    "cloth": "l",  # cloth
    "leather": "l",
    "ammo": "z",
    "weapons": "p",  # weapons
    "armor": "d",  # armor
    "gems": "g",
    "furniture": "u",
    "finished": "n",  # finished goods
    "refuse": "r",
    "animals": "a",
    "corpses": "y",
}


def stockpile_hub(
    categories: tuple[str, ...] = ("food", "drink", "wood", "stone"),
) -> list[BlueprintPhase]:
    """Stockpile hub — grid of 5x5 stockpiles, one per category.

    Args:
        categories: Tuple of stockpile category names.
    """
    n = len(categories)
    cols = 2
    pile_rows = math.ceil(n / cols)
    pile_size = 5
    gap = 1

    total_width = cols * pile_size + (cols - 1) * gap
    total_height = pile_rows * pile_size + (pile_rows - 1) * gap

    place = _grid(total_width, total_height, "`")

    idx = 0
    for pr in range(pile_rows):
        for pc in range(cols):
            if idx >= n:
                break
            cat = categories[idx]
            code = _STOCKPILE_CODES.get(cat, "s")
            x_off = pc * (pile_size + gap)
            y_off = pr * (pile_size + gap)
            for y in range(pile_size):
                for x in range(pile_size):
                    if y_off + y < total_height and x_off + x < total_width:
                        place[y_off + y][x_off + x] = code
            idx += 1

    return [
        BlueprintPhase(
            mode="#place",
            label="stockpile_hub",
            rows=_grid_to_rows(place),
        )
    ]


# ---------------------------------------------------------------------------
# Template: starter_fortress (meta-template)
# ---------------------------------------------------------------------------


def starter_fortress(target_population: int = 50) -> list[BlueprintPhase]:
    """Meta-template composing a complete starter fortress.

    Combines entrance defense, central stairwell, dining hall, bedrooms,
    workshops, farms, and stockpiles into an ordered build plan.

    Args:
        target_population: Target number of dwarves.
    """
    phases: list[BlueprintPhase] = []

    # Entrance
    phases.extend(entrance_defense(style="killbox"))

    # Central stairwell (deeper for larger forts)
    stair_depth = max(5, target_population // 10)
    phases.extend(central_stairwell(depth=stair_depth, width=3))

    # Dining hall
    phases.extend(dining_hall(capacity=target_population))

    # Bedrooms — one per dwarf, quality based on population
    quality = "basic" if target_population > 80 else "comfortable"
    phases.extend(bedroom_block(n_rooms=target_population, quality=quality))

    # Core workshops
    for ws in ("Craftsdwarfs", "Masons", "Carpenters", "Forge", "Smelter", "Kitchen"):
        phases.extend(workshop_pocket(workshop_type=ws))

    # Farms — scale with population
    n_plots = max(4, target_population // 10)
    phases.extend(farm_block(n_plots=n_plots, size=3))

    # Stockpiles
    phases.extend(
        stockpile_hub(categories=("food", "drink", "wood", "stone", "metal", "finished", "cloth"))
    )

    return phases


# ---------------------------------------------------------------------------
# Default registry
# ---------------------------------------------------------------------------

_registry = BlueprintRegistry()


def _register_defaults() -> None:
    _registry.register("central_stairwell", "infrastructure", central_stairwell)
    _registry.register("bedroom_block", "residential", bedroom_block)
    _registry.register("dining_hall", "infrastructure", dining_hall)
    _registry.register("workshop_pocket", "industrial", workshop_pocket)
    _registry.register("farm_block", "agriculture", farm_block)
    _registry.register("entrance_defense", "defense", entrance_defense)
    _registry.register("stockpile_hub", "infrastructure", stockpile_hub)
    _registry.register("starter_fortress", "infrastructure", starter_fortress)


_register_defaults()


def generate_blueprint(template_name: str, **params: Any) -> str:
    """Generate a quickfort CSV string from a named template."""
    phases = _registry.generate(template_name, **params)
    return phases_to_csv(phases)


def generate_fortress_plan(target_population: int = 50) -> list[tuple[str, str]]:
    """Generate ordered list of (phase_name, csv_string) for a complete fortress."""
    phases = starter_fortress(target_population=target_population)
    return [(p.label, phases_to_csv([p])) for p in phases]
