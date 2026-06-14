"""Firestore-backed grant tracker (YELLOW-zone data).

Moved here from admin-web: the public-facing admin tier must not hold
Firestore credentials, so grant-application storage lives behind this
service (same pattern as funerals). Collection: `grants`.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from app.domain.models import GrantApplication

if TYPE_CHECKING:
    from google.cloud.firestore import Client  # pragma: no cover


_COLLECTION = "grants"


def _doc_id(church_id: str, grant_id: str) -> str:
    return f"{church_id}__{grant_id}"


def _parse_dt(value):
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def _app_to_doc(a: GrantApplication) -> dict:
    return {
        "grant_id": a.grant_id,
        "church_id": a.church_id,
        "status": a.status,
        "started_at": a.started_at.isoformat() if a.started_at else None,
        "submitted_at": a.submitted_at.isoformat() if a.submitted_at else None,
        "amount_requested": a.amount_requested,
        "amount_granted": a.amount_granted,
        "notes": a.notes,
        "generated_draft_url": a.generated_draft_url,
        "project_name": a.project_name,
        "project_description": a.project_description,
        "target_group": a.target_group,
        "budget_amount": a.budget_amount,
        "own_contribution": a.own_contribution,
    }


def _doc_to_app(data: dict) -> GrantApplication:
    return GrantApplication(
        grant_id=data["grant_id"],
        church_id=data["church_id"],
        status=data.get("status", "not_started"),
        started_at=_parse_dt(data.get("started_at")),
        submitted_at=_parse_dt(data.get("submitted_at")),
        amount_requested=data.get("amount_requested"),
        amount_granted=data.get("amount_granted"),
        notes=data.get("notes", ""),
        generated_draft_url=data.get("generated_draft_url"),
        project_name=data.get("project_name", ""),
        project_description=data.get("project_description", ""),
        target_group=data.get("target_group", ""),
        budget_amount=data.get("budget_amount"),
        own_contribution=data.get("own_contribution"),
    )


class FirestoreGrantTracker:
    def __init__(self, client: "Client | None" = None) -> None:
        self._client = client

    def _coll(self):
        if self._client is None:
            from google.cloud import firestore  # pragma: no cover

            self._client = firestore.Client()
        return self._client.collection(_COLLECTION)

    def list_applications(self, church_id: str) -> list[GrantApplication]:
        query = self._coll().where("church_id", "==", church_id)
        return [_doc_to_app(doc.to_dict()) for doc in query.stream()]

    def get_application(self, church_id: str, grant_id: str) -> GrantApplication | None:
        snap = self._coll().document(_doc_id(church_id, grant_id)).get()
        if not snap.exists:
            return None
        return _doc_to_app(snap.to_dict())

    def save_application(self, app: GrantApplication) -> None:
        self._coll().document(_doc_id(app.church_id, app.grant_id)).set(
            _app_to_doc(app)
        )
