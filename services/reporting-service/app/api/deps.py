from __future__ import annotations

from fastapi import Depends, Header, HTTPException, status

from app.adapters.fake_auth import FakeAuthAdapter
from app.adapters.in_memory_report_repository import InMemoryReportRepository
from app.domain.errors import NotAuthorized
from app.domain.models import Actor
from app.ports.auth import AuthPort
from app.ports.report_repository import ReportRepository
from app.services.reporting_service import ReportingService


_REPO: ReportRepository = InMemoryReportRepository()
_AUTH: AuthPort = FakeAuthAdapter()


def get_repo() -> ReportRepository:
    return _REPO


def get_auth() -> AuthPort:
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
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing bearer token")
    token = authorization.split(" ", 1)[1]
    try:
        return auth.authenticate(token)
    except NotAuthorized as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
