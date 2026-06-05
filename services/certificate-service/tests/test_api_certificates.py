def _body():
    return {
        "certificate_type": "baptism",
        "issued_date": "2025-06-01",
        "member_id": "m-1",
        "church_name": "Sankt Johannes kyrka",
    }


def _headers(role: str, church: str = "c1") -> dict[str, str]:
    return {"Authorization": f"Bearer u1:{church}:{role}"}


def test_healthz(client):
    assert client.get("/healthz").status_code == 200


def test_issue_requires_auth(client):
    assert client.post("/certificates", json=_body()).status_code == 401


def test_secretary_forbidden_to_issue(client):
    r = client.post("/certificates", json=_body(), headers=_headers("secretary"))
    assert r.status_code == 403


def test_pastor_can_issue_and_public_verify(client):
    r = client.post("/certificates", json=_body(), headers=_headers("pastor"))
    assert r.status_code == 201, r.text
    cert_id = r.json()["certificate_id"]

    # Public verification — no auth header.
    r = client.get(f"/certificates/verify/{cert_id}")
    assert r.status_code == 200
    data = r.json()
    assert data["certificate_type"] == "baptism"
    assert data["status"] == "valid"
    assert "member_id" not in data
    assert "first_name" not in data
    assert "personal_number" not in data


def test_verify_unknown_is_404(client):
    r = client.get("/certificates/verify/does-not-exist")
    assert r.status_code == 404


def test_revoke_then_verify_returns_revoked(client):
    cert_id = client.post("/certificates", json=_body(), headers=_headers("pastor")).json()["certificate_id"]
    r = client.post(f"/certificates/{cert_id}/revoke", headers=_headers("admin"))
    assert r.status_code == 200
    assert client.get(f"/certificates/verify/{cert_id}").json()["status"] == "revoked"


def test_double_revoke_returns_409(client):
    cert_id = client.post("/certificates", json=_body(), headers=_headers("pastor")).json()["certificate_id"]
    client.post(f"/certificates/{cert_id}/revoke", headers=_headers("admin"))
    r = client.post(f"/certificates/{cert_id}/revoke", headers=_headers("admin"))
    assert r.status_code == 409


def test_download_requires_auth(client):
    r = client.get("/certificates/fake-id/download")
    assert r.status_code == 401


def test_download_forbidden_for_secretary(client):
    cert_id = client.post("/certificates", json=_body(), headers=_headers("pastor")).json()["certificate_id"]
    r = client.get(f"/certificates/{cert_id}/download", headers=_headers("secretary"))
    assert r.status_code == 403


def test_download_returns_html(client):
    cert_id = client.post("/certificates", json=_body(), headers=_headers("pastor")).json()["certificate_id"]
    r = client.get(f"/certificates/{cert_id}/download", headers=_headers("admin"))
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    assert "CERTIFICATE" in r.text or "certificate" in r.text.lower()


def test_download_unknown_is_404(client):
    r = client.get("/certificates/does-not-exist/download", headers=_headers("admin"))
    assert r.status_code == 404
