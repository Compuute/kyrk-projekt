"""Donation receipt endpoints.

Public POST /donations registers a donor-reported gift (the site cannot see
the actual Swish/bankgiro payment). Admin endpoints let a kassör match the
registration against the bank statement: verify → receipt email goes out,
dismiss → nothing is sent. Donor email is PII — admin listings only ever
expose a masked form.
"""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, Field

from app.api.deps import current_actor, get_donation_service
from app.domain.errors import (
    ChurchNotConfigured,
    ConsentMissing,
    DonationAlreadyProcessed,
    DonationNotFound,
    NotAuthorized,
    RateLimited,
    ReceiptDeliveryFailure,
)
from app.domain.models import Actor, DonationRecord
from app.services.donation_service import DonationPayload, DonationService


router = APIRouter(prefix="/donations", tags=["donations"])


def _mask_email(email: str) -> str:
    local, _, domain = email.partition("@")
    if not domain:
        return "***"
    return f"{local[:1]}***@{domain}"


class DonationRequest(BaseModel):
    church_id: str = Field(min_length=1, max_length=64)
    amount_sek: int = Field(ge=1, le=100_000)
    method: str = Field(pattern="^(swish|bankgiro)$")
    email: EmailStr
    gdpr_consent: bool


class DonationResponse(BaseModel):
    donation_id: str
    status: str


class PendingDonationItem(BaseModel):
    donation_id: str
    church_id: str
    amount_sek: int
    method: str
    email_masked: str
    received_at: datetime
    status: str

    @classmethod
    def from_domain(cls, d: DonationRecord) -> "PendingDonationItem":
        return cls(
            donation_id=d.donation_id,
            church_id=d.church_id,
            amount_sek=d.amount_sek,
            method=d.method,
            email_masked=_mask_email(d.email),
            received_at=d.received_at,
            status=d.status.value,
        )


class VerifyResponseModel(BaseModel):
    donation_id: str
    status: str
    receipt_number: str


class DismissResponseModel(BaseModel):
    donation_id: str
    status: str


def _translate(exc: Exception) -> HTTPException:
    if isinstance(exc, NotAuthorized):
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    if isinstance(exc, DonationNotFound):
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="donation not found"
        )
    if isinstance(exc, DonationAlreadyProcessed):
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="donation already processed"
        )
    if isinstance(exc, ReceiptDeliveryFailure):
        return HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail="receipt delivery failed"
        )
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="internal error"
    )


@router.post("", response_model=DonationResponse, status_code=status.HTTP_202_ACCEPTED)
def register_donation(
    body: DonationRequest,
    request: Request,
    svc: DonationService = Depends(get_donation_service),
) -> DonationResponse:
    client_ip = request.client.host if request.client else "unknown"
    payload = DonationPayload(**body.model_dump())
    try:
        donation = svc.register(payload, client_ip=client_ip)
    except (ConsentMissing, ChurchNotConfigured) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except RateLimited as exc:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(exc)) from exc
    return DonationResponse(donation_id=donation.donation_id, status=donation.status.value)


@router.get("", response_model=list[PendingDonationItem])
def list_pending(
    actor: Actor = Depends(current_actor),
    svc: DonationService = Depends(get_donation_service),
) -> list[PendingDonationItem]:
    try:
        items = svc.list_pending(actor)
    except NotAuthorized as exc:
        raise _translate(exc) from exc
    return [PendingDonationItem.from_domain(d) for d in items]


@router.post("/{donation_id}/verify", response_model=VerifyResponseModel)
def verify_donation(
    donation_id: str,
    actor: Actor = Depends(current_actor),
    svc: DonationService = Depends(get_donation_service),
) -> VerifyResponseModel:
    try:
        result = svc.verify(actor=actor, donation_id=donation_id)
    except (
        NotAuthorized,
        DonationNotFound,
        DonationAlreadyProcessed,
        ReceiptDeliveryFailure,
        ChurchNotConfigured,
    ) as exc:
        raise _translate(exc) from exc
    return VerifyResponseModel(
        donation_id=result.donation_id,
        status=result.status,
        receipt_number=result.receipt_number,
    )


@router.post("/{donation_id}/dismiss", response_model=DismissResponseModel)
def dismiss_donation(
    donation_id: str,
    actor: Actor = Depends(current_actor),
    svc: DonationService = Depends(get_donation_service),
) -> DismissResponseModel:
    try:
        donation = svc.dismiss(actor=actor, donation_id=donation_id)
    except (NotAuthorized, DonationNotFound, DonationAlreadyProcessed) as exc:
        raise _translate(exc) from exc
    return DismissResponseModel(
        donation_id=donation.donation_id,
        status=donation.status.value,
    )
