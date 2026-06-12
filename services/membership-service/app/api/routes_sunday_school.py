"""Sunday school HTTP routes: groups, enrollments, attendance.

Groups are courses (Grunderna, Fortsättning, Krar, Begena, ...). Staff
(admin/pastor/editor) manage groups and enrollments; teachers see and
record attendance only for groups they are assigned to. Attendance
responses include the derived YELLOW-zone aggregate (participants_total
+ age_band_counts) so callers can report to grants without touching PII.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.api.deps import current_actor, get_sunday_school_tracker
from app.domain.models import (
    AGE_BANDS,
    Actor,
    Role,
    SundaySchoolAttendance,
    SundaySchoolEnrollment,
    SundaySchoolGroup,
    age_band_for,
)
from app.ports.sunday_school import SundaySchoolPort

router = APIRouter(prefix="/sunday-school", tags=["sunday-school"])

_STAFF = (Role.ADMIN, Role.PASTOR, Role.EDITOR)


class GroupModel(BaseModel):
    # group_id/church_id may be omitted on create — the server generates
    # the id and takes the church from the authenticated actor.
    group_id: str = ""
    church_id: str = ""
    name: str = Field(min_length=1, max_length=100)
    description: str = ""
    teacher_user_ids: list[str] = Field(default_factory=list)
    active: bool = True

    def to_domain(self, church_id: str) -> SundaySchoolGroup:
        group = SundaySchoolGroup(
            church_id=church_id,
            name=self.name,
            description=self.description,
            teacher_user_ids=self.teacher_user_ids,
            active=self.active,
        )
        if self.group_id:
            group.group_id = self.group_id
        return group

    @classmethod
    def from_domain(cls, g: SundaySchoolGroup) -> "GroupModel":
        return cls(
            group_id=g.group_id,
            church_id=g.church_id,
            name=g.name,
            description=g.description,
            teacher_user_ids=g.teacher_user_ids,
            active=g.active,
        )


class EnrollmentRequest(BaseModel):
    child_first_name: str = Field(min_length=1, max_length=100)
    child_last_name: str = Field(min_length=1, max_length=100)
    birth_year: int = Field(ge=1900, le=2100)
    guardian_name: str = ""
    guardian_phone: str = ""
    guardian_consent: bool = False
    member_id: str = ""


class EnrollmentModel(BaseModel):
    enrollment_id: str
    church_id: str
    group_id: str
    child_first_name: str
    child_last_name: str
    birth_year: int
    guardian_name: str
    guardian_phone: str
    guardian_consent: bool
    member_id: str
    active: bool

    @classmethod
    def from_domain(cls, e: SundaySchoolEnrollment) -> "EnrollmentModel":
        return cls(
            enrollment_id=e.enrollment_id,
            church_id=e.church_id,
            group_id=e.group_id,
            child_first_name=e.child_first_name,
            child_last_name=e.child_last_name,
            birth_year=e.birth_year,
            guardian_name=e.guardian_name,
            guardian_phone=e.guardian_phone,
            guardian_consent=e.guardian_consent,
            member_id=e.member_id,
            active=e.active,
        )


class AttendanceRequest(BaseModel):
    date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    present_enrollment_ids: list[str] = Field(default_factory=list)


class AttendanceModel(BaseModel):
    attendance_id: str
    group_id: str
    date: str
    present_enrollment_ids: list[str]
    registered_by_user_id: str
    participants_total: int
    age_band_counts: dict[str, int]


def _require_role(actor: Actor) -> None:
    if actor.role not in (*_STAFF, Role.TEACHER):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="not authorized for RED zone operations",
        )


def _require_staff(actor: Actor) -> None:
    if actor.role not in _STAFF:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="staff role required",
        )


def _get_group_or_404(
    tracker: SundaySchoolPort, church_id: str, group_id: str
) -> SundaySchoolGroup:
    group = tracker.get_group(church_id, group_id)
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="group not found"
        )
    return group


def _require_group_access(actor: Actor, group: SundaySchoolGroup) -> None:
    if actor.role in _STAFF:
        return
    if actor.role == Role.TEACHER and actor.user_id in group.teacher_user_ids:
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="not a teacher of this group",
    )


def _aggregate(
    record: SundaySchoolAttendance, enrollments: list[SundaySchoolEnrollment]
) -> AttendanceModel:
    by_id = {e.enrollment_id: e for e in enrollments}
    counts = {band: 0 for band in AGE_BANDS}
    for enrollment_id in record.present_enrollment_ids:
        enrollment = by_id.get(enrollment_id)
        if enrollment:
            counts[age_band_for(enrollment.birth_year, record.date)] += 1
    return AttendanceModel(
        attendance_id=record.attendance_id,
        group_id=record.group_id,
        date=record.date,
        present_enrollment_ids=record.present_enrollment_ids,
        registered_by_user_id=record.registered_by_user_id,
        participants_total=len(record.present_enrollment_ids),
        age_band_counts=counts,
    )


@router.get("/groups", response_model=list[GroupModel])
def list_groups(
    actor: Actor = Depends(current_actor),
    tracker: SundaySchoolPort = Depends(get_sunday_school_tracker),
) -> list[GroupModel]:
    _require_role(actor)
    groups = tracker.list_groups(actor.church_id)
    if actor.role == Role.TEACHER:
        groups = [g for g in groups if actor.user_id in g.teacher_user_ids]
    return [GroupModel.from_domain(g) for g in groups]


@router.post("/groups", response_model=GroupModel, status_code=status.HTTP_201_CREATED)
def create_group(
    body: GroupModel,
    actor: Actor = Depends(current_actor),
    tracker: SundaySchoolPort = Depends(get_sunday_school_tracker),
) -> GroupModel:
    _require_staff(actor)
    if body.church_id and body.church_id != actor.church_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="church ID mismatch"
        )
    group = body.to_domain(actor.church_id)
    tracker.save_group(group)
    return GroupModel.from_domain(group)


@router.get("/groups/{group_id}/enrollments", response_model=list[EnrollmentModel])
def list_enrollments(
    group_id: str,
    actor: Actor = Depends(current_actor),
    tracker: SundaySchoolPort = Depends(get_sunday_school_tracker),
) -> list[EnrollmentModel]:
    _require_role(actor)
    group = _get_group_or_404(tracker, actor.church_id, group_id)
    _require_group_access(actor, group)
    enrollments = tracker.list_enrollments(actor.church_id, group_id)
    return [EnrollmentModel.from_domain(e) for e in enrollments if e.active]


@router.post(
    "/groups/{group_id}/enrollments",
    response_model=EnrollmentModel,
    status_code=status.HTTP_201_CREATED,
)
def create_enrollment(
    group_id: str,
    body: EnrollmentRequest,
    actor: Actor = Depends(current_actor),
    tracker: SundaySchoolPort = Depends(get_sunday_school_tracker),
) -> EnrollmentModel:
    # Teachers may register a child on the spot — but only into their own
    # groups; staff can enroll into any group.
    _require_role(actor)
    group = _get_group_or_404(tracker, actor.church_id, group_id)
    _require_group_access(actor, group)
    if not body.guardian_consent:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="guardian consent is required to enroll a child",
        )
    enrollment = SundaySchoolEnrollment(
        church_id=actor.church_id,
        group_id=group_id,
        child_first_name=body.child_first_name,
        child_last_name=body.child_last_name,
        birth_year=body.birth_year,
        guardian_name=body.guardian_name,
        guardian_phone=body.guardian_phone,
        guardian_consent=body.guardian_consent,
        member_id=body.member_id,
    )
    tracker.save_enrollment(enrollment)
    return EnrollmentModel.from_domain(enrollment)


@router.get("/groups/{group_id}/attendance", response_model=list[AttendanceModel])
def list_attendance(
    group_id: str,
    actor: Actor = Depends(current_actor),
    tracker: SundaySchoolPort = Depends(get_sunday_school_tracker),
) -> list[AttendanceModel]:
    _require_role(actor)
    group = _get_group_or_404(tracker, actor.church_id, group_id)
    _require_group_access(actor, group)
    enrollments = tracker.list_enrollments(actor.church_id, group_id)
    records = tracker.list_attendance(actor.church_id, group_id)
    return [_aggregate(r, enrollments) for r in sorted(records, key=lambda r: r.date)]


@router.post(
    "/groups/{group_id}/attendance",
    response_model=AttendanceModel,
    status_code=status.HTTP_201_CREATED,
)
def record_attendance(
    group_id: str,
    body: AttendanceRequest,
    actor: Actor = Depends(current_actor),
    tracker: SundaySchoolPort = Depends(get_sunday_school_tracker),
) -> AttendanceModel:
    _require_role(actor)
    group = _get_group_or_404(tracker, actor.church_id, group_id)
    _require_group_access(actor, group)

    enrollments = tracker.list_enrollments(actor.church_id, group_id)
    enrolled_ids = {e.enrollment_id for e in enrollments}
    unknown = [i for i in body.present_enrollment_ids if i not in enrolled_ids]
    if unknown:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="enrollment ids not in this group",
        )

    record = SundaySchoolAttendance(
        church_id=actor.church_id,
        group_id=group_id,
        date=body.date,
        present_enrollment_ids=body.present_enrollment_ids,
        registered_by_user_id=actor.user_id,
    )
    existing = tracker.get_attendance(actor.church_id, group_id, body.date)
    if existing:
        record.attendance_id = existing.attendance_id
    tracker.save_attendance(record)
    return _aggregate(record, enrollments)
