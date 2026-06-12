"""In-memory Sunday school tracker for local dev and tests."""
from __future__ import annotations

from app.domain.models import (
    SundaySchoolAttendance,
    SundaySchoolEnrollment,
    SundaySchoolGroup,
)


class InMemorySundaySchoolTracker:
    def __init__(self) -> None:
        self._groups: dict[str, SundaySchoolGroup] = {}
        self._enrollments: dict[str, SundaySchoolEnrollment] = {}
        self._attendance: dict[str, SundaySchoolAttendance] = {}

    @staticmethod
    def _key(church_id: str, item_id: str) -> str:
        return f"{church_id}::{item_id}"

    def list_groups(self, church_id: str) -> list[SundaySchoolGroup]:
        return [g for g in self._groups.values() if g.church_id == church_id]

    def get_group(self, church_id: str, group_id: str) -> SundaySchoolGroup | None:
        return self._groups.get(self._key(church_id, group_id))

    def save_group(self, group: SundaySchoolGroup) -> None:
        self._groups[self._key(group.church_id, group.group_id)] = group

    def list_enrollments(self, church_id: str, group_id: str) -> list[SundaySchoolEnrollment]:
        return [
            e for e in self._enrollments.values()
            if e.church_id == church_id and e.group_id == group_id
        ]

    def save_enrollment(self, enrollment: SundaySchoolEnrollment) -> None:
        key = self._key(enrollment.church_id, enrollment.enrollment_id)
        self._enrollments[key] = enrollment

    def list_attendance(self, church_id: str, group_id: str) -> list[SundaySchoolAttendance]:
        return [
            a for a in self._attendance.values()
            if a.church_id == church_id and a.group_id == group_id
        ]

    def get_attendance(
        self, church_id: str, group_id: str, date: str
    ) -> SundaySchoolAttendance | None:
        return self._attendance.get(self._key(church_id, f"{group_id}::{date}"))

    def save_attendance(self, record: SundaySchoolAttendance) -> None:
        key = self._key(record.church_id, f"{record.group_id}::{record.date}")
        self._attendance[key] = record
