from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.adapters.fake_clients import (
    FakeActivityClient,
    FakeCertificateClient,
    FakeIntakeClient,
    FakeReportingClient,
)
from app.adapters.fake_content_store import FakeContentStore
from app.adapters.fake_grant_tracker import FakeGrantTracker
from app.adapters.fake_translator import FakeTranslator
from app.api import deps
from app.main import create_app
from app.ports.clients import ActivityAggregate, PendingSubmission


@pytest.fixture
def intake() -> FakeIntakeClient:
    return FakeIntakeClient()


@pytest.fixture
def certificates() -> FakeCertificateClient:
    return FakeCertificateClient()


@pytest.fixture
def activity() -> FakeActivityClient:
    return FakeActivityClient()


@pytest.fixture
def reporting() -> FakeReportingClient:
    return FakeReportingClient()


@pytest.fixture
def grant_tracker() -> FakeGrantTracker:
    return FakeGrantTracker()


@pytest.fixture
def content_store() -> FakeContentStore:
    return FakeContentStore()


@pytest.fixture
def translator() -> FakeTranslator:
    return FakeTranslator()


@pytest.fixture
def client(intake, certificates, activity, reporting, grant_tracker, content_store, translator) -> TestClient:
    app = create_app()
    app.dependency_overrides[deps.get_intake_client] = lambda: intake
    app.dependency_overrides[deps.get_certificate_client] = lambda: certificates
    app.dependency_overrides[deps.get_activity_client] = lambda: activity
    app.dependency_overrides[deps.get_reporting_client] = lambda: reporting
    app.dependency_overrides[deps.get_grant_tracker] = lambda: grant_tracker
    app.dependency_overrides[deps.get_content_store] = lambda: content_store
    app.dependency_overrides[deps.get_translator] = lambda: translator
    # TestClient must not follow redirects by default — we test the flow explicitly.
    return TestClient(app, follow_redirects=False)


@pytest.fixture
def authed_client(client) -> TestClient:
    client.cookies.set("kyrk_session", "u-admin:c1:admin")
    return client


@pytest.fixture
def auth_cookies() -> dict[str, str]:
    return {"kyrk_session": "u-admin:c1:admin"}


@pytest.fixture
def seeded_submission(intake) -> PendingSubmission:
    item = PendingSubmission(
        submission_id="sub-123",
        church_id="c1",
        first_name="Anna",
        last_name="Andersson",
        received_at="2025-06-01T10:00:00+00:00",
        status="pending",
    )
    intake.seed(item)
    return item


@pytest.fixture
def seeded_activities(activity) -> list[ActivityAggregate]:
    items = [
        ActivityAggregate(
            activity_id="act-1",
            church_id="c1",
            activity_type="youth_tech",
            date="2025-06-05",
            location="Storgatan 1",
            funding_tag="arvsfonden",
            participants_total=20,
            age_band_counts={"0-6": 0, "7-12": 5, "13-17": 10, "18-25": 5, "26+": 0},
        ),
        ActivityAggregate(
            activity_id="act-2",
            church_id="c1",
            activity_type="coding",
            date="2025-06-10",
            location="Storgatan 1",
            funding_tag="kommunala",
            participants_total=10,
            age_band_counts={"0-6": 0, "7-12": 10, "13-17": 0, "18-25": 0, "26+": 0},
        ),
    ]
    for a in items:
        activity.seed(a)
    return items
