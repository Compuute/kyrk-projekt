"""Sunday school HTTP routes: groups, enrollments, attendance.

Groups are courses (Grunderna, Fortsättning, Krar, Begena, ...). Staff
(admin/pastor/editor) manage groups and enrollments; teachers see and
record attendance only for groups they are assigned to. Attendance
responses include the derived YELLOW-zone aggregate (participants_total
+ age_band_counts) so callers can report to grants without touching PII.
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from app.api.deps import (
    current_actor,
    get_payment_port,
    get_rate_limiter,
    get_sunday_school_tracker,
)
from app.domain.models import (
    AGE_BANDS,
    Actor,
    Role,
    SundaySchoolAttendance,
    SundaySchoolEnrollment,
    SundaySchoolGroup,
    age_band_for,
)
from app.domain.rate_limit import InMemoryRateLimiter
from app.ports.payment import (
    Payment,
    PaymentCategory,
    PaymentMethod,
    PaymentPort,
    PaymentStatus,
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
    pending: bool = False
    consent_timestamp: str = ""

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
            pending=e.pending,
            consent_timestamp=e.consent_timestamp,
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


# ------------------------------------------------ public application + approval
#
# Guardians enroll a Fredagsskola/Sunday-school child from the public site.
# This is the ONE unauthenticated door, so it is rate-limited and creates a
# PENDING enrollment (pending=True, active=False) that does not appear in any
# roster until staff approve it. Data minimization (GDPR Art. 8): child name +
# birth year + guardian name + consent only — NO personnummer, NO phone.


class PublicEnrollmentRequest(BaseModel):
    # The public form knows its church + the activity's group_id. No actor.
    church_id: str = Field(min_length=1, max_length=64)
    group_id: str = Field(min_length=1, max_length=64)
    child_first_name: str = Field(min_length=1, max_length=100)
    child_last_name: str = Field(min_length=1, max_length=100)
    birth_year: int = Field(ge=1900, le=2100)
    guardian_name: str = Field(min_length=1, max_length=100)
    guardian_consent: bool = False
    # Optional client-supplied consent time; the server stamps one if absent.
    consent_timestamp: str = ""


@router.post(
    "/public/enrollments",
    response_model=EnrollmentModel,
    status_code=status.HTTP_202_ACCEPTED,
)
def public_enroll(
    body: PublicEnrollmentRequest,
    request: Request,
    tracker: SundaySchoolPort = Depends(get_sunday_school_tracker),
    limiter: InMemoryRateLimiter = Depends(get_rate_limiter),
) -> EnrollmentModel:
    client_ip = request.client.host if request.client else "unknown"
    if not limiter.allow(client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="too many requests — try again later",
        )
    if not body.guardian_consent:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="guardian consent is required to enroll a child",
        )
    # The activity must map to a real group in this church.
    _get_group_or_404(tracker, body.church_id, body.group_id)
    enrollment = SundaySchoolEnrollment(
        church_id=body.church_id,
        group_id=body.group_id,
        child_first_name=body.child_first_name,
        child_last_name=body.child_last_name,
        birth_year=body.birth_year,
        guardian_name=body.guardian_name,
        guardian_consent=body.guardian_consent,
        # Data minimization: never store a phone from the public funnel.
        guardian_phone="",
        active=False,
        pending=True,
        consent_timestamp=body.consent_timestamp or datetime.now(timezone.utc).isoformat(),
    )
    tracker.save_enrollment(enrollment)
    return EnrollmentModel.from_domain(enrollment)


@router.get("/pending", response_model=list[EnrollmentModel])
def list_pending(
    actor: Actor = Depends(current_actor),
    tracker: SundaySchoolPort = Depends(get_sunday_school_tracker),
) -> list[EnrollmentModel]:
    # Staff/teachers review the queue of public applications, church-scoped.
    _require_role(actor)
    pending = tracker.list_pending_enrollments(actor.church_id)
    return [EnrollmentModel.from_domain(e) for e in pending]


def _get_pending_or_404(
    tracker: SundaySchoolPort, church_id: str, enrollment_id: str
) -> SundaySchoolEnrollment:
    enrollment = tracker.get_enrollment(church_id, enrollment_id)
    if not enrollment or not enrollment.pending:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="pending enrollment not found"
        )
    return enrollment


@router.post("/enrollments/{enrollment_id}/approve", response_model=EnrollmentModel)
def approve_enrollment(
    enrollment_id: str,
    actor: Actor = Depends(current_actor),
    tracker: SundaySchoolPort = Depends(get_sunday_school_tracker),
) -> EnrollmentModel:
    _require_role(actor)
    enrollment = _get_pending_or_404(tracker, actor.church_id, enrollment_id)
    enrollment.pending = False
    enrollment.active = True
    tracker.save_enrollment(enrollment)
    return EnrollmentModel.from_domain(enrollment)


@router.post("/enrollments/{enrollment_id}/reject", response_model=EnrollmentModel)
def reject_enrollment(
    enrollment_id: str,
    actor: Actor = Depends(current_actor),
    tracker: SundaySchoolPort = Depends(get_sunday_school_tracker),
) -> EnrollmentModel:
    _require_role(actor)
    enrollment = _get_pending_or_404(tracker, actor.church_id, enrollment_id)
    enrollment.pending = False
    enrollment.active = False
    tracker.save_enrollment(enrollment)
    return EnrollmentModel.from_domain(enrollment)


# ----------------------------------------------- Fredagsskola/söndagsskola fee
#
# The fee goes to the activity org's OWN Swish/PlusGiro, which the platform
# never sees automatically — so "paid" is human-confirmed by the kassör (same
# principle as donation verification), recorded as a completed
# Payment(category=SUNDAY_SCHOOL) linked to the enrollment + fee month. Teachers
# can READ paid-status during attendance; only staff (kassör) can mark paid.


class MarkPaidRequest(BaseModel):
    period: str = Field(pattern=r"^\d{4}-\d{2}$")  # fee month, e.g. "2026-06"
    amount_sek: int = Field(ge=0, le=100000)
    # The fee is per family/month; mark same-guardian siblings in this group
    # paid in one click.
    apply_to_siblings: bool = False


class PaidStatusModel(BaseModel):
    period: str
    paid_enrollment_ids: list[str]


def _paid_ids(payments: PaymentPort, church_id: str, period: str) -> set[str]:
    return {
        p.enrollment_id
        for p in payments.list_payments(church_id, category=PaymentCategory.SUNDAY_SCHOOL)
        if p.period == period
        and p.status == PaymentStatus.COMPLETED
        and p.enrollment_id
    }


def _record_fee(
    payments: PaymentPort, enrollment: SundaySchoolEnrollment, period: str,
    amount_sek: int, actor: Actor,
) -> None:
    payment = Payment(
        member_id=enrollment.member_id,  # "" for non-member children
        church_id=enrollment.church_id,
        amount_sek=amount_sek,
        category=PaymentCategory.SUNDAY_SCHOOL,
        method=PaymentMethod.MANUAL,
        enrollment_id=enrollment.enrollment_id,
        period=period,
        description=f"Fredagsskola/söndagsskola {period}",
    )
    payment = payments.initiate_payment(payment)
    payments.complete_payment(payment.payment_id, reference=f"kassor:{actor.user_id}")


@router.post("/enrollments/{enrollment_id}/mark-paid", response_model=PaidStatusModel)
def mark_enrollment_paid(
    enrollment_id: str,
    body: MarkPaidRequest,
    actor: Actor = Depends(current_actor),
    tracker: SundaySchoolPort = Depends(get_sunday_school_tracker),
    payments: PaymentPort = Depends(get_payment_port),
) -> PaidStatusModel:
    _require_staff(actor)  # financial confirmation = kassör/staff, not teachers
    enrollment = tracker.get_enrollment(actor.church_id, enrollment_id)
    if not enrollment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="enrollment not found"
        )
    targets = [enrollment]
    if body.apply_to_siblings and enrollment.guardian_name:
        targets.extend(
            e for e in tracker.list_enrollments(actor.church_id, enrollment.group_id)
            if e.active
            and e.guardian_name == enrollment.guardian_name
            and e.enrollment_id != enrollment.enrollment_id
        )
    already = _paid_ids(payments, actor.church_id, body.period)
    for e in targets:
        if e.enrollment_id not in already:
            _record_fee(payments, e, body.period, body.amount_sek, actor)
    paid = _paid_ids(payments, actor.church_id, body.period)
    return PaidStatusModel(period=body.period, paid_enrollment_ids=sorted(paid))


@router.get("/groups/{group_id}/paid-status", response_model=PaidStatusModel)
def group_paid_status(
    group_id: str,
    period: str,
    actor: Actor = Depends(current_actor),
    tracker: SundaySchoolPort = Depends(get_sunday_school_tracker),
    payments: PaymentPort = Depends(get_payment_port),
) -> PaidStatusModel:
    _require_role(actor)  # teachers read paid-status during attendance
    group = _get_group_or_404(tracker, actor.church_id, group_id)
    _require_group_access(actor, group)
    enrolled = {e.enrollment_id for e in tracker.list_enrollments(actor.church_id, group_id)}
    paid = _paid_ids(payments, actor.church_id, period) & enrolled
    return PaidStatusModel(period=period, paid_enrollment_ids=sorted(paid))


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
