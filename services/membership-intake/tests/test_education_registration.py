"""Public education-registration edge endpoint → forwards to membership-service."""
from __future__ import annotations

from app.domain.errors import DownstreamFailure, RateLimited


def _body(**over):
    b = {
        "church_id": "stockholm",
        "group_id": "fredagsskola",
        "child_first_name": "Naomi",
        "child_last_name": "Abebe",
        "birth_year": 2016,
        "guardian_name": "Lidya Abebe",
        "guardian_consent": True,
        "consent_timestamp": "2026-06-24T10:00:00+00:00",
    }
    b.update(over)
    return b


def test_accepts_and_forwards_to_membership_service(client, membership_client):
    r = client.post("/education-registration", json=_body())
    assert r.status_code == 202, r.text
    assert len(membership_client.enrollments) == 1
    req, client_ip = membership_client.enrollments[0]
    assert req.group_id == "fredagsskola"
    assert req.guardian_consent is True
    assert client_ip  # forwarded for downstream rate-limiting


def test_requires_consent(client, membership_client):
    r = client.post("/education-registration", json=_body(guardian_consent=False))
    assert r.status_code == 422
    assert membership_client.enrollments == []  # nothing forwarded


def test_ignores_extra_activity_id(client, membership_client):
    r = client.post("/education-registration", json=_body(activity_id="fredagsskola"))
    assert r.status_code == 202


def test_missing_field_is_422(client):
    r = client.post("/education-registration", json=_body(group_id=""))
    assert r.status_code == 422


def test_downstream_rate_limit_maps_to_429(client, membership_client):
    membership_client.enroll_fail_with = RateLimited("downstream")
    r = client.post("/education-registration", json=_body())
    assert r.status_code == 429


def test_downstream_failure_maps_to_502(client, membership_client):
    membership_client.enroll_fail_with = DownstreamFailure("boom")
    r = client.post("/education-registration", json=_body())
    assert r.status_code == 502


def test_edge_rate_limited_per_ip(client, membership_client):
    # conftest limiter is max_hits=3 → 4th from same caller is 429, not forwarded.
    for _ in range(3):
        assert client.post("/education-registration", json=_body()).status_code == 202
    r = client.post("/education-registration", json=_body())
    assert r.status_code == 429
    assert len(membership_client.enrollments) == 3
