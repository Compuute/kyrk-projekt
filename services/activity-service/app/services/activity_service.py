from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from app.domain.errors import ActivityNotFound, InvalidAgeBands, NotAuthorized
from app.domain.models import (
    AGE_BANDS,
    Activity,
    ActivityType,
    Actor,
    Role,
)
from app.ports.activity_repository import ActivityRepository


_WRITE_ROLES: set[Role] = {Role.ADMIN, Role.PASTOR, Role.SECRETARY}
_READ_ROLES: set[Role] = {Role.ADMIN, Role.PASTOR, Role.SECRETARY, Role.VIEWER}


@dataclass(frozen=True)
class CreateActivityInput:
    activity_type: ActivityType
    date: date
    location: str
    funding_tag: str
    participants_total: int
    age_band_counts: dict[str, int]


class ActivityService:
    def __init__(self, repo: ActivityRepository) -> None:
        self._repo = repo

    def create(self, actor: Actor, data: CreateActivityInput) -> Activity:
        self._require_role(actor, _WRITE_ROLES)
        self._validate_age_bands(data.age_band_counts, data.participants_total)

        activity = Activity(
            church_id=actor.church_id,
            activity_type=data.activity_type,
            date=data.date,
            location=data.location,
            funding_tag=data.funding_tag,
            participants_total=data.participants_total,
            age_band_counts=dict(data.age_band_counts),
        )
        self._repo.add(activity)
        return activity

    def get(self, actor: Actor, activity_id: str) -> Activity:
        self._require_role(actor, _READ_ROLES)
        activity = self._repo.get(actor.church_id, activity_id)
        if activity is None:
            raise ActivityNotFound(activity_id)
        return activity

    def export_period(
        self, actor: Actor, start: date, end: date
    ) -> list[dict]:
        """Aggregate export for reporting-service. YELLOW shape only."""
        self._require_role(actor, _READ_ROLES)
        activities = self._repo.list_in_period(actor.church_id, start, end)
        return [
            {
                "activity_id": a.activity_id,
                "church_id": a.church_id,
                "activity_type": a.activity_type.value,
                "date": a.date.isoformat(),
                "location": a.location,
                "funding_tag": a.funding_tag,
                "participants_total": a.participants_total,
                "age_band_counts": a.age_band_counts,
            }
            for a in activities
        ]

    # --------------------------------------------------------------- internals

    def _require_role(self, actor: Actor, allowed: set[Role]) -> None:
        if actor.role not in allowed:
            raise NotAuthorized(f"role {actor.role.value} cannot perform this action")

    def _validate_age_bands(self, bands: dict[str, int], total: int) -> None:
        unknown = set(bands) - set(AGE_BANDS)
        if unknown:
            raise InvalidAgeBands(f"unknown bands: {sorted(unknown)}")
        if any(v < 0 for v in bands.values()):
            raise InvalidAgeBands("band counts must be non-negative")
        if sum(bands.values()) != total:
            raise InvalidAgeBands("age band counts must sum to participants_total")
