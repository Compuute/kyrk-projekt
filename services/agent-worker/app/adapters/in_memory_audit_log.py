"""In-memory audit log for tests and local dev."""
from __future__ import annotations

from app.domain.models import AuditEvent, JobStatus


class InMemoryAuditLog:
    def __init__(self) -> None:
        self.events: list[AuditEvent] = []

    def record(self, event: AuditEvent) -> None:
        self.events.append(event)

    def seen(self, message_id: str) -> bool:
        return any(
            e.message_id == message_id and e.status is JobStatus.SUCCEEDED
            for e in self.events
        )
