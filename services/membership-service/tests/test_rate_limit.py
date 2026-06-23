"""Unit tests for the public-endpoint rate limiter."""
from __future__ import annotations

from app.domain.rate_limit import InMemoryRateLimiter


def test_allows_up_to_the_limit_then_blocks():
    rl = InMemoryRateLimiter(max_per_window=3, window_seconds=60)
    assert [rl.allow("ip", now=0.0) for _ in range(3)] == [True, True, True]
    assert rl.allow("ip", now=0.0) is False


def test_keys_are_independent():
    rl = InMemoryRateLimiter(max_per_window=1, window_seconds=60)
    assert rl.allow("a", now=0.0) is True
    assert rl.allow("a", now=0.0) is False
    assert rl.allow("b", now=0.0) is True  # different caller unaffected


def test_window_slides_so_old_hits_expire():
    rl = InMemoryRateLimiter(max_per_window=2, window_seconds=60)
    assert rl.allow("ip", now=0.0) is True
    assert rl.allow("ip", now=1.0) is True
    assert rl.allow("ip", now=2.0) is False        # both still within 60s
    assert rl.allow("ip", now=61.5) is True        # first hit (t=0) has expired


def test_blocked_call_does_not_extend_window():
    # A rejected call must not be recorded, else a spammer keeps the window full.
    rl = InMemoryRateLimiter(max_per_window=1, window_seconds=10)
    assert rl.allow("ip", now=0.0) is True
    assert rl.allow("ip", now=5.0) is False        # blocked, not recorded
    assert rl.allow("ip", now=10.5) is True        # only the t=0 hit aged out
