"""Firestore-backed report repository.

Scope: only the `reports` collection. Documents keyed by
`{church_id}__{report_id}`. YELLOW zone — by ingest validation no PII
ever lands here, so no encryption needed.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from app.domain.models import Report, ReportKind

if TYPE_CHECKING:
    from google.cloud.firestore import Client  # pragma: no cover


_COLLECTION = "reports"


def _doc_id(church_id: str, report_id: str) -> str:
    return f"{church_id}__{report_id}"


def _report_to_doc(r: Report) -> dict:
    return {
        "report_id": r.report_id,
        "church_id": r.church_id,
        "kind": r.kind.value,
        "period": r.period,
        "payload": r.payload,
        "created_at": r.created_at.isoformat(),
    }


def _parse_dt(value) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def _doc_to_report(data: dict) -> Report:
    return Report(
        church_id=data["church_id"],
        kind=ReportKind(data["kind"]),
        period=data["period"],
        payload=data["payload"],
        report_id=data["report_id"],
        created_at=_parse_dt(data["created_at"]),
    )


class FirestoreReportRepository:
    def __init__(self, client: "Client | None" = None) -> None:
        self._client = client

    def _coll(self):
        if self._client is None:
            from google.cloud import firestore  # pragma: no cover

            self._client = firestore.Client()
        return self._client.collection(_COLLECTION)

    def add(self, report: Report) -> None:
        self._coll().document(_doc_id(report.church_id, report.report_id)).set(
            _report_to_doc(report)
        )

    def get(self, church_id: str, report_id: str) -> Report | None:
        snap = self._coll().document(_doc_id(church_id, report_id)).get()
        if not snap.exists:
            return None
        return _doc_to_report(snap.to_dict())
