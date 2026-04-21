"""CBIP intensity-override surface — operator manual control.

Spec §6.2. Reads/writes the per-operator override file:
``~/.cache/hapax/cbip/intensity-override.json``.

When the file's ``value`` is ``"auto"`` (or missing), the stimmung-derived
default applies. When set to a numeric value in ``[0.0, 1.0]``, that
value wins.

Atomic tmp+rename on write so the renderer never sees a partial file.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

log = logging.getLogger(__name__)

DEFAULT_OVERRIDE_PATH = Path.home() / ".cache" / "hapax" / "cbip" / "intensity-override.json"


@dataclass(frozen=True)
class OverrideValue:
    """Parsed override file content.

    ``value=None`` means "auto" — the renderer should fall through to the
    stimmung-derived default. Otherwise ``value`` is a clamped float in
    ``[0.0, 1.0]``.
    """

    value: float | None


def read_override(path: Path = DEFAULT_OVERRIDE_PATH) -> OverrideValue:
    """Parse the override file. Falls back to "auto" on any error.

    Tolerated: missing file, malformed JSON, non-dict payload, missing
    ``value`` key, ``value="auto"``. The renderer must always be able to
    proceed, so anything ambiguous reads as "auto".
    """
    try:
        raw = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return OverrideValue(value=None)
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        log.debug("cbip-override JSON malformed at %s", path)
        return OverrideValue(value=None)
    if not isinstance(payload, dict):
        return OverrideValue(value=None)
    raw_value = payload.get("value", "auto")
    if raw_value == "auto" or raw_value is None:
        return OverrideValue(value=None)
    try:
        clamped = max(0.0, min(1.0, float(raw_value)))
    except (TypeError, ValueError):
        return OverrideValue(value=None)
    return OverrideValue(value=clamped)


def write_override(value: float | None, path: Path = DEFAULT_OVERRIDE_PATH) -> None:
    """Atomically write ``value`` to the override file.

    ``value=None`` writes ``{"value": "auto"}`` so the renderer falls
    through to the stimmung default. A numeric value is clamped to
    ``[0.0, 1.0]`` before writing.

    Parent directory is created on demand. Tmp file is renamed into
    place so the renderer never sees a half-written payload.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    if value is None:
        payload: dict = {"value": "auto"}
    else:
        clamped = max(0.0, min(1.0, float(value)))
        payload = {"value": clamped}
    fd, tmp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fp:
            json.dump(payload, fp)
        os.replace(tmp_name, path)
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise
