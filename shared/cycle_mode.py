"""shared/cycle_mode.py — DEPRECATED. Use shared.working_mode instead.

Backward-compatible shim: the two-mode system is now unified under
WorkingMode (research/rnd). CycleMode (dev/prod) no longer exists
as a separate concept.

Mapping: DEV → RND, PROD → RESEARCH (but callers should migrate to
WorkingMode directly).
"""

from shared.working_mode import WORKING_MODE_FILE as MODE_FILE  # noqa: F401
from shared.working_mode import WorkingMode as CycleMode  # noqa: F401
from shared.working_mode import get_working_mode as get_cycle_mode  # noqa: F401
