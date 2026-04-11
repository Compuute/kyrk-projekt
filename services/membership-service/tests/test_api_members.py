def _body():
    return {
        "first_name": "Anna",
        "last_name": "Andersson",
        "phone": "+4670000000",
        "email": "anna@example.se",
        "personal_number": "19800101-1234",
    }


def _headers(role: str, church: str = "c1", user: str = "u1") -> dict[str, str]:
    return {"Authorization": f"Bearer {user}:{church}:{role}"}


def test_healthz(client):
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_create_requires_bearer(client):
    r = client.post("/members", json=_body())
    assert r.status_code == 401


def test_create_rejects_viewer_role(client):
    r = client.post("/members", json=_body(), headers=_headers("viewer"))
    assert r.status_code == 403


def test_create_and_get_roundtrip(client):
    r = client.post("/members", json=_body(), headers=_headers("admin"))
    assert r.status_code == 201, r.text
    member_id = r.json()["member_id"]

    r = client.get(f"/members/{member_id}", headers=_headers("admin"))
    assert r.status_code == 200
    assert r.json()["first_name"] == "Anna"


def test_get_is_scoped_by_church(client):
    created = client.post("/members", json=_body(), headers=_headers("admin", "c1")).json()
    r = client.get(f"/members/{created['member_id']}", headers=_headers("admin", "c2"))
    assert r.status_code == 404


def test_update_patches_fields(client):
    member_id = client.post("/members", json=_body(), headers=_headers("admin")).json()["member_id"]
    r = client.patch(
        f"/members/{member_id}",
        json={"phone": "+4670999999"},
        headers=_headers("admin"),
    )
    assert r.status_code == 200
    assert r.json()["phone"] == "+4670999999"


def test_deactivate_requires_admin_or_pastor(client):
    member_id = client.post("/members", json=_body(), headers=_headers("admin")).json()["member_id"]
    r = client.post(f"/members/{member_id}/deactivate", headers=_headers("secretary"))
    assert r.status_code == 403

    r = client.post(f"/members/{member_id}/deactivate", headers=_headers("pastor"))
    assert r.status_code == 200
    assert r.json()["status"] == "inactive"


def test_malformed_input_returns_422(client):
    r = client.post(
        "/members",
        json={"first_name": "", "last_name": "", "phone": "", "email": "not-an-email", "personal_number": "x"},
        headers=_headers("admin"),
    )
    assert r.status_code == 422
