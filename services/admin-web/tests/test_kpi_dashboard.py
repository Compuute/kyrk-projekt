from app.ports.client_errors import ClientError


# ---------------------------------------------------------------- form route


def test_kpi_form_redirects_when_anonymous(client):
    r = client.get("/kpi")
    assert r.status_code == 302


def test_kpi_form_renders_current_month_by_default(client, auth_cookies):
    r = client.get("/kpi", cookies=auth_cookies)
    assert r.status_code == 200
    assert "KPI-dashboard" in r.text
    assert 'name="period"' in r.text
    assert 'name="operating_cost"' in r.text


def test_kpi_form_accepts_period_override(client, auth_cookies):
    r = client.get("/kpi?period=2025-06", cookies=auth_cookies)
    assert r.status_code == 200
    assert 'value="2025-06"' in r.text


# ------------------------------------------------------------- generate route


def test_kpi_generate_calls_downstreams_and_renders(
    client, activity, reporting, seeded_activities, auth_cookies
):
    r = client.post(
        "/kpi",
        data={
            "period": "2025-06",
            "operating_cost": "30000",
            "grants": "20000",
            "own_contribution": "10000",
        },
        cookies=auth_cookies,
    )
    assert r.status_code == 200

    # activity-service was asked for the full month
    assert len(activity.activities) == 2  # seed was 2 items

    # reporting-service was called once with the right payload shape
    assert reporting.last_call is not None
    assert reporting.last_call["period"] == "2025-06"
    assert reporting.last_call["finance"]["operating_cost"] == 30000.0
    assert len(reporting.last_call["activities"]) == 2

    # Rendered numbers show up in the HTML
    assert "30" in r.text  # participants_total
    assert "1000" in r.text  # cost per participant 30000 / 30
    # grant leverage 20000 / 10000 = 2.00
    assert "2.00x" in r.text
    # Activity type breakdown
    assert "youth_tech" in r.text
    assert "coding" in r.text


def test_kpi_generate_with_empty_activities_shows_dashes(client, auth_cookies):
    r = client.post(
        "/kpi",
        data={
            "period": "2025-07",
            "operating_cost": "0",
            "grants": "0",
            "own_contribution": "0",
        },
        cookies=auth_cookies,
    )
    assert r.status_code == 200
    # cost_per_participant and grant_leverage_ratio should both render as —
    assert "—" in r.text


def test_kpi_generate_handles_activity_service_error(
    client, activity, auth_cookies
):
    activity.export_error = ClientError("service unavailable", status_code=503)
    r = client.post(
        "/kpi",
        data={
            "period": "2025-06",
            "operating_cost": "0",
            "grants": "0",
            "own_contribution": "0",
        },
        cookies=auth_cookies,
    )
    assert r.status_code == 200
    assert "KPI-genereringen misslyckades" in r.text


def test_kpi_generate_handles_reporting_service_error(
    client, reporting, seeded_activities, auth_cookies
):
    reporting.generate_error = ClientError("rejected", status_code=422)
    r = client.post(
        "/kpi",
        data={
            "period": "2025-06",
            "operating_cost": "0",
            "grants": "0",
            "own_contribution": "0",
        },
        cookies=auth_cookies,
    )
    assert r.status_code == 200
    assert "KPI-genereringen misslyckades" in r.text


def test_kpi_generate_requires_auth(client):
    r = client.post(
        "/kpi",
        data={
            "period": "2025-06",
            "operating_cost": "0",
            "grants": "0",
            "own_contribution": "0",
        },
    )
    assert r.status_code == 302
    assert r.headers["location"] == "/login"
