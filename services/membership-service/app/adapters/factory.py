"""Adapter factory — selects memory vs production wiring via env.

ADAPTER_MODE=memory (default) wires in-memory adapters. Used by tests
and local dev. No external services are contacted.

ADAPTER_MODE=production wires:
- FirestoreMemberRepository (requires google-cloud-firestore)
- FirestoreAuditAdapter (requires google-cloud-firestore)
- KmsEncryptionAdapter (requires google-cloud-kms)
- PropelAuthAdapter (requires propelauth-fastapi)

Required env vars in production mode:
- KMS_KEY_NAME            full key resource name
- PROPELAUTH_URL          tenant URL
- PROPELAUTH_API_KEY      API key (load via Secret Manager)

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
            f"[membership-service] ADAPTER_MODE=production but {name} is unset\n"
        )
        raise RuntimeError(f"missing required env var: {name}")
    return value
