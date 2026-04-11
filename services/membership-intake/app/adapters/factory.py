"""Adapter factory for membership-intake.

ADAPTER_MODE=memory (default):
  InMemorySubmissionRepository, InMemoryNotifier, InMemoryRateLimiter,
  FakeAuthAdapter, FakeMembershipClient.

ADAPTER_MODE=production:
  FirestoreSubmissionRepository, HttpNotifier, InMemoryRateLimiter
  (see note), PropelAuthAdapter, HttpxMembershipClient.

Note on rate limiting: MVP production uses the in-memory limiter per
Cloud Run instance. When scaling out, swap this for a Redis-backed
limiter — currently not provisioned to keep MVP cost low.

Required env vars in production mode:
- PROPELAUTH_URL
- PROPELAUTH_API_KEY
- MEMBERSHIP_SERVICE_URL
- ADMIN_NOTIFY_WEBHOOK
"""
from __future__ import annotations

import os
import sys

from app.ports.auth import AuthPort
from app.ports.membership_client import MembershipClientPort
from app.ports.notifier import NotifierPort
from app.ports.rate_limiter import RateLimiterPort
from app.ports.submission_repository import SubmissionRepository


def _mode() -> str:
    return os.getenv("ADAPTER_MODE", "memory").lower()


def make_submission_repository() -> SubmissionRepository:
    if _mode() == "production":
        from app.adapters.firestore_submission_repository import (
            FirestoreSubmissionRepository,
        )

        return FirestoreSubmissionRepository()
    from app.adapters.in_memory_submission_repository import InMemorySubmissionRepository

    return InMemorySubmissionRepository()


def make_notifier() -> NotifierPort:
    if _mode() == "production":
        from app.adapters.http_notifier import HttpNotifier

        url = _require_env("ADMIN_NOTIFY_WEBHOOK")
        return HttpNotifier(webhook_url=url)
    from app.adapters.in_memory_notifier import InMemoryNotifier

    return InMemoryNotifier()


def make_rate_limiter() -> RateLimiterPort:
    from app.adapters.in_memory_rate_limiter import InMemoryRateLimiter

    return InMemoryRateLimiter(max_hits=5, window_seconds=60)


def make_auth() -> AuthPort:
    if _mode() == "production":
        from app.adapters.propelauth_auth import PropelAuthAdapter

        url = _require_env("PROPELAUTH_URL")
        key = _require_env("PROPELAUTH_API_KEY")
        return PropelAuthAdapter(auth_url=url, api_key=key)
    from app.adapters.fake_auth import FakeAuthAdapter

    return FakeAuthAdapter()


def make_membership_client() -> MembershipClientPort:
    if _mode() == "production":
        from app.adapters.httpx_membership_client import HttpxMembershipClient

        url = _require_env("MEMBERSHIP_SERVICE_URL")
        return HttpxMembershipClient(base_url=url)
    from app.adapters.fake_membership_client import FakeMembershipClient

    return FakeMembershipClient()


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        sys.stderr.write(
            f"[membership-intake] ADAPTER_MODE=production but {name} is unset\n"
        )
        raise RuntimeError(f"missing required env var: {name}")
    return value
