"""Client port for membership-service's Sunday school endpoints.

The downstream service enforces who sees what (teachers only their own
groups), keyed off the bearer token — this port just relays the calls.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class SchoolGroup:
    group_id: str
    name: str
    description: str = ""
    teacher_user_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class SchoolEnrollment:
    enrollment_id: str
    child_first_name: str
    child_last_name: str
    birth_year: int


@dataclass(frozen=True)
class AttendanceRecord:
    date: str
    present_enrollment_ids: tuple[str, ...] = ()
    participants_total: int = 0
    age_band_counts: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class AttendanceResult:
    attendance_id: str
    group_id: str
    date: str
    participants_total: int
    age_band_counts: dict[str, int]


class SundaySchoolClientPort(Protocol):
    def list_groups(self, token: str) -> list[SchoolGroup]: ...
    def list_enrollments(self, token: str, group_id: str) -> list[SchoolEnrollment]: ...
    def list_attendance(self, token: str, group_id: str) -> list[AttendanceRecord]: ...
    def record_attendance(
        self, token: str, group_id: str, date: str, present_enrollment_ids: list[str]
    ) -> AttendanceResult: ...
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
    ) -> SchoolEnrollment: ...
