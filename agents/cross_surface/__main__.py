"""Daemon entry — `python -m agents.cross_surface` (Discord webhook poster).

Phase 1 invokes the Discord poster directly. Future Phase 2 / 3 add
Bluesky + Mastodon as separate sub-daemons; this entry chooses
Discord by default.
"""

from agents.cross_surface.discord_webhook import main

if __name__ == "__main__":
    main()
