import pytest

from app.adapters.factory import (
    make_activity_repository,
    make_auth,
    make_bigquery_export,
    make_report_repository,
)
from app.adapters.fake_auth import FakeAuthAdapter
from app.adapters.in_memory_activity_repository import InMemoryActivityRepository
from app.adapters.in_memory_report_repository import InMemoryReportRepository
from app.adapters.stub_bigquery_export import StubBigQueryExport


@pytest.fixture(autouse=True)
def _clear_env(monkeypatch):
    for key in (
        "ADAPTER_MODE",
        "PROPELAUTH_URL",
        "PROPELAUTH_API_KEY",
        "BIGQUERY_PROJECT_ID",
        "BIGQUERY_DATASET_ID",
    ):
        monkeypatch.delenv(key, raising=False)


def test_default_mode_is_memory():
    assert isinstance(make_report_repository(), InMemoryReportRepository)
    assert isinstance(make_activity_repository(), InMemoryActivityRepository)
    assert isinstance(make_bigquery_export(), StubBigQueryExport)
    assert isinstance(make_auth(), FakeAuthAdapter)


def test_production_repo_picks_firestore(monkeypatch):
    monkeypatch.setenv("ADAPTER_MODE", "production")
    assert type(make_report_repository()).__name__ == "FirestoreReportRepository"


def test_production_activity_repo_picks_firestore(monkeypatch):
    monkeypatch.setenv("ADAPTER_MODE", "production")
    assert type(make_activity_repository()).__name__ == "FirestoreActivityRepository"


def test_production_bigquery_requires_env(monkeypatch):
    monkeypatch.setenv("ADAPTER_MODE", "production")
    with pytest.raises(RuntimeError, match="BIGQUERY_PROJECT_ID"):
        make_bigquery_export()
    monkeypatch.setenv("BIGQUERY_PROJECT_ID", "my-project")
    with pytest.raises(RuntimeError, match="BIGQUERY_DATASET_ID"):
        make_bigquery_export()
    monkeypatch.setenv("BIGQUERY_DATASET_ID", "kyrk_analytics")
    bq = make_bigquery_export()
    assert type(bq).__name__ == "BigQueryExport"


def test_production_auth_requires_env(monkeypatch):
    monkeypatch.setenv("ADAPTER_MODE", "production")
    with pytest.raises(RuntimeError, match="PROPELAUTH_URL"):
        make_auth()
