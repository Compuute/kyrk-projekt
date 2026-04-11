def test_healthz(client):
    r = client.get("/healthz")
    assert r.status_code == 200


def test_root_redirects_to_login_when_anonymous(client):
    r = client.get("/")
    assert r.status_code == 302
    assert r.headers["location"] == "/login"


def test_submissions_redirects_to_login_when_anonymous(client):
    r = client.get("/submissions")
    assert r.status_code == 302
    assert r.headers["location"] == "/login"


def test_login_page_renders(client):
    r = client.get("/login")
    assert r.status_code == 200
    assert "Logga in" in r.text
    assert "PropelAuth" in r.text  # MVP note


def test_login_sets_cookie_and_redirects(client):
    r = client.post(
        "/login",
        data={"user_id": "u-admin", "church_id": "c1", "role": "admin"},
    )
    assert r.status_code == 303
    assert r.headers["location"] == "/"
    set_cookie = r.headers.get("set-cookie", "")
    assert "kyrk_session=u-admin:c1:admin" in set_cookie
    assert "HttpOnly" in set_cookie


def test_login_rejects_unknown_role(client):
    r = client.post(
        "/login",
        data={"user_id": "u", "church_id": "c", "role": "god-mode"},
    )
    assert r.status_code == 303
    assert "/login" in r.headers["location"]
    assert "unknown" in r.headers["location"]


def test_logout_clears_cookie(client, auth_cookies):
    r = client.post("/logout", cookies=auth_cookies)
    assert r.status_code == 303
    assert r.headers["location"] == "/login"
    set_cookie = r.headers.get("set-cookie", "")
    assert "kyrk_session=" in set_cookie
