"""Firestore-backed audit adapter.

Scope: only the `audit_events` collection. The service uses WRITE-ONLY
access — it never reads its own audit log. Reads happen out-of-band via
a privileged reporting tool with its own service account.

IAM: `roles/datastore.user` scoped by Firestore security rules to allow
only writes on `audit_events/*`.
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
        })

    def events_for(self, church_id: str) -> list[AuditEvent]:
        # Intentionally not implemented. The service is write-only on the
        # audit log. Reads happen in a separate privileged tool.
        raise NotImplementedError(
            "membership-service does not read its own audit log; "
            "use the reporting tool with its own service account"
        )
