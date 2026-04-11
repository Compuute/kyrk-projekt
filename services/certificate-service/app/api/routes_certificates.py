from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.api.deps import current_actor, get_service
from app.domain.errors import (
    CertificateNotFound,
    InvalidStateTransition,
    NotAuthorized,
)
from app.domain.models import Actor, CertificateType
from app.services.certificate_service import (
    CertificateService,
    IssueCertificateInput,
)


router = APIRouter(prefix="/certificates", tags=["certificates"])


class IssueRequest(BaseModel):
    certificate_type: CertificateType
    issued_date: date
    member_id: str = Field(min_length=1, max_length=64)
    church_name: str = Field(min_length=1, max_length=200)


class CertificateResponse(BaseModel):
    certificate_id: str
    church_id: str
    certificate_type: str
    issued_date: str
    status: str
    verification_url: str


class VerificationResponse(BaseModel):
    certificate_type: str
    issued_date: str
    issuing_church_name: str
    status: str


def _to_response(cert, base_url: str = "/certificates/verify") -> CertificateResponse:
    return CertificateResponse(
        certificate_id=cert.certificate_id,
        church_id=cert.church_id,
        certificate_type=cert.certificate_type.value,
        issued_date=cert.issued_date.isoformat(),
        status=cert.status.value,
        verification_url=f"{base_url}/{cert.certificate_id}",
    )


def _translate(exc: Exception) -> HTTPException:
    if isinstance(exc, NotAuthorized):
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    if isinstance(exc, CertificateNotFound):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="certificate not found")
    if isinstance(exc, InvalidStateTransition):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="internal error")


@router.post("", response_model=CertificateResponse, status_code=status.HTTP_201_CREATED)
def issue_certificate(
    body: IssueRequest,
    actor: Actor = Depends(current_actor),
    svc: CertificateService = Depends(get_service),
) -> CertificateResponse:
    try:
        cert = svc.issue(actor, IssueCertificateInput(**body.model_dump()))
    except NotAuthorized as exc:
        raise _translate(exc) from exc
    return _to_response(cert)


@router.post("/{certificate_id}/revoke", response_model=CertificateResponse)
def revoke_certificate(
    certificate_id: str,
    actor: Actor = Depends(current_actor),
    svc: CertificateService = Depends(get_service),
) -> CertificateResponse:
    try:
        cert = svc.revoke(actor, certificate_id)
    except (NotAuthorized, CertificateNotFound, InvalidStateTransition) as exc:
        raise _translate(exc) from exc
    return _to_response(cert)


@router.post("/{certificate_id}/freeze", response_model=CertificateResponse)
def freeze_certificate(
    certificate_id: str,
    actor: Actor = Depends(current_actor),
    svc: CertificateService = Depends(get_service),
) -> CertificateResponse:
    try:
        cert = svc.freeze(actor, certificate_id)
    except (NotAuthorized, CertificateNotFound, InvalidStateTransition) as exc:
        raise _translate(exc) from exc
    return _to_response(cert)


@router.get("/verify/{certificate_id}", response_model=VerificationResponse)
def verify_certificate(
    certificate_id: str,
    svc: CertificateService = Depends(get_service),
) -> VerificationResponse:
    """Public verification endpoint — no auth, no identity in response."""
    try:
        result = svc.verify_public(certificate_id)
    except CertificateNotFound as exc:
        raise _translate(exc) from exc
    return VerificationResponse(
        certificate_type=result.certificate_type,
        issued_date=result.issued_date,
        issuing_church_name=result.issuing_church_name,
        status=result.status,
    )
