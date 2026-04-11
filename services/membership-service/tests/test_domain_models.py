from app.domain.models import Member, MemberStatus


def _mk_member(**overrides):
    defaults = dict(
        church_id="c1",
        first_name="Anna",
        last_name="Andersson",
        phone="+4670000000",
        email="anna@example.se",
        personal_number_encrypted="enc::xxx",
    )
    defaults.update(overrides)
    return Member(**defaults)


def test_new_member_is_pending_with_uuid():
    m = _mk_member()
    assert m.status is MemberStatus.PENDING
    assert isinstance(m.member_id, str) and len(m.member_id) >= 32


def test_activate_and_deactivate_transitions():
    m = _mk_member()
    m.activate()
    assert m.status is MemberStatus.ACTIVE
    m.deactivate()
    assert m.status is MemberStatus.INACTIVE
