"""Bundled-asset loaders for hapax-axioms.

Lazy-loads the bundled axioms / patterns YAML from `data/`. Callers can
override the source path with the `path` argument or the
`HAPAX_AXIOMS_PATH` / `HAPAX_AXIOMS_PATTERNS_PATH` environment variables
to point at a project-local axiom set instead of the bundled snapshot.
"""

from __future__ import annotations

import os
from importlib import resources
from pathlib import Path

import yaml

from hapax_axioms.models import AxiomBundle, PatternBundle

_AXIOMS_RESOURCE = "axioms.yaml"
_PATTERNS_RESOURCE = "patterns.yaml"

_AXIOMS_ENV = "HAPAX_AXIOMS_PATH"
_PATTERNS_ENV = "HAPAX_AXIOMS_PATTERNS_PATH"


def bundled_axioms_path() -> Path:
    """Filesystem path to the bundled axioms YAML."""
    with resources.as_file(resources.files("hapax_axioms.data") / _AXIOMS_RESOURCE) as p:
        return Path(p)


def bundled_patterns_path() -> Path:
    """Filesystem path to the bundled patterns YAML."""
    with resources.as_file(resources.files("hapax_axioms.data") / _PATTERNS_RESOURCE) as p:
        return Path(p)


def load_axioms(*, path: Path | str | None = None) -> AxiomBundle:
    """Load the axiom bundle.

    Resolution order:
      1. Explicit `path` argument.
      2. `HAPAX_AXIOMS_PATH` environment variable.
      3. Bundled snapshot.
    """
    resolved = _resolve(path, _AXIOMS_ENV, bundled_axioms_path())
    data = yaml.safe_load(resolved.read_text(encoding="utf-8"))
    return AxiomBundle.model_validate(data)


def load_patterns(*, path: Path | str | None = None) -> PatternBundle:
    """Load the pattern bundle.

    Resolution order:
      1. Explicit `path` argument.
      2. `HAPAX_AXIOMS_PATTERNS_PATH` environment variable.
      3. Bundled snapshot.
    """
    resolved = _resolve(path, _PATTERNS_ENV, bundled_patterns_path())
    data = yaml.safe_load(resolved.read_text(encoding="utf-8"))
    return PatternBundle.model_validate(data)


def _resolve(explicit: Path | str | None, env: str, default: Path) -> Path:
    if explicit is not None:
        candidate = Path(explicit)
        if not candidate.is_file():
            raise FileNotFoundError(f"hapax-axioms bundle not found: {candidate}")
        return candidate
    env_val = os.environ.get(env)
    if env_val:
        candidate = Path(env_val)
        if not candidate.is_file():
            raise FileNotFoundError(
                f"hapax-axioms bundle (from ${env}) not found: {candidate}",
            )
        return candidate
    return default
