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


def _headers(role: str, church: str = "c1", user: str = "u-admin") -> dict[str, str]:
    return {"Authorization": f"Bearer {user}:{church}:{role}"}


def _submit(client, **overrides) -> str:
    r = client.post("/intake", json=_body(**overrides))
    assert r.status_code == 202, r.text
    return r.json()["submission_id"]


# ---------------------------------------------------------------- list API


def test_list_pending_requires_auth(client):
    assert client.get("/submissions").status_code == 401


def test_list_pending_viewer_forbidden(client):
    r = client.get("/submissions", headers=_headers("viewer"))
    assert r.status_code == 403


def test_list_pending_returns_submitted_items(client):
    sid = _submit(client)
    r = client.get("/submissions", headers=_headers("admin"))
    assert r.status_code == 200
    ids = [item["submission_id"] for item in r.json()]
    assert sid in ids


def test_list_pending_scoped_per_church(client):
    _submit(client, church_id="c1")
    _submit(client, church_id="c2")
    r = client.get("/submissions", headers=_headers("admin", church="c1"))
    assert r.status_code == 200
    assert all(item["church_id"] == "c1" for item in r.json())


# ------------------------------------------------------------- approve API


def test_approve_requires_auth(client):
    sid = _submit(client)
    assert client.post(f"/submissions/{sid}/approve").status_code == 401


def test_approve_viewer_forbidden(client):
    sid = _submit(client)
    r = client.post(f"/submissions/{sid}/approve", headers=_headers("viewer"))
    assert r.status_code == 403


def test_approve_happy_path(client, membership_client):
    sid = _submit(client)
    r = client.post(f"/submissions/{sid}/approve", headers=_headers("admin"))
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["status"] == "approved"
    assert data["created_member_id"]
    # The bearer token was forwarded to the downstream client.
    assert len(membership_client.calls) == 1
    assert membership_client.calls[0][0] == "u-admin:c1:admin"


def test_approve_unknown_submission_404(client):
    r = client.post("/submissions/does-not-exist/approve", headers=_headers("admin"))
    assert r.status_code == 404


def test_approve_twice_409(client):
    sid = _submit(client)
    client.post(f"/submissions/{sid}/approve", headers=_headers("admin"))
    r = client.post(f"/submissions/{sid}/approve", headers=_headers("admin"))
    assert r.status_code == 409


# -------------------------------------------------------------- reject API


def test_reject_happy_path(client):
    sid = _submit(client)
    r = client.post(f"/submissions/{sid}/reject", headers=_headers("pastor"))
    assert r.status_code == 200
    assert r.json()["status"] == "rejected"


def test_reject_viewer_forbidden(client):
    sid = _submit(client)
    r = client.post(f"/submissions/{sid}/reject", headers=_headers("viewer"))
    assert r.status_code == 403
