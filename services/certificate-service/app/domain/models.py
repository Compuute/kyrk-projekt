from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from enum import Enum
from uuid import uuid4


class CertificateType(str, Enum):
    BAPTISM = "baptism"
    CONFIRMATION = "confirmation"
    MARRIAGE = "marriage"
    FUNERAL = "funeral"


class CertificateStatus(str, Enum):
    VALID = "valid"
    REVOKED = "revoked"
    FROZEN = "frozen"


class Role(str, Enum):
    ADMIN = "admin"
    PASTOR = "pastor"
    SECRETARY = "secretary"
    VIEWER = "viewer"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _new_id() -> str:
    return str(uuid4())


@dataclass
class Certificate:
    church_id: str
    church_name: str
    certificate_type: CertificateType
    issued_date: date
    # Identity is referenced by member_id; never duplicated as plaintext here.
    member_id: str
    issued_by_user_id: str
    status: CertificateStatus = CertificateStatus.VALID
    certificate_id: str = field(default_factory=_new_id)
    created_at: datetime = field(default_factory=_now)


@dataclass
class Actor:
    user_id: str
    church_id: str
    role: Role
