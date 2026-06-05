"""Firestore-backed activity repository.

Scope: only the `activities` collection. Documents keyed by
`{church_id}__{activity_id}`. YELLOW zone only — contains no identity
fields by construction, so no encryption needed.
"""
from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from app.domain.models import Activity, ActivityType

if TYPE_CHECKING:
    from google.cloud.firestore import Client  # pragma: no cover


_COLLECTION = "activities"


def _doc_id(church_id: str, activity_id: str) -> str:
    return f"{church_id}__{activity_id}"


def _activity_to_doc(a: Activity) -> dict:
    return {
        "activity_id": a.activity_id,
        "church_id": a.church_id,
        "activity_type": a.activity_type.value,
        "date": a.date.isoformat(),
        "location": a.location,
        "funding_tag": a.funding_tag,
        "participants_total": a.participants_total,
        "age_band_counts": a.age_band_counts,
    }


def _doc_to_activity(data: dict) -> Activity:
    return Activity(
        church_id=data["church_id"],
        activity_type=ActivityType(data["activity_type"]),
        date=date.fromisoformat(data["date"]),
        location=data["location"],
        funding_tag=data["funding_tag"],
        participants_total=data["participants_total"],
        age_band_counts=dict(data["age_band_counts"]),
        activity_id=data["activity_id"],
    )


class FirestoreActivityRepository:
    def __init__(self, client: "Client | None" = None) -> None:
        self._client = client

    def _coll(self):
        if self._client is None:
            from google.cloud import firestore  # pragma: no cover

            self._client = firestore.Client()
        return self._client.collection(_COLLECTION)

    def add(self, activity: Activity) -> None:
        self._coll().document(_doc_id(activity.church_id, activity.activity_id)).set(
            _activity_to_doc(activity)
        )

    def get(self, church_id: str, activity_id: str) -> Activity | None:
        snap = self._coll().document(_doc_id(church_id, activity_id)).get()
        if not snap.exists:
            return None
        return _doc_to_activity(snap.to_dict())

    def list_in_period(
        self, church_id: str, start: date, end: date
    ) -> list[Activity]:
        query = (
            self._coll()
            .where("church_id", "==", church_id)
            .where("date", ">=", start.isoformat())
            .where("date", "<=", end.isoformat())
        )
        return [_doc_to_activity(doc.to_dict()) for doc in query.stream()]
