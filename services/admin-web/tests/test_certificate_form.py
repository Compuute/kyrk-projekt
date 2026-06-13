from app.ports.client_errors import ClientError


def test_cert_form_redirects_when_anonymous(client):
    r = client.get("/certificates/new")
    assert r.status_code == 302


def test_cert_form_renders_church_dropdown_and_language(client, auth_cookies):
    r = client.get("/certificates/new", cookies=auth_cookies)
    assert r.status_code == 200
    assert "Utfärda certifikat" in r.text
    assert 'name="member_id"' in r.text
    # Church is now a dropdown of the real churches, not free text.
    assert 'name="church_id"' in r.text
    assert "Medhane Alem" in r.text  # a seeded church option
    assert "Stockholm" in r.text
    assert 'name="church_name"' not in r.text
    # Language selector present.
    assert 'name="language"' in r.text


def test_issue_resolves_church_names_and_language(client, certificates, auth_cookies):
    r = client.post(
        "/certificates/new",
        data={
            "certificate_type": "baptism",
            "issued_date": "2025-06-01",
            "member_id": "m-1",
            "church_id": "stockholm",
            "language": "am",
        },
        cookies=auth_cookies,
    )
    assert r.status_code == 303
    assert "level=success" in r.headers["location"]
    assert len(certificates.requests) == 1
    req = certificates.requests[0]
    # admin-web resolved the bilingual names from the church id.
    assert req.church_name == "Medhane Alem"
    assert req.church_name_am == "መድኃኔ ዓለም"
    assert req.language == "am"


def test_issue_unknown_church_shows_error(client, certificates, auth_cookies):
    r = client.post(
        "/certificates/new",
        data={
            "certificate_type": "baptism",
            "issued_date": "2025-06-01",
            "member_id": "m-1",
            "church_id": "does-not-exist",
            "language": "sv",
        },
        cookies=auth_cookies,
    )
    assert r.status_code == 303
    assert "level=error" in r.headers["location"]
    assert certificates.requests == []


def test_issue_flash_links_to_preview(client, certificates, auth_cookies):
    r = client.post(
        "/certificates/new",
        data={
            "certificate_type": "baptism",
            "issued_date": "2025-06-01",
            "member_id": "m-1",
            "church_id": "stockholm",
            "language": "sv",
        },
        cookies=auth_cookies,
    )
    assert r.status_code == 303
    issued_id = certificates.issued[0].certificate_id
    assert f"/certificates/{issued_id}/download" in r.headers["location"]


def test_download_proxies_rendered_certificate(client, certificates, auth_cookies):
    certificates.rendered = b"<html>cert</html>"
    r = client.get("/certificates/cert-xyz/download", cookies=auth_cookies)
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    assert r.content == b"<html>cert</html>"
    assert certificates.downloaded == ["cert-xyz"]


def test_download_redirects_when_anonymous(client):
    r = client.get("/certificates/cert-xyz/download")
    assert r.status_code == 302


def test_issue_error_shows_flash(client, certificates, auth_cookies):
    certificates.issue_error = ClientError("forbidden", status_code=403)
    r = client.post(
        "/certificates/new",
        data={
            "certificate_type": "baptism",
            "issued_date": "2025-06-01",
            "member_id": "m-1",
            "church_id": "stockholm",
            "language": "sv",
        },
        cookies=auth_cookies,
    )
    assert r.status_code == 303
    assert "level=error" in r.headers["location"]
