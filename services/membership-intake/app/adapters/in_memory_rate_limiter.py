"""Simple fixed-window in-memory rate limiter.

Production should swap this for a Redis-backed limiter so the window is
shared across Cloud Run instances.
"""
from __future__ import annotations

import time


class InMemoryRateLimiter:
    def __init__(self, max_hits: int = 5, window_seconds: int = 60) -> None:
        self._max = max_hits
        self._window = window_seconds
        self._log: dict[str, list[float]] = {}

    def check(self, key: str) -> bool:
        now = time.monotonic()
        window_start = now - self._window
        hits = [t for t in self._log.get(key, []) if t >= window_start]
        if len(hits) >= self._max:
            self._log[key] = hits
            return False
        hits.append(now)
        self._log[key] = hits
        return True
