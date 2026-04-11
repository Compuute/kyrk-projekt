from datetime import date

import pytest

from app.domain.errors import InvalidAgeBands, NotAuthorized
from app.domain.models import Actor, ActivityType, Role
from app.services.activity_service import CreateActivityInput


def _actor(role: Role, church_id: str = "c1") -> Actor:
    return Actor(user_id="u1", church_id=church_id, role=role)


def _payload(**overrides) -> CreateActivityInput:
    defaults = dict(
        activity_type=ActivityType.YOUTH_TECH,
        date=date(2025, 6, 1),
        location="Storgatan 1",
        funding_tag="arvsfonden",
        participants_total=20,
        age_band_counts={"0-6": 0, "7-12": 5, "13-17": 10, "18-25": 5, "26+": 0},
    )
    defaults.update(overrides)
    return CreateActivityInput(**defaults)


def test_admin_can_create(service):
    a = service.create(_actor(Role.ADMIN), _payload())
    assert a.participants_total == 20


def test_viewer_cannot_create(service):
    with pytest.raises(NotAuthorized):
        service.create(_actor(Role.VIEWER), _payload())


def test_age_band_sum_must_match(service):
    with pytest.raises(InvalidAgeBands):
        service.create(
            _actor(Role.ADMIN),
            _payload(age_band_counts={"0-6": 0, "7-12": 5, "13-17": 5, "18-25": 5, "26+": 0}),
        )


def test_unknown_band_rejected(service):
    with pytest.raises(InvalidAgeBands):
        service.create(
            _actor(Role.ADMIN),
            _payload(age_band_counts={"weird": 20}),
        )


def test_export_period_is_aggregate_only(service):
    service.create(_actor(Role.ADMIN), _payload())
    out = service.export_period(_actor(Role.VIEWER), date(2025, 1, 1), date(2025, 12, 31))
    assert len(out) == 1
    row = out[0]
    # No identity fields must appear in aggregate export
    for forbidden in ("name", "first_name", "last_name", "personal_number", "email", "phone"):
        assert forbidden not in row


def test_export_is_scoped_by_church(service):
    service.create(_actor(Role.ADMIN, "c1"), _payload())
    service.create(_actor(Role.ADMIN, "c2"), _payload())
    out = service.export_period(_actor(Role.VIEWER, "c1"), date(2025, 1, 1), date(2025, 12, 31))
    assert len(out) == 1
    assert out[0]["church_id"] == "c1"
