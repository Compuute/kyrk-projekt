"""Firestore-backed audit log — the `audit_events` collection.

Document id is "<job or unparseable>:<message_id>" so a successful run is
trivially findable for redelivery dedupe. Only GREEN/YELLOW fields are
stored (status, period, report id) — never member data. Audit events are
permanent: no TTL on this collection by design.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from app.domain.models import AuditEvent, JobStatus

if TYPE_CHECKING:
    from google.cloud.firestore import Client  # pragma: no cover

_COLLECTION = "audit_events"


class FirestoreAuditLog:
    def __init__(self, client: "Client | None" = None) -> None:
        self._client = client

    def _coll(self):
        if self._client is None:
            from google.cloud import firestore  # pragma: no cover

            self._client = firestore.Client()
        return self._client.collection(_COLLECTION)

    @staticmethod
    def _success_doc_id(message_id: str) -> str:
        return f"success:{message_id}"

    def record(self, event: AuditEvent) -> None:
        doc = {
            "message_id": event.message_id,
            "job": event.job,
            "status": event.status.value,
            "agent": event.agent,
            "created_at": event.created_at,
            "period": event.period,
            "report_id": event.report_id,
            "detail": event.detail,
        }
        if event.status is JobStatus.SUCCEEDED:
            doc_id = self._success_doc_id(event.message_id)
        else:
            doc_id = f"{event.status.value}:{event.message_id}:{event.created_at.isoformat()}"
        self._coll().document(doc_id).set(doc)

    def seen(self, message_id: str) -> bool:
        snap = self._coll().document(self._success_doc_id(message_id)).get()
        return bool(snap.exists)
