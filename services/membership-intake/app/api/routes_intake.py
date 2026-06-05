from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, Field

from app.api.deps import current_actor, current_token, get_service
from app.domain.errors import ConsentMissing, RateLimited
from app.domain.models import Actor
from app.services.intake_service import IntakePayload, IntakeService


router = APIRouter(prefix="/intake", tags=["intake"])


class IntakeRequest(BaseModel):
    church_id: str = Field(min_length=1, max_length=64)
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    phone: str = Field(min_length=4, max_length=30)
    email: EmailStr
    personal_number: str = Field(min_length=10, max_length=13)
    gdpr_consent: bool
    consent_timestamp: datetime
    source: str = Field(default="direct", max_length=32)


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
    except RateLimited as exc:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(exc)) from exc
    return IntakeResponse(submission_id=submission.submission_id, status=submission.status.value)
