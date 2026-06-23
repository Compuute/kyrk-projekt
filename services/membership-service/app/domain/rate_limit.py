"""Minimal in-process rate limiter for public (unauthenticated) endpoints.

The public Fredagsskola/Sunday-school enrollment endpoint is the only door
into the service that does not require a bearer token, so it needs a basic
abuse brake. This is a per-key sliding-window counter — good enough as a
first line in front of the edge (Cloudflare) limiting. It holds no PII; the
key is the caller IP only.
"""
from __future__ import annotations

import time
from collections import defaultdict, deque


class InMemoryRateLimiter:
    def __init__(self, max_per_window: int = 5, window_seconds: int = 60) -> None:
        self._max = max_per_window
        self._window = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str, *, now: float | None = None) -> bool:
        """Record a hit for ``key`` and return True if it is within the limit.

        A call that exceeds the limit returns False and is NOT counted, so a
        blocked caller cannot push the window forward forever.
        """
        t = time.monotonic() if now is None else now
        bucket = self._hits[key]
        cutoff = t - self._window
        while bucket and bucket[0] <= cutoff:
            bucket.popleft()
        if len(bucket) >= self._max:
            return False
        bucket.append(t)
        return True
