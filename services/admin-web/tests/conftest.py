from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.adapters.fake_clients import FakeCertificateClient, FakeIntakeClient
from app.api import deps
from app.main import create_app
from app.ports.clients import PendingSubmission


@pytest.fixture
def intake() -> FakeIntakeClient:
    return FakeIntakeClient()


@pytest.fixture
def certificates() -> FakeCertificateClient:
    return FakeCertificateClient()


@pytest.fixture
def client(intake, certificates) -> TestClient:
    app = create_app()
    app.dependency_overrides[deps.get_intake_client] = lambda: intake
    app.dependency_overrides[deps.get_certificate_client] = lambda: certificates
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
