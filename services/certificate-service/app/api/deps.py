from __future__ import annotations

from fastapi import Depends, Header, HTTPException, status

from app.adapters.fake_auth import FakeAuthAdapter
from app.adapters.in_memory_audit import InMemoryAuditAdapter
from app.adapters.in_memory_certificate_repository import InMemoryCertificateRepository
from app.domain.errors import NotAuthorized
from app.domain.models import Actor
from app.ports.audit import AuditPort
from app.ports.auth import AuthPort
from app.ports.certificate_repository import CertificateRepository
from app.services.certificate_service import CertificateService


_REPO: CertificateRepository = InMemoryCertificateRepository()
_AUTH: AuthPort = FakeAuthAdapter()
_AUDIT: AuditPort = InMemoryAuditAdapter()


def get_repo() -> CertificateRepository:
    return _REPO


def get_auth() -> AuthPort:
    return _AUTH


def get_audit() -> AuditPort:
    return _AUDIT


def get_service(
    repo: CertificateRepository = Depends(get_repo),
    audit: AuditPort = Depends(get_audit),
) -> CertificateService:
    return CertificateService(repo=repo, audit=audit)


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
