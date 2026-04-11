from __future__ import annotations

from fastapi import Depends, Header, HTTPException, status

from app.adapters.fake_auth import FakeAuthAdapter
from app.adapters.fake_membership_client import FakeMembershipClient
from app.adapters.in_memory_notifier import InMemoryNotifier
from app.adapters.in_memory_rate_limiter import InMemoryRateLimiter
from app.adapters.in_memory_submission_repository import InMemorySubmissionRepository
from app.domain.errors import NotAuthorized
from app.domain.models import Actor
from app.ports.auth import AuthPort
from app.ports.membership_client import MembershipClientPort
from app.ports.notifier import NotifierPort
from app.ports.rate_limiter import RateLimiterPort
from app.ports.submission_repository import SubmissionRepository
from app.services.intake_service import IntakeService


_REPO: SubmissionRepository = InMemorySubmissionRepository()
_NOTIFIER: NotifierPort = InMemoryNotifier()
_LIMITER: RateLimiterPort = InMemoryRateLimiter(max_hits=5, window_seconds=60)
_AUTH: AuthPort = FakeAuthAdapter()
_MEMBERSHIP_CLIENT: MembershipClientPort = FakeMembershipClient()


def get_repo() -> SubmissionRepository:
    return _REPO


def get_notifier() -> NotifierPort:
    return _NOTIFIER


def get_limiter() -> RateLimiterPort:
    return _LIMITER


def get_auth() -> AuthPort:
    return _AUTH


def get_membership_client() -> MembershipClientPort:
    return _MEMBERSHIP_CLIENT


def get_service(
    repo: SubmissionRepository = Depends(get_repo),
    notifier: NotifierPort = Depends(get_notifier),
    limiter: RateLimiterPort = Depends(get_limiter),
    membership_client: MembershipClientPort = Depends(get_membership_client),
) -> IntakeService:
    return IntakeService(
        repo=repo,
        notifier=notifier,
        limiter=limiter,
        membership_client=membership_client,
    )


def _extract_bearer(authorization: str | None) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing bearer token",
        )
    return authorization.split(" ", 1)[1]


def current_actor(
    authorization: str | None = Header(default=None),
    auth: AuthPort = Depends(get_auth),
) -> Actor:
    token = _extract_bearer(authorization)
    try:
        return auth.authenticate(token)
    except NotAuthorized as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)
        ) from exc


def current_token(authorization: str | None = Header(default=None)) -> str:
    """Return the raw bearer token — needed to forward to membership-service."""
    return _extract_bearer(authorization)
