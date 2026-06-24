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
class PendingEnrollment:
    """A public application awaiting staff approval. Minimal data only
    (GDPR Art. 8): no personnummer, no phone."""
    enrollment_id: str
    group_id: str
    child_first_name: str
    child_last_name: str
    birth_year: int
    guardian_name: str = ""
    consent_timestamp: str = ""


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
    def list_pending(self, token: str) -> list[PendingEnrollment]: ...
    def approve(self, token: str, enrollment_id: str) -> None: ...
    def reject(self, token: str, enrollment_id: str) -> None: ...
    def list_paid_status(self, token: str, group_id: str, period: str) -> list[str]: ...
    def mark_paid(
        self, token: str, enrollment_id: str, period: str,
        amount_sek: int, apply_to_siblings: bool,
    ) -> list[str]: ...
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
    def create_group(
        self, token: str, name: str, description: str, teacher_user_ids: list[str]
    ) -> SchoolGroup: ...
