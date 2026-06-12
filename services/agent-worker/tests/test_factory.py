import pytest

from app.adapters.factory import make_audit_log, make_reporting_client
from app.adapters.fake_reporting_client import FakeReportingClient
from app.adapters.in_memory_audit_log import InMemoryAuditLog


@pytest.fixture(autouse=True)
def _clear_env(monkeypatch):
    for key in (
        "ADAPTER_MODE",
        "REPORTING_SERVICE_URL",
        "ZITADEL_ISSUER_URL",
        "AGENT_CLIENT_ID",
        "AGENT_CLIENT_SECRET",
        "AGENT_TOKEN_SCOPE",
    ):
        monkeypatch.delenv(key, raising=False)


def test_default_mode_is_memory():
    assert isinstance(make_reporting_client(), FakeReportingClient)
    assert isinstance(make_audit_log(), InMemoryAuditLog)


def test_production_reporting_client_requires_env(monkeypatch):
    monkeypatch.setenv("ADAPTER_MODE", "production")
    with pytest.raises(RuntimeError, match="REPORTING_SERVICE_URL"):
        make_reporting_client()
    monkeypatch.setenv("REPORTING_SERVICE_URL", "https://reporting.example")
    with pytest.raises(RuntimeError, match="ZITADEL_ISSUER_URL"):
        make_reporting_client()
    monkeypatch.setenv("ZITADEL_ISSUER_URL", "https://auth.example")
    with pytest.raises(RuntimeError, match="AGENT_CLIENT_ID"):
        make_reporting_client()
    monkeypatch.setenv("AGENT_CLIENT_ID", "cid")
    with pytest.raises(RuntimeError, match="AGENT_CLIENT_SECRET"):
        make_reporting_client()
    monkeypatch.setenv("AGENT_CLIENT_SECRET", "hemlis")
    client = make_reporting_client()
    assert type(client).__name__ == "HttpxReportingClient"


def test_production_audit_log_is_firestore(monkeypatch):
    monkeypatch.setenv("ADAPTER_MODE", "production")
    audit = make_audit_log()
    assert type(audit).__name__ == "FirestoreAuditLog"
