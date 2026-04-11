"""Shared fixtures. Every test wires fresh in-memory adapters."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.adapters.fake_auth import FakeAuthAdapter
from app.adapters.in_memory_audit import InMemoryAuditAdapter
from app.adapters.in_memory_encryption import InMemoryEncryptionAdapter
from app.adapters.in_memory_member_repository import InMemoryMemberRepository
from app.api import deps
from app.main import create_app
from app.services.membership_service import MembershipService


@pytest.fixture
def repo() -> InMemoryMemberRepository:
    return InMemoryMemberRepository()


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
def client(repo, encryption, audit, auth) -> TestClient:
    app = create_app()
    app.dependency_overrides[deps.get_repo] = lambda: repo
    app.dependency_overrides[deps.get_encryption] = lambda: encryption
    app.dependency_overrides[deps.get_audit] = lambda: audit
    app.dependency_overrides[deps.get_auth] = lambda: auth
    return TestClient(app)
