"""Concurrency test for MusicPolicy._path_b_window_opened_at serialization (D-19)."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from shared.governance.music_policy import (
    MusicDetectionResult,
    MusicPath,
    MusicPolicy,
)


@dataclass
class _DetectorReturningMusic:
    """Always says music is playing — fixture for evaluate() stress."""

    result: MusicDetectionResult

    def detect(self, audio_window: object) -> MusicDetectionResult:
        return self.result


class TestPathBWindowConcurrency:
    def test_concurrent_evaluate_single_window_open(self) -> None:
        """N threads calling evaluate() under Path B — exactly one 'window opened' decision.

        Without the lock, two threads could both observe
        self._path_b_window_opened_at is None, both write ts, and both
        return `window opened` — corrupting the single-window-per-music-
        event invariant.
        """
        detector = _DetectorReturningMusic(
            result=MusicDetectionResult(detected=True, confidence=0.9, source="test")
        )
        policy = MusicPolicy(path=MusicPath.PATH_B, detector=detector, window_s=60.0)
        # Fixed `now` so every thread sees the same clock — isolates the
        # race to the state-read-then-write on _path_b_window_opened_at.
        now = 1000.0
        decisions = []
        with ThreadPoolExecutor(max_workers=32) as ex:
            futures = [ex.submit(policy.evaluate, None, now=now) for _ in range(128)]
            for f in futures:
                decisions.append(f.result())
        # Exactly one evaluate should report 'window opened'; the rest
        # should report 'window open, 0.0/60.0 s elapsed'.
        window_opened = [d for d in decisions if "window opened" in d.reason]
        window_open = [d for d in decisions if "window open," in d.reason]
        assert len(window_opened) == 1, (
            f"expected exactly one window-opened decision under concurrent evaluate; "
            f"got {len(window_opened)} (reasons: {[d.reason for d in window_opened[:3]]})"
        )
        assert len(window_open) == len(decisions) - 1

    def test_reset_window_is_serialized(self) -> None:
        """reset_window() + evaluate() race — no TypeError from partial state."""
        detector = _DetectorReturningMusic(
            result=MusicDetectionResult(detected=True, confidence=0.9)
        )
        policy = MusicPolicy(path=MusicPath.PATH_B, detector=detector, window_s=30.0)

        def evaluator(n: int) -> None:
            for _ in range(n):
                policy.evaluate(None)

        def resetter(n: int) -> None:
            for _ in range(n):
                policy.reset_window()

        with ThreadPoolExecutor(max_workers=8) as ex:
            futures = []
            for _ in range(4):
                futures.append(ex.submit(evaluator, 100))
            for _ in range(4):
                futures.append(ex.submit(resetter, 100))
            # If the lock weren't there, some of these could raise
            # TypeError (None - float) from reading _path_b_window_opened_at
            # after it's been reset mid-compute. The test passes iff no
            # exceptions propagate.
            for f in futures:
                f.result()
