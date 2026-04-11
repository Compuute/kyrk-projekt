from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.adapters.fake_auth import FakeAuthAdapter
from app.adapters.in_memory_audit import InMemoryAuditAdapter
from app.adapters.in_memory_certificate_repository import InMemoryCertificateRepository
from app.api import deps
from app.main import create_app
from app.services.certificate_service import CertificateService


@pytest.fixture
def repo() -> InMemoryCertificateRepository:
    return InMemoryCertificateRepository()


@pytest.fixture
def audit() -> InMemoryAuditAdapter:
    return InMemoryAuditAdapter()


@pytest.fixture
def auth() -> FakeAuthAdapter:
    return FakeAuthAdapter()


@pytest.fixture
def service(repo, audit) -> CertificateService:
    return CertificateService(repo=repo, audit=audit)


@pytest.fixture
def client(repo, audit, auth) -> TestClient:
    app = create_app()
    app.dependency_overrides[deps.get_repo] = lambda: repo
    app.dependency_overrides[deps.get_audit] = lambda: audit
    app.dependency_overrides[deps.get_auth] = lambda: auth
    return TestClient(app)
