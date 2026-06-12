"""Firestore-backed fixed-window rate limiter, shared across instances.

The in-memory limiter keeps its window per Cloud Run instance, so the
effective limit multiplies with scale-out. This limiter keeps one counter
document per (key, window) so every instance sees the same count: one read
plus at most one write per check, no composite index (the window index is
encoded in the document id).

Concurrency note: the read-then-write is deliberately not transactional.
Two instances can read the same count simultaneously and both allow, so a
burst may exceed max_hits by at most the number of concurrent instances —
acceptable for abuse limiting, and Increment() keeps the stored count
itself correct. A transaction would add a retry loop and contention on the
hot path for no practical gain here.

Documents carry `expires_at` (two windows ahead); point a Firestore TTL
policy at that field on the `rate_limit_windows` collection to
garbage-collect old windows.
"""
from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from google.cloud.firestore import Client  # pragma: no cover

_COLLECTION = "rate_limit_windows"


class FirestoreRateLimiter:
    def __init__(
        self,
        max_hits: int = 5,
        window_seconds: int = 60,
        client: "Client | None" = None,
        now_fn: Callable[[], float] = time.time,
    ) -> None:
        self._max = max_hits
        self._window = window_seconds
        self._client = client
        self._now_fn = now_fn

    def _coll(self):
        if self._client is None:
            from google.cloud import firestore  # pragma: no cover

            self._client = firestore.Client()
        return self._client.collection(_COLLECTION)

    def check(self, key: str) -> bool:
        now = self._now_fn()
        window_index = int(now // self._window)
        # "/" is the only character a Firestore doc id cannot contain.
        doc_id = f"{key.replace('/', '_')}|{window_index}"
        ref = self._coll().document(doc_id)

        snap = ref.get()
        count = (snap.to_dict() or {}).get("count", 0) if snap.exists else 0
        if count >= self._max:
            return False

        from google.cloud.firestore import Increment

        expires_at = datetime.fromtimestamp(
            (window_index + 2) * self._window, tz=timezone.utc
        )
        ref.set({"count": Increment(1), "expires_at": expires_at}, merge=True)
        return True
