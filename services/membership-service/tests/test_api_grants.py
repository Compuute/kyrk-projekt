"""Tests for grant application API endpoints."""
from __future__ import annotations


def _body(grant_id: str = "sst-org-2025", church_id: str = "c1", **overrides):
    body = {
        "grant_id": grant_id,
        "church_id": church_id,
        "status": "in_progress",
        "project_name": "Ungdomsläger",
        "target_group": "unga 13-25",
        "budget_amount": 120000,
        "own_contribution": 20000,
    }
    body.update(overrides)
    return body


def _headers(role: str, church: str = "c1", user: str = "u1") -> dict[str, str]:
    return {"Authorization": f"Bearer {user}:{church}:{role}"}


def test_list_requires_bearer(client):
    assert client.get("/grants").status_code == 401


def test_list_rejects_viewer_role(client):
    assert client.get("/grants", headers=_headers("viewer")).status_code == 403


def test_create_and_get_roundtrip(client):
    r = client.post("/grants", json=_body(), headers=_headers("pastor"))
    assert r.status_code == 201, r.text
    assert r.json()["project_name"] == "Ungdomsläger"

    r = client.get("/grants/sst-org-2025", headers=_headers("pastor"))
    assert r.status_code == 200
    assert r.json()["budget_amount"] == 120000

    r = client.get("/grants", headers=_headers("pastor"))
    assert r.status_code == 200
    assert len(r.json()) == 1


def test_get_unknown_returns_404(client):
    r = client.get("/grants/does-not-exist", headers=_headers("admin"))
    assert r.status_code == 404


def test_church_scoping_on_save(client):
    # Body church must match the actor's org — no cross-church writes.
    r = client.post("/grants", json=_body(church_id="c2"), headers=_headers("admin", "c1"))
    assert r.status_code == 400


def test_applications_are_church_scoped(client):
    client.post("/grants", json=_body("g1", "c1"), headers=_headers("admin", "c1"))
    # Another church's admin sees nothing of c1's applications.
    r = client.get("/grants", headers=_headers("admin", "c2"))
    assert r.status_code == 200
    assert r.json() == []


def test_save_is_idempotent_per_grant(client):
    client.post("/grants", json=_body(status="in_progress"), headers=_headers("admin"))
    client.post("/grants", json=_body(status="submitted"), headers=_headers("admin"))
    r = client.get("/grants", headers=_headers("admin"))
    assert len(r.json()) == 1
    assert r.json()[0]["status"] == "submitted"
