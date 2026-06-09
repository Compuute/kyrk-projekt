"""Firestore-backed funeral tracker."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from app.domain.models import FuneralCase

if TYPE_CHECKING:
    from google.cloud.firestore import Client  # pragma: no cover


_COLLECTION = "funerals"


def _doc_id(church_id: str, case_id: str) -> str:
    return f"{church_id}__{case_id}"


def _case_to_doc(c: FuneralCase) -> dict:
    return {
        "case_id": c.case_id,
        "church_id": c.church_id,
        "status": c.status,
        "created_at": c.created_at.isoformat() if c.created_at else None,
        "deceased_name": c.deceased_name,
        "deceased_name_am": c.deceased_name_am,
        "date_of_death": c.date_of_death,
        "date_of_birth": c.date_of_birth,
        "contact_person": c.contact_person,
        "contact_phone": c.contact_phone,
        "package": c.package,
        "repatriation": c.repatriation,
        "repatriation_destination": c.repatriation_destination,
        "ceremony_date": c.ceremony_date,
        "ceremony_time": c.ceremony_time,
        "burial_location": c.burial_location,
        "eder_name": c.eder_name,
        "eder_contribution": c.eder_contribution,
        "package_price": c.package_price,
        "repatriation_price": c.repatriation_price,
        "total_price": c.total_price,
        "paid": c.paid,
        "checklist": c.checklist,
        "memorial_page_url": c.memorial_page_url,
        "memorial_text_sv": c.memorial_text_sv,
        "memorial_text_am": c.memorial_text_am,
        "memorial_photo_url": c.memorial_photo_url,
        "grief_calendar_active": c.grief_calendar_active,
        "next_memorial_date": c.next_memorial_date,
        "next_memorial_name": c.next_memorial_name,
        "notes": c.notes,
    }


def _doc_to_case(data: dict) -> FuneralCase:
    created_at_val = data.get("created_at")
    created_at = None
    if created_at_val:
        if isinstance(created_at_val, datetime):
            created_at = created_at_val
        else:
            created_at = datetime.fromisoformat(created_at_val.replace("Z", "+00:00")).astimezone(timezone.utc)

    return FuneralCase(
        case_id=data["case_id"],
        church_id=data["church_id"],
        status=data.get("status", "registered"),
        created_at=created_at,
        deceased_name=data.get("deceased_name", ""),
        deceased_name_am=data.get("deceased_name_am", ""),
        date_of_death=data.get("date_of_death", ""),
        date_of_birth=data.get("date_of_birth", ""),
        contact_person=data.get("contact_person", ""),
        contact_phone=data.get("contact_phone", ""),
        package=data.get("package", "standard"),
        repatriation=data.get("repatriation", False),
        repatriation_destination=data.get("repatriation_destination", ""),
        ceremony_date=data.get("ceremony_date", ""),
        ceremony_time=data.get("ceremony_time", ""),
        burial_location=data.get("burial_location", ""),
        eder_name=data.get("eder_name", ""),
        eder_contribution=data.get("eder_contribution", 0.0),
        package_price=data.get("package_price", 0.0),
        repatriation_price=data.get("repatriation_price", 0.0),
        total_price=data.get("total_price", 0.0),
        paid=data.get("paid", False),
        checklist=data.get("checklist", {}),
        memorial_page_url=data.get("memorial_page_url", ""),
        memorial_text_sv=data.get("memorial_text_sv", ""),
        memorial_text_am=data.get("memorial_text_am", ""),
        memorial_photo_url=data.get("memorial_photo_url", ""),
        grief_calendar_active=data.get("grief_calendar_active", False),
        next_memorial_date=data.get("next_memorial_date", ""),
        next_memorial_name=data.get("next_memorial_name", ""),
        notes=data.get("notes", ""),
    )


class FirestoreFuneralTracker:
    def __init__(self, client: "Client | None" = None) -> None:
        self._client = client

    def _coll(self):
        if self._client is None:
            from google.cloud import firestore  # pragma: no cover

            self._client = firestore.Client()
        return self._client.collection(_COLLECTION)

    def list_cases(self, church_id: str) -> list[FuneralCase]:
        query = self._coll().where("church_id", "==", church_id)
        return [_doc_to_case(doc.to_dict()) for doc in query.stream()]

    def get_case(self, church_id: str, case_id: str) -> FuneralCase | None:
        snap = self._coll().document(_doc_id(church_id, case_id)).get()
        if not snap.exists:
            return None
        return _doc_to_case(snap.to_dict())

    def save_case(self, case: FuneralCase) -> None:
        self._coll().document(_doc_id(case.church_id, case.case_id)).set(
            _case_to_doc(case)
        )

    def delete_case(self, church_id: str, case_id: str) -> None:
        self._coll().document(_doc_id(church_id, case_id)).delete()
