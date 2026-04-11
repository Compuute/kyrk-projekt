"""Adapter factory for activity-service.

YELLOW zone — the data contains no PII by construction, so no
encryption is wired here. Each activity is a count bucket.
"""
from __future__ import annotations

import os
import sys

from app.ports.activity_repository import ActivityRepository
from app.ports.auth import AuthPort


def _mode() -> str:
    return os.getenv("ADAPTER_MODE", "memory").lower()


def make_activity_repository() -> ActivityRepository:
    if _mode() == "production":
        from app.adapters.firestore_activity_repository import (
            FirestoreActivityRepository,
        )

        return FirestoreActivityRepository()
    from app.adapters.in_memory_activity_repository import InMemoryActivityRepository

    return InMemoryActivityRepository()


def make_auth() -> AuthPort:
    if _mode() == "production":
        from app.adapters.propelauth_auth import PropelAuthAdapter

        url = _require_env("PROPELAUTH_URL")
        key = _require_env("PROPELAUTH_API_KEY")
        return PropelAuthAdapter(auth_url=url, api_key=key)
    from app.adapters.fake_auth import FakeAuthAdapter

    return FakeAuthAdapter()


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        sys.stderr.write(
            f"[activity-service] ADAPTER_MODE=production but {name} is unset\n"
        )
        raise RuntimeError(f"missing required env var: {name}")
    return value
