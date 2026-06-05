import pytest

from app.adapters.factory import (
    make_activity_client,
    make_certificate_client,
    make_intake_client,
    make_reporting_client,
)
from app.adapters.fake_clients import (
    FakeActivityClient,
    FakeCertificateClient,
    FakeIntakeClient,
    FakeReportingClient,
)


@pytest.fixture(autouse=True)
def _clear_env(monkeypatch):
    for key in (
        "ADAPTER_MODE",
        "INTAKE_BASE_URL",
        "CERTIFICATE_BASE_URL",
        "REPORTING_BASE_URL",
    ):
        monkeypatch.delenv(key, raising=False)


def test_default_mode_is_memory():
    assert isinstance(make_intake_client(), FakeIntakeClient)
    assert isinstance(make_certificate_client(), FakeCertificateClient)
    assert isinstance(make_activity_client(), FakeActivityClient)
    assert isinstance(make_reporting_client(), FakeReportingClient)


def test_production_intake_requires_base_url(monkeypatch):
    monkeypatch.setenv("ADAPTER_MODE", "production")
    with pytest.raises(RuntimeError, match="INTAKE_BASE_URL"):
        make_intake_client()
    monkeypatch.setenv("INTAKE_BASE_URL", "https://intake.example")
    client = make_intake_client()
    assert type(client).__name__ == "HttpxIntakeClient"


def test_production_certificate_requires_base_url(monkeypatch):
    monkeypatch.setenv("ADAPTER_MODE", "production")
    with pytest.raises(RuntimeError, match="CERTIFICATE_BASE_URL"):
        make_certificate_client()
    monkeypatch.setenv("CERTIFICATE_BASE_URL", "https://certs.example")
    client = make_certificate_client()
    assert type(client).__name__ == "HttpxCertificateClient"


def test_production_activity_uses_reporting_base_url(monkeypatch):
    monkeypatch.setenv("ADAPTER_MODE", "production")
    # activity-service was merged into reporting-service; activity client
    # now reads REPORTING_BASE_URL instead of a separate ACTIVITY_BASE_URL.
    with pytest.raises(RuntimeError, match="REPORTING_BASE_URL"):
        make_activity_client()
    monkeypatch.setenv("REPORTING_BASE_URL", "https://reporting.example")
    client = make_activity_client()
    assert type(client).__name__ == "HttpxActivityClient"


def test_production_reporting_requires_base_url(monkeypatch):
    monkeypatch.setenv("ADAPTER_MODE", "production")
    with pytest.raises(RuntimeError, match="REPORTING_BASE_URL"):
        make_reporting_client()
    monkeypatch.setenv("REPORTING_BASE_URL", "https://reporting.example")
    client = make_reporting_client()
    assert type(client).__name__ == "HttpxReportingClient"
