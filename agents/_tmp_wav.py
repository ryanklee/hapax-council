"""Vendored temporary WAV file management for the agents package.

Managed temporary WAV file creation with leak prevention.
Files are created in ~/.cache/hapax/tmp-wav/ instead of /tmp.
"""

from __future__ import annotations

import logging
import tempfile
import time
from pathlib import Path

from agents._config import HAPAX_TMP_WAV_DIR

log = logging.getLogger(__name__)

_MAX_AGE_S = 120


def _ensure_dir() -> Path:
    """Create the tmp-wav directory if it doesn't exist."""
    HAPAX_TMP_WAV_DIR.mkdir(parents=True, exist_ok=True)
    return HAPAX_TMP_WAV_DIR


def tmp_wav_path() -> Path:
    """Create a new temporary wav file path in the managed directory.

    The caller MUST delete the file in a finally block.
    """
    d = _ensure_dir()
    fd, path = tempfile.mkstemp(suffix=".wav", dir=str(d))
    import os

    os.close(fd)
    return Path(path)


def cleanup_stale_wavs(max_age_s: float = _MAX_AGE_S) -> int:
    """Remove wav files older than max_age_s. Returns count removed."""
    d = _ensure_dir()
    now = time.time()
    removed = 0
    for f in d.glob("*.wav"):
        try:
            age = now - f.stat().st_mtime
            if age > max_age_s:
                f.unlink()
                removed += 1
                log.info("Cleaned orphan wav (%.0fs old): %s", age, f.name)
        except OSError:
            pass
    return removed


def cleanup_all_wavs() -> int:
    """Remove ALL wav files in the managed directory. Use on startup."""
    d = _ensure_dir()
    removed = 0
    for f in d.glob("*.wav"):
        try:
            f.unlink()
            removed += 1
        except OSError:
            pass
    if removed:
        log.info("Startup cleanup: removed %d orphan wav files", removed)
    return removed
