from app.ports.client_errors import ClientError


def test_cert_form_redirects_when_anonymous(client):
    r = client.get("/certificates/new")
    assert r.status_code == 302


def test_cert_form_renders(client, auth_cookies):
    r = client.get("/certificates/new", cookies=auth_cookies)
    assert r.status_code == 200
    assert "Utfärda certifikat" in r.text
    assert 'name="member_id"' in r.text
    assert 'name="church_name"' in r.text


def test_issue_happy_path_flashes_verification_url(client, certificates, auth_cookies):
    r = client.post(
        "/certificates/new",
        data={
            "certificate_type": "baptism",
            "issued_date": "2025-06-01",
            "member_id": "m-1",
            "church_name": "Sankt Johannes kyrka",
        },
        cookies=auth_cookies,
    )
    assert r.status_code == 303
    assert "/certificates/new" in r.headers["location"]
    assert "level=success" in r.headers["location"]
    assert len(certificates.issued) == 1
    assert certificates.issued[0].certificate_type == "baptism"


def test_issue_error_shows_flash(client, certificates, auth_cookies):
    certificates.issue_error = ClientError("forbidden", status_code=403)
    r = client.post(
        "/certificates/new",
        data={
            "certificate_type": "baptism",
            "issued_date": "2025-06-01",
            "member_id": "m-1",
            "church_name": "Sankt Johannes",
        },
        cookies=auth_cookies,
    )
    assert r.status_code == 303
    assert "level=error" in r.headers["location"]
