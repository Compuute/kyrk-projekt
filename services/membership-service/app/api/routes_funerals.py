"""Funeral HTTP routes."""
from __future__ import annotations

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.api.deps import current_actor, get_funeral_tracker
from app.domain.models import Actor, FuneralCase, Role
from app.ports.funeral_tracker import FuneralTrackerPort

router = APIRouter(prefix="/funerals", tags=["funerals"])


class FuneralCaseModel(BaseModel):
    case_id: str
    church_id: str
    status: str = "registered"
    created_at: datetime | None = None
    deceased_name: str = ""
    deceased_name_am: str = ""
    date_of_death: str = ""
    date_of_birth: str = ""
    contact_person: str = ""
    contact_phone: str = ""
    package: str = "standard"
    repatriation: bool = False
    repatriation_destination: str = ""
    ceremony_date: str = ""
    ceremony_time: str = ""
    burial_location: str = ""
    eder_name: str = ""
    eder_contribution: float = 0.0
    package_price: float = 0.0
    repatriation_price: float = 0.0
    total_price: float = 0.0
    paid: bool = False
    checklist: dict[str, bool] = Field(default_factory=dict)
    memorial_page_url: str = ""
    memorial_text_sv: str = ""
    memorial_text_am: str = ""
    memorial_photo_url: str = ""
    grief_calendar_active: bool = False
    next_memorial_date: str = ""
    next_memorial_name: str = ""
    notes: str = ""

    def to_domain(self) -> FuneralCase:
        return FuneralCase(
            case_id=self.case_id,
            church_id=self.church_id,
            status=self.status,
            created_at=self.created_at,
            deceased_name=self.deceased_name,
            deceased_name_am=self.deceased_name_am,
            date_of_death=self.date_of_death,
            date_of_birth=self.date_of_birth,
            contact_person=self.contact_person,
            contact_phone=self.contact_phone,
            package=self.package,
            repatriation=self.repatriation,
            repatriation_destination=self.repatriation_destination,
            ceremony_date=self.ceremony_date,
            ceremony_time=self.ceremony_time,
            burial_location=self.burial_location,
            eder_name=self.eder_name,
            eder_contribution=self.eder_contribution,
            package_price=self.package_price,
            repatriation_price=self.repatriation_price,
            total_price=self.total_price,
            paid=self.paid,
            checklist=self.checklist,
            memorial_page_url=self.memorial_page_url,
            memorial_text_sv=self.memorial_text_sv,
            memorial_text_am=self.memorial_text_am,
            memorial_photo_url=self.memorial_photo_url,
            grief_calendar_active=self.grief_calendar_active,
            next_memorial_date=self.next_memorial_date,
            next_memorial_name=self.next_memorial_name,
            notes=self.notes,
        )

    @classmethod
    def from_domain(cls, c: FuneralCase) -> FuneralCaseModel:
        return cls(
            case_id=c.case_id,
            church_id=c.church_id,
            status=c.status,
            created_at=c.created_at,
            deceased_name=c.deceased_name,
            deceased_name_am=c.deceased_name_am,
            date_of_death=c.date_of_death,
            date_of_birth=c.date_of_birth,
            contact_person=c.contact_person,
            contact_phone=c.contact_phone,
            package=c.package,
            repatriation=c.repatriation,
            repatriation_destination=c.repatriation_destination,
            ceremony_date=c.ceremony_date,
            ceremony_time=c.ceremony_time,
            burial_location=c.burial_location,
            eder_name=c.eder_name,
            eder_contribution=c.eder_contribution,
            package_price=c.package_price,
            repatriation_price=c.repatriation_price,
            total_price=c.total_price,
            paid=c.paid,
            checklist=c.checklist,
            memorial_page_url=c.memorial_page_url,
            memorial_text_sv=c.memorial_text_sv,
            memorial_text_am=c.memorial_text_am,
            memorial_photo_url=c.memorial_photo_url,
            grief_calendar_active=c.grief_calendar_active,
            next_memorial_date=c.next_memorial_date,
            next_memorial_name=c.next_memorial_name,
            notes=c.notes,
        )


def _check_auth(actor: Actor) -> None:
    if actor.role not in (Role.ADMIN, Role.PASTOR, Role.EDITOR):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="not authorized for RED zone operations"
        )


@router.get("", response_model=list[FuneralCaseModel])
def list_funerals(
    actor: Actor = Depends(current_actor),
    tracker: FuneralTrackerPort = Depends(get_funeral_tracker),
) -> list[FuneralCaseModel]:
    _check_auth(actor)
    cases = tracker.list_cases(actor.church_id)
    return [FuneralCaseModel.from_domain(c) for c in cases]


@router.get("/{case_id}", response_model=FuneralCaseModel)
def get_funeral(
    case_id: str,
    actor: Actor = Depends(current_actor),
    tracker: FuneralTrackerPort = Depends(get_funeral_tracker),
) -> FuneralCaseModel:
    _check_auth(actor)
    case = tracker.get_case(actor.church_id, case_id)
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="funeral case not found"
        )
    return FuneralCaseModel.from_domain(case)


@router.post("", response_model=FuneralCaseModel, status_code=status.HTTP_201_CREATED)
def save_funeral(
    body: FuneralCaseModel,
    actor: Actor = Depends(current_actor),
    tracker: FuneralTrackerPort = Depends(get_funeral_tracker),
) -> FuneralCaseModel:
    _check_auth(actor)
    if body.church_id != actor.church_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="church ID mismatch"
        )
    domain_case = body.to_domain()
    tracker.save_case(domain_case)
    return FuneralCaseModel.from_domain(domain_case)


@router.delete("/{case_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_funeral(
    case_id: str,
    actor: Actor = Depends(current_actor),
    tracker: FuneralTrackerPort = Depends(get_funeral_tracker),
) -> None:
    _check_auth(actor)
    case = tracker.get_case(actor.church_id, case_id)
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="funeral case not found"
        )
    tracker.delete_case(actor.church_id, case_id)
