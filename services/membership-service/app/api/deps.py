"""FastAPI dependency wiring.

The factory (`app.adapters.factory`) reads `ADAPTER_MODE` at startup
and selects memory (default) or production adapters. Tests override
the individual `get_*` functions via `app.dependency_overrides`, so
the ADAPTER_MODE env var is never read in the test suite.
"""
from __future__ import annotations

from fastapi import Depends, Header, HTTPException, Request, status

from app.adapters.factory import (
    make_audit,
    make_auth,
    make_encryption,
    make_member_repository,
    make_funeral_tracker,
    make_grant_tracker,
    make_sunday_school_tracker,
)
from app.domain.errors import NotAuthorized
from app.domain.models import Actor
from app.domain.rate_limit import InMemoryRateLimiter
from app.ports.audit import AuditPort
from app.ports.auth import AuthPort
from app.ports.encryption import EncryptionPort
from app.ports.member_repository import MemberRepository
from app.ports.funeral_tracker import FuneralTrackerPort
from app.ports.grant_tracker import GrantTrackerPort
from app.ports.payment import PaymentPort
from app.ports.sunday_school import SundaySchoolPort
from app.services.membership_service import MembershipService


# Lazy singletons — instantiated on first use so tests never hit the factory
# at import time, and production wiring happens only once per process.
_REPO: MemberRepository | None = None
_AUTH: AuthPort | None = None
_ENCRYPTION: EncryptionPort | None = None
_AUDIT: AuditPort | None = None
_FUNERAL_TRACKER: FuneralTrackerPort | None = None
_GRANT_TRACKER: GrantTrackerPort | None = None


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


def get_funeral_tracker() -> FuneralTrackerPort:
    global _FUNERAL_TRACKER
    if _FUNERAL_TRACKER is None:
        _FUNERAL_TRACKER = make_funeral_tracker()
    return _FUNERAL_TRACKER


def get_grant_tracker() -> GrantTrackerPort:
    global _GRANT_TRACKER
    if _GRANT_TRACKER is None:
        _GRANT_TRACKER = make_grant_tracker()
    return _GRANT_TRACKER


_SUNDAY_SCHOOL: SundaySchoolPort | None = None


def get_sunday_school_tracker() -> SundaySchoolPort:
    global _SUNDAY_SCHOOL
    if _SUNDAY_SCHOOL is None:
        _SUNDAY_SCHOOL = make_sunday_school_tracker()
    return _SUNDAY_SCHOOL


_PAYMENT: PaymentPort | None = None


def get_payment_port() -> PaymentPort:
    # NOTE: in-memory only for now — there is no Firestore payment adapter yet.
    # Acceptable while the Fredagsskola fee flow is gated/synthetic; durable
    # persistence is a pre-go-live item (tracked with #156's RED-zone gaps).
    global _PAYMENT
    if _PAYMENT is None:
        from app.adapters.fake_payment import FakePaymentAdapter

        _PAYMENT = FakePaymentAdapter()
    return _PAYMENT


def get_rate_limiter(request: Request) -> "InMemoryRateLimiter":
    # One limiter per app instance (set in create_app). Tests build a fresh
    # app per case, so the public-enroll limiter never leaks between tests.
    return request.app.state.enroll_rate_limiter


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
