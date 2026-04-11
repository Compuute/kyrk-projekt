"""FastAPI dependency wiring.

The factory (`app.adapters.factory`) reads `ADAPTER_MODE` at startup
and selects memory (default) or production adapters. Tests override
the individual `get_*` functions via `app.dependency_overrides`, so
the ADAPTER_MODE env var is never read in the test suite.
"""
from __future__ import annotations

from fastapi import Depends, Header, HTTPException, status

from app.adapters.factory import (
    make_audit,
    make_auth,
    make_encryption,
    make_member_repository,
)
from app.domain.errors import NotAuthorized
from app.domain.models import Actor
from app.ports.audit import AuditPort
from app.ports.auth import AuthPort
from app.ports.encryption import EncryptionPort
from app.ports.member_repository import MemberRepository
from app.services.membership_service import MembershipService


# Lazy singletons — instantiated on first use so tests never hit the factory
# at import time, and production wiring happens only once per process.
_REPO: MemberRepository | None = None
_AUTH: AuthPort | None = None
_ENCRYPTION: EncryptionPort | None = None
_AUDIT: AuditPort | None = None


def get_repo() -> MemberRepository:
    global _REPO
    if _REPO is None:
        _REPO = make_member_repository()
    return _REPO


def get_auth() -> AuthPort:
    global _AUTH
    if _AUTH is None:
        _AUTH = make_auth()
    return _AUTH


def get_encryption() -> EncryptionPort:
    global _ENCRYPTION
    if _ENCRYPTION is None:
        _ENCRYPTION = make_encryption()
    return _ENCRYPTION


def get_audit() -> AuditPort:
    global _AUDIT
    if _AUDIT is None:
        _AUDIT = make_audit()
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
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="missing bearer token"
        )
    token = authorization.split(" ", 1)[1]
    try:
        return auth.authenticate(token)
    except NotAuthorized as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)
        ) from exc
