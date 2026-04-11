from __future__ import annotations

from typing import Protocol


class RateLimiterPort(Protocol):
    def check(self, key: str) -> bool:
        """Return True if the action is allowed, False if the key is over the limit."""
        ...
