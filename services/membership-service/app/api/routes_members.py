"""Member HTTP routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field

from app.api.deps import current_actor, get_service
from app.domain.errors import (
    ChurchMismatch,
    MemberNotFound,
    NotAuthorized,
)
from app.domain.models import Actor, Member
from app.services.membership_service import (
    CreateMemberInput,
    MembershipService,
    UpdateMemberInput,
)


router = APIRouter(prefix="/members", tags=["members"])


class CreateMemberRequest(BaseModel):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    phone: str = Field(min_length=4, max_length=30)
    email: EmailStr
    personal_number: str = Field(min_length=10, max_length=13)


class UpdateMemberRequest(BaseModel):
    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
    phone: str | None = Field(default=None, min_length=4, max_length=30)
    email: EmailStr | None = None


class MemberResponse(BaseModel):
    member_id: str
    church_id: str
    first_name: str
    last_name: str
    phone: str
    email: str
    status: str

    @classmethod
    def from_domain(cls, m: Member) -> "MemberResponse":
        return cls(
            member_id=m.member_id,
            church_id=m.church_id,
            first_name=m.first_name,
            last_name=m.last_name,
            phone=m.phone,
            email=m.email,
            status=m.status.value,
        )


def _translate(exc: Exception) -> HTTPException:
    if isinstance(exc, NotAuthorized):
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    if isinstance(exc, (MemberNotFound, ChurchMismatch)):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="member not found")
    return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="internal error")


@router.post("", response_model=MemberResponse, status_code=status.HTTP_201_CREATED)
def create_member(
    body: CreateMemberRequest,
    actor: Actor = Depends(current_actor),
    svc: MembershipService = Depends(get_service),
) -> MemberResponse:
    try:
        member = svc.create(actor, CreateMemberInput(**body.model_dump()))
    except NotAuthorized as exc:
        raise _translate(exc) from exc
    return MemberResponse.from_domain(member)


@router.get("/{member_id}", response_model=MemberResponse)
def get_member(
    member_id: str,
    actor: Actor = Depends(current_actor),
    svc: MembershipService = Depends(get_service),
) -> MemberResponse:
    try:
        member = svc.get(actor, member_id)
    except (NotAuthorized, MemberNotFound, ChurchMismatch) as exc:
        raise _translate(exc) from exc
    return MemberResponse.from_domain(member)


@router.patch("/{member_id}", response_model=MemberResponse)
def update_member(
    member_id: str,
    body: UpdateMemberRequest,
    actor: Actor = Depends(current_actor),
    svc: MembershipService = Depends(get_service),
) -> MemberResponse:
    try:
        member = svc.update(actor, member_id, UpdateMemberInput(**body.model_dump()))
    except (NotAuthorized, MemberNotFound, ChurchMismatch) as exc:
        raise _translate(exc) from exc
    return MemberResponse.from_domain(member)


@router.post("/{member_id}/deactivate", response_model=MemberResponse)
def deactivate_member(
    member_id: str,
    actor: Actor = Depends(current_actor),
    svc: MembershipService = Depends(get_service),
) -> MemberResponse:
    try:
        member = svc.deactivate(actor, member_id)
    except (NotAuthorized, MemberNotFound, ChurchMismatch) as exc:
        raise _translate(exc) from exc
    return MemberResponse.from_domain(member)
