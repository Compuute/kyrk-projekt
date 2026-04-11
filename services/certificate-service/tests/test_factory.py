import pytest

from app.adapters.factory import (
    make_audit,
    make_auth,
    make_certificate_repository,
)
from app.adapters.fake_auth import FakeAuthAdapter
from app.adapters.in_memory_audit import InMemoryAuditAdapter
from app.adapters.in_memory_certificate_repository import InMemoryCertificateRepository


@pytest.fixture(autouse=True)
def _clear_env(monkeypatch):
    for key in ("ADAPTER_MODE", "PROPELAUTH_URL", "PROPELAUTH_API_KEY"):
        monkeypatch.delenv(key, raising=False)


def test_default_mode_is_memory():
    assert isinstance(make_certificate_repository(), InMemoryCertificateRepository)
    assert isinstance(make_audit(), InMemoryAuditAdapter)
    assert isinstance(make_auth(), FakeAuthAdapter)


def test_production_repo_picks_firestore(monkeypatch):
    monkeypatch.setenv("ADAPTER_MODE", "production")
    assert type(make_certificate_repository()).__name__ == "FirestoreCertificateRepository"


def test_production_audit_picks_firestore(monkeypatch):
    monkeypatch.setenv("ADAPTER_MODE", "production")
    assert type(make_audit()).__name__ == "FirestoreAuditAdapter"


def test_production_auth_requires_env(monkeypatch):
    monkeypatch.setenv("ADAPTER_MODE", "production")
    with pytest.raises(RuntimeError, match="PROPELAUTH_URL"):
        make_auth()
    monkeypatch.setenv("PROPELAUTH_URL", "https://auth.example")
    with pytest.raises(RuntimeError, match="PROPELAUTH_API_KEY"):
        make_auth()
    monkeypatch.setenv("PROPELAUTH_API_KEY", "key")
    assert type(make_auth()).__name__ == "PropelAuthAdapter"
