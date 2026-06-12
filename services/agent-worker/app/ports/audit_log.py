from __future__ import annotations

from typing import Protocol

from app.domain.models import AuditEvent


class AuditLogPort(Protocol):
    def record(self, event: AuditEvent) -> None:
        ...

    def seen(self, message_id: str) -> bool:
        """True if this message id already completed successfully —
        used to dedupe Pub/Sub redeliveries."""
        ...
