"""FastAPI dependency wiring.

The factory (`app.adapters.factory`) reads `ADAPTER_MODE` at startup
and selects memory (default) or production adapters. Tests override
the individual `get_*` functions via `app.dependency_overrides`, so
the ADAPTER_MODE env var is never read in the test suite.
"""
from __future__ import annotations

from fastapi import Depends, Header, HTTPException, status

from app.adapters.factory import (
    make_auth,
    make_donation_repository,
    make_email_sender,
    make_membership_client,
    make_notifier,
    make_rate_limiter,
    make_submission_repository,
)
from app.domain.errors import NotAuthorized
from app.domain.models import Actor
from app.ports.auth import AuthPort
from app.ports.donation_repository import DonationRepository
from app.ports.email_sender import EmailSenderPort
from app.ports.membership_client import MembershipClientPort
from app.ports.notifier import NotifierPort
from app.ports.rate_limiter import RateLimiterPort
from app.ports.submission_repository import SubmissionRepository
from app.services.donation_service import DonationService
from app.services.intake_service import IntakeService


# Lazy singletons — instantiated on first use.
_REPO: SubmissionRepository | None = None
_NOTIFIER: NotifierPort | None = None
_LIMITER: RateLimiterPort | None = None
_AUTH: AuthPort | None = None
_MEMBERSHIP_CLIENT: MembershipClientPort | None = None
_DONATION_REPO: DonationRepository | None = None
_EMAIL_SENDER: EmailSenderPort | None = None


def get_repo() -> SubmissionRepository:
    global _REPO
    if _REPO is None:
        _REPO = make_submission_repository()
    return _REPO


def get_notifier() -> NotifierPort:
    global _NOTIFIER
    if _NOTIFIER is None:
        _NOTIFIER = make_notifier()
    return _NOTIFIER


def get_limiter() -> RateLimiterPort:
    global _LIMITER
    if _LIMITER is None:
        _LIMITER = make_rate_limiter()
    return _LIMITER


def get_auth() -> AuthPort:
    global _AUTH
    if _AUTH is None:
        _AUTH = make_auth()
    return _AUTH


def get_membership_client() -> MembershipClientPort:
    global _MEMBERSHIP_CLIENT
    if _MEMBERSHIP_CLIENT is None:
        _MEMBERSHIP_CLIENT = make_membership_client()
    return _MEMBERSHIP_CLIENT


def get_donation_repo() -> DonationRepository:
    global _DONATION_REPO
    if _DONATION_REPO is None:
        _DONATION_REPO = make_donation_repository()
    return _DONATION_REPO


def get_email_sender() -> EmailSenderPort:
    global _EMAIL_SENDER
    if _EMAIL_SENDER is None:
        _EMAIL_SENDER = make_email_sender()
    return _EMAIL_SENDER


def get_donation_service(
    repo: DonationRepository = Depends(get_donation_repo),
    email_sender: EmailSenderPort = Depends(get_email_sender),
    limiter: RateLimiterPort = Depends(get_limiter),
) -> DonationService:
    return DonationService(repo=repo, email_sender=email_sender, limiter=limiter)


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
    """Return the raw bearer token — forwarded to membership-service."""
    return _extract_bearer(authorization)
