"""FastAPI dependency wiring.

Production startup swaps these singletons for real adapters (PropelAuth,
Firestore repository, Cloud KMS encryption, Cloud Logging audit). Tests
override them via `app.dependency_overrides`.
"""
from __future__ import annotations

from fastapi import Depends, Header, HTTPException, status

from app.adapters.fake_auth import FakeAuthAdapter
from app.adapters.in_memory_audit import InMemoryAuditAdapter
from app.adapters.in_memory_encryption import InMemoryEncryptionAdapter
from app.adapters.in_memory_member_repository import InMemoryMemberRepository
from app.domain.errors import NotAuthorized
from app.domain.models import Actor
from app.ports.audit import AuditPort
from app.ports.auth import AuthPort
from app.ports.encryption import EncryptionPort
from app.ports.member_repository import MemberRepository
from app.services.membership_service import MembershipService


# Singletons — swapped out in tests and production entrypoint.
_REPO: MemberRepository = InMemoryMemberRepository()
_AUTH: AuthPort = FakeAuthAdapter()
_ENCRYPTION: EncryptionPort = InMemoryEncryptionAdapter()
_AUDIT: AuditPort = InMemoryAuditAdapter()


def get_repo() -> MemberRepository:
    return _REPO


def get_auth() -> AuthPort:
    return _AUTH


def get_encryption() -> EncryptionPort:
    return _ENCRYPTION


def get_audit() -> AuditPort:
    return _AUDIT


def get_service(
    repo: MemberRepository = Depends(get_repo),
    encryption: EncryptionPort = Depends(get_encryption),
    audit: AuditPort = Depends(get_audit),
) -> MembershipService:
    return MembershipService(repo=repo, encryption=encryption, audit=audit)


def current_actor(
    authorization: str | None = Header(default=None),
    auth: AuthPort = Depends(get_auth),
) -> Actor:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing bearer token")
    token = authorization.split(" ", 1)[1]
    try:
        return auth.authenticate(token)
    except NotAuthorized as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
