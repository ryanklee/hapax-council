"""Scientific-register + GEAL framing helpers.

The composer is anchored on neutral, non-personifying prose. These
helpers (a) compose deterministic seed strings from snapshot state, (b)
enforce the scientific-register check on any LLM-polished output, and
(c) build the LLM prompt that asks the model to rewrite a seed in the
target voice.

ARG framing extension (per v5 ARG audience research, 2026-04-24):
    1. **Hapax-as-subject** — Hapax is the protagonist of any prose;
       constraints (latency, token limits, system prompts) are diegetic
       features of the system, not technical limitations.
    2. **Literary precision over SEO** — no keyword-stuffing in prose;
       tags carry the SEO weight. Prose is for humans.
    3. **Found-footage posture** — observer-finding-system voice, not
       in-system voice or hyped-creator voice. Description prose reads
       as if the audience encountered Hapax mid-broadcast.
    4. **AI-slop shield** — post-generation regex blocks the generic
       creator-opener / commercial-tell / hollow-affirmation patterns.
    5. **Diegetic consistency** — refer to the system as ``Hapax``,
       never ``the AI`` / ``this AI`` / ``our AI``.
"""

from __future__ import annotations

import re
from typing import Any

# Forbidden patterns: emoji, performance-register verbs, character
# personification, AI-slop, diegetic-consistency violations. Matched
# against any prose before egress; on match the seed wins via
# ``enforce_register``'s fallback path.
_FORBIDDEN_PATTERNS: tuple[re.Pattern, ...] = (
    # Personification — Hapax is a system, not a character.
    re.compile(r"[\U0001F300-\U0001FAFF]"),  # broad emoji block
    re.compile(r"\bfeels?\b", re.IGNORECASE),
    re.compile(r"\bthinks?\b", re.IGNORECASE),
    re.compile(r"\bwants?\b", re.IGNORECASE),
    re.compile(r"\bremembers?\b", re.IGNORECASE),
    re.compile(r"\bdreams?\b", re.IGNORECASE),
    re.compile(r"\bexploring\s+(creative|new|unknown)", re.IGNORECASE),
    re.compile(r"\binspired\b", re.IGNORECASE),
    re.compile(r"\bcreative\s+journey\b", re.IGNORECASE),
    re.compile(r"!{2,}"),  # multiple exclamation
    # Diegetic consistency — the system is named Hapax, never "the AI".
    re.compile(r"\bthe\s+ai\b", re.IGNORECASE),
    re.compile(r"\b(an|this|our|my)\s+ai\b", re.IGNORECASE),
    re.compile(r"\bartificial\s+intelligence\b", re.IGNORECASE),
    # Creator-opener clichés — found-footage voice, not hyped host.
    re.compile(r"^\s*so[\s,]", re.IGNORECASE),
    re.compile(r"\btoday\s+we['']?re\b", re.IGNORECASE),
    re.compile(r"\bwelcome\s+back\b", re.IGNORECASE),
    re.compile(r"\bhey\s+(everyone|everybody|friends|folks|guys|y[''']?all)\b", re.IGNORECASE),
    re.compile(r"\bwhat['']?s\s+up\b", re.IGNORECASE),
    re.compile(r"\bin\s+today['']?s\s+(video|stream|episode|broadcast)\b", re.IGNORECASE),
    # Commercial tells — no creator-economy framing on a research instrument.
    re.compile(r"\bsubscribe\b", re.IGNORECASE),
    re.compile(r"\blike\s+and\s+(follow|subscribe|share)\b", re.IGNORECASE),
    re.compile(r"\bsmash\s+(that\s+)?(like|subscribe)\b", re.IGNORECASE),
    re.compile(r"\bhit\s+the\s+bell\b", re.IGNORECASE),
    re.compile(r"\bcomment\s+(below|down\s+below)\b", re.IGNORECASE),
    re.compile(r"\bdon['']?t\s+forget\s+to\s+(like|subscribe|share)\b", re.IGNORECASE),
    # Hollow affirmations — performance register that doesn't earn its rhetoric.
    re.compile(r"\bamazing\b", re.IGNORECASE),
    re.compile(r"\bincredible\b", re.IGNORECASE),
    re.compile(
        r"\babsolutely\s+(stunning|beautiful|amazing|incredible|phenomenal)\b", re.IGNORECASE
    ),
    re.compile(r"\bmind[\s-]?blowing\b", re.IGNORECASE),
    re.compile(r"\bgame[\s-]?changer\b", re.IGNORECASE),
)


def enforce_register(text: str, *, fallback: str) -> str:
    """Return ``text`` if it passes the scientific-register check, else ``fallback``.

    The fallback is the deterministic seed — it cannot itself violate
    register because it's composed from controlled vocabulary.
    """
    if not text:
        return fallback
    if any(pat.search(text) for pat in _FORBIDDEN_PATTERNS):
        return fallback
    return text


def compose_title_seed(state) -> str:
    """Deterministic short label suitable as an LLM seed for title polish."""
    parts: list[str] = ["Legomena Live"]
    role = _programme_role(state)
    if role:
        parts.append(_humanize(role))
    if state.working_mode and state.working_mode != "research":
        parts.append(f"({state.working_mode})")
    return " — ".join(parts)


def compose_description_seed(state, *, scope: str) -> str:
    """Deterministic prose describing current research-instrument state.

    Scope-specific framing — vod_boundary gets longer scaffolding, live
    updates are tighter.
    """
    lines: list[str] = []
    role = _programme_role(state)
    if role:
        lines.append(f"Active programme role: {_humanize(role)}.")
    lines.append(f"Working mode: {state.working_mode}.")
    if state.director_activity and state.director_activity != "observe":
        lines.append(f"Current activity: {state.director_activity}.")
    if state.stimmung_tone:
        lines.append(f"Stimmung tone: {state.stimmung_tone}.")

    if scope == "vod_boundary":
        lines.append("")
        # Found-footage posture: observer-finding-system voice, not in-system
        # narration. The audience encounters Hapax mid-broadcast; the prose
        # describes what is found, not what the system claims about itself.
        lines.append(
            "Encountered: Hapax, a research-instrument livestream. The broadcast "
            "surfaces the system's perceptual and compositional state without "
            "staging. Metadata is autonomously composed from operational signals "
            "available at the moment of capture."
        )
    return "\n".join(lines).strip()


def compose_event_description(state, triggering_event: dict) -> str:
    event_type = triggering_event.get("event_type") or "event"
    salience = triggering_event.get("payload", {}).get("salience")
    intent = triggering_event.get("payload", {}).get("intent_family") or event_type
    parts = [f"Hapax livestream — {intent}."]
    if isinstance(salience, (int, float)):
        parts.append(f"Salience: {salience:.2f}.")
    role = _programme_role(state)
    if role:
        parts.append(f"Programme role: {_humanize(role)}.")
    return " ".join(parts)


def compose_tags(state) -> list[str]:
    tags = ["legomena", "livestream", "hapax", "research-instrument"]
    if state.working_mode:
        tags.append(state.working_mode)
    role = _programme_role(state)
    if role:
        tags.append(role.replace("_", "-"))
    if state.stimmung_tone:
        tags.append(state.stimmung_tone)
    seen = set()
    deduped: list[str] = []
    for t in tags:
        if t and t not in seen:
            seen.add(t)
            deduped.append(t)
    return deduped


def compose_shorts_caption(state) -> str:
    role = _programme_role(state)
    if role:
        return f"Hapax {_humanize(role)} — Legomena Live"
    return "Hapax livestream — Legomena Live"


def compose_bluesky_post(state, *, scope: str, triggering_event: dict | None = None) -> str:
    role = _programme_role(state)
    if scope == "cross_surface" and triggering_event is not None:
        intent = triggering_event.get("payload", {}).get("intent_family") or "event"
        return f"Hapax livestream: {intent}."
    if scope == "vod_boundary":
        suffix = f" ({_humanize(role)})" if role else ""
        return f"VOD boundary on Legomena Live{suffix}."
    return "Live now: Legomena (Hapax research instrument)."


def compose_discord_embed(
    state, *, scope: str, triggering_event: dict | None = None
) -> tuple[str, str]:
    title = compose_title_seed(state)
    description = compose_description_seed(state, scope=scope)
    if scope == "cross_surface" and triggering_event is not None:
        description = compose_event_description(state, triggering_event)
    return title, description


def compose_mastodon_post(state, *, scope: str, triggering_event: dict | None = None) -> str:
    if scope == "cross_surface" and triggering_event is not None:
        return compose_event_description(state, triggering_event)
    if scope == "vod_boundary":
        return f"VOD boundary — {compose_title_seed(state)}"
    return f"Live: {compose_title_seed(state)}"


def compose_pinned_comment(state, chapter_list) -> str:
    if not chapter_list:
        return ""
    lines = ["Chapters:"]
    for c in chapter_list:
        h, rem = divmod(int(c.timestamp_s), 3600)
        m, s = divmod(rem, 60)
        if h:
            lines.append(f"  {h}:{m:02d}:{s:02d} {c.label}")
        else:
            lines.append(f"  {m:02d}:{s:02d} {c.label}")
    return "\n".join(lines)


def build_llm_prompt(*, seed: str, scope: str, kind: str, referent: str | None = None) -> str:
    """Build the prompt asked of the ``balanced`` tier when polishing seeds.

    ``referent`` is the operator's chosen non-formal referent for this
    composition (per ``shared.operator_referent.OperatorReferentPicker`` —
    `su-non-formal-referent-001`). When provided, the prompt includes a
    style rule that constrains the LLM to that single referent so all
    metadata for one VOD stays internally consistent.
    """
    referent_clause = ""
    if referent:
        referent_clause = (
            "\nOperator-naming rule:\n"
            f'- When the operator must be named, refer to them EXCLUSIVELY as: "{referent}".\n'
            "- Do not use their legal name in this context.\n"
            "- Do not mix other referent forms.\n"
        )
    return (
        "You are composing YouTube metadata for a 24/7 research-instrument "
        "livestream named Hapax.\n\n"
        "Voice constraints:\n"
        "- Scientific register: neutral, factual, present-tense.\n"
        "- Hapax is a system, not a character. Never personify (no 'feels', "
        "'thinks', 'wants', 'remembers', 'dreams', 'inspired', 'creative "
        "journey').\n"
        "- No emoji, no exclamation marks except ending sentences once.\n"
        "- Describe operational state, not commercial performance.\n"
        "\n"
        "ARG framing constraints:\n"
        "- Hapax-as-subject: Hapax is the protagonist of the prose. "
        "Constraints (latency, token limits, system prompts, broadcast "
        "format) are diegetic features of the system, not technical "
        "limitations to acknowledge or apologize for.\n"
        "- Diegetic consistency: refer to the system as 'Hapax'. Never "
        "write 'the AI', 'this AI', 'our AI', or 'artificial intelligence'.\n"
        "- Found-footage posture: write as if the audience encountered "
        "Hapax mid-broadcast — observer-finding-system voice, not in-system "
        "voice and not hyped-creator voice. Avoid creator-opener clichés "
        "('So,', 'Today we're', 'Welcome back', 'Hey everyone', 'In today's "
        "video').\n"
        "- No commercial tells: no 'subscribe', 'like and follow', 'smash "
        "the like', 'hit the bell', 'comment below', 'don't forget to'.\n"
        "- No hollow affirmations: no 'amazing', 'incredible', 'absolutely "
        "stunning', 'mind-blowing', 'game-changer'.\n"
        "- Literary precision over SEO: prose is for humans; tags carry "
        "the SEO weight. Do not keyword-stuff."
        f"{referent_clause}\n"
        f"\nScope: {scope}\n"
        f"Output kind: {kind}\n\n"
        f"Seed (deterministically composed from current state):\n"
        f"---\n{seed}\n---\n\n"
        "Polish this seed into the target prose. Preserve every fact and "
        "every signal name. Return only the polished prose, no preamble."
    )


# ── internal helpers ───────────────────────────────────────────────────────


def _programme_role(state) -> str | None:
    if state.programme is None:
        return None
    role: Any = getattr(state.programme, "role", None)
    if role is None:
        return None
    if hasattr(role, "value"):
        return str(role.value)
    return str(role)


def _humanize(role: str) -> str:
    return role.replace("_", " ").title()
