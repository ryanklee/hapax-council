"""HLS segment decoder — extract frames from MPEG-TS segments for temporal analysis."""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path

import cv2
import numpy as np

log = logging.getLogger(__name__)


def decode_segment(segment_path: Path, max_frames: int = 10) -> list[np.ndarray]:
    """Extract evenly-spaced frames from an HLS .ts segment via ffmpeg.

    Returns list of BGR numpy arrays (may be fewer than max_frames).
    """
    if not segment_path.exists():
        return []

    try:
        # Probe duration
        probe = subprocess.run(
            [
                "ffprobe",
                "-v",
                "quiet",
                "-print_format",
                "json",
                "-show_format",
                str(segment_path),
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )
        import json

        duration = float(json.loads(probe.stdout).get("format", {}).get("duration", 2.0))

        # Extract frames: select every Nth frame to get max_frames total
        # For a 2s segment at 30fps = 60 frames, select every 6th
        fps = 30
        total_frames = int(duration * fps)
        select_every = max(1, total_frames // max_frames)

        result = subprocess.run(
            [
                "ffmpeg",
                "-i",
                str(segment_path),
                "-vf",
                f"select=not(mod(n\\,{select_every}))",
                "-frames:v",
                str(max_frames),
                "-f",
                "rawvideo",
                "-pix_fmt",
                "bgr24",
                "-v",
                "quiet",
                "-y",
                "pipe:1",
            ],
            capture_output=True,
            timeout=10,
        )

        if result.returncode != 0:
            return []

        raw = result.stdout
        if not raw:
            return []

        # Assume 1920x1080 (compositor output) — adjust if needed
        w, h = 1920, 1080
        frame_size = w * h * 3
        frames = []
        for i in range(0, len(raw), frame_size):
            chunk = raw[i : i + frame_size]
            if len(chunk) == frame_size:
                frame = np.frombuffer(chunk, dtype=np.uint8).reshape(h, w, 3)
                frames.append(frame.copy())
            if len(frames) >= max_frames:
                break

        return frames

    except Exception:
        log.debug("HLS segment decode failed: %s", segment_path, exc_info=True)
        return []


def compute_motion_energy(frames: list[np.ndarray]) -> float:
    """Compute mean motion energy across consecutive frame pairs.

    Returns 0.0 (no motion) to 1.0 (maximum change).
    """
    if len(frames) < 2:
        return 0.0

    energies = []
    for i in range(1, len(frames)):
        prev_gray = cv2.cvtColor(frames[i - 1], cv2.COLOR_BGR2GRAY)
        curr_gray = cv2.cvtColor(frames[i], cv2.COLOR_BGR2GRAY)
        diff = cv2.absdiff(prev_gray, curr_gray)
        energies.append(float(diff.mean()) / 255.0)

    return sum(energies) / len(energies) if energies else 0.0
