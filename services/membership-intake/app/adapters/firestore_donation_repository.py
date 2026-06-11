"""Firestore-backed donation repository.

Scope: only the `donation_records` collection, keyed by donation_id (UUID).
Same data-minimization stance as intake_submissions: the donor email is
redacted in the document as soon as the record leaves PENDING_VERIFICATION
(see DonationRecord.redact), so verified/dismissed rows hold no address.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from app.domain.models import DonationRecord, DonationStatus

if TYPE_CHECKING:
    from google.cloud.firestore import Client  # pragma: no cover


_COLLECTION = "donation_records"


def _donation_to_doc(d: DonationRecord) -> dict:
    return {
        "donation_id": d.donation_id,
        "church_id": d.church_id,
        "amount_sek": d.amount_sek,
        "method": d.method,
        "email": d.email,
        "gdpr_consent": d.gdpr_consent,
        "status": d.status.value,
        "received_at": d.received_at.isoformat(),
        "processed_at": d.processed_at.isoformat() if d.processed_at else None,
        "processed_by_user_id": d.processed_by_user_id,
        "receipt_number": d.receipt_number,
    }


def _parse_dt(value) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def _doc_to_donation(doc: dict) -> DonationRecord:
    return DonationRecord(
        church_id=doc["church_id"],
        amount_sek=doc["amount_sek"],
        method=doc["method"],
        email=doc["email"],
        gdpr_consent=doc["gdpr_consent"],
        status=DonationStatus(doc["status"]),
        donation_id=doc["donation_id"],
        received_at=_parse_dt(doc["received_at"]),
        processed_at=_parse_dt(doc["processed_at"]) if doc.get("processed_at") else None,
        processed_by_user_id=doc.get("processed_by_user_id"),
        receipt_number=doc.get("receipt_number", ""),
    )


class FirestoreDonationRepository:
    def __init__(self, client: "Client | None" = None) -> None:
        self._client = client

    def _coll(self):
        if self._client is None:
            from google.cloud import firestore  # pragma: no cover

            self._client = firestore.Client()
        return self._client.collection(_COLLECTION)

    def add(self, donation: DonationRecord) -> None:
        self._coll().document(donation.donation_id).set(_donation_to_doc(donation))

    def get(self, donation_id: str) -> DonationRecord | None:
        snap = self._coll().document(donation_id).get()
        if not snap.exists:
            return None
        return _doc_to_donation(snap.to_dict())

    def update(self, donation: DonationRecord) -> None:
        self._coll().document(donation.donation_id).set(_donation_to_doc(donation))

    def list_pending(self, church_id: str) -> list[DonationRecord]:
        query = (
            self._coll()
            .where("church_id", "==", church_id)
            .where("status", "==", DonationStatus.PENDING_VERIFICATION.value)
        )
        return [_doc_to_donation(snap.to_dict()) for snap in query.stream()]
