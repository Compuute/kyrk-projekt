"""Shared fixtures. Every test wires fresh in-memory adapters."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.adapters.fake_auth import FakeAuthAdapter
from app.adapters.in_memory_audit import InMemoryAuditAdapter
from app.adapters.in_memory_encryption import InMemoryEncryptionAdapter
from app.adapters.in_memory_member_repository import InMemoryMemberRepository
from app.adapters.in_memory_funeral_tracker import InMemoryFuneralTracker
from app.adapters.in_memory_grant_tracker import InMemoryGrantTracker
from app.adapters.in_memory_sunday_school import InMemorySundaySchoolTracker
from app.api import deps
from app.main import create_app
from app.services.membership_service import MembershipService


@pytest.fixture
def repo() -> InMemoryMemberRepository:
    return InMemoryMemberRepository()


@pytest.fixture
def funeral_tracker() -> InMemoryFuneralTracker:
    return InMemoryFuneralTracker()


@pytest.fixture
def grant_tracker() -> InMemoryGrantTracker:
    return InMemoryGrantTracker()


@pytest.fixture
def sunday_school() -> InMemorySundaySchoolTracker:
    return InMemorySundaySchoolTracker()


@pytest.fixture
def payment():
    from app.adapters.fake_payment import FakePaymentAdapter

    return FakePaymentAdapter()


@pytest.fixture
def encryption() -> InMemoryEncryptionAdapter:
    return InMemoryEncryptionAdapter()


@pytest.fixture
def audit() -> InMemoryAuditAdapter:
    return InMemoryAuditAdapter()


@pytest.fixture
def auth() -> FakeAuthAdapter:
    return FakeAuthAdapter()


@pytest.fixture
def service(repo, encryption, audit) -> MembershipService:
    return MembershipService(repo=repo, encryption=encryption, audit=audit)


@pytest.fixture
def client(repo, encryption, audit, auth, funeral_tracker, grant_tracker, sunday_school, payment) -> TestClient:
    app = create_app()
    app.dependency_overrides[deps.get_repo] = lambda: repo
    app.dependency_overrides[deps.get_encryption] = lambda: encryption
    app.dependency_overrides[deps.get_audit] = lambda: audit
    app.dependency_overrides[deps.get_auth] = lambda: auth
    app.dependency_overrides[deps.get_funeral_tracker] = lambda: funeral_tracker
    app.dependency_overrides[deps.get_grant_tracker] = lambda: grant_tracker
    app.dependency_overrides[deps.get_sunday_school_tracker] = lambda: sunday_school
    app.dependency_overrides[deps.get_payment_port] = lambda: payment
    return TestClient(app)
