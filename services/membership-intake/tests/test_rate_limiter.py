"""Tests for the Firestore-backed rate limiter (shared across instances).

The in-memory limiter is per Cloud Run instance, so production scale-out
silently weakens the limit (debt item #4 in docs/28). The Firestore
limiter shares one fixed window per key across all instances.
"""
from unittest.mock import MagicMock

from app.adapters.firestore_rate_limiter import FirestoreRateLimiter


def _limiter(max_hits=3, window_seconds=60, now=1_000_000.0, existing_count=None):
    """Build a limiter against a mocked Firestore client.

    existing_count=None means the window document does not exist yet.
    Returns (limiter, document_ref_mock, collection_mock).
    """
    client = MagicMock()
    coll = client.collection.return_value
    ref = coll.document.return_value
    snap = ref.get.return_value
    if existing_count is None:
        snap.exists = False
        snap.to_dict.return_value = None
    else:
        snap.exists = True
        snap.to_dict.return_value = {"count": existing_count}
    limiter = FirestoreRateLimiter(
        max_hits=max_hits,
        window_seconds=window_seconds,
        client=client,
        now_fn=lambda: now,
    )
    return limiter, ref, coll


def test_first_hit_in_window_is_allowed_and_recorded():
    limiter, ref, _ = _limiter(existing_count=None)
    assert limiter.check("ip:1.2.3.4") is True
    ref.set.assert_called_once()
    _, kwargs = ref.set.call_args
    assert kwargs.get("merge") is True


def test_under_limit_is_allowed():
    limiter, ref, _ = _limiter(max_hits=3, existing_count=2)
    assert limiter.check("ip:1.2.3.4") is True
    ref.set.assert_called_once()


def test_at_limit_is_blocked_without_write():
    limiter, ref, _ = _limiter(max_hits=3, existing_count=3)
    assert limiter.check("ip:1.2.3.4") is False
    ref.set.assert_not_called()


def test_over_limit_is_blocked():
    limiter, ref, _ = _limiter(max_hits=3, existing_count=7)
    assert limiter.check("ip:1.2.3.4") is False
    ref.set.assert_not_called()


def test_document_id_encodes_key_and_window():
    window = 60
    now = 1_000_000.0
    limiter, _, coll = _limiter(window_seconds=window, now=now)
    limiter.check("church:nacka")
    doc_id = coll.document.call_args[0][0]
    assert doc_id == f"church:nacka|{int(now // window)}"


def test_new_window_gets_new_document():
    window = 60
    clock = {"now": 1_000_000.0}
    client = MagicMock()
    client.collection.return_value.document.return_value.get.return_value.exists = False
    limiter = FirestoreRateLimiter(
        max_hits=1, window_seconds=window, client=client, now_fn=lambda: clock["now"]
    )
    limiter.check("ip:1.2.3.4")
    clock["now"] += window  # next fixed window
    limiter.check("ip:1.2.3.4")
    ids = [c.args[0] for c in client.collection.return_value.document.call_args_list]
    assert len(set(ids)) == 2


def test_slash_in_key_is_sanitized_for_doc_id():
    limiter, _, coll = _limiter()
    limiter.check("ip:::ffff/weird")
    doc_id = coll.document.call_args[0][0]
    assert "/" not in doc_id


def test_uses_dedicated_collection():
    limiter, _, _ = _limiter()
    limiter.check("ip:1.2.3.4")
    limiter._client.collection.assert_called_with("rate_limit_windows")
