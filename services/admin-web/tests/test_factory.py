import pytest

from app.adapters.factory import make_certificate_client, make_intake_client
from app.adapters.fake_clients import FakeCertificateClient, FakeIntakeClient


@pytest.fixture(autouse=True)
def _clear_env(monkeypatch):
    for key in ("ADAPTER_MODE", "INTAKE_BASE_URL", "CERTIFICATE_BASE_URL"):
        monkeypatch.delenv(key, raising=False)


def test_default_mode_is_memory():
    assert isinstance(make_intake_client(), FakeIntakeClient)
    assert isinstance(make_certificate_client(), FakeCertificateClient)


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
