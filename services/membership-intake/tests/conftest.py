from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.adapters.fake_auth import FakeAuthAdapter
from app.adapters.fake_membership_client import FakeMembershipClient
from app.adapters.in_memory_notifier import InMemoryNotifier
from app.adapters.in_memory_rate_limiter import InMemoryRateLimiter
from app.adapters.in_memory_submission_repository import InMemorySubmissionRepository
from app.api import deps
from app.main import create_app
from app.services.intake_service import IntakeService


@pytest.fixture
def repo() -> InMemorySubmissionRepository:
    return InMemorySubmissionRepository()


@pytest.fixture
def notifier() -> InMemoryNotifier:
    return InMemoryNotifier()


@pytest.fixture
def limiter() -> InMemoryRateLimiter:
    return InMemoryRateLimiter(max_hits=3, window_seconds=60)


@pytest.fixture
def auth() -> FakeAuthAdapter:
    return FakeAuthAdapter()


@pytest.fixture
def membership_client() -> FakeMembershipClient:
    return FakeMembershipClient()


@pytest.fixture
def service(repo, notifier, limiter, membership_client) -> IntakeService:
    return IntakeService(
        repo=repo,
        notifier=notifier,
        limiter=limiter,
        membership_client=membership_client,
    )


@pytest.fixture
def client(repo, notifier, limiter, auth, membership_client) -> TestClient:
    app = create_app()
    app.dependency_overrides[deps.get_repo] = lambda: repo
    app.dependency_overrides[deps.get_notifier] = lambda: notifier
    app.dependency_overrides[deps.get_limiter] = lambda: limiter
    app.dependency_overrides[deps.get_auth] = lambda: auth
    app.dependency_overrides[deps.get_membership_client] = lambda: membership_client
    return TestClient(app)
