from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Protocol


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class AuditEvent:
    actor_user_id: str
    church_id: str
    action: str
    target_id: str
    at: datetime = field(default_factory=_now)


class AuditPort(Protocol):
    def record(self, event: AuditEvent) -> None: ...
    def events_for(self, church_id: str) -> list[AuditEvent]: ...
