from __future__ import annotations

from fastapi import Depends, Header, HTTPException, status

from app.adapters.factory import make_auth, make_report_repository
from app.domain.errors import NotAuthorized
from app.domain.models import Actor
from app.ports.auth import AuthPort
from app.ports.report_repository import ReportRepository
from app.services.reporting_service import ReportingService


_REPO: ReportRepository | None = None
_AUTH: AuthPort | None = None


def get_repo() -> ReportRepository:
    global _REPO
    if _REPO is None:
        _REPO = make_report_repository()
    return _REPO


def get_auth() -> AuthPort:
    global _AUTH
    if _AUTH is None:
        _AUTH = make_auth()
    return _AUTH


def get_service(
    repo: ReportRepository = Depends(get_repo),
) -> ReportingService:
    return ReportingService(repo=repo)


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
