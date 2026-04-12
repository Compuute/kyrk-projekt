"""In-memory fake clients for tests and local dev.

The fakes mimic the behavior of the real downstream services:
- `FakeIntakeClient` holds a list of pending submissions and lets tests
  programmatically add, approve, reject, and raise errors.
- `FakeCertificateClient` holds issued certificates and lets tests
  programmatically raise errors.
- `FakeActivityClient` holds seedable aggregates filtered by period.
- `FakeReportingClient` runs a minimal aggregation so the KPI dashboard
  can be exercised end-to-end in tests without the real service.
"""
from __future__ import annotations

from uuid import uuid4

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


class FakeIntakeClient:
    def __init__(self) -> None:
        self.submissions: dict[str, PendingSubmission] = {}
        self.approve_error: ClientError | None = None
        self.list_error: ClientError | None = None

    def seed(self, item: PendingSubmission) -> None:
        self.submissions[item.submission_id] = item

    def list_pending(self, token: str) -> list[PendingSubmission]:  # noqa: ARG002
        if self.list_error is not None:
            raise self.list_error
        return [s for s in self.submissions.values() if s.status == "pending"]

    def approve(self, token: str, submission_id: str) -> ApprovalResult:  # noqa: ARG002
        if self.approve_error is not None:
            raise self.approve_error
        sub = self.submissions.get(submission_id)
        if sub is None:
            raise ClientError("not found", status_code=404)
        if sub.status != "pending":
            raise ClientError("already processed", status_code=409)
        member_id = str(uuid4())
        self.submissions[submission_id] = PendingSubmission(
            submission_id=sub.submission_id,
            church_id=sub.church_id,
            first_name=sub.first_name,
            last_name=sub.last_name,
            received_at=sub.received_at,
            status="approved",
        )
        return ApprovalResult(
            submission_id=submission_id,
            status="approved",
            created_member_id=member_id,
        )

    def reject(self, token: str, submission_id: str) -> RejectResult:  # noqa: ARG002
        sub = self.submissions.get(submission_id)
        if sub is None:
            raise ClientError("not found", status_code=404)
        if sub.status != "pending":
            raise ClientError("already processed", status_code=409)
        self.submissions[submission_id] = PendingSubmission(
            submission_id=sub.submission_id,
            church_id=sub.church_id,
            first_name=sub.first_name,
            last_name=sub.last_name,
            received_at=sub.received_at,
            status="rejected",
        )
        return RejectResult(submission_id=submission_id, status="rejected")


class FakeCertificateClient:
    def __init__(self) -> None:
        self.issued: list[IssuedCertificate] = []
        self.issue_error: ClientError | None = None

    def issue(self, token: str, request: IssueCertificateRequest) -> IssuedCertificate:  # noqa: ARG002
        if self.issue_error is not None:
            raise self.issue_error
        cert_id = str(uuid4())
        issued = IssuedCertificate(
            certificate_id=cert_id,
            certificate_type=request.certificate_type,
            issued_date=request.issued_date,
            status="valid",
            verification_url=f"/certificates/verify/{cert_id}",
        )
        self.issued.append(issued)
        return issued


class FakeActivityClient:
    def __init__(self) -> None:
        self.activities: list[ActivityAggregate] = []
        self.export_error: ClientError | None = None

    def seed(self, item: ActivityAggregate) -> None:
        self.activities.append(item)

    def export_period(
        self, token: str, start: str, end: str  # noqa: ARG002
    ) -> list[ActivityAggregate]:
        if self.export_error is not None:
            raise self.export_error
        return [a for a in self.activities if start <= a.date <= end]


class FakeReportingClient:
    """Runs the same aggregation as the real reporting-service monthly report.

    Kept deliberately simple so the test does not need to spin up a
    second in-process service just to check the KPI dashboard rendering.
    """

    def __init__(self) -> None:
        self.generate_error: ClientError | None = None
        self.last_call: dict | None = None

    def generate_monthly(
        self,
        token: str,  # noqa: ARG002
        period: str,
        activities: list[dict],
        finance: dict,
    ) -> MonthlyReport:
        if self.generate_error is not None:
            raise self.generate_error
        self.last_call = {
            "period": period,
            "activities": activities,
            "finance": finance,
        }
        total = sum(a.get("participants_total", 0) for a in activities)
        by_type: dict[str, int] = {}
        by_age: dict[str, int] = {}
        for a in activities:
            by_type[a["activity_type"]] = (
                by_type.get(a["activity_type"], 0) + a.get("participants_total", 0)
            )
            for band, n in a.get("age_band_counts", {}).items():
                by_age[band] = by_age.get(band, 0) + n

        op_cost = float(finance.get("operating_cost", 0.0))
        grants = float(finance.get("grants", 0.0))
        own = float(finance.get("own_contribution", 0.0))
        cost_pp = op_cost / total if total > 0 else None
        leverage = grants / own if own > 0 else None

        return MonthlyReport(
            report_id=str(uuid4()),
            kind="monthly",
            period=period,
            payload={
                "period": period,
                "activities_count": len(activities),
                "participants_total": total,
                "participants_by_type": by_type,
                "participants_by_age_band": by_age,
                "cost_per_participant": cost_pp,
                "grant_leverage_ratio": leverage,
            },
        )
