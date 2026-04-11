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


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _new_id() -> str:
    return str(uuid4())


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
