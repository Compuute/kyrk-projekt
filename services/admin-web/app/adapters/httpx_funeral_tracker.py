"""HTTP-backed client for accessing membership-service's funeral endpoints."""
from __future__ import annotations

from datetime import datetime, timezone
import json
from typing import TYPE_CHECKING

from app.ports.client_errors import ClientError
from app.ports.funeral_tracker import FuneralCase

if TYPE_CHECKING:
    import httpx


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


class HttpxFuneralTracker:
    def __init__(
        self,
        base_url: str,
        token: str,
        timeout_seconds: float = 5.0,
        id_token_provider=None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._token = token
        self._timeout = timeout_seconds
        self._id_token_provider = id_token_provider

    def _headers(self) -> dict[str, str]:
        headers = {"Authorization": f"Bearer {self._token}"}
        if self._id_token_provider is not None:
            id_token = self._id_token_provider(self._base_url)
            if id_token:
                headers["X-Serverless-Authorization"] = f"Bearer {id_token}"
        return headers

    def list_cases(self, church_id: str) -> list[FuneralCase]:  # noqa: ARG002
        import httpx

        try:
            r = httpx.get(
                f"{self._base_url}/funerals",
                headers=self._headers(),
                timeout=self._timeout,
            )
        except httpx.HTTPError as exc:
            raise ClientError(f"network error: {exc}") from exc
        if r.status_code != 200:
            raise ClientError(r.text, status_code=r.status_code)
        return [_doc_to_case(item) for item in r.json()]

    def get_case(self, church_id: str, case_id: str) -> FuneralCase | None:  # noqa: ARG002
        import httpx

        try:
            r = httpx.get(
                f"{self._base_url}/funerals/{case_id}",
                headers=self._headers(),
                timeout=self._timeout,
            )
        except httpx.HTTPError as exc:
            raise ClientError(f"network error: {exc}") from exc
        if r.status_code == 404:
            return None
        if r.status_code != 200:
            raise ClientError(r.text, status_code=r.status_code)
        return _doc_to_case(r.json())

    def save_case(self, case: FuneralCase) -> None:
        import httpx

        # Serialize case to dictionary
        body = {
            "case_id": case.case_id,
            "church_id": case.church_id,
            "status": case.status,
            "created_at": case.created_at.isoformat() if case.created_at else None,
            "deceased_name": case.deceased_name,
            "deceased_name_am": case.deceased_name_am,
            "date_of_death": case.date_of_death,
            "date_of_birth": case.date_of_birth,
            "contact_person": case.contact_person,
            "contact_phone": case.contact_phone,
            "package": case.package,
            "repatriation": case.repatriation,
            "repatriation_destination": case.repatriation_destination,
            "ceremony_date": case.ceremony_date,
            "ceremony_time": case.ceremony_time,
            "burial_location": case.burial_location,
            "eder_name": case.eder_name,
            "eder_contribution": case.eder_contribution,
            "package_price": case.package_price,
            "repatriation_price": case.repatriation_price,
            "total_price": case.total_price,
            "paid": case.paid,
            "checklist": case.checklist,
            "memorial_page_url": case.memorial_page_url,
            "memorial_text_sv": case.memorial_text_sv,
            "memorial_text_am": case.memorial_text_am,
            "memorial_photo_url": case.memorial_photo_url,
            "grief_calendar_active": case.grief_calendar_active,
            "next_memorial_date": case.next_memorial_date,
            "next_memorial_name": case.next_memorial_name,
            "notes": case.notes,
        }
        try:
            r = httpx.post(
                f"{self._base_url}/funerals",
                json=body,
                headers=self._headers(),
                timeout=self._timeout,
            )
        except httpx.HTTPError as exc:
            raise ClientError(f"network error: {exc}") from exc
        if r.status_code not in (200, 201):
            raise ClientError(r.text, status_code=r.status_code)

    def delete_case(self, church_id: str, case_id: str) -> None:  # noqa: ARG002
        import httpx

        try:
            r = httpx.delete(
                f"{self._base_url}/funerals/{case_id}",
                headers=self._headers(),
                timeout=self._timeout,
            )
        except httpx.HTTPError as exc:
            raise ClientError(f"network error: {exc}") from exc
        if r.status_code != 204:
            raise ClientError(r.text, status_code=r.status_code)
