"""HTTP client ports for downstream services.

Tests use fake in-memory implementations; production wires httpx clients
behind the same interface.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


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
