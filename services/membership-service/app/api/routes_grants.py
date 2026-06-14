"""Grant application HTTP routes (YELLOW zone).

Storage moved behind this service so the public-facing admin tier holds no
Firestore credentials (same rationale as funerals). One application per
(church_id, grant_id).
"""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.api.deps import current_actor, get_grant_tracker
from app.domain.models import Actor, GrantApplication, Role
from app.ports.grant_tracker import GrantTrackerPort

router = APIRouter(prefix="/grants", tags=["grants"])


class GrantApplicationModel(BaseModel):
    grant_id: str
    church_id: str
    status: str = "not_started"
    started_at: datetime | None = None
    submitted_at: datetime | None = None
    amount_requested: float | None = None
    amount_granted: float | None = None
    notes: str = ""
    generated_draft_url: str | None = None
    project_name: str = ""
    project_description: str = ""
    target_group: str = ""
    budget_amount: float | None = None
    own_contribution: float | None = None

    def to_domain(self) -> GrantApplication:
        return GrantApplication(**self.model_dump())

    @classmethod
    def from_domain(cls, a: GrantApplication) -> "GrantApplicationModel":
        return cls(
            grant_id=a.grant_id,
            church_id=a.church_id,
            status=a.status,
            started_at=a.started_at,
            submitted_at=a.submitted_at,
            amount_requested=a.amount_requested,
            amount_granted=a.amount_granted,
            notes=a.notes,
            generated_draft_url=a.generated_draft_url,
            project_name=a.project_name,
            project_description=a.project_description,
            target_group=a.target_group,
            budget_amount=a.budget_amount,
            own_contribution=a.own_contribution,
        )


def _check_auth(actor: Actor) -> None:
    if actor.role not in (Role.ADMIN, Role.PASTOR, Role.EDITOR):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="not authorized for grant operations",
        )


@router.get("", response_model=list[GrantApplicationModel])
def list_grants(
    actor: Actor = Depends(current_actor),
    tracker: GrantTrackerPort = Depends(get_grant_tracker),
) -> list[GrantApplicationModel]:
    _check_auth(actor)
    apps = tracker.list_applications(actor.church_id)
    return [GrantApplicationModel.from_domain(a) for a in apps]


@router.get("/{grant_id}", response_model=GrantApplicationModel)
def get_grant(
    grant_id: str,
    actor: Actor = Depends(current_actor),
    tracker: GrantTrackerPort = Depends(get_grant_tracker),
) -> GrantApplicationModel:
    _check_auth(actor)
    app = tracker.get_application(actor.church_id, grant_id)
    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="grant application not found",
        )
    return GrantApplicationModel.from_domain(app)


@router.post("", response_model=GrantApplicationModel, status_code=status.HTTP_201_CREATED)
def save_grant(
    body: GrantApplicationModel,
    actor: Actor = Depends(current_actor),
    tracker: GrantTrackerPort = Depends(get_grant_tracker),
) -> GrantApplicationModel:
    _check_auth(actor)
    if body.church_id != actor.church_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="church ID mismatch",
        )
    domain_app = body.to_domain()
    tracker.save_application(domain_app)
    return GrantApplicationModel.from_domain(domain_app)
