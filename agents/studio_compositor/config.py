"""Configuration constants and loaders for the studio compositor."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

from .models import CameraSpec, CompositorConfig

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Path constants
# ---------------------------------------------------------------------------

CACHE_DIR = Path.home() / ".cache" / "hapax-compositor"
STATUS_FILE = CACHE_DIR / "status.json"
CONSENT_AUDIT_PATH = CACHE_DIR / "consent-audit.jsonl"
DEFAULT_CONFIG_PATH = Path.home() / ".config" / "hapax-compositor" / "config.yaml"
SNAPSHOT_DIR = Path("/dev/shm/hapax-compositor")
PERCEPTION_STATE_PATH = Path.home() / ".cache" / "hapax-daimonion" / "perception-state.json"
PROFILES_CONFIG_PATH = Path.home() / ".config" / "hapax-compositor" / "profiles.yaml"

# A+ Stage 2 (2026-04-17): canvas 1920x1080 → 1280x720. Operator directive
# 2026-04-17: "1080p is NOT a priority at all." Rationale per research:
# 2.25x fewer pixels through the cudacompositor + glfeedback chain + NVENC
# encoder; YouTube Live at 720p30 accepts 2500-4000 kbps (vs 6000 at 1080p);
# OBS and every PiP in the current layout are already ≤720p natively, so
# 1080p canvas was upscale-then-downscale waste. Layout JSON coordinates
# are scaled below via LAYOUT_COORD_SCALE.
#
# Override via HAPAX_COMPOSITOR_OUTPUT_WIDTH / _HEIGHT env vars for
# debugging or A/B comparison without a code change.
import os as _os

OUTPUT_WIDTH = int(_os.environ.get("HAPAX_COMPOSITOR_OUTPUT_WIDTH", "1280"))
OUTPUT_HEIGHT = int(_os.environ.get("HAPAX_COMPOSITOR_OUTPUT_HEIGHT", "720"))
# Multiplier applied to absolute pixel coordinates in layout JSON so
# existing 1920x1080-authored layouts render correctly at the smaller
# canvas. 1280/1920 = 0.6667.
LAYOUT_COORD_SCALE = OUTPUT_WIDTH / 1920.0

# ---------------------------------------------------------------------------
# Default camera config
# ---------------------------------------------------------------------------

_DEFAULT_CAMERAS: list[dict[str, Any]] = [
    {
        "role": "brio-operator",
        "device": "/dev/v4l/by-id/usb-046d_Logitech_BRIO_5342C819-video-index0",
        "width": 1280,
        "height": 720,
        "input_format": "mjpeg",
        "hero": True,
    },
    {
        "role": "c920-desk",
        "device": "/dev/v4l/by-id/usb-046d_HD_Pro_Webcam_C920_2657DFCF-video-index0",
        "width": 1280,
        "height": 720,
        "input_format": "mjpeg",
    },
    {
        "role": "c920-room",
        "device": "/dev/v4l/by-id/usb-046d_HD_Pro_Webcam_C920_86B6B75F-video-index0",
        "width": 1280,
        "height": 720,
        "input_format": "mjpeg",
    },
    {
        "role": "c920-overhead",
        "device": "/dev/v4l/by-id/usb-046d_HD_Pro_Webcam_C920_7B88C71F-video-index0",
        "width": 1280,
        "height": 720,
        "input_format": "mjpeg",
    },
    {
        "role": "brio-room",
        "device": "/dev/v4l/by-id/usb-046d_Logitech_BRIO_43B0576A-video-index0",
        "width": 1280,
        "height": 720,
        "input_format": "mjpeg",
    },
    {
        "role": "brio-synths",
        "device": "/dev/v4l/by-id/usb-046d_Logitech_BRIO_9726C031-video-index0",
        "width": 1280,
        "height": 720,
        "input_format": "mjpeg",
    },
]


def _default_config() -> CompositorConfig:
    return CompositorConfig(cameras=[CameraSpec(**c) for c in _DEFAULT_CAMERAS])


def load_config(path: Path | None = None) -> CompositorConfig:
    config_path = path or DEFAULT_CONFIG_PATH
    if config_path.exists():
        try:
            data = yaml.safe_load(config_path.read_text()) or {}
            return CompositorConfig(**data)
        except Exception as exc:
            log.warning("Failed to load config from %s: %s -- using defaults", config_path, exc)
    return _default_config()
