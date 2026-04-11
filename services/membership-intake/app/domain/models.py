"""Domain entities for intake."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4


class SubmissionStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class Role(str, Enum):
    ADMIN = "admin"
    PASTOR = "pastor"
    SECRETARY = "secretary"
    VIEWER = "viewer"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _new_id() -> str:
    return str(uuid4())


_REDACTED = "***redacted***"


@dataclass
class IntakeSubmission:
    church_id: str
    first_name: str
    last_name: str
    phone: str
    email: str
    personal_number: str
    gdpr_consent: bool
    consent_timestamp: datetime
    status: SubmissionStatus = SubmissionStatus.PENDING
    submission_id: str = field(default_factory=_new_id)
    received_at: datetime = field(default_factory=_now)
    processed_at: datetime | None = None
    processed_by_user_id: str | None = None
    created_member_id: str | None = None

    def redact(self) -> None:
        """Zero sensitive fields after handoff to membership-service."""
        self.personal_number = _REDACTED
        self.phone = _REDACTED
        self.email = _REDACTED

    def mark_approved(self, actor_user_id: str, member_id: str) -> None:
        self.status = SubmissionStatus.APPROVED
        self.processed_at = _now()
        self.processed_by_user_id = actor_user_id
        self.created_member_id = member_id
        self.redact()

    def mark_rejected(self, actor_user_id: str) -> None:
        self.status = SubmissionStatus.REJECTED
        self.processed_at = _now()
        self.processed_by_user_id = actor_user_id
        self.redact()


@dataclass
class Actor:
    user_id: str
    church_id: str
    role: Role
