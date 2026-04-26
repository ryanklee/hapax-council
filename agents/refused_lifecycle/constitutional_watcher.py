"""Type-B constitutional-refusal watcher (filesystem inotify).

Daemon that watches the canonical constitutional surfaces (axiom registry,
manifesto, refusal-brief, MEMORY.md). On any change, walks all type-B
REFUSED tasks and re-evaluates against the current axiom state. NO
clock-poll — events are atomic, axioms are stable until amended.

Probe semantics for type-B (per spec §2.B): the lift-condition is the
*removal* of an axiom-tag or feedback-rule from the watched file, NOT its
presence. The ``evaluation_probe.lift_polarity`` field discriminates:
``absent`` (default for type-B) means keyword absent ⇒ lift detected.

Daemon I/O wires watchdog filesystem-event observers to the probe layer.
The pure ``probe_constitutional`` decision logic is unit-tested; the
event-loop and debounce machinery is smoke-tested via systemd in
production.

Spec: ``docs/research/2026-04-25-refused-lifecycle-pipeline.md`` §2.B.
"""

from __future__ import annotations

import logging
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from agents.refused_lifecycle import runner
from agents.refused_lifecycle.evaluator import decide_transition
from agents.refused_lifecycle.metrics import probe_failures_total, probes_total
from agents.refused_lifecycle.state import ProbeResult, RefusalTask

log = logging.getLogger(__name__)


WATCHED_PATHS: tuple[Path, ...] = (
    Path.home() / "projects/hapax-constitution/axioms/registry.yaml",
    Path.home() / "Documents/Personal/30-areas/hapax/manifesto.md",
    Path.home() / "Documents/Personal/30-areas/hapax/refusal-brief.md",
    Path.home() / ".claude/projects/-home-hapax-projects/memory/MEMORY.md",
)

DEBOUNCE_SECONDS = 2.0
SNIPPET_MAX_CHARS = 500
SNIPPET_HALF_WINDOW = 200


def _extract_snippet(text: str, keywords: list[str]) -> str:
    """Return ≤500 chars around the first matching keyword, or leading 500."""
    lower = text.lower()
    for kw in keywords:
        idx = lower.find(kw.lower())
        if idx == -1:
            continue
        start = max(0, idx - SNIPPET_HALF_WINDOW)
        end = min(len(text), idx + len(kw) + SNIPPET_HALF_WINDOW)
        return text[start:end][:SNIPPET_MAX_CHARS]
    return text[:SNIPPET_MAX_CHARS]


def probe_constitutional(task: RefusalTask, changed_paths: set[Path]) -> ProbeResult:
    """Evaluate a type-B task against the set of recently-changed paths.

    Pure: no global state, no I/O outside reading the configured target
    file. Returns a ProbeResult discriminating between still-prohibited
    (``changed=False``) and lift-detected (``changed=True`` + snippet).

    The polarity of ``lift_keywords`` matters:
    - ``absent``: keyword absent from the file ⇒ lift (typical type-B —
      axiom retired, refusal lifts)
    - ``present``: keyword present ⇒ lift (rare for type-B but supported
      for the multi-classified ``cold-contact-alphaxiv-comments`` slug)
    """
    probes_total.labels(trigger="constitutional", slug=task.slug).inc()

    probe = task.evaluation_probe or {}
    conditional_path = probe.get("conditional_path")
    if not conditional_path:
        probe_failures_total.labels(
            trigger="constitutional", slug=task.slug, reason="no-path"
        ).inc()
        return ProbeResult(changed=False, error="no conditional_path configured")

    target = Path(conditional_path).expanduser()

    if target not in changed_paths:
        # Inotify event was for an unrelated watched file
        return ProbeResult(changed=False)

    try:
        content = target.read_text(encoding="utf-8")
    except OSError as exc:
        probe_failures_total.labels(
            trigger="constitutional", slug=task.slug, reason="read-error"
        ).inc()
        return ProbeResult(changed=False, error=f"read: {exc!r}")

    keywords = probe.get("lift_keywords") or []
    polarity = probe.get("lift_polarity", "absent")
    content_lower = content.lower()
    keyword_present = any(kw.lower() in content_lower for kw in keywords)

    if polarity == "absent":
        # Type-B default: keyword still in file → still prohibited
        if keyword_present:
            return ProbeResult(changed=False)
        # Keyword removed — lift detected; capture leading context as evidence
        snippet = content[:SNIPPET_MAX_CHARS]
        return ProbeResult(changed=True, evidence_url=str(target), snippet=snippet)

    # polarity == "present" — keyword appearing means lift (rare for type-B)
    if not keyword_present:
        return ProbeResult(changed=False)
    snippet = _extract_snippet(content, keywords)
    return ProbeResult(changed=True, evidence_url=str(target), snippet=snippet)


class _ConstitutionalEventHandler(FileSystemEventHandler):
    """Collect changed-paths into a set; debounce window flushes them."""

    def __init__(self) -> None:
        self.changed: set[Path] = set()

    def on_modified(self, event):
        if event.is_directory:
            return
        try:
            p = Path(event.src_path).resolve()
        except (OSError, RuntimeError):
            return
        if p in {wp.resolve() for wp in WATCHED_PATHS}:
            self.changed.add(p)

    def on_moved(self, event):
        if event.is_directory:
            return
        try:
            p = Path(event.dest_path).resolve()
        except (OSError, RuntimeError):
            return
        if p in {wp.resolve() for wp in WATCHED_PATHS}:
            self.changed.add(p)


def _re_evaluate_type_b(now: datetime, changed_paths: set[Path]) -> int:
    """Walk all REFUSED type-B tasks and dispatch decisions; return event count."""
    count = 0
    for task in runner.iter_refused_tasks():
        if "constitutional" not in task.evaluation_trigger:
            continue
        result = probe_constitutional(task, changed_paths)
        event = decide_transition(task, [result])
        runner.apply_transition(Path(task.path), task, event, now)
        count += 1
    return count


def main(argv: list[str] | None = None) -> int:
    """Always-on inotify daemon. ``Type=simple`` in systemd."""
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--once", action="store_true", help="Re-evaluate all type-B tasks once and exit"
    )
    args = parser.parse_args(argv)

    if args.once:
        # Treat all watched paths as if they just changed; useful for boot
        # and for `systemctl --user start hapax-refused-lifecycle-constitutional`
        now = datetime.now(UTC)
        changed = {p for p in WATCHED_PATHS if p.exists()}
        count = _re_evaluate_type_b(now, changed)
        print(f"constitutional-watcher (--once): re-evaluated {count} type-B tasks")
        return 0

    handler = _ConstitutionalEventHandler()
    observer = Observer()
    watched_dirs = {wp.parent for wp in WATCHED_PATHS if wp.parent.exists()}
    for parent in watched_dirs:
        observer.schedule(handler, str(parent), recursive=False)
    observer.start()
    log.info("constitutional-watcher started; watching %d dirs", len(watched_dirs))

    try:
        while True:
            time.sleep(DEBOUNCE_SECONDS)
            if not handler.changed:
                continue
            # Snapshot + clear under non-atomic single-thread access; a small
            # window where new events are missed is acceptable since the
            # next debounce tick will pick them up.
            changed = handler.changed
            handler.changed = set()
            now = datetime.now(UTC)
            count = _re_evaluate_type_b(now, changed)
            log.info("re-evaluated %d type-B tasks after %d path changes", count, len(changed))
    finally:
        observer.stop()
        observer.join(timeout=5)
    return 0


if __name__ == "__main__":
    sys.exit(main())


__all__ = [
    "DEBOUNCE_SECONDS",
    "SNIPPET_MAX_CHARS",
    "WATCHED_PATHS",
    "main",
    "probe_constitutional",
    "probe_failures_total",
    "probes_total",
]
