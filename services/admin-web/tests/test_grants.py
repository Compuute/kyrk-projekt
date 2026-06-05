"""Tests for the grant tracking and application module."""
from __future__ import annotations

from datetime import date, datetime, timedelta

import pytest

from app.adapters.fake_grant_tracker import FakeGrantTracker
from app.ports.grant_tracker import GrantApplication


# --------------------------------------------------------- FakeGrantTracker unit


class TestFakeGrantTracker:
    def test_list_empty(self):
        tracker = FakeGrantTracker()
        assert tracker.list_applications("c1") == []

    def test_save_and_get(self):
        tracker = FakeGrantTracker()
        app = GrantApplication(grant_id="sst-org-2025", church_id="c1", status="in_progress")
        tracker.save_application(app)
        result = tracker.get_application("c1", "sst-org-2025")
        assert result is not None
        assert result.status == "in_progress"
        assert result.grant_id == "sst-org-2025"

    def test_list_filters_by_church(self):
        tracker = FakeGrantTracker()
        tracker.save_application(GrantApplication(grant_id="g1", church_id="c1"))
        tracker.save_application(GrantApplication(grant_id="g2", church_id="c2"))
        tracker.save_application(GrantApplication(grant_id="g3", church_id="c1"))
        assert len(tracker.list_applications("c1")) == 2
        assert len(tracker.list_applications("c2")) == 1

    def test_get_returns_none_for_missing(self):
        tracker = FakeGrantTracker()
        assert tracker.get_application("c1", "nonexistent") is None

    def test_save_overwrites(self):
        tracker = FakeGrantTracker()
        app = GrantApplication(grant_id="g1", church_id="c1", status="not_started")
        tracker.save_application(app)
        app.status = "submitted"
        tracker.save_application(app)
        result = tracker.get_application("c1", "g1")
        assert result.status == "submitted"

    def test_seed(self):
        tracker = FakeGrantTracker()
        app = GrantApplication(grant_id="g1", church_id="c1", status="approved", amount_granted=100000)
        tracker.seed(app)
        assert tracker.get_application("c1", "g1").amount_granted == 100000


# --------------------------------------------------------- Grant list route


def test_grants_list_requires_auth(client):
    r = client.get("/grants")
    assert r.status_code == 302
    assert r.headers["location"] == "/login"


def test_grants_list_renders(authed_client):
    r = authed_client.get("/grants")
    assert r.status_code == 200
    assert "Bidrag" in r.text
    assert "SST Organisationsstöd" in r.text


def test_grants_list_shows_deadline_coloring(authed_client):
    r = authed_client.get("/grants")
    assert r.status_code == 200
    # All grants have deadlines > 60 days out, so should be green
    assert "deadline-green" in r.text


def test_grants_list_shows_status(authed_client, grant_tracker):
    grant_tracker.save_application(
        GrantApplication(grant_id="sst-org-2025", church_id="c1", status="submitted")
    )
    r = authed_client.get("/grants")
    assert r.status_code == 200
    assert "Inskickad" in r.text


def test_grants_list_shows_starta_button(authed_client):
    r = authed_client.get("/grants")
    assert r.status_code == 200
    assert "Starta ansökan" in r.text


# --------------------------------------------------------- Grant detail route


def test_grant_detail_renders(authed_client):
    r = authed_client.get("/grants/sst-org-2025")
    assert r.status_code == 200
    assert "SST Organisationsstöd" in r.text
    assert "Myndigheten" in r.text


def test_grant_detail_shows_eligibility(authed_client):
    r = authed_client.get("/grants/sst-org-2025")
    assert r.status_code == 200
    assert "Krav och behörighet" in r.text
    assert "Registrerat trossamfund" in r.text


def test_grant_detail_requires_auth(client):
    r = client.get("/grants/sst-org-2025")
    assert r.status_code == 302


def test_grant_detail_not_found_redirects(authed_client):
    r = authed_client.get("/grants/nonexistent")
    assert r.status_code == 303
    assert "/grants" in r.headers["location"]


# --------------------------------------------------------- Application form


def test_grant_apply_form_renders(authed_client):
    r = authed_client.get("/grants/sst-org-2025/apply")
    assert r.status_code == 200
    assert "Ansökningsformulär" in r.text
    assert "Projektnamn" in r.text
    assert "Projektbeskrivning" in r.text
    assert "Målgrupp" in r.text


def test_grant_apply_form_shows_existing_data(authed_client, grant_tracker):
    grant_tracker.save_application(
        GrantApplication(
            grant_id="sst-org-2025",
            church_id="c1",
            status="in_progress",
            project_name="Ungdomsverksamhet 2026",
            project_description="Ett fantastiskt projekt",
        )
    )
    r = authed_client.get("/grants/sst-org-2025/apply")
    assert r.status_code == 200
    assert "Ungdomsverksamhet 2026" in r.text
    assert "Ett fantastiskt projekt" in r.text


def test_grant_apply_save(authed_client, grant_tracker):
    r = authed_client.post(
        "/grants/sst-org-2025/apply",
        data={
            "project_name": "Testprojekt",
            "project_description": "Beskrivning här",
            "target_group": "Ungdomar 13-25",
            "budget_amount": "150000",
            "own_contribution": "50000",
            "notes": "Kontakta handläggare",
        },
    )
    assert r.status_code == 303
    assert "/grants/sst-org-2025" in r.headers["location"]

    app = grant_tracker.get_application("c1", "sst-org-2025")
    assert app is not None
    assert app.project_name == "Testprojekt"
    assert app.status == "in_progress"
    assert app.started_at is not None


def test_grant_apply_requires_auth(client):
    r = client.post("/grants/sst-org-2025/apply", data={"project_name": "test"})
    assert r.status_code == 302


# --------------------------------------------------------- Status CRUD


def test_grant_status_update(authed_client, grant_tracker):
    r = authed_client.post(
        "/grants/sst-org-2025/status",
        data={
            "new_status": "submitted",
            "amount_requested": "200000",
            "amount_granted": "0",
            "notes": "Skickad via e-post",
        },
    )
    assert r.status_code == 303

    app = grant_tracker.get_application("c1", "sst-org-2025")
    assert app is not None
    assert app.status == "submitted"
    assert app.submitted_at is not None
    assert app.amount_requested == 200000


def test_grant_status_invalid(authed_client):
    r = authed_client.post(
        "/grants/sst-org-2025/status",
        data={"new_status": "bogus", "amount_requested": "0", "amount_granted": "0", "notes": ""},
    )
    assert r.status_code == 303
    assert "level=error" in r.headers["location"]


def test_grant_status_get(authed_client):
    r = authed_client.get("/grants/sst-org-2025/status")
    assert r.status_code == 200
    assert "SST Organisationsstöd" in r.text


# --------------------------------------------------------- Generate draft


def test_grant_generate_draft(authed_client, grant_tracker, seeded_activities):
    grant_tracker.save_application(
        GrantApplication(
            grant_id="sst-org-2025",
            church_id="c1",
            status="in_progress",
            project_name="Ungdomsverksamhet 2026",
            project_description="Utöka ungdomsverksamheten",
            target_group="Ungdomar 13-25",
            budget_amount=200000,
            own_contribution=50000,
        )
    )
    r = authed_client.post("/grants/sst-org-2025/generate")
    assert r.status_code == 200
    assert "Genererat ansökningsunderlag" in r.text
    assert "Sammanfattning" in r.text
    assert "Projektbeskrivning" in r.text
    assert "KPI-underlag" in r.text
    # KPI data from seeded activities should appear
    assert "30" in r.text  # total participants from seeded_activities
    assert "aktiviteter" in r.text


def test_grant_generate_draft_requires_auth(client):
    r = client.post("/grants/sst-org-2025/generate")
    assert r.status_code == 302


def test_grant_generate_handles_activity_error(authed_client, activity, grant_tracker):
    from app.ports.client_errors import ClientError

    grant_tracker.save_application(
        GrantApplication(
            grant_id="sst-org-2025",
            church_id="c1",
            status="in_progress",
            project_name="Test",
        )
    )
    activity.export_error = ClientError("service down", status_code=503)
    r = authed_client.post("/grants/sst-org-2025/generate")
    assert r.status_code == 200
    assert "Kunde inte hämta KPI-data" in r.text


def test_grant_generate_english_draft(authed_client, grant_tracker, seeded_activities):
    grant_tracker.save_application(
        GrantApplication(
            grant_id="erasmus-ka2-2025",
            church_id="c1",
            status="in_progress",
            project_name="Youth Digital Skills",
            project_description="An Erasmus+ partnership",
            target_group="Youth 13-25 across 3 countries",
            budget_amount=250000,
            own_contribution=50000,
        )
    )
    r = authed_client.post("/grants/erasmus-ka2-2025/generate")
    assert r.status_code == 200
    assert "Summary" in r.text
    assert "Project Description" in r.text
    assert "KPI Evidence" in r.text


# --------------------------------------------------------- Dashboard tile


def test_dashboard_shows_grants_tile(authed_client):
    r = authed_client.get("/")
    assert r.status_code == 200
    assert "bidrag med deadline snart" in r.text


# --------------------------------------------------------- Navbar


def test_navbar_has_bidrag_link(authed_client):
    r = authed_client.get("/")
    assert r.status_code == 200
    assert 'href="/grants"' in r.text
    assert "Bidrag" in r.text


# --------------------------------------------------------- Factory


def test_factory_produces_fake_grant_tracker():
    from app.adapters.factory import make_grant_tracker
    from app.adapters.fake_grant_tracker import FakeGrantTracker

    tracker = make_grant_tracker()
    assert isinstance(tracker, FakeGrantTracker)
