import pytest

from app.domain.errors import ChurchMismatch, MemberNotFound, NotAuthorized
from app.domain.models import Actor, MemberStatus, Role
from app.services.membership_service import CreateMemberInput, UpdateMemberInput


def _actor(role: Role, church_id: str = "c1") -> Actor:
    return Actor(user_id="u1", church_id=church_id, role=role)


def _payload() -> CreateMemberInput:
    return CreateMemberInput(
        first_name="Anna",
        last_name="Andersson",
        phone="+4670000000",
        email="anna@example.se",
        personal_number="19800101-1234",
    )


def test_admin_can_create_member(service, audit):
    member = service.create(_actor(Role.ADMIN), _payload())
    assert member.church_id == "c1"
    assert member.first_name == "Anna"
    # personal_number never stored in plaintext
    assert "1980" not in member.personal_number_encrypted
    assert member.status is MemberStatus.PENDING
    events = audit.events_for("c1")
    assert len(events) == 1
    assert events[0].action == "member.create"


def test_viewer_cannot_create_member(service):
    with pytest.raises(NotAuthorized):
        service.create(_actor(Role.VIEWER), _payload())


def test_secretary_can_create_and_update(service):
    member = service.create(_actor(Role.SECRETARY), _payload())
    updated = service.update(
        _actor(Role.SECRETARY),
        member.member_id,
        UpdateMemberInput(phone="+4670999999"),
    )
    assert updated.phone == "+4670999999"


def test_secretary_cannot_deactivate(service):
    member = service.create(_actor(Role.ADMIN), _payload())
    with pytest.raises(NotAuthorized):
        service.deactivate(_actor(Role.SECRETARY), member.member_id)


def test_pastor_can_deactivate(service):
    member = service.create(_actor(Role.ADMIN), _payload())
    out = service.deactivate(_actor(Role.PASTOR), member.member_id)
    assert out.status is MemberStatus.INACTIVE


def test_cross_church_read_returns_not_found(service):
    member = service.create(_actor(Role.ADMIN, "c1"), _payload())
    with pytest.raises(MemberNotFound):
        service.get(_actor(Role.ADMIN, "c2"), member.member_id)


def test_audit_events_scoped_per_church(service, audit):
    service.create(_actor(Role.ADMIN, "c1"), _payload())
    service.create(_actor(Role.ADMIN, "c2"), _payload())
    assert len(audit.events_for("c1")) == 1
    assert len(audit.events_for("c2")) == 1
