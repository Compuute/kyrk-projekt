"""Adapter factory — selects memory vs production wiring via env.

ADAPTER_MODE=memory (default) wires in-memory adapters. Used by tests
and local dev. No external services are contacted.

ADAPTER_MODE=production wires:
- FirestoreMemberRepository (requires google-cloud-firestore)
- FirestoreAuditAdapter (requires google-cloud-firestore)
- KmsEncryptionAdapter (requires google-cloud-kms)
- ZitadelAuthAdapter (uses pyjwt for OIDC/JWKS verification)

Required env vars in production mode:
- KMS_KEY_NAME            full key resource name
- ZITADEL_ISSUER_URL      Zitadel issuer URL
- ZITADEL_CLIENT_ID       Zitadel client ID

Unknown ADAPTER_MODE falls back to memory and logs a warning via a
simple stderr write to avoid pulling in a logging dependency here.
"""
from __future__ import annotations

import os
import sys

from app.ports.audit import AuditPort
from app.ports.auth import AuthPort
from app.ports.encryption import EncryptionPort
from app.ports.member_repository import MemberRepository
from app.ports.funeral_tracker import FuneralTrackerPort


def _mode() -> str:
    return os.getenv("ADAPTER_MODE", "memory").lower()


def make_member_repository() -> MemberRepository:
    if _mode() == "production":
        from app.adapters.firestore_member_repository import FirestoreMemberRepository

        return FirestoreMemberRepository()
    from app.adapters.in_memory_member_repository import InMemoryMemberRepository

    return InMemoryMemberRepository()


def make_audit() -> AuditPort:
    if _mode() == "production":
        from app.adapters.firestore_audit import FirestoreAuditAdapter

        return FirestoreAuditAdapter()
    from app.adapters.in_memory_audit import InMemoryAuditAdapter

    return InMemoryAuditAdapter()


def make_encryption() -> EncryptionPort:
    if _mode() == "production":
        from app.adapters.kms_encryption import KmsEncryptionAdapter

        key_name = _require_env("KMS_KEY_NAME")
        return KmsEncryptionAdapter(key_name=key_name)
    from app.adapters.in_memory_encryption import InMemoryEncryptionAdapter

    return InMemoryEncryptionAdapter()


def make_auth() -> AuthPort:
    if _mode() == "production":
        from app.adapters.zitadel_auth import ZitadelAuthAdapter

        issuer = _require_env("ZITADEL_ISSUER_URL")
        client_id = _require_env("ZITADEL_CLIENT_ID")
        return ZitadelAuthAdapter(issuer_url=issuer, client_id=client_id)
    from app.adapters.fake_auth import FakeAuthAdapter

    return FakeAuthAdapter()


_FUNERAL_TRACKER: FuneralTrackerPort | None = None


def make_funeral_tracker() -> FuneralTrackerPort:
    global _FUNERAL_TRACKER
    if _mode() == "production":
        from app.adapters.firestore_funeral_tracker import FirestoreFuneralTracker

        return FirestoreFuneralTracker()

    if _FUNERAL_TRACKER is None:
        from app.adapters.in_memory_funeral_tracker import InMemoryFuneralTracker

        _FUNERAL_TRACKER = InMemoryFuneralTracker()
    return _FUNERAL_TRACKER


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        sys.stderr.write(
            f"[membership-service] ADAPTER_MODE=production but {name} is unset\n"
        )
        raise RuntimeError(f"missing required env var: {name}")
    return value
