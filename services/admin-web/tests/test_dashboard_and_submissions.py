from app.ports.client_errors import ClientError


def test_dashboard_shows_pending_count(client, intake, seeded_submission, auth_cookies):
    r = client.get("/", cookies=auth_cookies)
    assert r.status_code == 200
    assert "Hej u-admin" in r.text
    assert "väntande intake" in r.text
    assert "1" in r.text  # pending count


def test_dashboard_unauthenticated_redirects_to_login(client):
    # Landing on the root without a session must send the user into the
    # login flow — not return a bare 401 JSON. A session-requiring
    # dependency on the route would short-circuit the redirect.
    r = client.get("/")
    assert r.status_code == 302
    assert r.headers["location"] == "/login"


def test_dashboard_redirects_with_real_dependency_wiring():
    # The shared `client` fixture overrides get_funeral_tracker with a
    # session-free lambda, which hides the production bug where the route's
    # Depends(get_funeral_tracker) -> Depends(current_session) raises 401
    # before _require_session can redirect. Exercise the REAL deps so a
    # regression in production wiring is caught here.
    from fastapi.testclient import TestClient
    from app.api import deps
    from app.main import create_app
    from app.adapters.fake_clients import FakeIntakeClient

    app = create_app()
    app.dependency_overrides[deps.get_intake_client] = lambda: FakeIntakeClient()
    real_wiring = TestClient(app, follow_redirects=False)
    r = real_wiring.get("/")
    assert r.status_code == 302, f"expected redirect, got {r.status_code}: {r.text}"
    assert r.headers["location"] == "/login"


def test_dashboard_tolerates_downstream_error(client, intake, auth_cookies):
    intake.list_error = ClientError("boom", status_code=500)
    r = client.get("/", cookies=auth_cookies)
    assert r.status_code == 200
    assert "0" in r.text  # falls back to 0


def test_submissions_list_renders_pending(client, seeded_submission, auth_cookies):
    r = client.get("/submissions", cookies=auth_cookies)
    assert r.status_code == 200
    assert "Anna" in r.text
    assert "Andersson" in r.text
    assert seeded_submission.submission_id[:8] in r.text


def test_submissions_list_shows_empty_state(client, auth_cookies):
    r = client.get("/submissions", cookies=auth_cookies)
    assert r.status_code == 200
    assert "Inga väntande ansökningar" in r.text


def test_submissions_list_shows_error_on_downstream_failure(client, intake, auth_cookies):
    intake.list_error = ClientError("service unavailable", status_code=503)
    r = client.get("/submissions", cookies=auth_cookies)
    assert r.status_code == 200
    assert "Kunde inte läsa" in r.text


def test_approve_happy_path_redirects_with_flash(client, intake, seeded_submission, auth_cookies):
    r = client.post(
        f"/submissions/{seeded_submission.submission_id}/approve",
        cookies=auth_cookies,
    )
    assert r.status_code == 303
    assert "/submissions" in r.headers["location"]
    assert "Godk" in r.headers["location"] or "Godk" in r.headers.get("location", "")
    # Underlying fake client actually transitioned state
    assert intake.submissions[seeded_submission.submission_id].status == "approved"


def test_approve_error_redirects_with_error_flash(client, intake, seeded_submission, auth_cookies):
    intake.approve_error = ClientError("downstream 502", status_code=502)
    r = client.post(
        f"/submissions/{seeded_submission.submission_id}/approve",
        cookies=auth_cookies,
    )
    assert r.status_code == 303
    assert "level=error" in r.headers["location"]


def test_reject_happy_path(client, intake, seeded_submission, auth_cookies):
    r = client.post(
        f"/submissions/{seeded_submission.submission_id}/reject",
        cookies=auth_cookies,
    )
    assert r.status_code == 303
    assert "level=success" in r.headers["location"]
    assert intake.submissions[seeded_submission.submission_id].status == "rejected"


def test_approve_requires_auth(client, seeded_submission):
    r = client.post(f"/submissions/{seeded_submission.submission_id}/approve")
    assert r.status_code == 302
    assert r.headers["location"] == "/login"
