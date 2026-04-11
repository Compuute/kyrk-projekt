"""Firestore-backed submission repository.

Scope: only the `intake_submissions` collection. Documents keyed by
submission_id (a UUID). Error messages never include document contents.

IAM: `roles/datastore.user` on the Firestore database. Security rules
further restrict reads/writes to this single collection.

Known data-minimization gap: pending submissions currently hold
plaintext personal_number / phone / email. For strict least-exposure
these should be encrypted with a dedicated KMS key at write time and
decrypted only during the approval handoff. Tracked as a follow-up.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from app.domain.models import IntakeSubmission, SubmissionStatus

if TYPE_CHECKING:
    from google.cloud.firestore import Client  # pragma: no cover


_COLLECTION = "intake_submissions"


def _submission_to_doc(s: IntakeSubmission) -> dict:
    return {
        "submission_id": s.submission_id,
        "church_id": s.church_id,
        "first_name": s.first_name,
        "last_name": s.last_name,
        "phone": s.phone,
        "email": s.email,
        "personal_number": s.personal_number,
        "gdpr_consent": s.gdpr_consent,
        "consent_timestamp": s.consent_timestamp.isoformat(),
        "status": s.status.value,
        "received_at": s.received_at.isoformat(),
        "processed_at": s.processed_at.isoformat() if s.processed_at else None,
        "processed_by_user_id": s.processed_by_user_id,
        "created_member_id": s.created_member_id,
    }


def _parse_dt(value) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def _doc_to_submission(data: dict) -> IntakeSubmission:
    return IntakeSubmission(
        church_id=data["church_id"],
        first_name=data["first_name"],
        last_name=data["last_name"],
        phone=data["phone"],
        email=data["email"],
        personal_number=data["personal_number"],
        gdpr_consent=data["gdpr_consent"],
        consent_timestamp=_parse_dt(data["consent_timestamp"]),
        status=SubmissionStatus(data["status"]),
        submission_id=data["submission_id"],
        received_at=_parse_dt(data["received_at"]),
        processed_at=_parse_dt(data["processed_at"]) if data.get("processed_at") else None,
        processed_by_user_id=data.get("processed_by_user_id"),
        created_member_id=data.get("created_member_id"),
    )


class FirestoreSubmissionRepository:
    def __init__(self, client: "Client | None" = None) -> None:
        self._client = client

    def _coll(self):
        if self._client is None:
            from google.cloud import firestore  # pragma: no cover

            self._client = firestore.Client()
        return self._client.collection(_COLLECTION)

    def add(self, submission: IntakeSubmission) -> None:
        self._coll().document(submission.submission_id).set(_submission_to_doc(submission))

    def get(self, submission_id: str) -> IntakeSubmission | None:
        snap = self._coll().document(submission_id).get()
        if not snap.exists:
            return None
        return _doc_to_submission(snap.to_dict())

    def update(self, submission: IntakeSubmission) -> None:
        self._coll().document(submission.submission_id).set(_submission_to_doc(submission))

    def list_pending(self, church_id: str) -> list[IntakeSubmission]:
        query = (
            self._coll()
            .where("church_id", "==", church_id)
            .where("status", "==", SubmissionStatus.PENDING.value)
        )
        return [_doc_to_submission(doc.to_dict()) for doc in query.stream()]
