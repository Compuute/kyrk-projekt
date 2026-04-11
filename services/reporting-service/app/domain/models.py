from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4


class ReportKind(str, Enum):
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    BOARD_EXPORT = "board_export"


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
class Report:
    church_id: str
    kind: ReportKind
    period: str  # e.g. "2025-06" or "2025-Q2" or "2025-annual"
    payload: dict  # structured JSON; schema depends on kind
    report_id: str = field(default_factory=_new_id)
    created_at: datetime = field(default_factory=_now)


@dataclass
class Actor:
    user_id: str
    church_id: str
    role: Role
