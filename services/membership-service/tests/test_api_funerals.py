"""Tests for funeral API endpoints."""
from __future__ import annotations


def _body(case_id: str = "case1", church_id: str = "c1"):
    return {
        "case_id": case_id,
        "church_id": church_id,
        "status": "registered",
        "deceased_name": "John Doe",
        "contact_person": "Jane Doe",
        "contact_phone": "+4670000001",
        "package": "standard",
        "repatriation": False,
    }


def _headers(role: str, church: str = "c1", user: str = "u1") -> dict[str, str]:
    return {"Authorization": f"Bearer {user}:{church}:{role}"}


def test_list_requires_bearer(client):
    r = client.get("/funerals")
    assert r.status_code == 401


def test_list_rejects_viewer_role(client):
    r = client.get("/funerals", headers=_headers("viewer"))
    assert r.status_code == 403


def test_create_and_get_roundtrip(client):
    # Create a funeral case
    r = client.post("/funerals", json=_body(), headers=_headers("pastor"))
    assert r.status_code == 201, r.text
    assert r.json()["deceased_name"] == "John Doe"

    # Get the funeral case
    r = client.get("/funerals/case1", headers=_headers("pastor"))
    assert r.status_code == 200
    assert r.json()["deceased_name"] == "John Doe"

    # List funeral cases
    r = client.get("/funerals", headers=_headers("pastor"))
    assert r.status_code == 200
    assert len(r.json()) == 1
    assert r.json()[0]["case_id"] == "case1"


def test_church_isolation(client):
    # Create case in c1
    r = client.post("/funerals", json=_body("case1", "c1"), headers=_headers("admin", "c1"))
    assert r.status_code == 201

    # Attempt to read from c2
    r = client.get("/funerals/case1", headers=_headers("admin", "c2"))
    assert r.status_code == 404

    # Attempt to delete from c2
    r = client.delete("/funerals/case1", headers=_headers("admin", "c2"))
    assert r.status_code == 404


def test_create_rejects_different_church_id(client):
    # Admin of c1 tries to create case for c2
    r = client.post("/funerals", json=_body("case1", "c2"), headers=_headers("admin", "c1"))
    assert r.status_code == 400
    assert "church ID mismatch" in r.json()["detail"]


def test_delete_case(client):
    # Create case
    r = client.post("/funerals", json=_body(), headers=_headers("admin"))
    assert r.status_code == 201

    # Delete case
    r = client.delete("/funerals/case1", headers=_headers("admin"))
    assert r.status_code == 204

    # Verify deleted
    r = client.get("/funerals/case1", headers=_headers("admin"))
    assert r.status_code == 404
