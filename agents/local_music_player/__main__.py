"""Entrypoint: ``uv run python -m agents.local_music_player``.

Phase 4b: spins up a MusicProgrammer on top of the player so the
daemon auto-recruits the next track when one ends. The repos the
programmer queries are loaded fresh on each ``select_next()`` call.

Per the 2026-04-24 directive, the programmer also draws from an
interstitial repo (Epidemic Sound found-sounds + WWII-peak American
radio newsclips) and inserts brief accents between music tracks at
the configured cadence (default 1 music : 2 interstitials).
"""

from __future__ import annotations

import logging
import sys

from agents.local_music_player.player import LocalMusicPlayer, PlayerConfig
from agents.local_music_player.programmer import MusicProgrammer, ProgrammerConfig
from shared.music_repo import LocalMusicRepo

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    cfg = PlayerConfig.from_env()
    prog_cfg = ProgrammerConfig.from_env()
    local_repo = LocalMusicRepo(path=cfg.repo_path)
    local_repo.load()
    sc_repo = LocalMusicRepo(path=cfg.sc_repo_path)
    sc_repo.load()
    interstitial_repo: LocalMusicRepo | None = None
    if prog_cfg.interstitial_enabled and prog_cfg.interstitial_repo_path.exists():
        interstitial_repo = LocalMusicRepo(path=prog_cfg.interstitial_repo_path)
        interstitial_repo.load()
    programmer = MusicProgrammer(
        prog_cfg,
        local_repo=local_repo,
        sc_repo=sc_repo,
        interstitial_repo=interstitial_repo,
    )
    sys.exit(LocalMusicPlayer(cfg, programmer=programmer).run())
