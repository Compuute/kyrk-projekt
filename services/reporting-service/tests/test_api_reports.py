def _headers(role: str, church: str = "c1") -> dict[str, str]:
    return {"Authorization": f"Bearer u1:{church}:{role}"}


def _body():
    return {
        "period": "2025-06",
        "activities": [
            {
                "activity_type": "youth_tech",
                "date": "2025-06-01",
                "location": "Storgatan 1",
                "funding_tag": "arvsfonden",
                "participants_total": 10,
                "age_band_counts": {"0-6": 0, "7-12": 5, "13-17": 5, "18-25": 0, "26+": 0},
            }
        ],
        "finance": {"operating_cost": 5000, "grants": 3000, "own_contribution": 2000},
    }


def test_healthz(client):
    assert client.get("/healthz").status_code == 200


def test_monthly_requires_auth(client):
    assert client.post("/reports/monthly", json=_body()).status_code == 401


def test_viewer_cannot_post_monthly(client):
    r = client.post("/reports/monthly", json=_body(), headers=_headers("viewer"))
    assert r.status_code == 403


def test_admin_can_post_monthly(client):
    r = client.post("/reports/monthly", json=_body(), headers=_headers("admin"))
    assert r.status_code == 201, r.text
    assert r.json()["kind"] == "monthly"
    assert r.json()["payload"]["participants_total"] == 10


def test_pii_in_payload_returns_422(client):
    body = _body()
    body["activities"][0]["first_name"] = "Anna"
    r = client.post("/reports/monthly", json=body, headers=_headers("admin"))
    assert r.status_code == 422


def test_get_report_as_viewer(client):
    rid = client.post("/reports/monthly", json=_body(), headers=_headers("admin")).json()["report_id"]
    r = client.get(f"/reports/{rid}", headers=_headers("viewer"))
    assert r.status_code == 200


def test_board_export(client):
    r = client.post("/reports/board-export", json=_body(), headers=_headers("admin"))
    assert r.status_code == 201
    assert r.json()["payload"]["openclaw_ready"] is True
