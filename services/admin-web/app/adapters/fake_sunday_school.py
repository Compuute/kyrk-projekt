"""In-memory fake Sunday school client for tests and local dev.

Mimics membership-service behavior: groups are filtered by the caller's
role/user (parsed from the dev token `user_id:church_id:role`), and the
attendance aggregate is derived from the enrolled children's birth years.
"""
from __future__ import annotations

from uuid import uuid4

from app.ports.client_errors import ClientError
from app.ports.sunday_school import (
    AttendanceRecord,
    AttendanceResult,
    PendingEnrollment,
    SchoolEnrollment,
    SchoolGroup,
)

_AGE_BANDS = ("0-6", "7-12", "13-17", "18-25", "26+")


def _age_band_for(birth_year: int, on_date: str) -> str:
    age = max(0, int(on_date[:4]) - birth_year)
    if age <= 6:
        return "0-6"
    if age <= 12:
        return "7-12"
    if age <= 17:
        return "13-17"
    if age <= 25:
        return "18-25"
    return "26+"


class FakeSundaySchoolClient:
    def __init__(self) -> None:
        self.groups: dict[str, SchoolGroup] = {}
        self.enrollments: dict[str, list[SchoolEnrollment]] = {}
        self.attendance: dict[str, list[AttendanceRecord]] = {}
        self.recorded: list[dict] = []
        self.enrolled: list[dict] = []
        self.created_groups: list[dict] = []
        self.pending: list[PendingEnrollment] = []
        self.approved: list[str] = []
        self.rejected: list[str] = []
        self.paid: set[tuple[str, str]] = set()  # (enrollment_id, period)
        self.marked_paid: list[dict] = []
        self.list_error: ClientError | None = None
        self.record_error: ClientError | None = None
        self.enroll_error: ClientError | None = None
        self.pending_error: ClientError | None = None

    def seed_group(self, group: SchoolGroup) -> None:
        self.groups[group.group_id] = group

    def seed_enrollment(self, group_id: str, enrollment: SchoolEnrollment) -> None:
        self.enrollments.setdefault(group_id, []).append(enrollment)

    def seed_attendance(self, group_id: str, record: AttendanceRecord) -> None:
        self.attendance.setdefault(group_id, []).append(record)

    def seed_pending(self, enrollment: PendingEnrollment) -> None:
        self.pending.append(enrollment)

    def list_pending(self, token: str) -> list[PendingEnrollment]:
        if self.pending_error is not None:
            raise self.pending_error
        return list(self.pending)

    def approve(self, token: str, enrollment_id: str) -> None:
        match = next((p for p in self.pending if p.enrollment_id == enrollment_id), None)
        if match is None:
            raise ClientError("pending enrollment not found", status_code=404)
        self.pending = [p for p in self.pending if p.enrollment_id != enrollment_id]
        self.approved.append(enrollment_id)
        self.seed_enrollment(
            match.group_id,
            SchoolEnrollment(
                enrollment_id=match.enrollment_id,
                child_first_name=match.child_first_name,
                child_last_name=match.child_last_name,
                birth_year=match.birth_year,
            ),
        )

    def reject(self, token: str, enrollment_id: str) -> None:
        match = next((p for p in self.pending if p.enrollment_id == enrollment_id), None)
        if match is None:
            raise ClientError("pending enrollment not found", status_code=404)
        self.pending = [p for p in self.pending if p.enrollment_id != enrollment_id]
        self.rejected.append(enrollment_id)

    def seed_paid(self, enrollment_id: str, period: str) -> None:
        self.paid.add((enrollment_id, period))

    def list_paid_status(self, token: str, group_id: str, period: str) -> list[str]:
        ids = {e.enrollment_id for e in self.enrollments.get(group_id, [])}
        return [eid for eid in ids if (eid, period) in self.paid]

    def mark_paid(
        self, token: str, enrollment_id: str, period: str,
        amount_sek: int, apply_to_siblings: bool,
    ) -> list[str]:
        self.paid.add((enrollment_id, period))
        self.marked_paid.append({
            "enrollment_id": enrollment_id,
            "period": period,
            "amount_sek": amount_sek,
            "apply_to_siblings": apply_to_siblings,
        })
        return [eid for (eid, p) in self.paid if p == period]

    @staticmethod
    def _token_parts(token: str) -> tuple[str, str]:
        parts = token.split(":")
        if len(parts) == 3:
            return parts[0], parts[2]
        return "", "admin"

    def list_groups(self, token: str) -> list[SchoolGroup]:
        if self.list_error is not None:
            raise self.list_error
        user_id, role = self._token_parts(token)
        groups = list(self.groups.values())
        if role == "teacher":
            groups = [g for g in groups if user_id in g.teacher_user_ids]
        return groups

    def list_enrollments(self, token: str, group_id: str) -> list[SchoolEnrollment]:
        self._check_access(token, group_id)
        return list(self.enrollments.get(group_id, []))

    def list_attendance(self, token: str, group_id: str) -> list[AttendanceRecord]:
        self._check_access(token, group_id)
        return sorted(self.attendance.get(group_id, []), key=lambda r: r.date)

    def record_attendance(
        self, token: str, group_id: str, date: str, present_enrollment_ids: list[str]
    ) -> AttendanceResult:
        if self.record_error is not None:
            raise self.record_error
        self._check_access(token, group_id)
        by_id = {e.enrollment_id: e for e in self.enrollments.get(group_id, [])}
        counts = {band: 0 for band in _AGE_BANDS}
        for enrollment_id in present_enrollment_ids:
            enrollment = by_id.get(enrollment_id)
            if enrollment is None:
                raise ClientError("enrollment ids not in this group", status_code=422)
            counts[_age_band_for(enrollment.birth_year, date)] += 1
        self.recorded.append({
            "group_id": group_id,
            "date": date,
            "present_enrollment_ids": list(present_enrollment_ids),
        })
        result = AttendanceResult(
            attendance_id=str(uuid4()),
            group_id=group_id,
            date=date,
            participants_total=len(present_enrollment_ids),
            age_band_counts=counts,
        )
        self.seed_attendance(group_id, AttendanceRecord(
            date=date,
            present_enrollment_ids=tuple(present_enrollment_ids),
            participants_total=result.participants_total,
            age_band_counts=counts,
        ))
        return result

    def enroll(
        self,
        token: str,
        group_id: str,
        child_first_name: str,
        child_last_name: str,
        birth_year: int,
        guardian_name: str,
        guardian_phone: str,
        guardian_consent: bool,
    ) -> SchoolEnrollment:
        if self.enroll_error is not None:
            raise self.enroll_error
        self._check_access(token, group_id)
        if not guardian_consent:
            raise ClientError("guardian consent is required", status_code=422)
        enrollment = SchoolEnrollment(
            enrollment_id=str(uuid4()),
            child_first_name=child_first_name,
            child_last_name=child_last_name,
            birth_year=birth_year,
        )
        self.seed_enrollment(group_id, enrollment)
        self.enrolled.append({
            "group_id": group_id,
            "child_first_name": child_first_name,
            "child_last_name": child_last_name,
            "birth_year": birth_year,
            "guardian_name": guardian_name,
            "guardian_phone": guardian_phone,
            "guardian_consent": guardian_consent,
        })
        return enrollment

    def create_group(
        self, token: str, name: str, description: str, teacher_user_ids: list[str],
        funding_tag: str = "sondagsskola", fee_required: bool = False,
    ) -> SchoolGroup:
        _, role = self._token_parts(token)
        if role not in {"admin", "pastor", "editor"}:
            raise ClientError("staff role required", status_code=403)
        group = SchoolGroup(
            group_id=str(uuid4()),
            name=name,
            description=description,
            teacher_user_ids=tuple(teacher_user_ids),
            funding_tag=funding_tag or "sondagsskola",
            fee_required=fee_required,
        )
        self.seed_group(group)
        self.created_groups.append({
            "name": name,
            "description": description,
            "teacher_user_ids": list(teacher_user_ids),
            "funding_tag": funding_tag,
            "fee_required": fee_required,
        })
        return group

    def _check_access(self, token: str, group_id: str) -> None:
        group = self.groups.get(group_id)
        if group is None:
            raise ClientError("group not found", status_code=404)
        user_id, role = self._token_parts(token)
        if role == "teacher" and user_id not in group.teacher_user_ids:
            raise ClientError("not a teacher of this group", status_code=403)
