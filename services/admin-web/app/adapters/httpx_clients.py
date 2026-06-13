"""Production httpx-backed clients for downstream services.

Lazy-imports httpx so that test code using the fake clients never needs
the library installed.
"""
from __future__ import annotations

from app.ports.client_errors import ClientError
from app.ports.clients import (
    ActivityAggregate,
    ApprovalResult,
    DismissDonationResult,
    IssueCertificateRequest,
    IssuedCertificate,
    MonthlyReport,
    PendingDonation,
    PendingSubmission,
    RejectResult,
    VerifyDonationResult,
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

    def list_donations(self, token: str) -> list[PendingDonation]:
        import httpx

        headers = {"Authorization": f"Bearer {token}"}
        try:
            r = httpx.get(
                f"{self._base_url}/donations",
                headers=headers,
                timeout=self._timeout,
            )
        except httpx.HTTPError as exc:
            raise ClientError(f"network error: {exc}") from exc
        if r.status_code != 200:
            raise ClientError(r.text, status_code=r.status_code)
        return [
            PendingDonation(
                donation_id=item["donation_id"],
                church_id=item["church_id"],
                amount_sek=item["amount_sek"],
                method=item["method"],
                email_masked=item["email_masked"],
                received_at=item["received_at"],
                status=item["status"],
            )
            for item in r.json()
        ]

    def verify_donation(self, token: str, donation_id: str) -> VerifyDonationResult:
        import httpx

        headers = {"Authorization": f"Bearer {token}"}
        try:
            r = httpx.post(
                f"{self._base_url}/donations/{donation_id}/verify",
                headers=headers,
                timeout=self._timeout,
            )
        except httpx.HTTPError as exc:
            raise ClientError(f"network error: {exc}") from exc
        if r.status_code != 200:
            raise ClientError(r.text, status_code=r.status_code)
        data = r.json()
        return VerifyDonationResult(
            donation_id=data["donation_id"],
            status=data["status"],
            receipt_number=data["receipt_number"],
        )

    def dismiss_donation(self, token: str, donation_id: str) -> DismissDonationResult:
        import httpx

        headers = {"Authorization": f"Bearer {token}"}
        try:
            r = httpx.post(
                f"{self._base_url}/donations/{donation_id}/dismiss",
                headers=headers,
                timeout=self._timeout,
            )
        except httpx.HTTPError as exc:
            raise ClientError(f"network error: {exc}") from exc
        if r.status_code != 200:
            raise ClientError(r.text, status_code=r.status_code)
        data = r.json()
        return DismissDonationResult(
            donation_id=data["donation_id"], status=data["status"]
        )


class HttpxCertificateClient:
    def __init__(self, base_url: str, timeout_seconds: float = 5.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout_seconds

    def download(self, token: str, certificate_id: str) -> bytes:
        import httpx

        headers = {"Authorization": f"Bearer {token}"}
        try:
            r = httpx.get(
                f"{self._base_url}/certificates/{certificate_id}/download",
                headers=headers,
                timeout=self._timeout,
            )
        except httpx.HTTPError as exc:
            raise ClientError(f"network error: {exc}") from exc
        if r.status_code != 200:
            raise ClientError(r.text, status_code=r.status_code)
        return r.content

    def issue(self, token: str, request: IssueCertificateRequest) -> IssuedCertificate:
        import httpx

        headers = {"Authorization": f"Bearer {token}"}
        body = {
            "certificate_type": request.certificate_type,
            "issued_date": request.issued_date,
            "member_id": request.member_id,
            "church_name": request.church_name,
            "church_name_am": request.church_name_am,
            "language": request.language,
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
    def __init__(
        self,
        base_url: str,
        timeout_seconds: float = 5.0,
        id_token_provider=None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout_seconds
        self._id_token_provider = id_token_provider

    def _headers(self, token: str) -> dict[str, str]:
        headers = {"Authorization": f"Bearer {token}"}
        if self._id_token_provider is not None:
            id_token = self._id_token_provider(self._base_url)
            if id_token:
                headers["X-Serverless-Authorization"] = f"Bearer {id_token}"
        return headers

    def export_period(
        self, token: str, start: str, end: str
    ) -> list[ActivityAggregate]:
        import httpx

        headers = self._headers(token)
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

    def log_activity(
        self,
        token: str,
        activity_type: str,
        date: str,
        location: str,
        funding_tag: str,
        participants_total: int,
        age_band_counts: dict[str, int],
    ) -> str:
        import httpx

        try:
            r = httpx.post(
                f"{self._base_url}/activities",
                json={
                    "activity_type": activity_type,
                    "date": date,
                    "location": location,
                    "funding_tag": funding_tag,
                    "participants_total": participants_total,
                    "age_band_counts": age_band_counts,
                },
                headers=self._headers(token),
                timeout=self._timeout,
            )
        except httpx.HTTPError as exc:
            raise ClientError(f"network error: {exc}") from exc
        if r.status_code != 201:
            raise ClientError(r.text, status_code=r.status_code)
        return r.json()["activity_id"]


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
