"""Production httpx-backed clients for downstream services.

Lazy-imports httpx so that test code using the fake clients never needs
the library installed.
"""
from __future__ import annotations

from app.ports.client_errors import ClientError
from app.ports.clients import (
    ActivityAggregate,
    ApprovalResult,
    IssueCertificateRequest,
    IssuedCertificate,
    MonthlyReport,
    PendingSubmission,
    RejectResult,
)


class HttpxIntakeClient:
    def __init__(self, base_url: str, timeout_seconds: float = 5.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout_seconds

    def list_pending(self, token: str) -> list[PendingSubmission]:
        import httpx

        headers = {"Authorization": f"Bearer {token}"}
        try:
            r = httpx.get(
                f"{self._base_url}/submissions",
                headers=headers,
                timeout=self._timeout,
            )
        except httpx.HTTPError as exc:
            raise ClientError(f"network error: {exc}") from exc
        if r.status_code != 200:
            raise ClientError(r.text, status_code=r.status_code)
        return [
            PendingSubmission(
                submission_id=item["submission_id"],
                church_id=item["church_id"],
                first_name=item["first_name"],
                last_name=item["last_name"],
                received_at=item["received_at"],
                status=item["status"],
            )
            for item in r.json()
        ]

    def approve(self, token: str, submission_id: str) -> ApprovalResult:
        import httpx

        headers = {"Authorization": f"Bearer {token}"}
        try:
            r = httpx.post(
                f"{self._base_url}/submissions/{submission_id}/approve",
                headers=headers,
                timeout=self._timeout,
            )
        except httpx.HTTPError as exc:
            raise ClientError(f"network error: {exc}") from exc
        if r.status_code != 200:
            raise ClientError(r.text, status_code=r.status_code)
        data = r.json()
        return ApprovalResult(
            submission_id=data["submission_id"],
            status=data["status"],
            created_member_id=data["created_member_id"],
        )

    def reject(self, token: str, submission_id: str) -> RejectResult:
        import httpx

        headers = {"Authorization": f"Bearer {token}"}
        try:
            r = httpx.post(
                f"{self._base_url}/submissions/{submission_id}/reject",
                headers=headers,
                timeout=self._timeout,
            )
        except httpx.HTTPError as exc:
            raise ClientError(f"network error: {exc}") from exc
        if r.status_code != 200:
            raise ClientError(r.text, status_code=r.status_code)
        data = r.json()
        return RejectResult(submission_id=data["submission_id"], status=data["status"])


class HttpxCertificateClient:
    def __init__(self, base_url: str, timeout_seconds: float = 5.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout_seconds

    def issue(self, token: str, request: IssueCertificateRequest) -> IssuedCertificate:
        import httpx

        headers = {"Authorization": f"Bearer {token}"}
        body = {
            "certificate_type": request.certificate_type,
            "issued_date": request.issued_date,
            "member_id": request.member_id,
            "church_name": request.church_name,
        }
        try:
            r = httpx.post(
                f"{self._base_url}/certificates",
                json=body,
                headers=headers,
                timeout=self._timeout,
            )
        except httpx.HTTPError as exc:
            raise ClientError(f"network error: {exc}") from exc
        if r.status_code != 201:
            raise ClientError(r.text, status_code=r.status_code)
        data = r.json()
        return IssuedCertificate(
            certificate_id=data["certificate_id"],
            certificate_type=data["certificate_type"],
            issued_date=data["issued_date"],
            status=data["status"],
            verification_url=data["verification_url"],
        )


class HttpxActivityClient:
    def __init__(self, base_url: str, timeout_seconds: float = 5.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout_seconds

    def export_period(
        self, token: str, start: str, end: str
    ) -> list[ActivityAggregate]:
        import httpx

        headers = {"Authorization": f"Bearer {token}"}
        try:
            r = httpx.get(
                f"{self._base_url}/activities/export/period",
                params={"start": start, "end": end},
                headers=headers,
                timeout=self._timeout,
            )
        except httpx.HTTPError as exc:
            raise ClientError(f"network error: {exc}") from exc
        if r.status_code != 200:
            raise ClientError(r.text, status_code=r.status_code)
        return [
            ActivityAggregate(
                activity_id=row["activity_id"],
                church_id=row["church_id"],
                activity_type=row["activity_type"],
                date=row["date"],
                location=row["location"],
                funding_tag=row["funding_tag"],
                participants_total=row["participants_total"],
                age_band_counts=dict(row["age_band_counts"]),
            )
            for row in r.json()
        ]


class HttpxReportingClient:
    def __init__(self, base_url: str, timeout_seconds: float = 5.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout_seconds

    def generate_monthly(
        self,
        token: str,
        period: str,
        activities: list[dict],
        finance: dict,
    ) -> MonthlyReport:
        import httpx

        headers = {"Authorization": f"Bearer {token}"}
        body = {
            "period": period,
            "activities": activities,
            "finance": finance,
        }
        try:
            r = httpx.post(
                f"{self._base_url}/reports/monthly",
                json=body,
                headers=headers,
                timeout=self._timeout,
            )
        except httpx.HTTPError as exc:
            raise ClientError(f"network error: {exc}") from exc
        if r.status_code != 201:
            raise ClientError(r.text, status_code=r.status_code)
        data = r.json()
        return MonthlyReport(
            report_id=data["report_id"],
            kind=data["kind"],
            period=data["period"],
            payload=data["payload"],
        )
