#!/usr/bin/env python3
"""Mock YouTube chat for testing Hapax's chat awareness.

Writes messages directly to /dev/shm/hapax-compositor/chat-recent.json
and chat-state.json, bypassing the chat-monitor entirely. Use this
during practice mode when there's no live YouTube stream.

Usage:
  # Interactive mode — type messages as a viewer:
  python scripts/mock-chat.py

  # As Oudepode:
  python scripts/mock-chat.py --as oudepode

  # Single message:
  python scripts/mock-chat.py "what is this"

  # Single message as Oudepode:
  python scripts/mock-chat.py --as oudepode "nice one hapax"
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

SHM_DIR = Path("/dev/shm/hapax-compositor")
RECENT_FILE = SHM_DIR / "chat-recent.json"
STATE_FILE = SHM_DIR / "chat-state.json"

# Rolling buffer of recent messages
_messages: list[dict] = []
_total: int = 0
_authors: set[str] = set()


def _load_existing() -> None:
    global _messages, _total, _authors
    try:
        if RECENT_FILE.exists():
            _messages = json.loads(RECENT_FILE.read_text())
        if STATE_FILE.exists():
            state = json.loads(STATE_FILE.read_text())
            _total = state.get("total_messages", 0)
            _authors = set()
    except Exception:
        pass


def send(text: str, author: str = "viewer") -> None:
    global _total
    _messages.append({"author": author, "text": text})
    # Keep last 5
    while len(_messages) > 5:
        _messages.pop(0)
    _total += 1
    _authors.add(author)

    SHM_DIR.mkdir(parents=True, exist_ok=True)
    RECENT_FILE.write_text(json.dumps(_messages))
    STATE_FILE.write_text(
        json.dumps(
            {
                "unique_authors": len(_authors),
                "total_messages": _total,
                "mattr": 0.75,
                "hapax_ratio": 0.4,
                "novel_rate": 0.5,
                "updated": time.time(),
            }
        )
    )
    print(f"  [{author}] {text}")


def main() -> None:
    _load_existing()

    as_author = "viewer"
    args = sys.argv[1:]

    if "--as" in args:
        idx = args.index("--as")
        as_author = args[idx + 1]
        args = args[:idx] + args[idx + 2 :]

    # Single message mode
    if args:
        send(" ".join(args), as_author)
        return

    # Interactive mode
    print(f"Mock chat (as {as_author}). Type messages, Ctrl+C to quit.")
    print("  /as <name>  — switch author")
    print("  /clear      — clear chat")
    print()
    try:
        while True:
            try:
                line = input(f"[{as_author}] > ").strip()
            except EOFError:
                break
            if not line:
                continue
            if line.startswith("/as "):
                as_author = line[4:].strip()
                print(f"  Now chatting as: {as_author}")
                continue
            if line == "/clear":
                _messages.clear()
                RECENT_FILE.write_text("[]")
                print("  Chat cleared.")
                continue
            send(line, as_author)
    except KeyboardInterrupt:
        print("\nDone.")


if __name__ == "__main__":
    main()
