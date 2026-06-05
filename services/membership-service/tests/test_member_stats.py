"""Tests for GET /members/stats/summary and the membership stats use case."""
from datetime import datetime, timezone

from app.domain.models import Actor, Member, MemberStatus, Role
from app.services.membership_service import CreateMemberInput


def _actor(role=Role.ADMIN, church_id="c1"):
    return Actor(user_id="u1", church_id=church_id, role=role)


def _payload(**kw):
    defaults = dict(
        first_name="Anna", last_name="A", phone="+46700000000",
        email="a@example.se", personal_number="19800101-1234",
    )
    defaults.update(kw)
    return CreateMemberInput(**defaults)


def test_stats_empty_church(service):
    s = service.stats(_actor())
    assert s.total == 0
    assert s.active == 0
    assert s.retention_rate == 1.0
    assert s.growth_rate_quarterly == 0.0


def test_stats_counts_active_and_inactive(service):
    m1 = service.create(_actor(), _payload(first_name="A"))
    service.activate(_actor(), m1.member_id)
    m2 = service.create(_actor(), _payload(first_name="B"))
    service.activate(_actor(), m2.member_id)
    m3 = service.create(_actor(), _payload(first_name="C"))
    service.activate(_actor(), m3.member_id)
    service.deactivate(_actor(), m3.member_id)

    s = service.stats(_actor())
    assert s.total == 3
    assert s.active == 2
    assert s.inactive == 1
    assert s.pending == 0
    assert s.retention_rate == round(2 / 3, 4)


def test_stats_new_this_month(service):
    service.create(_actor(), _payload(first_name="New"))
    s = service.stats(_actor())
    assert s.new_this_month >= 1


def test_stats_scoped_by_church(service):
    service.create(_actor(church_id="c1"), _payload(first_name="A"))
    service.create(_actor(church_id="c2"), _payload(first_name="B"))
    s = service.stats(_actor(church_id="c1"))
    assert s.total == 1
    assert s.church_id == "c1"


def test_stats_viewer_can_access(service):
    service.create(_actor(), _payload())
    s = service.stats(_actor(role=Role.VIEWER))
    assert s.total == 1


def test_stats_api_returns_json(client):
    # Create a member first
    client.post("/members", json={
        "first_name": "Anna", "last_name": "A", "phone": "+46700",
        "email": "a@example.se", "personal_number": "19800101-1234",
    }, headers={"Authorization": "Bearer u1:c1:admin"})

    r = client.get("/members/stats/summary",
                   headers={"Authorization": "Bearer u1:c1:admin"})
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 1
    assert data["church_id"] == "c1"
    assert "retention_rate" in data
    assert "growth_rate_quarterly" in data
    assert "new_this_month" in data


def test_stats_requires_auth(client):
    r = client.get("/members/stats/summary")
    assert r.status_code == 401


def test_stats_no_pii_in_response(client):
    client.post("/members", json={
        "first_name": "Anna", "last_name": "Andersson",
        "phone": "+4670000", "email": "anna@example.se",
        "personal_number": "19800101-1234",
    }, headers={"Authorization": "Bearer u1:c1:admin"})

    r = client.get("/members/stats/summary",
                   headers={"Authorization": "Bearer u1:c1:admin"})
    text = r.text.lower()
    assert "anna" not in text
    assert "andersson" not in text
    assert "19800101" not in text
    assert "example.se" not in text
