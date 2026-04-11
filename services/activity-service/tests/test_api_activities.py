def _body(**overrides):
    body = {
        "activity_type": "youth_tech",
        "date": "2025-06-01",
        "location": "Storgatan 1",
        "funding_tag": "arvsfonden",
        "participants_total": 20,
        "age_band_counts": {"0-6": 0, "7-12": 5, "13-17": 10, "18-25": 5, "26+": 0},
    }
    body.update(overrides)
    return body


def _headers(role: str, church: str = "c1") -> dict[str, str]:
    return {"Authorization": f"Bearer u1:{church}:{role}"}


def test_healthz(client):
    assert client.get("/healthz").status_code == 200


def test_create_requires_auth(client):
    assert client.post("/activities", json=_body()).status_code == 401


def test_viewer_cannot_create(client):
    r = client.post("/activities", json=_body(), headers=_headers("viewer"))
    assert r.status_code == 403


def test_admin_create_and_get(client):
    r = client.post("/activities", json=_body(), headers=_headers("admin"))
    assert r.status_code == 201, r.text
    aid = r.json()["activity_id"]
    r = client.get(f"/activities/{aid}", headers=_headers("viewer"))
    assert r.status_code == 200


def test_invalid_age_band_sum_returns_422(client):
    r = client.post(
        "/activities",
        json=_body(age_band_counts={"0-6": 0, "7-12": 1, "13-17": 1, "18-25": 1, "26+": 1}),
        headers=_headers("admin"),
    )
    assert r.status_code == 422


def test_export_period(client):
    client.post("/activities", json=_body(), headers=_headers("admin"))
    r = client.get(
        "/activities/export/period",
        params={"start": "2025-01-01", "end": "2025-12-31"},
        headers=_headers("viewer"),
    )
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert "first_name" not in data[0]
    assert "personal_number" not in data[0]
