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
    SECRETARY = "secretary"
    VIEWER = "viewer"


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
