from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.adapters.fake_reporting_client import FakeReportingClient
from app.adapters.in_memory_audit_log import InMemoryAuditLog
from app.api import deps
from app.main import create_app
from app.services.job_service import JobService


@pytest.fixture
def reporting() -> FakeReportingClient:
    return FakeReportingClient()


@pytest.fixture
def audit_log() -> InMemoryAuditLog:
    return InMemoryAuditLog()


@pytest.fixture
def client(reporting, audit_log) -> TestClient:
    app = create_app()
    app.dependency_overrides[deps.get_job_service] = lambda: JobService(
        reporting=reporting, audit=audit_log
    )
    return TestClient(app, raise_server_exceptions=False)
