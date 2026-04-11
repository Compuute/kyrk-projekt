from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.adapters.fake_auth import FakeAuthAdapter
from app.adapters.in_memory_activity_repository import InMemoryActivityRepository
from app.api import deps
from app.main import create_app
from app.services.activity_service import ActivityService


@pytest.fixture
def repo() -> InMemoryActivityRepository:
    return InMemoryActivityRepository()


@pytest.fixture
def auth() -> FakeAuthAdapter:
    return FakeAuthAdapter()


@pytest.fixture
def service(repo) -> ActivityService:
    return ActivityService(repo=repo)


@pytest.fixture
def client(repo, auth) -> TestClient:
    app = create_app()
    app.dependency_overrides[deps.get_repo] = lambda: repo
    app.dependency_overrides[deps.get_auth] = lambda: auth
    return TestClient(app)
