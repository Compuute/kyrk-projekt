"""Adapter factory for reporting-service (activity + reporting).

YELLOW zone. Production wires Firestore for storage and BigQuery for
analytics export. Both are restricted to a single dataset/collection.
Activities use a separate `activities` Firestore collection.

Required env vars in production mode:
- PROPELAUTH_URL
- PROPELAUTH_API_KEY
- BIGQUERY_PROJECT_ID
- BIGQUERY_DATASET_ID  (e.g. kyrk_analytics)
"""
from __future__ import annotations

import os
import sys

from app.ports.activity_repository import ActivityRepository
from app.ports.auth import AuthPort
from app.ports.bigquery_export import BigQueryExportPort
from app.ports.report_repository import ReportRepository


def _mode() -> str:
    return os.getenv("ADAPTER_MODE", "memory").lower()


def make_activity_repository() -> ActivityRepository:
    if _mode() == "production":
        from app.adapters.firestore_activity_repository import (
            FirestoreActivityRepository,
        )

        return FirestoreActivityRepository()
    from app.adapters.in_memory_activity_repository import InMemoryActivityRepository

    return InMemoryActivityRepository()


def make_report_repository() -> ReportRepository:
    if _mode() == "production":
        from app.adapters.firestore_report_repository import FirestoreReportRepository

        return FirestoreReportRepository()
    from app.adapters.in_memory_report_repository import InMemoryReportRepository

    return InMemoryReportRepository()


def make_bigquery_export() -> BigQueryExportPort:
    if _mode() == "production":
        from app.adapters.bigquery_export import BigQueryExport

        project = _require_env("BIGQUERY_PROJECT_ID")
        dataset = _require_env("BIGQUERY_DATASET_ID")
        return BigQueryExport(project_id=project, dataset_id=dataset)
    from app.adapters.stub_bigquery_export import StubBigQueryExport

    return StubBigQueryExport()


def make_auth() -> AuthPort:
    if _mode() == "production":
        from app.adapters.propelauth_auth import PropelAuthAdapter

        url = _require_env("PROPELAUTH_URL")
        key = _require_env("PROPELAUTH_API_KEY")
        return PropelAuthAdapter(auth_url=url, api_key=key)
    from app.adapters.fake_auth import FakeAuthAdapter

    return FakeAuthAdapter()


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        sys.stderr.write(
            f"[reporting-service] ADAPTER_MODE=production but {name} is unset\n"
        )
        raise RuntimeError(f"missing required env var: {name}")
    return value
