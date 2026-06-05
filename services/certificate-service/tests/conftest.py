from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.adapters.fake_auth import FakeAuthAdapter
from app.adapters.in_memory_audit import InMemoryAuditAdapter
from app.adapters.in_memory_certificate_repository import InMemoryCertificateRepository
from app.adapters.stub_pdf_generator import StubPdfGenerator
from app.api import deps
from app.main import create_app
from app.ports.pdf_generator import PdfGeneratorPort
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
def pdf_generator() -> StubPdfGenerator:
    return StubPdfGenerator()


@pytest.fixture
def service(repo, audit) -> CertificateService:
    return CertificateService(repo=repo, audit=audit)


@pytest.fixture
def client(repo, audit, auth, pdf_generator) -> TestClient:
    app = create_app()
    app.dependency_overrides[deps.get_repo] = lambda: repo
    app.dependency_overrides[deps.get_audit] = lambda: audit
    app.dependency_overrides[deps.get_auth] = lambda: auth
    app.dependency_overrides[deps.get_pdf_generator] = lambda: pdf_generator
    return TestClient(app)
