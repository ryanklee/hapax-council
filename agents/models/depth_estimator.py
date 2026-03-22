"""Monocular depth estimation via Depth-Anything-V2-Small.

Lazy-loaded, ~1.2GB VRAM. Replaces the bbox-ratio heuristic for person
distance estimation with actual depth map inference.
"""

from __future__ import annotations

import logging

import numpy as np

log = logging.getLogger(__name__)


def _bbox_fallback(frame: np.ndarray, person_boxes: list[list[float]]) -> str:
    """Bounding-box height ratio heuristic (fallback when model unavailable)."""
    frame_h = frame.shape[0]
    if frame_h < 1:
        return "none"
    max_ratio = 0.0
    for box in person_boxes:
        box_h = box[3] - box[1]
        max_ratio = max(max_ratio, box_h / frame_h)
    if max_ratio > 0.6:
        return "close"
    if max_ratio > 0.3:
        return "medium"
    return "far"


class DepthEstimator:
    """Thin wrapper around Depth-Anything-V2-Small for person distance."""

    def __init__(self) -> None:
        self._pipe: object | None = None
        self._failed: bool = False

    def _load(self) -> bool:
        if self._pipe is not None:
            return True
        if self._failed:
            return False
        try:
            from transformers import pipeline

            self._pipe = pipeline(
                "depth-estimation",
                model="depth-anything/Depth-Anything-V2-Small-hf",
                device="cuda",
            )
            log.info("Depth-Anything-V2-Small loaded on CUDA")
            return True
        except Exception:
            log.warning("Depth-Anything-V2 load failed, using bbox fallback", exc_info=True)
            self._failed = True
            return False

    def estimate(self, frame: np.ndarray, person_boxes: list[list[float]]) -> str:
        """Estimate closest person distance from monocular depth map.

        Returns "close", "medium", "far", or "none".
        """
        if not person_boxes:
            return "none"
        if not self._load():
            return _bbox_fallback(frame, person_boxes)

        try:
            import cv2
            from PIL import Image

            # Convert BGR to RGB PIL image
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(rgb)

            # Run depth estimation
            result = self._pipe(pil_img)
            depth_map = np.array(result["depth"])  # type: ignore[index]

            # Scale depth map to frame dimensions
            h, w = frame.shape[:2]
            if depth_map.shape[:2] != (h, w):
                depth_map = cv2.resize(depth_map.astype(np.float32), (w, h))

            # Sample depth at person bbox centers — higher value = farther
            min_depth = float("inf")
            for box in person_boxes:
                cx = int((box[0] + box[2]) / 2)
                cy = int((box[1] + box[3]) / 2)
                cx = max(0, min(w - 1, cx))
                cy = max(0, min(h - 1, cy))
                # Sample 5x5 patch around center for robustness
                y0, y1 = max(0, cy - 2), min(h, cy + 3)
                x0, x1 = max(0, cx - 2), min(w, cx + 3)
                patch = depth_map[y0:y1, x0:x1]
                if patch.size > 0:
                    median_depth = float(np.median(patch))
                    min_depth = min(min_depth, median_depth)

            if min_depth == float("inf"):
                return _bbox_fallback(frame, person_boxes)

            # Depth-Anything returns disparity (higher = closer)
            # Normalize to 0-1 range within this frame's depth distribution
            d_min, d_max = float(depth_map.min()), float(depth_map.max())
            if d_max - d_min < 1e-6:
                return "medium"
            normalized = (min_depth - d_min) / (d_max - d_min)

            # Higher normalized value = closer (disparity convention)
            if normalized > 0.6:
                return "close"
            if normalized > 0.3:
                return "medium"
            return "far"

        except Exception:
            log.debug("Depth estimation failed, using bbox fallback", exc_info=True)
            return _bbox_fallback(frame, person_boxes)

    def to_cpu(self) -> None:
        """Release GPU memory."""
        if self._pipe is not None:
            try:
                self._pipe.model.cpu()  # type: ignore[union-attr]
                import torch

                torch.cuda.empty_cache()
            except Exception:
                pass
