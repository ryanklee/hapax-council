"""Multimodal visual observation for DMN reverberation feedback loop.

Uses gemini-flash via LiteLLM to describe the rendered visual surface,
enabling the DMN to detect visual surprises that imagination didn't predict.
"""

from __future__ import annotations

import base64
import logging
import os
from pathlib import Path

log = logging.getLogger("dmn.vision")

VISUAL_OBSERVATION_SYSTEM = """You are observing a visual display surface. Describe what you see
in one concrete sentence: colors, shapes, motion, text fragments, spatial arrangement.
Do not evaluate quality. Do not describe system health. Only describe visual appearance."""

_vision_client = None


def _get_vision_client():
    """Lazy-init AsyncOpenAI client for vision calls via LiteLLM."""
    global _vision_client
    if _vision_client is None:
        from openai import AsyncOpenAI

        _vision_client = AsyncOpenAI(
            base_url="http://localhost:4000",
            api_key=os.environ.get("LITELLM_API_KEY", "sk-dummy"),
        )
    return _vision_client


async def _generate_visual_observation(frame_path: str, imagination_narrative: str) -> str:
    """Describe the rendered visual surface using a vision-capable model."""
    frame = Path(frame_path)
    if not frame.exists():
        return ""
    try:
        b64 = base64.b64encode(frame.read_bytes()).decode()
    except OSError:
        return ""

    client = _get_vision_client()
    try:
        resp = await client.chat.completions.create(
            model="gemini-flash",
            messages=[
                {"role": "system", "content": VISUAL_OBSERVATION_SYSTEM},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
                        },
                        {
                            "type": "text",
                            "text": f"The system intended to show: {imagination_narrative}",
                        },
                    ],
                },
            ],
            temperature=0.1,
            max_tokens=100,
        )
        return resp.choices[0].message.content.strip()
    except Exception:
        log.debug("Visual observation generation failed", exc_info=True)
        return ""
