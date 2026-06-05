"""HTTP client ports for downstream services.

Tests use fake in-memory implementations; production wires httpx clients
behind the same interface.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


# --------------------------------------------------------------------- intake


@dataclass(frozen=True)
class PendingSubmission:
    submission_id: str
    church_id: str
    first_name: str
    last_name: str
    received_at: str
    status: str


@dataclass(frozen=True)
class ApprovalResult:
    submission_id: str
    status: str
    created_member_id: str


@dataclass(frozen=True)
class RejectResult:
    submission_id: str
    status: str


class IntakeClientPort(Protocol):
    def list_pending(self, token: str) -> list[PendingSubmission]: ...
    def approve(self, token: str, submission_id: str) -> ApprovalResult: ...
    def reject(self, token: str, submission_id: str) -> RejectResult: ...


# ---------------------------------------------------------------- certificates


@dataclass(frozen=True)
class IssueCertificateRequest:
    certificate_type: str
    issued_date: str  # ISO date
    member_id: str
    church_name: str


@dataclass(frozen=True)
class IssuedCertificate:
    certificate_id: str
    certificate_type: str
    issued_date: str
    status: str
    verification_url: str


class CertificateClientPort(Protocol):
    def issue(self, token: str, request: IssueCertificateRequest) -> IssuedCertificate: ...


# -------------------------------------------------------------------- activity


@dataclass(frozen=True)
class ActivityAggregate:
    """A single activity row from reporting-service's YELLOW-only activity export."""
    activity_id: str
    church_id: str
    activity_type: str
    date: str
    location: str
    funding_tag: str
    participants_total: int
    age_band_counts: dict[str, int]


class ActivityClientPort(Protocol):
    def export_period(
        self, token: str, start: str, end: str
    ) -> list[ActivityAggregate]: ...


# ------------------------------------------------------------------- reporting


@dataclass(frozen=True)
class MonthlyReport:
    report_id: str
    kind: str
    period: str
    payload: dict  # see reporting-service monthly schema


class ReportingClientPort(Protocol):
    def generate_monthly(
        self,
        token: str,
        period: str,
        activities: list[dict],
        finance: dict,
    ) -> MonthlyReport: ...
