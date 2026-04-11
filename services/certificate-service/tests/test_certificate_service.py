from datetime import date

import pytest

from app.domain.errors import (
    CertificateNotFound,
    InvalidStateTransition,
    NotAuthorized,
)
from app.domain.models import Actor, CertificateStatus, CertificateType, Role
from app.services.certificate_service import IssueCertificateInput


def _actor(role: Role, church_id: str = "c1") -> Actor:
    return Actor(user_id="u1", church_id=church_id, role=role)


def _payload() -> IssueCertificateInput:
    return IssueCertificateInput(
        certificate_type=CertificateType.BAPTISM,
        issued_date=date(2025, 6, 1),
        member_id="m-1",
        church_name="Sankt Johannes kyrka",
    )


def test_pastor_can_issue(service):
    cert = service.issue(_actor(Role.PASTOR), _payload())
    assert cert.status is CertificateStatus.VALID
    assert cert.church_id == "c1"


def test_secretary_cannot_issue(service):
    with pytest.raises(NotAuthorized):
        service.issue(_actor(Role.SECRETARY), _payload())


def test_viewer_cannot_issue(service):
    with pytest.raises(NotAuthorized):
        service.issue(_actor(Role.VIEWER), _payload())


def test_verification_returns_no_identity(service):
    cert = service.issue(_actor(Role.PASTOR), _payload())
    result = service.verify_public(cert.certificate_id)
    # Identity fields must not leak
    data = result.__dict__
    for forbidden in ("member_id", "name", "first_name", "last_name", "personal_number"):
        assert forbidden not in data
    assert result.certificate_type == "baptism"
    assert result.issuing_church_name == "Sankt Johannes kyrka"
    assert result.status == "valid"


def test_verify_unknown_returns_not_found(service):
    with pytest.raises(CertificateNotFound):
        service.verify_public("does-not-exist")


def test_revoke_changes_status(service):
    cert = service.issue(_actor(Role.PASTOR), _payload())
    out = service.revoke(_actor(Role.ADMIN), cert.certificate_id)
    assert out.status is CertificateStatus.REVOKED


def test_double_revoke_is_conflict(service):
    cert = service.issue(_actor(Role.PASTOR), _payload())
    service.revoke(_actor(Role.ADMIN), cert.certificate_id)
    with pytest.raises(InvalidStateTransition):
        service.revoke(_actor(Role.ADMIN), cert.certificate_id)


def test_freeze_only_admin(service):
    cert = service.issue(_actor(Role.PASTOR), _payload())
    with pytest.raises(NotAuthorized):
        service.freeze(_actor(Role.PASTOR), cert.certificate_id)
    out = service.freeze(_actor(Role.ADMIN), cert.certificate_id)
    assert out.status is CertificateStatus.FROZEN


def test_cross_church_revoke_hidden_as_not_found(service):
    cert = service.issue(_actor(Role.PASTOR, "c1"), _payload())
    with pytest.raises(CertificateNotFound):
        service.revoke(_actor(Role.ADMIN, "c2"), cert.certificate_id)


def test_audit_on_issue_and_revoke(service, audit):
    cert = service.issue(_actor(Role.PASTOR), _payload())
    service.revoke(_actor(Role.ADMIN), cert.certificate_id)
    events = audit.events_for("c1")
    actions = [e.action for e in events]
    assert "certificate.issue" in actions
    assert "certificate.revoke" in actions
