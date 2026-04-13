"""Studio Compositor package — backward-compatible re-exports.

Source-registry epic completion is planned in
``docs/superpowers/plans/2026-04-13-reverie-source-registry-completion-plan.md``
(umbrella over the parent 2026-04-12 source-registry foundation plan).
"""

from .compositor import StudioCompositor
from .config import load_config
from .layout import compute_tile_layout
from .models import (
    CameraProfile,
    CameraSpec,
    CameraV4L2,
    CompositorConfig,
    HlsConfig,
    OverlayData,
    OverlayState,
    RecordingConfig,
    TileRect,
)
from .profiles import (
    apply_camera_profile,
    evaluate_active_profile,
    load_camera_profiles,
)

__all__ = [
    "CameraProfile",
    "CameraSpec",
    "CameraV4L2",
    "CompositorConfig",
    "HlsConfig",
    "OverlayData",
    "OverlayState",
    "RecordingConfig",
    "StudioCompositor",
    "TileRect",
    "apply_camera_profile",
    "compute_tile_layout",
    "evaluate_active_profile",
    "load_camera_profiles",
    "load_config",
]
