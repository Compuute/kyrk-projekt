"""Firestore-backed audit adapter for certificate-service.

Write-only. The service never reads its own audit log — reads happen
in a separate privileged tool with its own service account.
"""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from app.ports.audit import AuditEvent

if TYPE_CHECKING:
    from google.cloud.firestore import Client  # pragma: no cover


_COLLECTION = "audit_events"


class FirestoreAuditAdapter:
    def __init__(self, client: "Client | None" = None) -> None:
        self._client = client

    def _coll(self):
        if self._client is None:
            from google.cloud import firestore  # pragma: no cover

            self._client = firestore.Client()
        return self._client.collection(_COLLECTION)

    def record(self, event: AuditEvent) -> None:
        self._coll().add({
            "actor_user_id": event.actor_user_id,
            "church_id": event.church_id,
            "action": event.action,
            "target_id": event.target_id,
            "at": event.at.isoformat() if isinstance(event.at, datetime) else event.at,
            "source_service": "certificate-service",
        })

    def events_for(self, church_id: str) -> list[AuditEvent]:
        raise NotImplementedError(
            "certificate-service does not read its own audit log; "
            "use the reporting tool with its own service account"
        )
