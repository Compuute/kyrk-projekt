"""Certificate use cases — issue, revoke, freeze, verify."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from app.domain.errors import (
    CertificateNotFound,
    InvalidStateTransition,
    NotAuthorized,
)
from app.domain.models import (
    Actor,
    Certificate,
    CertificateStatus,
    CertificateType,
    Role,
)
from app.ports.audit import AuditEvent, AuditPort
from app.ports.certificate_repository import CertificateRepository


_ISSUE_ROLES: set[Role] = {Role.ADMIN, Role.PASTOR}
_REVOKE_ROLES: set[Role] = {Role.ADMIN, Role.PASTOR}
_FREEZE_ROLES: set[Role] = {Role.ADMIN}


@dataclass(frozen=True)
class IssueCertificateInput:
    certificate_type: CertificateType
    issued_date: date
    member_id: str
    church_name: str


@dataclass(frozen=True)
class VerificationResult:
    """Privacy-preserving payload. No identity ever."""
    certificate_type: str
    issued_date: str
    issuing_church_name: str
    status: str


class CertificateService:
    def __init__(self, repo: CertificateRepository, audit: AuditPort) -> None:
        self._repo = repo
        self._audit = audit

    # ------------------------------------------------------------------ writes

    def issue(self, actor: Actor, data: IssueCertificateInput) -> Certificate:
        self._require_role(actor, _ISSUE_ROLES)
        cert = Certificate(
            church_id=actor.church_id,
            church_name=data.church_name,
            certificate_type=data.certificate_type,
            issued_date=data.issued_date,
            member_id=data.member_id,
            issued_by_user_id=actor.user_id,
        )
        self._repo.add(cert)
        self._audit.record(AuditEvent(
            actor_user_id=actor.user_id,
            church_id=actor.church_id,
            action="certificate.issue",
            target_id=cert.certificate_id,
        ))
        return cert

    def revoke(self, actor: Actor, certificate_id: str) -> Certificate:
        self._require_role(actor, _REVOKE_ROLES)
        cert = self._load_scoped(actor, certificate_id)
        if cert.status is CertificateStatus.REVOKED:
            raise InvalidStateTransition("already revoked")
        cert.status = CertificateStatus.REVOKED
        self._repo.update(cert)
        self._audit.record(AuditEvent(
            actor_user_id=actor.user_id,
            church_id=actor.church_id,
            action="certificate.revoke",
            target_id=cert.certificate_id,
        ))
        return cert

    def freeze(self, actor: Actor, certificate_id: str) -> Certificate:
        self._require_role(actor, _FREEZE_ROLES)
        cert = self._load_scoped(actor, certificate_id)
        if cert.status is CertificateStatus.REVOKED:
            raise InvalidStateTransition("cannot freeze a revoked certificate")
        cert.status = CertificateStatus.FROZEN
        self._repo.update(cert)
        self._audit.record(AuditEvent(
            actor_user_id=actor.user_id,
            church_id=actor.church_id,
            action="certificate.freeze",
            target_id=cert.certificate_id,
        ))
        return cert

    # ------------------------------------------------------------------- reads

    def verify_public(self, certificate_id: str) -> VerificationResult:
        """Public verification. Returns only the minimum safe payload."""
        cert = self._repo.get(certificate_id)
        if cert is None:
            raise CertificateNotFound(certificate_id)
        return VerificationResult(
            certificate_type=cert.certificate_type.value,
            issued_date=cert.issued_date.isoformat(),
            issuing_church_name=cert.church_name,
            status=cert.status.value,
        )

    # --------------------------------------------------------------- internals

    def _require_role(self, actor: Actor, allowed: set[Role]) -> None:
        if actor.role not in allowed:
            raise NotAuthorized(f"role {actor.role.value} cannot perform this action")

    def _load_scoped(self, actor: Actor, certificate_id: str) -> Certificate:
        cert = self._repo.get(certificate_id)
        if cert is None or cert.church_id != actor.church_id:
            raise CertificateNotFound(certificate_id)
        return cert
