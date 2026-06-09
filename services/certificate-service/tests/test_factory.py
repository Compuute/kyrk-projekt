import pytest

from app.adapters.factory import (
    make_audit,
    make_auth,
    make_certificate_repository,
    make_pdf_generator,
)
from app.adapters.fake_auth import FakeAuthAdapter
from app.adapters.in_memory_audit import InMemoryAuditAdapter
from app.adapters.in_memory_certificate_repository import InMemoryCertificateRepository
from app.adapters.stub_pdf_generator import StubPdfGenerator


@pytest.fixture(autouse=True)
def _clear_env(monkeypatch):
    for key in ("ADAPTER_MODE", "ZITADEL_ISSUER_URL", "ZITADEL_CLIENT_ID"):
        monkeypatch.delenv(key, raising=False)


def test_default_mode_is_memory():
    assert isinstance(make_certificate_repository(), InMemoryCertificateRepository)
    assert isinstance(make_audit(), InMemoryAuditAdapter)
    assert isinstance(make_auth(), FakeAuthAdapter)
    assert isinstance(make_pdf_generator(), StubPdfGenerator)


def test_production_repo_picks_firestore(monkeypatch):
    monkeypatch.setenv("ADAPTER_MODE", "production")
    assert type(make_certificate_repository()).__name__ == "FirestoreCertificateRepository"


def test_production_audit_picks_firestore(monkeypatch):
    monkeypatch.setenv("ADAPTER_MODE", "production")
    assert type(make_audit()).__name__ == "FirestoreAuditAdapter"


def test_production_auth_requires_env(monkeypatch):
    monkeypatch.setenv("ADAPTER_MODE", "production")
    with pytest.raises(RuntimeError, match="ZITADEL_ISSUER_URL"):
        make_auth()
    monkeypatch.setenv("ZITADEL_ISSUER_URL", "https://auth.example")
    with pytest.raises(RuntimeError, match="ZITADEL_CLIENT_ID"):
        make_auth()
    monkeypatch.setenv("ZITADEL_CLIENT_ID", "client")
    assert type(make_auth()).__name__ == "ZitadelAuthAdapter"


def test_production_pdf_generator_picks_html(monkeypatch):
    monkeypatch.setenv("ADAPTER_MODE", "production")
    gen = make_pdf_generator()
    assert type(gen).__name__ == "HtmlPdfGenerator"
