"""Domain entities for membership.

These are plain dataclasses — no framework coupling.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4


class MemberStatus(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    INACTIVE = "inactive"


class Role(str, Enum):
    ADMIN = "admin"
    PASTOR = "pastor"
    EDITOR = "editor"
    VIEWER = "viewer"
    TEACHER = "teacher"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _new_id() -> str:
    return str(uuid4())


@dataclass
class Member:
    church_id: str
    first_name: str
    last_name: str
    phone: str
    email: str
    personal_number_encrypted: str  # encrypted at rest; never store plaintext on this entity
    status: MemberStatus = MemberStatus.PENDING
    member_id: str = field(default_factory=_new_id)
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)

    def activate(self) -> None:
        self.status = MemberStatus.ACTIVE
        self.updated_at = _now()

    def deactivate(self) -> None:
        self.status = MemberStatus.INACTIVE
        self.updated_at = _now()


@dataclass
class Actor:
    """The authenticated caller. Populated by the auth dependency."""
    user_id: str
    church_id: str
    role: Role


# Same bands as reporting-service expects in YELLOW-zone activity aggregates.
AGE_BANDS = ("0-6", "7-12", "13-17", "18-25", "26+")


def age_band_for(birth_year: int, on_date: str) -> str:
    """Map a birth year to an age band as of an ISO date (YYYY-MM-DD)."""
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


@dataclass
class SundaySchoolGroup:
    """A Sunday school course group (Grunderna, Fortsättning, Krar, Begena, ...)."""
    church_id: str
    name: str
    description: str = ""
    teacher_user_ids: list[str] = field(default_factory=list)
    active: bool = True
    group_id: str = field(default_factory=_new_id)
    created_at: datetime = field(default_factory=_now)


@dataclass
class SundaySchoolEnrollment:
    """A child enrolled in one group. The same child may be enrolled in
    several groups (one enrollment per group)."""
    church_id: str
    group_id: str
    child_first_name: str
    child_last_name: str
    birth_year: int
    guardian_name: str = ""
    guardian_phone: str = ""
    guardian_consent: bool = False
    member_id: str = ""  # optional link to a Member/family record
    active: bool = True
    enrollment_id: str = field(default_factory=_new_id)
    created_at: datetime = field(default_factory=_now)


@dataclass
class SundaySchoolAttendance:
    """Attendance for one group on one date. One record per (group, date) —
    re-registering the same date replaces the record."""
    church_id: str
    group_id: str
    date: str  # ISO date YYYY-MM-DD
    present_enrollment_ids: list[str] = field(default_factory=list)
    registered_by_user_id: str = ""
    attendance_id: str = field(default_factory=_new_id)
    created_at: datetime = field(default_factory=_now)


@dataclass
class FuneralCase:
    case_id: str
    church_id: str
    status: str = "registered"
    created_at: datetime | None = None

    # Deceased info (RED-zone personal data, handled securely in backend)
    deceased_name: str = ""
    deceased_name_am: str = ""
    date_of_death: str = ""
    date_of_birth: str = ""
    contact_person: str = ""
    contact_phone: str = ""

    # Service options
    package: str = "standard"  # enkel | standard | komplett
    repatriation: bool = False
    repatriation_destination: str = ""  # "ethiopia" | other
    ceremony_date: str = ""
    ceremony_time: str = ""
    burial_location: str = ""

    # Eder
    eder_name: str = ""
    eder_contribution: float = 0.0

    # Financials
    package_price: float = 0.0
    repatriation_price: float = 0.0
    total_price: float = 0.0
    paid: bool = False

    # Checklist (stored as JSON-serializable dict)
    checklist: dict[str, bool] = field(default_factory=dict)

    # Memorial
    memorial_page_url: str = ""
    memorial_text_sv: str = ""
    memorial_text_am: str = ""
    memorial_photo_url: str = ""

    # Grief calendar
    grief_calendar_active: bool = False
    next_memorial_date: str = ""
    next_memorial_name: str = ""

    notes: str = ""

