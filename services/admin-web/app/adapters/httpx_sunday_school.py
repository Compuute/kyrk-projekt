"""Production httpx-backed Sunday school client (membership-service)."""
from __future__ import annotations

from app.ports.client_errors import ClientError
from app.ports.sunday_school import (
    AttendanceRecord,
    AttendanceResult,
    PendingEnrollment,
    SchoolEnrollment,
    SchoolGroup,
)


class HttpxSundaySchoolClient:
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

    def _get(self, token: str, path: str):
        import httpx

        try:
            r = httpx.get(
                f"{self._base_url}{path}",
                headers=self._headers(token),
                timeout=self._timeout,
            )
        except httpx.HTTPError as exc:
            raise ClientError(f"network error: {exc}") from exc
        if r.status_code != 200:
            raise ClientError(r.text, status_code=r.status_code)
        return r.json()

    def _post(self, token: str, path: str, payload: dict):
        import httpx

        try:
            r = httpx.post(
                f"{self._base_url}{path}",
                json=payload,
                headers=self._headers(token),
                timeout=self._timeout,
            )
        except httpx.HTTPError as exc:
            raise ClientError(f"network error: {exc}") from exc
        if r.status_code not in (200, 201):
            raise ClientError(r.text, status_code=r.status_code)
        return r.json()

    def list_groups(self, token: str) -> list[SchoolGroup]:
        rows = self._get(token, "/sunday-school/groups")
        return [
            SchoolGroup(
                group_id=row["group_id"],
                name=row["name"],
                description=row.get("description", ""),
                teacher_user_ids=tuple(row.get("teacher_user_ids", [])),
                funding_tag=row.get("funding_tag", "sondagsskola"),
                fee_required=row.get("fee_required", False),
            )
            for row in rows
        ]

    def list_pending(self, token: str) -> list[PendingEnrollment]:
        rows = self._get(token, "/sunday-school/pending")
        return [
            PendingEnrollment(
                enrollment_id=row["enrollment_id"],
                group_id=row["group_id"],
                child_first_name=row["child_first_name"],
                child_last_name=row["child_last_name"],
                birth_year=row["birth_year"],
                guardian_name=row.get("guardian_name", ""),
                consent_timestamp=row.get("consent_timestamp", ""),
            )
            for row in rows
        ]

    def approve(self, token: str, enrollment_id: str) -> None:
        self._post(token, f"/sunday-school/enrollments/{enrollment_id}/approve", {})

    def reject(self, token: str, enrollment_id: str) -> None:
        self._post(token, f"/sunday-school/enrollments/{enrollment_id}/reject", {})

    def list_paid_status(self, token: str, group_id: str, period: str) -> list[str]:
        data = self._get(
            token, f"/sunday-school/groups/{group_id}/paid-status?period={period}"
        )
        return list(data.get("paid_enrollment_ids", []))

    def mark_paid(
        self, token: str, enrollment_id: str, period: str,
        amount_sek: int, apply_to_siblings: bool,
    ) -> list[str]:
        data = self._post(
            token,
            f"/sunday-school/enrollments/{enrollment_id}/mark-paid",
            {"period": period, "amount_sek": amount_sek, "apply_to_siblings": apply_to_siblings},
        )
        return list(data.get("paid_enrollment_ids", []))

    def list_enrollments(self, token: str, group_id: str) -> list[SchoolEnrollment]:
        rows = self._get(token, f"/sunday-school/groups/{group_id}/enrollments")
        return [
            SchoolEnrollment(
                enrollment_id=row["enrollment_id"],
                child_first_name=row["child_first_name"],
                child_last_name=row["child_last_name"],
                birth_year=row["birth_year"],
            )
            for row in rows
        ]

    def list_attendance(self, token: str, group_id: str) -> list[AttendanceRecord]:
        rows = self._get(token, f"/sunday-school/groups/{group_id}/attendance")
        return [
            AttendanceRecord(
                date=row["date"],
                present_enrollment_ids=tuple(row.get("present_enrollment_ids", [])),
                participants_total=row["participants_total"],
                age_band_counts=dict(row["age_band_counts"]),
            )
            for row in rows
        ]

    def record_attendance(
        self, token: str, group_id: str, date: str, present_enrollment_ids: list[str]
    ) -> AttendanceResult:
        row = self._post(
            token,
            f"/sunday-school/groups/{group_id}/attendance",
            {"date": date, "present_enrollment_ids": present_enrollment_ids},
        )
        return AttendanceResult(
            attendance_id=row["attendance_id"],
            group_id=row["group_id"],
            date=row["date"],
            participants_total=row["participants_total"],
            age_band_counts=dict(row["age_band_counts"]),
        )

    def enroll(
        self,
        token: str,
        group_id: str,
        child_first_name: str,
        child_last_name: str,
        birth_year: int,
        guardian_name: str,
        guardian_phone: str,
        guardian_consent: bool,
    ) -> SchoolEnrollment:
        row = self._post(
            token,
            f"/sunday-school/groups/{group_id}/enrollments",
            {
                "child_first_name": child_first_name,
                "child_last_name": child_last_name,
                "birth_year": birth_year,
                "guardian_name": guardian_name,
                "guardian_phone": guardian_phone,
                "guardian_consent": guardian_consent,
            },
        )
        return SchoolEnrollment(
            enrollment_id=row["enrollment_id"],
            child_first_name=row["child_first_name"],
            child_last_name=row["child_last_name"],
            birth_year=row["birth_year"],
        )

    def create_group(
        self, token: str, name: str, description: str, teacher_user_ids: list[str],
        funding_tag: str = "sondagsskola", fee_required: bool = False,
    ) -> SchoolGroup:
        row = self._post(
            token,
            "/sunday-school/groups",
            {
                "name": name,
                "description": description,
                "teacher_user_ids": teacher_user_ids,
                "funding_tag": funding_tag,
                "fee_required": fee_required,
            },
        )
        return SchoolGroup(
            group_id=row["group_id"],
            name=row["name"],
            description=row.get("description", ""),
            teacher_user_ids=tuple(row.get("teacher_user_ids", [])),
            funding_tag=row.get("funding_tag", "sondagsskola"),
            fee_required=row.get("fee_required", False),
        )
