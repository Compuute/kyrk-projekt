from app.ports.client_errors import ClientError


def test_dashboard_shows_pending_count(client, intake, seeded_submission, auth_cookies):
    r = client.get("/", cookies=auth_cookies)
    assert r.status_code == 200
    assert "Hej u-admin" in r.text
    assert "väntande intake" in r.text
    assert "1" in r.text  # pending count


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
