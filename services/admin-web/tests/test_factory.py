import pytest

from app.adapters.factory import (
    make_activity_client,
    make_certificate_client,
    make_intake_client,
    make_reporting_client,
    make_translator,
    make_funeral_tracker,
    make_grant_tracker,
    make_session_adapter,
)
from app.adapters.fake_clients import (
    FakeActivityClient,
    FakeCertificateClient,
    FakeIntakeClient,
    FakeReportingClient,
)
from app.adapters.fake_translator import FakeTranslator


@pytest.fixture(autouse=True)
def _clear_env(monkeypatch):
    for key in (
        "ADAPTER_MODE",
        "INTAKE_BASE_URL",
        "CERTIFICATE_BASE_URL",
        "REPORTING_BASE_URL",
        "ANTHROPIC_API_KEY",
        "MEMBERSHIP_BASE_URL",
        "ZITADEL_ISSUER_URL",
        "ZITADEL_CLIENT_ID",
    ):
        monkeypatch.delenv(key, raising=False)


def test_default_mode_is_memory():
    assert isinstance(make_intake_client(), FakeIntakeClient)
    assert isinstance(make_certificate_client(), FakeCertificateClient)
    assert isinstance(make_activity_client(), FakeActivityClient)
    assert isinstance(make_reporting_client(), FakeReportingClient)
    assert isinstance(make_translator(), FakeTranslator)


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


def test_production_translator_requires_api_key(monkeypatch):
    monkeypatch.setenv("ADAPTER_MODE", "production")
    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
        make_translator()
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key")
    translator = make_translator()
    assert type(translator).__name__ == "AnthropicTranslator"


def test_production_funeral_tracker_requires_base_url(monkeypatch):
    monkeypatch.setenv("ADAPTER_MODE", "production")
    with pytest.raises(RuntimeError, match="MEMBERSHIP_BASE_URL"):
        make_funeral_tracker()
    monkeypatch.setenv("MEMBERSHIP_BASE_URL", "https://membership.example")
    tracker = make_funeral_tracker()
    assert type(tracker).__name__ == "HttpxFuneralTracker"


def test_production_grant_tracker_picks_firestore(monkeypatch):
    monkeypatch.setenv("ADAPTER_MODE", "production")
    tracker = make_grant_tracker()
    assert type(tracker).__name__ == "FirestoreGrantTracker"


def test_production_session_requires_env(monkeypatch):
    monkeypatch.setenv("ADAPTER_MODE", "production")
    with pytest.raises(RuntimeError, match="ZITADEL_ISSUER_URL"):
        make_session_adapter()
    monkeypatch.setenv("ZITADEL_ISSUER_URL", "https://auth.example")
    with pytest.raises(RuntimeError, match="ZITADEL_CLIENT_ID"):
        make_session_adapter()
    monkeypatch.setenv("ZITADEL_CLIENT_ID", "client")
    with pytest.raises(RuntimeError, match="ZITADEL_CLIENT_SECRET"):
        make_session_adapter()
    monkeypatch.setenv("ZITADEL_CLIENT_SECRET", "secret")
    with pytest.raises(RuntimeError, match="ZITADEL_REDIRECT_URI"):
        make_session_adapter()
    monkeypatch.setenv("ZITADEL_REDIRECT_URI", "https://redirect.example")
    assert type(make_session_adapter()).__name__ == "JWTSessionAdapter"
