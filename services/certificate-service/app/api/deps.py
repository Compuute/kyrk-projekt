from __future__ import annotations

from fastapi import Depends, Header, HTTPException, status

from app.adapters.factory import (
    make_audit,
    make_auth,
    make_certificate_repository,
    make_pdf_generator,
)
from app.domain.errors import NotAuthorized
from app.domain.models import Actor
from app.ports.audit import AuditPort
from app.ports.auth import AuthPort
from app.ports.certificate_repository import CertificateRepository
from app.ports.pdf_generator import PdfGeneratorPort
from app.services.certificate_service import CertificateService


_REPO: CertificateRepository | None = None
_AUTH: AuthPort | None = None
_AUDIT: AuditPort | None = None
_PDF: PdfGeneratorPort | None = None


def get_repo() -> CertificateRepository:
    global _REPO
    if _REPO is None:
        _REPO = make_certificate_repository()
    return _REPO


def get_auth() -> AuthPort:
    global _AUTH
    if _AUTH is None:
        _AUTH = make_auth()
    return _AUTH


def get_audit() -> AuditPort:
    global _AUDIT
    if _AUDIT is None:
        _AUDIT = make_audit()
    return _AUDIT


def get_pdf_generator() -> PdfGeneratorPort:
    global _PDF
    if _PDF is None:
        _PDF = make_pdf_generator()
    return _PDF


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
