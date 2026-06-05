from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.api.deps import current_actor, get_activity_service
from app.domain.errors import ActivityNotFound, InvalidAgeBands, NotAuthorized
from app.domain.models import Activity, ActivityType, Actor
from app.services.activity_service import ActivityService, CreateActivityInput


router = APIRouter(prefix="/activities", tags=["activities"])


class CreateActivityRequest(BaseModel):
    activity_type: ActivityType
    date: date
    location: str = Field(min_length=1, max_length=200)
    funding_tag: str = Field(min_length=1, max_length=64)
    participants_total: int = Field(ge=0, le=100000)
    age_band_counts: dict[str, int]


class ActivityResponse(BaseModel):
    activity_id: str
    church_id: str
    activity_type: str
    date: str
    location: str
    funding_tag: str
    participants_total: int
    age_band_counts: dict[str, int]

    @classmethod
    def from_domain(cls, a: Activity) -> "ActivityResponse":
        return cls(
            activity_id=a.activity_id,
            church_id=a.church_id,
            activity_type=a.activity_type.value,
            date=a.date.isoformat(),
            location=a.location,
            funding_tag=a.funding_tag,
            participants_total=a.participants_total,
            age_band_counts=a.age_band_counts,
        )


def _translate(exc: Exception) -> HTTPException:
    if isinstance(exc, NotAuthorized):
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    if isinstance(exc, ActivityNotFound):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="activity not found")
    if isinstance(exc, InvalidAgeBands):
        return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="internal error")


@router.post("", response_model=ActivityResponse, status_code=status.HTTP_201_CREATED)
def create_activity(
    body: CreateActivityRequest,
    actor: Actor = Depends(current_actor),
    svc: ActivityService = Depends(get_activity_service),
) -> ActivityResponse:
    try:
        activity = svc.create(actor, CreateActivityInput(**body.model_dump()))
    except (NotAuthorized, InvalidAgeBands) as exc:
        raise _translate(exc) from exc
    return ActivityResponse.from_domain(activity)


@router.get("/{activity_id}", response_model=ActivityResponse)
def get_activity(
    activity_id: str,
    actor: Actor = Depends(current_actor),
    svc: ActivityService = Depends(get_activity_service),
) -> ActivityResponse:
    try:
        activity = svc.get(actor, activity_id)
    except (NotAuthorized, ActivityNotFound) as exc:
        raise _translate(exc) from exc
    return ActivityResponse.from_domain(activity)


@router.get("/export/period")
def export_period(
    start: date = Query(...),
    end: date = Query(...),
    actor: Actor = Depends(current_actor),
    svc: ActivityService = Depends(get_activity_service),
) -> list[dict]:
    try:
        return svc.export_period(actor, start, end)
    except NotAuthorized as exc:
        raise _translate(exc) from exc
