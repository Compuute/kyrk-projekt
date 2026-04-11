"""Firestore-backed member repository.

Scope: only the `members` collection. Documents are keyed by
`{church_id}__{member_id}` so a cross-church read cannot even accidentally
succeed. The adapter never logs the raw document contents — error messages
carry only the document path so operators can diagnose without exposing PII.

IAM: the service account running this service needs
`roles/datastore.user` on the Firestore database (not editor, not owner).
Security rules further restrict reads/writes per collection.
"""
from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from app.domain.models import Member, MemberStatus

if TYPE_CHECKING:
    from google.cloud.firestore import Client  # pragma: no cover


_COLLECTION = "members"


def _doc_id(church_id: str, member_id: str) -> str:
    return f"{church_id}__{member_id}"


def _member_to_doc(m: Member) -> dict:
    return {
        "church_id": m.church_id,
        "first_name": m.first_name,
        "last_name": m.last_name,
        "phone": m.phone,
        "email": m.email,
        "personal_number_encrypted": m.personal_number_encrypted,
        "status": m.status.value,
        "member_id": m.member_id,
        "created_at": m.created_at.isoformat(),
        "updated_at": m.updated_at.isoformat(),
    }


def _doc_to_member(data: dict) -> Member:
    return Member(
        church_id=data["church_id"],
        first_name=data["first_name"],
        last_name=data["last_name"],
        phone=data["phone"],
        email=data["email"],
        personal_number_encrypted=data["personal_number_encrypted"],
        status=MemberStatus(data["status"]),
        member_id=data["member_id"],
        created_at=_parse_dt(data["created_at"]),
        updated_at=_parse_dt(data["updated_at"]),
    )


def _parse_dt(value: str) -> datetime:
    # Firestore Timestamps come back as `datetime`; ISO strings stay as-is.
    if isinstance(value, datetime):
        return value
    # Python 3.11+ handles ISO with Z via fromisoformat in 3.11+
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


class FirestoreMemberRepository:
    def __init__(self, client: "Client | None" = None) -> None:
        self._client = client

    def _coll(self):
        if self._client is None:
            # Lazy import so tests that never instantiate this adapter
            # don't require google-cloud-firestore to be installed.
            from google.cloud import firestore  # pragma: no cover

            self._client = firestore.Client()
        return self._client.collection(_COLLECTION)

    def add(self, member: Member) -> None:
        self._coll().document(_doc_id(member.church_id, member.member_id)).set(
            _member_to_doc(member)
        )

    def get(self, church_id: str, member_id: str) -> Member | None:
        snap = self._coll().document(_doc_id(church_id, member_id)).get()
        if not snap.exists:
            return None
        return _doc_to_member(snap.to_dict())

    def update(self, member: Member) -> None:
        self._coll().document(_doc_id(member.church_id, member.member_id)).set(
            _member_to_doc(member)
        )

    def list_by_church(self, church_id: str) -> list[Member]:
        query = self._coll().where("church_id", "==", church_id)
        return [_doc_to_member(doc.to_dict()) for doc in query.stream()]
