"""Kassörens gåvovy: lista väntande registreringar, verifiera (skickar
kvittot via membership-intake) eller avfärda."""
from __future__ import annotations

import pytest

from app.ports.client_errors import ClientError
from app.ports.clients import PendingDonation


@pytest.fixture
def seeded_donation(intake) -> PendingDonation:
    donation = PendingDonation(
        donation_id="don-12345678",
        church_id="c1",
        amount_sek=500,
        method="swish",
        email_masked="g***@example.se",
        received_at="2026-06-11T20:00:00+00:00",
        status="pending_verification",
    )
    intake.seed_donation(donation)
    return donation


def test_donations_requires_auth(client):
    r = client.get("/donations")
    assert r.status_code == 302
    assert r.headers["location"] == "/login"


def test_donations_list_renders_pending(client, seeded_donation, auth_cookies):
    r = client.get("/donations", cookies=auth_cookies)
    assert r.status_code == 200
    assert "500" in r.text
    assert "g***@example.se" in r.text
    assert seeded_donation.donation_id[:8] in r.text


def test_donations_list_shows_empty_state(client, auth_cookies):
    r = client.get("/donations", cookies=auth_cookies)
    assert r.status_code == 200
    assert "Inga väntande gåvor" in r.text


def test_donations_list_shows_error_on_downstream_failure(client, intake, auth_cookies):
    intake.donations_list_error = ClientError("service unavailable", status_code=503)
    r = client.get("/donations", cookies=auth_cookies)
    assert r.status_code == 200
    assert "Kunde inte läsa" in r.text


def test_verify_requires_auth(client, seeded_donation):
    r = client.post(f"/donations/{seeded_donation.donation_id}/verify")
    assert r.status_code == 302
    assert r.headers["location"] == "/login"


def test_verify_happy_path_redirects_with_receipt_number(
    client, intake, seeded_donation, auth_cookies
):
    r = client.post(
        f"/donations/{seeded_donation.donation_id}/verify", cookies=auth_cookies
    )
    assert r.status_code == 303
    assert "/donations" in r.headers["location"]
    assert "GK-" in r.headers["location"]
    assert intake.donations[seeded_donation.donation_id].status == "verified"


def test_verify_error_redirects_with_error_flash(
    client, intake, seeded_donation, auth_cookies
):
    intake.verify_donation_error = ClientError("downstream 502", status_code=502)
    r = client.post(
        f"/donations/{seeded_donation.donation_id}/verify", cookies=auth_cookies
    )
    assert r.status_code == 303
    assert "level=error" in r.headers["location"]
    # Stays pending so the kassör can retry.
    assert intake.donations[seeded_donation.donation_id].status == "pending_verification"


def test_dismiss_happy_path(client, intake, seeded_donation, auth_cookies):
    r = client.post(
        f"/donations/{seeded_donation.donation_id}/dismiss", cookies=auth_cookies
    )
    assert r.status_code == 303
    assert "/donations" in r.headers["location"]
    assert intake.donations[seeded_donation.donation_id].status == "dismissed"


def test_nav_links_to_donations(client, auth_cookies):
    r = client.get("/donations", cookies=auth_cookies)
    assert 'href="/donations"' in r.text
