from __future__ import annotations

import re
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, Field, field_validator

from app.api.deps import current_actor, current_token, get_service
from app.domain.errors import ConsentMissing, DuplicateSubmission, RateLimited
from app.domain.models import Actor
from app.services.intake_service import IntakePayload, IntakeService


router = APIRouter(prefix="/intake", tags=["intake"])


def _luhn_check(digits: str) -> bool:
    total = 0
    for i, ch in enumerate(digits):
        d = int(ch)
        if i % 2 == 0:
            d *= 2
        if d > 9:
            d -= 9
        total += d
    return total % 10 == 0


def _normalize_phone(phone: str) -> str:
    clean = re.sub(r"[-\s]", "", phone)
    if clean.startswith("0"):
        clean = "+46" + clean[1:]
    return clean


class IntakeRequest(BaseModel):
    church_id: str = Field(min_length=1, max_length=64)
    first_name: str = Field(min_length=2, max_length=100)
    last_name: str = Field(min_length=2, max_length=100)
    phone: str = Field(min_length=4, max_length=30)
    email: EmailStr
    personal_number: str = Field(min_length=10, max_length=13)
    gdpr_consent: bool
    consent_timestamp: datetime
    source: str = Field(default="direct", max_length=32)

    @field_validator("first_name", "last_name")
    @classmethod
    def name_no_digits(cls, v: str) -> str:
        v = v.strip()
        if any(ch.isdigit() for ch in v):
            raise ValueError("namn får inte innehålla siffror")
        return v

    @field_validator("phone")
    @classmethod
    def phone_e164(cls, v: str) -> str:
        normalized = _normalize_phone(v)
        if not re.match(r"^\+46\d{7,10}$", normalized):
            raise ValueError("ogiltigt telefonnummer — använd 07X-XXX XX XX")
        return normalized

    @field_validator("personal_number")
    @classmethod
    def personnummer_luhn(cls, v: str) -> str:
        clean = re.sub(r"[-\s]", "", v)
        if len(clean) == 12:
            clean = clean[2:]
        if len(clean) != 10 or not clean.isdigit():
            raise ValueError("ogiltigt format — använd YYYYMMDD-XXXX")
        if not _luhn_check(clean):
            raise ValueError("ogiltig kontrollsiffra i personnummer")
        return v


class IntakeResponse(BaseModel):
    submission_id: str
    status: str


class PendingSubmissionSummary(BaseModel):
    submission_id: str
    church_id: str
    first_name: str
    last_name: str
    received_at: datetime
    status: str


class ApprovalResponseModel(BaseModel):
    submission_id: str
    status: str
    created_member_id: str


class RejectResponseModel(BaseModel):
    submission_id: str
    status: str


@router.post("", response_model=IntakeResponse, status_code=status.HTTP_202_ACCEPTED)
def submit_intake(
    body: IntakeRequest,
    request: Request,
    svc: IntakeService = Depends(get_service),
) -> IntakeResponse:
    client_ip = request.client.host if request.client else "unknown"
    payload = IntakePayload(**body.model_dump())
    try:
        submission = svc.submit(payload, client_ip=client_ip)
    except ConsentMissing as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except DuplicateSubmission as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except RateLimited as exc:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(exc)) from exc
    return IntakeResponse(submission_id=submission.submission_id, status=submission.status.value)
