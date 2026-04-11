"""In-memory fake clients for tests and local dev.

The fakes mimic the behavior of the real downstream services:
- `FakeIntakeClient` holds a list of pending submissions and lets tests
  programmatically add, approve, reject, and raise errors.
- `FakeCertificateClient` holds issued certificates and lets tests
  programmatically raise errors.
"""
from __future__ import annotations

from uuid import uuid4

from app.ports.client_errors import ClientError
from app.ports.clients import (
    ApprovalResult,
    IssueCertificateRequest,
    IssuedCertificate,
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
