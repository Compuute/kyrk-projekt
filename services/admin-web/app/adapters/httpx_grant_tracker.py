"""Production httpx-backed grant tracker.

Proxies grant-application storage to membership-service (/grants), forwarding
the admin's bearer token. Keeps Firestore credentials out of the public-facing
admin-web tier — same pattern as HttpxFuneralTracker.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.ports.client_errors import ClientError
from app.ports.grant_tracker import GrantApplication


def _parse_dt(value):
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def _app_to_body(a: GrantApplication) -> dict:
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


def _json_to_app(data: dict) -> GrantApplication:
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


class HttpxGrantTracker:
    def __init__(self, base_url: str, token: str, timeout_seconds: float = 5.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._token = token
        self._timeout = timeout_seconds

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._token}"}

    def list_applications(self, church_id: str) -> list[GrantApplication]:  # noqa: ARG002
        import httpx

        try:
            r = httpx.get(
                f"{self._base_url}/grants",
                headers=self._headers(),
                timeout=self._timeout,
            )
        except httpx.HTTPError as exc:
            raise ClientError(f"network error: {exc}") from exc
        if r.status_code != 200:
            raise ClientError(r.text, status_code=r.status_code)
        return [_json_to_app(item) for item in r.json()]

    def get_application(self, church_id: str, grant_id: str) -> GrantApplication | None:  # noqa: ARG002
        import httpx

        try:
            r = httpx.get(
                f"{self._base_url}/grants/{grant_id}",
                headers=self._headers(),
                timeout=self._timeout,
            )
        except httpx.HTTPError as exc:
            raise ClientError(f"network error: {exc}") from exc
        if r.status_code == 404:
            return None
        if r.status_code != 200:
            raise ClientError(r.text, status_code=r.status_code)
        return _json_to_app(r.json())

    def save_application(self, app: GrantApplication) -> None:
        import httpx

        try:
            r = httpx.post(
                f"{self._base_url}/grants",
                json=_app_to_body(app),
                headers=self._headers(),
                timeout=self._timeout,
            )
        except httpx.HTTPError as exc:
            raise ClientError(f"network error: {exc}") from exc
        if r.status_code not in (200, 201):
            raise ClientError(r.text, status_code=r.status_code)
