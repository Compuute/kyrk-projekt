from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.adapters.fake_auth import FakeAuthAdapter
from app.adapters.in_memory_activity_repository import InMemoryActivityRepository
from app.adapters.in_memory_report_repository import InMemoryReportRepository
from app.api import deps
from app.main import create_app
from app.services.activity_service import ActivityService
from app.services.reporting_service import ReportingService


@pytest.fixture
def repo() -> InMemoryReportRepository:
    return InMemoryReportRepository()


@pytest.fixture
def activity_repo() -> InMemoryActivityRepository:
    return InMemoryActivityRepository()


@pytest.fixture
def auth() -> FakeAuthAdapter:
    return FakeAuthAdapter()


@pytest.fixture
def service(repo) -> ReportingService:
    return ReportingService(repo=repo)


@pytest.fixture
def activity_service(activity_repo) -> ActivityService:
    return ActivityService(repo=activity_repo)


@pytest.fixture
def client(repo, activity_repo, auth) -> TestClient:
    app = create_app()
    app.dependency_overrides[deps.get_repo] = lambda: repo
    app.dependency_overrides[deps.get_activity_repo] = lambda: activity_repo
    app.dependency_overrides[deps.get_auth] = lambda: auth
    return TestClient(app)
