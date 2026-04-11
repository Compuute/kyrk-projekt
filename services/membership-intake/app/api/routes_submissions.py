"""Admin endpoints: list, approve, reject pending intake submissions.

Distinct from the public POST /intake endpoint. Every route here requires
an authenticated admin/pastor/secretary. Approval forwards the bearer token
to membership-service so the downstream RBAC applies.
"""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.api.deps import current_actor, current_token, get_service
from app.domain.errors import (
    DownstreamFailure,
    NotAuthorized,
    SubmissionAlreadyProcessed,
    SubmissionNotFound,
)
from app.domain.models import Actor, IntakeSubmission
from app.services.intake_service import IntakeService


router = APIRouter(prefix="/submissions", tags=["submissions"])


class PendingSubmissionItem(BaseModel):
    submission_id: str
    church_id: str
    first_name: str
    last_name: str
    received_at: datetime
    status: str

    @classmethod
    def from_domain(cls, s: IntakeSubmission) -> "PendingSubmissionItem":
        return cls(
            submission_id=s.submission_id,
            church_id=s.church_id,
            first_name=s.first_name,
            last_name=s.last_name,
            received_at=s.received_at,
            status=s.status.value,
        )


class ApprovalResponseModel(BaseModel):
    submission_id: str
    status: str
    created_member_id: str


class RejectResponseModel(BaseModel):
    submission_id: str
    status: str


def _translate(exc: Exception) -> HTTPException:
    if isinstance(exc, NotAuthorized):
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    if isinstance(exc, SubmissionNotFound):
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="submission not found"
        )
    if isinstance(exc, SubmissionAlreadyProcessed):
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="submission already processed",
        )
    if isinstance(exc, DownstreamFailure):
        return HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)
        )
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="internal error"
    )


@router.get("", response_model=list[PendingSubmissionItem])
def list_pending(
    actor: Actor = Depends(current_actor),
    svc: IntakeService = Depends(get_service),
) -> list[PendingSubmissionItem]:
    try:
        items = svc.list_pending(actor)
    except NotAuthorized as exc:
        raise _translate(exc) from exc
    return [PendingSubmissionItem.from_domain(s) for s in items]


@router.post(
    "/{submission_id}/approve",
    response_model=ApprovalResponseModel,
)
def approve_submission(
    submission_id: str,
    actor: Actor = Depends(current_actor),
    token: str = Depends(current_token),
    svc: IntakeService = Depends(get_service),
) -> ApprovalResponseModel:
    try:
        result = svc.approve(actor=actor, actor_token=token, submission_id=submission_id)
    except (
        NotAuthorized,
        SubmissionNotFound,
        SubmissionAlreadyProcessed,
        DownstreamFailure,
    ) as exc:
        raise _translate(exc) from exc
    return ApprovalResponseModel(
        submission_id=result.submission_id,
        status=result.status,
        created_member_id=result.created_member_id,
    )


@router.post(
    "/{submission_id}/reject",
    response_model=RejectResponseModel,
)
def reject_submission(
    submission_id: str,
    actor: Actor = Depends(current_actor),
    svc: IntakeService = Depends(get_service),
) -> RejectResponseModel:
    try:
        submission = svc.reject(actor=actor, submission_id=submission_id)
    except (NotAuthorized, SubmissionNotFound, SubmissionAlreadyProcessed) as exc:
        raise _translate(exc) from exc
    return RejectResponseModel(
        submission_id=submission.submission_id,
        status=submission.status.value,
    )
