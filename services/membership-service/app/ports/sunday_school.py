"""Port for Sunday school groups, enrollments and attendance."""
from __future__ import annotations

from typing import Protocol

from app.domain.models import (
    SundaySchoolAttendance,
    SundaySchoolEnrollment,
    SundaySchoolGroup,
)


class SundaySchoolPort(Protocol):
    def list_groups(self, church_id: str) -> list[SundaySchoolGroup]:
        """List all groups for a church."""
        ...

    def get_group(self, church_id: str, group_id: str) -> SundaySchoolGroup | None:
        """Get a group by ID."""
        ...

    def save_group(self, group: SundaySchoolGroup) -> None:
        """Save/update a group."""
        ...

    def list_enrollments(self, church_id: str, group_id: str) -> list[SundaySchoolEnrollment]:
        """List enrollments for a group."""
        ...

    def save_enrollment(self, enrollment: SundaySchoolEnrollment) -> None:
        """Save/update an enrollment."""
        ...

    def list_attendance(self, church_id: str, group_id: str) -> list[SundaySchoolAttendance]:
        """List attendance records for a group."""
        ...

    def get_attendance(
        self, church_id: str, group_id: str, date: str
    ) -> SundaySchoolAttendance | None:
        """Get the attendance record for a group on a date, if any."""
        ...

    def save_attendance(self, record: SundaySchoolAttendance) -> None:
        """Save/replace the attendance record for (group, date)."""
        ...
