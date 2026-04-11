from datetime import datetime, timezone


def _body(**overrides):
    body = {
        "church_id": "c1",
        "first_name": "Anna",
        "last_name": "Andersson",
        "phone": "+4670000000",
        "email": "anna@example.se",
        "personal_number": "19800101-1234",
        "gdpr_consent": True,
        "consent_timestamp": datetime.now(timezone.utc).isoformat(),
    }
    body.update(overrides)
    return body


def test_healthz(client):
    r = client.get("/healthz")
    assert r.status_code == 200


def test_happy_path_returns_202_pending(client):
    r = client.post("/intake", json=_body())
    assert r.status_code == 202, r.text
    data = r.json()
    assert data["status"] == "pending"
    assert data["submission_id"]


def test_consent_required_returns_400(client):
    r = client.post("/intake", json=_body(gdpr_consent=False))
    assert r.status_code == 400


def test_invalid_email_returns_422(client):
    r = client.post("/intake", json=_body(email="not-an-email"))
    assert r.status_code == 422


def test_rate_limit_returns_429(client):
    for _ in range(3):
        assert client.post("/intake", json=_body()).status_code == 202
    r = client.post("/intake", json=_body())
    assert r.status_code == 429
