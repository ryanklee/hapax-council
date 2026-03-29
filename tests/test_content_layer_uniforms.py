"""Tests for material encoding in uniforms.json."""

from __future__ import annotations

import json
from pathlib import Path

MATERIAL_MAP = {"water": 0, "fire": 1, "earth": 2, "air": 3, "void": 4}


def test_material_map_covers_all_values():
    """All 5 Bachelard materials have numeric encodings."""
    assert set(MATERIAL_MAP.keys()) == {"water", "fire", "earth", "air", "void"}
    assert list(MATERIAL_MAP.values()) == [0, 1, 2, 3, 4]


def test_material_encoding_in_uniforms_json(tmp_path: Path):
    """DMN writes material as custom[0] in uniforms.json."""
    uniforms_path = tmp_path / "pipeline" / "uniforms.json"
    imagination_path = tmp_path / "current.json"

    imagination_path.write_text(
        json.dumps(
            {
                "id": "abc123",
                "material": "fire",
                "salience": 0.7,
                "dimensions": {"intensity": 0.5},
            }
        )
    )

    from agents.dmn.__main__ import write_imagination_uniforms

    write_imagination_uniforms(imagination_path, uniforms_path)

    data = json.loads(uniforms_path.read_text())
    assert data["custom"][0] == 1.0  # fire = 1
    assert data["slot_opacities"][0] == 0.7  # salience


def test_material_encoding_default_water(tmp_path: Path):
    """Missing material field defaults to water (0)."""
    uniforms_path = tmp_path / "pipeline" / "uniforms.json"
    imagination_path = tmp_path / "current.json"

    imagination_path.write_text(
        json.dumps(
            {
                "id": "abc123",
                "salience": 0.5,
                "dimensions": {},
            }
        )
    )

    from agents.dmn.__main__ import write_imagination_uniforms

    write_imagination_uniforms(imagination_path, uniforms_path)

    data = json.loads(uniforms_path.read_text())
    assert data["custom"][0] == 0.0  # water = 0


def test_material_encoding_missing_file(tmp_path: Path):
    """No imagination file → no uniforms written."""
    uniforms_path = tmp_path / "pipeline" / "uniforms.json"
    imagination_path = tmp_path / "nonexistent.json"

    from agents.dmn.__main__ import write_imagination_uniforms

    write_imagination_uniforms(imagination_path, uniforms_path)

    assert not uniforms_path.exists()
