"""LRR Phase 8 item 11 — environmental salience → compositor emphasis.

When a high-salience ambient signal co-occurs with an active research
objective that lists ``observe`` or ``react`` in its
``activities_that_advance`` list, the compositor briefly emphasizes the
relevant surface — hero-mode on the appropriate camera, with a short
hysteresis-bounded lifetime so the stream doesn't jitter.

Pure recommendation layer. Consumer (systemd timer / compositor
integration) decides whether to act on the recommendation. Injection
seams keep the tests hermetic; production callers rely on the
filesystem-reader defaults.

Scope for the first ship:

* **Salience input:** ``ir_hand_activity`` on the overhead Pi NoIR (the
  signal that most reliably indicates the operator is doing something
  visible and worth foregrounding). Numeric-scored as 0.0 / 0.5 / 1.0 for
  ``none`` / ``light`` / ``active``.
* **Gate:** at least one active objective lists ``observe`` or ``react``.
* **Output:** a recommended camera role (``"hardware"`` for hand activity
  at the overhead / desk Pi, ``"operator"`` when the signal is weak-but-
  present and the objective prefers ``operator`` framing).
* **Hysteresis:** 30s minimum between emphasis events. The recommender
  returns ``None`` inside that window; callers reset their last-emphasis
  timestamp externally so the same seam works across restarts.

Not shipped here (explicit follow-ups):

* Overlay highlight on active object — needs a compositor highlight
  surface that doesn't exist yet.
* Audio duck on competing sources — needs PipeWire-side sink routing,
  owned by ``agents/hapax_daimonion``.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

IR_STATE_DIR = Path.home() / "hapax-state" / "pi-noir"
DEFAULT_OBJECTIVES_DIR = Path.home() / "Documents" / "Personal" / "30-areas" / "hapax-objectives"

HYSTERESIS_SECONDS: float = 30.0
SALIENCE_MIN_SCORE: float = 0.5  # "light" hand activity or better
SALIENCE_HIGH_SCORE: float = 1.0  # "active" hand activity

HAND_ACTIVITY_SCORE: dict[str, float] = {
    "none": 0.0,
    "light": 0.5,
    "active": 1.0,
}

# observe / react objectives → preferred hero camera for environmental events.
OBSERVE_HERO: str = "hardware"
REACT_HERO: str = "hardware"


@dataclass(frozen=True)
class EmphasisRecommendation:
    camera_role: str
    reason: str
    salience_score: float
    ttl_seconds: float = 8.0


IrReader = Callable[[], dict[str, dict[str, Any]]]
ObjectivesReader = Callable[[], list[dict[str, Any]]]


# ── IR reader default implementation ────────────────────────────────────────


def _default_ir_reader(directory: Path | None = None) -> dict[str, dict[str, Any]]:
    """Read Pi NoIR snapshot JSONs; return {role: payload}.

    Resolves ``IR_STATE_DIR`` at call time so tests can monkeypatch the
    module-level constant.
    """
    directory = directory or IR_STATE_DIR
    out: dict[str, dict[str, Any]] = {}
    if not directory.is_dir():
        return out
    for p in directory.glob("*.json"):
        try:
            out[p.stem] = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            log.debug("ir state unreadable at %s", p, exc_info=True)
    return out


# ── Objectives reader default implementation ────────────────────────────────


def _default_objectives_reader(directory: Path | None = None) -> list[dict[str, Any]]:
    """Read active objective frontmatter dicts.

    Resolves ``DEFAULT_OBJECTIVES_DIR`` at call time so tests can
    monkeypatch the module-level constant.
    """
    directory = directory or DEFAULT_OBJECTIVES_DIR
    if not directory.is_dir():
        return []
    import yaml

    out: list[dict[str, Any]] = []
    for md in directory.glob("*.md"):
        try:
            text = md.read_text(encoding="utf-8")
        except OSError:
            continue
        if not text.startswith("---"):
            continue
        end = text.find("\n---", 3)
        if end == -1:
            continue
        try:
            frontmatter = yaml.safe_load(text[3:end])
        except yaml.YAMLError:
            continue
        if isinstance(frontmatter, dict) and frontmatter.get("status") == "active":
            out.append(frontmatter)
    return out


# ── Salience scoring ────────────────────────────────────────────────────────


def _score_ir_hand_salience(ir_states: dict[str, dict[str, Any]]) -> float:
    """Return the max ``ir_hand_activity`` score across all Pi roles.

    The overhead Pi is the primary source; desk is secondary. We take
    the max so any Pi reporting active hand activity promotes the signal.
    """
    best = 0.0
    for _role, payload in ir_states.items():
        if not isinstance(payload, dict):
            continue
        label = payload.get("ir_hand_activity") or payload.get("hand_activity")
        if not isinstance(label, str):
            continue
        score = HAND_ACTIVITY_SCORE.get(label, 0.0)
        if score > best:
            best = score
    return best


def _objective_prefers_emphasis(objectives: list[dict[str, Any]]) -> str | None:
    """Return the matching activity label (``observe`` / ``react``) if any
    active objective requests it, else ``None``.

    ``react`` wins over ``observe`` — a react-mode objective is the
    stronger signal that the operator wants live environmental hand-off.
    """
    matched_observe = False
    for obj in objectives:
        activities = obj.get("activities_that_advance") or []
        if not isinstance(activities, (list, tuple)):
            continue
        if "react" in activities:
            return "react"
        if "observe" in activities:
            matched_observe = True
    return "observe" if matched_observe else None


# ── Top-level recommender ───────────────────────────────────────────────────


def recommend_emphasis(
    *,
    now_monotonic: float,
    last_emphasis_at: float,
    ir_reader: IrReader | None = None,
    objectives_reader: ObjectivesReader | None = None,
    hysteresis_seconds: float = HYSTERESIS_SECONDS,
) -> EmphasisRecommendation | None:
    """Decide whether to emphasize a surface right now.

    Returns ``None`` unless (a) an active objective requests ``observe``
    or ``react``, (b) an IR hand-activity signal scores at least
    ``SALIENCE_MIN_SCORE``, and (c) the hysteresis window has elapsed.
    """
    if now_monotonic - last_emphasis_at < hysteresis_seconds:
        return None

    objectives = (objectives_reader or _default_objectives_reader)()
    matched_activity = _objective_prefers_emphasis(objectives)
    if matched_activity is None:
        return None

    ir_states = (ir_reader or _default_ir_reader)()
    salience = _score_ir_hand_salience(ir_states)
    if salience < SALIENCE_MIN_SCORE:
        return None

    # React always hero-switches to hardware; observe only on the
    # higher-salience threshold so the stream isn't emphasizing every
    # passing hand.
    if matched_activity == "react":
        role = REACT_HERO
    elif salience >= SALIENCE_HIGH_SCORE:
        role = OBSERVE_HERO
    else:
        return None

    reason = f"ir_hand_activity={salience:.2f} + objective_activity={matched_activity}"
    return EmphasisRecommendation(camera_role=role, reason=reason, salience_score=salience)
