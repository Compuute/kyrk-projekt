from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

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
def service(repo, notifier, limiter) -> IntakeService:
    return IntakeService(repo=repo, notifier=notifier, limiter=limiter)


@pytest.fixture
def client(repo, notifier, limiter) -> TestClient:
    app = create_app()
    app.dependency_overrides[deps.get_repo] = lambda: repo
    app.dependency_overrides[deps.get_notifier] = lambda: notifier
    app.dependency_overrides[deps.get_limiter] = lambda: limiter
    return TestClient(app)
