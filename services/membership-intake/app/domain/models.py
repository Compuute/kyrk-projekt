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
    EDITOR = "editor"
    VIEWER = "viewer"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _new_id() -> str:
    return str(uuid4())


_REDACTED = "***redacted***"


@dataclass
class FamilyMemberRecord:
    first_name: str
    last_name: str
    personal_number: str = ""
    relation: str = ""


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
    source: str = ""  # wifi, telegram, donate, event, referral, direct
    membership_type: str = "individual"  # individual | family
    monthly_fee_sek: int = 200
    family_members: list[FamilyMemberRecord] = field(default_factory=list)
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


class DonationStatus(str, Enum):
    PENDING_VERIFICATION = "pending_verification"
    VERIFIED = "verified"
    DISMISSED = "dismissed"


@dataclass
class DonationRecord:
    """A donor-reported gift awaiting kassör verification.

    The site never sees the actual Swish/bankgiro transaction, so a record
    starts as PENDING_VERIFICATION and the receipt email is sent only when a
    kassör has matched it against the bank statement.
    """

    church_id: str
    amount_sek: int
    method: str  # swish | bankgiro
    email: str
    gdpr_consent: bool
    status: DonationStatus = DonationStatus.PENDING_VERIFICATION
    donation_id: str = field(default_factory=_new_id)
    received_at: datetime = field(default_factory=_now)
    processed_at: datetime | None = None
    processed_by_user_id: str | None = None
    receipt_number: str = ""

    def redact(self) -> None:
        """Zero the donor email once the record leaves PENDING."""
        self.email = _REDACTED

    def mark_verified(self, actor_user_id: str, receipt_number: str) -> None:
        self.status = DonationStatus.VERIFIED
        self.processed_at = _now()
        self.processed_by_user_id = actor_user_id
        self.receipt_number = receipt_number
        self.redact()

    def mark_dismissed(self, actor_user_id: str) -> None:
        self.status = DonationStatus.DISMISSED
        self.processed_at = _now()
        self.processed_by_user_id = actor_user_id
        self.redact()
