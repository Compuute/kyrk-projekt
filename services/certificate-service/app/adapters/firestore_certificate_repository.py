"""Firestore-backed certificate repository.

Scope: only the `certificates` collection. Documents keyed by
certificate_id (UUID). Error messages never include document contents.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import TYPE_CHECKING

from app.domain.models import Certificate, CertificateStatus, CertificateType

if TYPE_CHECKING:
    from google.cloud.firestore import Client  # pragma: no cover


_COLLECTION = "certificates"


def _cert_to_doc(c: Certificate) -> dict:
    return {
        "certificate_id": c.certificate_id,
        "church_id": c.church_id,
        "church_name": c.church_name,
        "certificate_type": c.certificate_type.value,
        "issued_date": c.issued_date.isoformat(),
        "member_id": c.member_id,
        "issued_by_user_id": c.issued_by_user_id,
        "status": c.status.value,
        "created_at": c.created_at.isoformat(),
    }


def _parse_dt(value) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def _doc_to_cert(data: dict) -> Certificate:
    return Certificate(
        church_id=data["church_id"],
        church_name=data["church_name"],
        certificate_type=CertificateType(data["certificate_type"]),
        issued_date=date.fromisoformat(data["issued_date"]),
        member_id=data["member_id"],
        issued_by_user_id=data["issued_by_user_id"],
        status=CertificateStatus(data["status"]),
        certificate_id=data["certificate_id"],
        created_at=_parse_dt(data["created_at"]),
    )


class FirestoreCertificateRepository:
    def __init__(self, client: "Client | None" = None) -> None:
        self._client = client

    def _coll(self):
        if self._client is None:
            from google.cloud import firestore  # pragma: no cover

            self._client = firestore.Client()
        return self._client.collection(_COLLECTION)

    def add(self, certificate: Certificate) -> None:
        self._coll().document(certificate.certificate_id).set(_cert_to_doc(certificate))

    def get(self, certificate_id: str) -> Certificate | None:
        snap = self._coll().document(certificate_id).get()
        if not snap.exists:
            return None
        return _doc_to_cert(snap.to_dict())

    def update(self, certificate: Certificate) -> None:
        self._coll().document(certificate.certificate_id).set(_cert_to_doc(certificate))
