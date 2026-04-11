"""In-memory audit adapter. Production wires to Firestore or Cloud Logging."""
from __future__ import annotations

from app.ports.audit import AuditEvent


class InMemoryAuditAdapter:
    def __init__(self) -> None:
        self._events: list[AuditEvent] = []

    def record(self, event: AuditEvent) -> None:
        self._events.append(event)

    def events_for(self, church_id: str) -> list[AuditEvent]:
        return [e for e in self._events if e.church_id == church_id]
