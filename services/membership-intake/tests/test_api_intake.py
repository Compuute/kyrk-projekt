from datetime import datetime, timezone

_PNR = ["19800101-1231","19810101-1230","19820101-1239","19830101-1238","19840101-1237","19850101-1236","19860101-1235","19870101-1234","19880101-1233","19890101-1232"]
_pi = 0
def _next_pnr():
    global _pi; pnr = _PNR[_pi % len(_PNR)]; _pi += 1; return pnr

def _body(**overrides):
    body = {
        "church_id": "c1",
        "first_name": "Anna",
        "last_name": "Andersson",
        "phone": "+46701234567",
        "email": "anna@example.se",
        "personal_number": _next_pnr(),
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
