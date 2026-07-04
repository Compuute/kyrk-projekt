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


def test_verify_unauthenticated_shows_public_page(client, certificates):
    from app.ports.clients import IssueCertificateRequest
    cert = certificates.issue("mock-token", IssueCertificateRequest(
        certificate_type="baptism",
        issued_date="2025-06-01",
        member_id="m-1",
        church_name="Sankt Johannes",
    ))
    
    r = client.get(f"/certificates/verify/{cert.certificate_id}")
    assert r.status_code == 200
    assert "Verifierat kyrkligt certifikat" in r.text
    assert "Sankt Johannes" in r.text
    assert "m-1" not in r.text


def test_verify_authenticated_renders_full_certificate(client, certificates, auth_cookies):
    from app.ports.clients import IssueCertificateRequest
    cert = certificates.issue("mock-token", IssueCertificateRequest(
        certificate_type="baptism",
        issued_date="2025-06-01",
        member_id="m-1",
        church_name="Sankt Johannes",
    ))
    
    r = client.get(f"/certificates/verify/{cert.certificate_id}", cookies=auth_cookies)
    assert r.status_code == 200
    assert "Certificate" in r.text
    assert "Daniel Abbay" in r.text
