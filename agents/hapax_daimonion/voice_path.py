"""Voice-path router — tier → audio-path selection (dual-FX Phase 3).

Phase 3 of docs/superpowers/plans/2026-04-20-dual-fx-routing-plan.md.
Maps a ``VoiceTier`` to one of four addressable paths:

- ``dry``: Ryzen analog only, no DSP (intelligibility-maximising).
- ``radio``: S-4 USB-direct pitched/reverb without granular.
- ``evil_pet``: Ryzen → L6 ch 5 → AUX 1 → Evil Pet → return.
- ``both``: parallel — S-4 direct alongside Evil Pet for wide stereo.

The path decision is SOFT — the router returns a suggested path given
current tier + caller context, never enforces it. Downstream wiring
(``VocalChainCapability``, ``engine_gate.apply_tier_gated``) reads the
choice and switches the PipeWire route. Operator override via the
``hapax-voice-tier`` CLI writes a SHM flag this router checks first.

Data source: ``config/voice-paths.yaml``. Keeps the mapping as
data rather than code so the operator can hand-tune tier→path biases
without a rebuild.

Reference:
    - docs/research/2026-04-20-dual-fx-routing-design.md
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

import yaml

from shared.voice_tier import TIER_NAMES, VoiceTier

_DEFAULT_CONFIG = Path(__file__).resolve().parents[2] / "config" / "voice-paths.yaml"


class VoicePath(StrEnum):
    """Addressable voice routing paths.

    String values match the YAML keys in ``config/voice-paths.yaml``
    so config edits round-trip through the enum parser without a
    separate mapping layer.
    """

    DRY = "dry"
    RADIO = "radio"
    EVIL_PET = "evil_pet"
    BOTH = "both"


@dataclass(frozen=True)
class PathConfig:
    """Single-path config from voice-paths.yaml."""

    path: VoicePath
    description: str
    sink: str
    via_evil_pet: bool
    via_s4: bool
    default_for_tiers: frozenset[str]


def load_paths(path: Path | None = None) -> dict[VoicePath, PathConfig]:
    """Parse ``config/voice-paths.yaml`` into a ``{VoicePath: PathConfig}`` map."""
    source = path if path is not None else _DEFAULT_CONFIG
    data = yaml.safe_load(source.read_text())
    out: dict[VoicePath, PathConfig] = {}
    for key, raw in data.get("paths", {}).items():
        vp = VoicePath(key)
        out[vp] = PathConfig(
            path=vp,
            description=raw.get("description", ""),
            sink=raw["sink"],
            via_evil_pet=bool(raw.get("via_evil_pet", False)),
            via_s4=bool(raw.get("via_s4", False)),
            default_for_tiers=frozenset(raw.get("default_for_tiers", [])),
        )
    return out


def _tier_canonical(tier: VoiceTier) -> str:
    """Return the ``TIER_NAMES`` canonical name with dashes→underscores.

    YAML uses ``broadcast_ghost``/``granular_wash``; ``TIER_NAMES``
    stores the dash form. Normalise so the comparison is consistent.
    """
    return TIER_NAMES[tier].replace("-", "_")


def select_voice_path(
    tier: VoiceTier,
    paths: dict[VoicePath, PathConfig] | None = None,
) -> VoicePath:
    """Pick the default voice path for a tier.

    First path whose ``default_for_tiers`` contains the canonical tier
    name wins. If no path claims the tier, falls back to ``DRY`` —
    safest intelligibility-preserving choice for unrecognised inputs.
    """
    data = paths if paths is not None else load_paths()
    canonical = _tier_canonical(tier)
    for path_cfg in data.values():
        if canonical in path_cfg.default_for_tiers:
            return path_cfg.path
    return VoicePath.DRY


def requires_granular_engine(path: VoicePath) -> bool:
    """True when the path routes audio through the Evil Pet granular engine.

    Callers use this to decide whether they need to acquire the
    ``evil_pet_granular_engine`` mutex before emitting CCs —
    ``EVIL_PET`` and ``BOTH`` both drive the engine, ``DRY`` and
    ``RADIO`` leave it untouched.
    """
    data = load_paths()
    return data[path].via_evil_pet


def describe_path(path: VoicePath) -> str:
    """Operator-readable description from the config — used in CLI output."""
    return load_paths()[path].description


def all_paths() -> list[VoicePath]:
    """All addressable paths, ordered by YAML key."""
    return list(load_paths().keys())
