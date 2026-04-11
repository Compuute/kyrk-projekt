import pytest

from app.adapters.factory import make_activity_repository, make_auth
from app.adapters.fake_auth import FakeAuthAdapter
from app.adapters.in_memory_activity_repository import InMemoryActivityRepository


@pytest.fixture(autouse=True)
def _clear_env(monkeypatch):
    for key in ("ADAPTER_MODE", "PROPELAUTH_URL", "PROPELAUTH_API_KEY"):
        monkeypatch.delenv(key, raising=False)


def test_default_mode_is_memory():
    assert isinstance(make_activity_repository(), InMemoryActivityRepository)
    assert isinstance(make_auth(), FakeAuthAdapter)


def test_production_repo_picks_firestore(monkeypatch):
    monkeypatch.setenv("ADAPTER_MODE", "production")
    assert type(make_activity_repository()).__name__ == "FirestoreActivityRepository"


def test_production_auth_requires_env(monkeypatch):
    monkeypatch.setenv("ADAPTER_MODE", "production")
    with pytest.raises(RuntimeError, match="PROPELAUTH_URL"):
        make_auth()
    monkeypatch.setenv("PROPELAUTH_URL", "https://auth.example")
    with pytest.raises(RuntimeError, match="PROPELAUTH_API_KEY"):
        make_auth()
